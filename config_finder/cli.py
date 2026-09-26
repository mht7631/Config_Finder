import argparse
import asyncio
from pathlib import Path

from .crawler import Crawler
from .db import Database
from .discovery import DuckDuckGoProvider
from .exporter import export_configs

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "config" / "sources.txt"
QUERIES = ROOT / "config" / "queries.txt"
DATA = ROOT / "data"
DB_PATH = DATA / "configs.db"


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def command_discover() -> None:
    queries = read_lines(QUERIES)
    if not queries:
        print("No queries configured. Edit config/queries.txt")
        return

    results = asyncio.run(DuckDuckGoProvider().search(queries))
    sources = read_lines(SOURCES)
    seen = set(sources)

    for result in results:
        if result.error:
            print(f"[ERROR] search '{result.query}': {result.error}")
            continue
        print(f"[OK] search '{result.query}': {len(result.urls)} results")
        for url in result.urls:
            if url not in seen:
                seen.add(url)
                sources.append(url)

    SOURCES.parent.mkdir(parents=True, exist_ok=True)
    SOURCES.write_text("\n".join(sources) + ("\n" if sources else ""), encoding="utf-8")
    print(f"Configured source URLs: {len(sources)}")


def command_crawl() -> None:
    urls = read_lines(SOURCES)
    if not urls:
        print("No sources configured. Run discover or edit config/sources.txt")
        return

    results = asyncio.run(Crawler().crawl(urls))
    db = Database(DB_PATH)
    try:
        for result in results:
            if result.error:
                print(f"[ERROR] {result.source}: {result.error}")
                continue
            for config in result.links:
                db.upsert(config)
            print(f"[OK] {result.source}: {len(result.links)} configs")
        export_configs(db.all(), DATA)
        print(f"Database contains {len(db.all())} unique configs.")
    finally:
        db.close()


def command_test(limit: int | None) -> None:
    db = Database(DB_PATH)
    try:
        configs = db.all()
        if limit is not None:
            configs = configs[:limit]
        from .tester import EndpointTester
        results = asyncio.run(EndpointTester().test_all(configs))
        for config, status, latency, error in results:
            db.update_test(config.link, status, latency, error)
        export_configs(db.all(), DATA)
        print(f"Tested: {len(results)} endpoints")
    finally:
        db.close()


def command_export() -> None:
    db = Database(DB_PATH)
    try:
        configs = db.all()
        export_configs(configs, DATA)
        print(f"Exported: {len(configs)} configs")
    finally:
        db.close()


def command_stats() -> None:
    db = Database(DB_PATH)
    try:
        configs = db.all()
    finally:
        db.close()

    reachable = sum(c.tcp_status == "reachable" for c in configs)
    unreachable = sum(c.tcp_status == "unreachable" for c in configs)
    invalid = sum(c.tcp_status == "invalid" for c in configs)
    print(f"Total: {len(configs)}")
    print(f"TCP reachable: {reachable}")
    print(f"TCP unreachable: {unreachable}")
    print(f"Invalid endpoint: {invalid}")
    print(f"Untested: {len(configs) - reachable - unreachable - invalid}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="config-finder")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("discover")
    sub.add_parser("crawl")
    test = sub.add_parser("test")
    test.add_argument("--limit", type=int, default=None)
    sub.add_parser("stats")
    sub.add_parser("export")
    sub.add_parser("all")

    args = parser.parse_args()
    command = args.command or "all"

    if command == "discover":
        command_discover()
    elif command == "crawl":
        command_crawl()
    elif command == "test":
        command_test(args.limit)
    elif command == "stats":
        command_stats()
    elif command == "export":
        command_export()
    elif command == "all":
        command_discover()
        command_crawl()
        command_test(None)
        command_export()


if __name__ == "__main__":
    main()
