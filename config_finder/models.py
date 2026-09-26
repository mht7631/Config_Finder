from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

SUPPORTED_SCHEMES = ("vless", "vmess", "trojan", "ss", "shadowsocks")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Config:
    scheme: str
    link: str
    host: Optional[str] = None
    port: Optional[int] = None
    source: Optional[str] = None
    first_seen: str = ""
    last_seen: str = ""
    tcp_status: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        now = utc_now()
        if not self.first_seen:
            self.first_seen = now
        if not self.last_seen:
            self.last_seen = now
