import asyncio
import time

from .models import Config


class EndpointTester:
    def __init__(self, concurrency: int = 100, timeout: float = 5.0):
        self.sem = asyncio.Semaphore(concurrency)
        self.timeout = timeout

    async def test_one(self, config: Config) -> tuple[Config, str, float | None, str | None]:
        if not config.host or not config.port:
            return config, "invalid", None, "missing host/port"

        writer = None
        async with self.sem:
            start = time.perf_counter()
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(config.host, config.port),
                    timeout=self.timeout,
                )
                latency = (time.perf_counter() - start) * 1000
                return config, "reachable", round(latency, 2), None
            except Exception as exc:
                return config, "unreachable", None, f"{type(exc).__name__}: {exc}"
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass

    async def test_all(self, configs: list[Config]) -> list[tuple[Config, str, float | None, str | None]]:
        return await asyncio.gather(*(self.test_one(config) for config in configs))
