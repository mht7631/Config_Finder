import json
from pathlib import Path

from .models import Config
from .ranking import rank_configs

PROTOCOLS = ("vless", "vmess", "trojan", "ss", "shadowsocks")


def _write_lines(path: Path, links: list[str]) -> None:
    path.write_text(
        "\n".join(links) + ("\n" if links else ""),
        encoding="utf-8",
    )


def export_configs(configs: list[Config], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    reachable = [c for c in configs if c.tcp_status == "reachable"]
    unreachable = [c for c in configs if c.tcp_status == "unreachable"]

    _write_lines(output_dir / "all.txt", [c.link for c in configs])
    _write_lines(output_dir / "reachable.txt", [c.link for c in reachable])
    _write_lines(output_dir / "unreachable.txt", [c.link for c in unreachable])

    for scheme in PROTOCOLS:
        _write_lines(output_dir / f"{scheme}.txt", [c.link for c in configs if c.scheme == scheme])
        _write_lines(
            output_dir / f"{scheme}_reachable.txt",
            [c.link for c in reachable if c.scheme == scheme],
        )

    ranked = rank_configs(configs)
    top = [config.link for config, _score in ranked if config.tcp_status == "reachable"]
    _write_lines(output_dir / "top100.txt", top[:100])

    fastest = sorted(
        reachable,
        key=lambda c: c.latency_ms if c.latency_ms is not None else float("inf"),
    )
    _write_lines(output_dir / "fastest.txt", [c.link for c in fastest[:100]])

    records = [
        {
            "scheme": c.scheme,
            "link": c.link,
            "host": c.host,
            "port": c.port,
            "source": c.source,
            "first_seen": c.first_seen,
            "last_seen": c.last_seen,
            "tcp_status": c.tcp_status,
            "latency_ms": c.latency_ms,
            "error": c.error,
        }
        for c in configs
    ]
    (output_dir / "configs.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    summary = {
        "total": len(configs),
        "reachable": len(reachable),
        "unreachable": len(unreachable),
        "invalid": sum(c.tcp_status == "invalid" for c in configs),
        "untested": sum(c.tcp_status is None for c in configs),
        "schemes": {},
    }
    for config in configs:
        summary["schemes"][config.scheme] = summary["schemes"].get(config.scheme, 0) + 1

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
