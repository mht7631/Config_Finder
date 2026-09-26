import asyncio
from dataclasses import dataclass

import aiohttp
from bs4 import BeautifulSoup

from .extract import extract_links
from .models import Config
from .normalize import deduplicate, parse_config


@dataclass(slots=True)
class CrawlResult:
    source: str
    links: list[Config]
    error: str | None = None


class Crawler:
    def __init__(self, concurrency: int = 8, timeout: int = 20, max_bytes: int = 5_000_000):
        self.sem = asyncio.Semaphore(concurrency)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_bytes = max_bytes

    async def fetch(self, session: aiohttp.ClientSession, url: str) -> CrawlResult:
        async with self.sem:
            try:
                async with session.get(
                    url,
                    allow_redirects=True,
                    headers={"User-Agent": "Config-Finder/0.1 (+public-source-collector)"},
                ) as response:
                    response.raise_for_status()
                    body = await response.content.read(self.max_bytes)
                    text = body.decode(response.charset or "utf-8", errors="replace")

                    links = extract_links(text)
                    soup = BeautifulSoup(text, "html.parser")
                    for tag in soup.find_all(["a", "button", "code", "pre", "script"]):
                        for value in tag.attrs.values():
                            if isinstance(value, str):
                                links.extend(extract_links(value))
                        links.extend(extract_links(tag.get_text(" ", strip=False)))

                    configs = [
                        parse_config(link, str(response.url))
                        for link in dict.fromkeys(links)
                    ]
                    return CrawlResult(str(response.url), deduplicate(configs))
            except Exception as exc:
                return CrawlResult(url, [], f"{type(exc).__name__}: {exc}")

    async def crawl(self, urls: list[str]) -> list[CrawlResult]:
        connector = aiohttp.TCPConnector(limit=32, ssl=True)
        async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
            return await asyncio.gather(*(self.fetch(session, url) for url in urls))
