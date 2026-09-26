import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .crawler import Crawler
from .db import Database
from .discovery import DuckDuckGoProvider
from .exporter import export_configs

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "config" / "sources.txt"
QUERIES = ROOT / "config" / "queries.txt"
DATA = ROOT / "data"
DB_PATH = DATA / "configs.db"


@dataclass(slots=True)
class PipelineStats:
    stage: str = "idle"
    queries: int = 0
    discovered_sources: int = 0
    crawled_sources: int = 0
    source_errors: int = 0
    configs_found: int = 0
    unique_configs: int = 0
    tested: int = 0
    reachable: int = 0
    unreachable: int = 0
    invalid: int = 0


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


class Pipeline:
    def __init__(self, callback: Callable[[PipelineStats, str], None] | None = None):
        self.callback = callback
        self.stats = PipelineStats()
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def emit(self, message: str = "") -> None:
        if self.callback:
            self.callback(self.stats, message)

    def run(self) -> PipelineStats:
        asyncio.run(self._run())
        return self.stats

    async def _run(self) -> None:
        self.stats.stage = "discovering"
        queries = read_lines(QUERIES)
        self.stats.queries = len(queries)
        self.emit(f"Discovering from {len(queries)} public search queries...")

        results = await DuckDuckGoProvider().search(
            queries,
            progress=lambda result: self._discovery_progress(result),
            should_stop=lambda: self._stop,
        )
        if self._stop:
            self.stats.stage = "stopped"
            self.emit("Scan stopped.")
            return

        sources = read_lines(SOURCES)
        seen = set(sources)
        for result in results:
            if result.error:
                self.stats.source_errors += 1
                continue
            for url in result.urls:
                if url not in seen:
                    seen.add(url)
                    sources.append(url)

        SOURCES.parent.mkdir(parents=True, exist_ok=True)
        SOURCES.write_text(
            "\n".join(sources) + ("\n" if sources else ""),
            encoding="utf-8",
        )
        self.stats.discovered_sources = len(sources)
        self.emit(f"Discovery complete: {len(sources)} source URLs.")

        self.stats.stage = "collecting"
        self.emit("Collecting configs with bounded recursive crawling...")
        db = Database(DB_PATH)
        try:
            crawler = Crawler(
                concurrency=16,
                timeout=20,
                max_bytes=5_000_000,
                max_depth=1,
                max_pages=400,
            )
            results = await crawler.crawl(
                sources,
                progress=lambda result: self._crawl_progress(result, db),
                should_stop=lambda: self._stop,
            )
            if self._stop:
                self.stats.stage = "stopped"
                self.emit("Scan stopped.")
                return

            configs = db.all()
            self.stats.unique_configs = len(configs)
            self.emit(f"Collection complete: {len(configs)} unique configurations.")

            self.stats.stage = "testing"
            self.emit("Testing advertised endpoints...")
            from .tester import EndpointTester

            results = await EndpointTester(
                concurrency=100,
                timeout=5.0,
            ).test_all(configs)
            for config, status, latency, error in results:
                db.update_test(config.link, status, latency, error)
                self.stats.tested += 1
                if status == "reachable":
                    self.stats.reachable += 1
                elif status == "unreachable":
                    self.stats.unreachable += 1
                else:
                    self.stats.invalid += 1
                if self.stats.tested % 25 == 0:
                    self.emit(f"Tested {self.stats.tested} endpoints...")
                if self._stop:
                    break

            configs = db.all()
            self.stats.stage = "exporting"
            export_configs(configs, DATA)
            self.stats.unique_configs = len(configs)
            self.emit(f"Export complete: {len(configs)} configurations.")
        finally:
            db.close()

        self.stats.stage = "completed"
        self.emit("Full scan completed.")

    def _discovery_progress(self, result) -> None:
        self.emit(f"Search: {result.query} -> {len(result.urls)} URLs")

    def _crawl_progress(self, result, db: Database) -> None:
        self.stats.crawled_sources += 1
        if result.error:
            self.stats.source_errors += 1
        else:
            self.stats.configs_found += len(result.links)
            for config in result.links:
                db.upsert(config)
        self.stats.unique_configs = len(db.all())
        if self.stats.crawled_sources % 10 == 0 or result.error:
            self.emit(
                f"Crawled {self.stats.crawled_sources} sources | "
                f"found {self.stats.configs_found} | unique {self.stats.unique_configs}"
            )
