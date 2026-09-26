from .models import Config


def quality_score(config: Config) -> float:
    if config.tcp_status != "reachable":
        return 0.0
    if config.latency_ms is None:
        return 50.0

    latency = config.latency_ms
    if latency <= 50:
        return 100.0
    if latency <= 100:
        return 90.0
    if latency <= 200:
        return 80.0
    if latency <= 400:
        return 65.0
    if latency <= 800:
        return 45.0
    return 25.0


def rank_configs(configs: list[Config]) -> list[tuple[Config, float]]:
    ranked = [(config, quality_score(config)) for config in configs]
    ranked.sort(
        key=lambda item: (
            item[1],
            -(item[0].latency_ms if item[0].latency_ms is not None else float("inf")),
        ),
        reverse=True,
    )
    return ranked
