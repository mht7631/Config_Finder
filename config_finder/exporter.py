import json
from pathlib import Path

from .models import Config


def export_configs(configs: list[Config], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    all_links = [c.link for c in configs]
    reachable = [c.link for c in configs if c.tcp_status == "reachable"]
    unreachable = [c.link for c in configs if c.tcp_status == "unreachable"]

    for filename, links in (
        ("all.txt", all_links),
        ("reachable.txt", reachable),
        ("unreachable.txt", unreachable),
    ):
        (output_dir / filename).write_text(
            "\n".join(links) + ("\n" if links else ""),
            encoding="utf-8",
        )

    for scheme in ("vless", "vmess", "trojan", "ss", "shadowsocks"):
        links = [c.link for c in configs if c.scheme == scheme]
        (output_dir / f"{scheme}.txt").write_text(
            "\n".join(links) + ("\n" if links else ""),
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
