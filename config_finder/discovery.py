import asyncio
from dataclasses import dataclass
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup


@dataclass(slots=True)
class SearchResult:
    query: str
    urls: list[str]
    error: str | None = None


class DuckDuckGoProvider:
    endpoint = "https://html.duckduckgo.com/html/?q={query}"

    def __init__(self, timeout: int = 20, concurrency: int = 3, delay: float = 0.8):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.concurrency = max(1, concurrency)
        self.delay = max(0.0, delay)

    async def search_one(self, session: aiohttp.ClientSession, query: str) -> SearchResult:
        try:
            url = self.endpoint.format(query=quote_plus(query))
            async with session.get(
                url,
                headers={"User-Agent": "Config-Finder/0.2 (+public-search-discovery)"},
            ) as response:
                response.raise_for_status()
                text = await response.text(errors="replace")

            soup = BeautifulSoup(text, "html.parser")
            urls: list[str] = []
            seen: set[str] = set()
            for anchor in soup.select(".result__a"):
                href = anchor.get("href")
                if href and href.startswith(("http://", "https://")) and href not in seen:
                    seen.add(href)
                    urls.append(href)
            return SearchResult(query, urls)
        except Exception as exc:
            return SearchResult(query, [], f"{type(exc).__name__}: {exc}")

    async def search(self, queries, progress=None, should_stop=None) -> list[SearchResult]:
        connector = aiohttp.TCPConnector(limit=self.concurrency, ssl=True)
        async with aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector,
        ) as session:
            results: list[SearchResult] = []
            for query in queries:
                if should_stop and should_stop():
                    break
                result = await self.search_one(session, query)
                results.append(result)
                if progress:
                    progress(result)
                if self.delay:
                    await asyncio.sleep(self.delay)
            return results
