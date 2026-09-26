import asyncio
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import aiohttp
from bs4 import BeautifulSoup

from .extract import extract_links
from .models import Config
from .normalize import deduplicate, parse_config


@dataclass(slots=True)
class CrawlResult:
    source: str
    links: list[Config]
    discovered_urls: list[str]
    depth: int
    error: str | None = None


class Crawler:
    def __init__(
        self,
        concurrency: int = 16,
        timeout: int = 20,
        max_bytes: int = 5_000_000,
        max_depth: int = 1,
        max_pages: int = 400,
        max_links_per_page: int = 80,
    ):
        self.sem = asyncio.Semaphore(max(1, concurrency))
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_bytes = max_bytes
        self.max_depth = max(0, max_depth)
        self.max_pages = max(1, max_pages)
        self.max_links_per_page = max(1, max_links_per_page)
        self.visited: set[str] = set()
        self.visited_lock = asyncio.Lock()
        self.page_count = 0
        self.page_count_lock = asyncio.Lock()

    async def _claim_url(self, url: str) -> bool:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            return False
        async with self.visited_lock:
            if url in self.visited or self.page_count >= self.max_pages:
                return False
            self.visited.add(url)
            self.page_count += 1
            return True

    async def fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
        depth: int,
    ) -> CrawlResult:
        if not await self._claim_url(url):
            return CrawlResult(url, [], [], depth)

        async with self.sem:
            try:
                async with session.get(
                    url,
                    allow_redirects=True,
                    headers={"User-Agent": "Config-Finder/0.2 (+public-source-collector)"},
                ) as response:
                    response.raise_for_status()
                    body = await response.content.read(self.max_bytes)
                    text = body.decode(response.charset or "utf-8", errors="replace")

                    links = extract_links(text)
                    discovered: list[str] = []
                    soup = BeautifulSoup(text, "html.parser")

                    for tag in soup.find_all(["a", "button", "code", "pre", "script"]):
                        for value in tag.attrs.values():
                            if isinstance(value, str):
                                links.extend(extract_links(value))
                        links.extend(extract_links(tag.get_text(" ", strip=False)))

                    if depth < self.max_depth:
                        base = str(response.url)
                        root_host = urlsplit(base).netloc.lower()
                        for anchor in soup.find_all("a", href=True):
                            target = urljoin(base, anchor.get("href", ""))
                            parts = urlsplit(target)
                            if (
                                parts.scheme in ("http", "https")
                                and parts.netloc
                                and parts.netloc.lower() == root_host
                            ):
                                discovered.append(target.split("#", 1)[0])
                                if len(discovered) >= self.max_links_per_page:
                                    break

                    configs = [
                        parse_config(link, str(response.url))
                        for link in dict.fromkeys(links)
                    ]
                    return CrawlResult(
                        str(response.url),
                        deduplicate(configs),
                        list(dict.fromkeys(discovered)),
                        depth,
                    )
            except Exception as exc:
                return CrawlResult(url, [], [], depth, f"{type(exc).__name__}: {exc}")

    async def crawl(self, urls, progress=None, should_stop=None) -> list[CrawlResult]:
        self.visited.clear()
        self.page_count = 0
        connector = aiohttp.TCPConnector(limit=max(8, self.sem._value), ssl=True)
        async with aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector,
        ) as session:
            pending = [(url, 0) for url in urls]
            results: list[CrawlResult] = []
            while pending and self.page_count < self.max_pages:
                if should_stop and should_stop():
                    break
                batch = pending[: max(1, self.sem._value * 2)]
                pending = pending[len(batch):]
                batch_results = await asyncio.gather(
                    *(self.fetch(session, url, depth) for url, depth in batch)
                )
                for result in batch_results:
                    if result.source in self.visited and result.links or result.error:
                        results.append(result)
                    if progress:
                        progress(result)
                    if result.depth < self.max_depth:
                        pending.extend(
                            (url, result.depth + 1)
                            for url in result.discovered_urls
                            if url not in self.visited
                        )
            return results
