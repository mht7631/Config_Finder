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

    def __init__(self, timeout: int = 20):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def search_one(self, session: aiohttp.ClientSession, query: str) -> SearchResult:
        try:
            url = self.endpoint.format(query=quote_plus(query))
            async with session.get(
                url,
                headers={"User-Agent": "Config-Finder/0.1 (+public-search-discovery)"},
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

    async def search(self, queries: list[str]) -> list[SearchResult]:
        connector = aiohttp.TCPConnector(limit=4, ssl=True)
        async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
            results = []
            for query in queries:
                results.append(await self.search_one(session, query))
                await asyncio.sleep(1.0)
            return results
