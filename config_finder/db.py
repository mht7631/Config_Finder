import sqlite3
from pathlib import Path

from .models import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    host TEXT,
    port INTEGER,
    source TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    tcp_status TEXT,
    latency_ms REAL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_configs_scheme ON configs(scheme);
CREATE INDEX IF NOT EXISTS idx_configs_host ON configs(host);
CREATE INDEX IF NOT EXISTS idx_configs_status ON configs(tcp_status);
"""


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert(self, config: Config) -> None:
        self.conn.execute(
            """
            INSERT INTO configs
            (scheme, link, host, port, source, first_seen, last_seen, tcp_status, latency_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(link) DO UPDATE SET
              last_seen=excluded.last_seen,
              source=COALESCE(excluded.source, configs.source),
              host=COALESCE(excluded.host, configs.host),
              port=COALESCE(excluded.port, configs.port)
            """,
            (
                config.scheme, config.link, config.host, config.port, config.source,
                config.first_seen, config.last_seen, config.tcp_status,
                config.latency_ms, config.error,
            ),
        )
        self.conn.commit()

    def update_test(self, link: str, status: str, latency_ms: float | None, error: str | None) -> None:
        self.conn.execute(
            "UPDATE configs SET tcp_status=?, latency_ms=?, error=? WHERE link=?",
            (status, latency_ms, error, link),
        )
        self.conn.commit()

    def all(self) -> list[Config]:
        rows = self.conn.execute(
            """SELECT scheme, link, host, port, source, first_seen, last_seen,
                      tcp_status, latency_ms, error
               FROM configs ORDER BY id"""
        ).fetchall()
        return [Config(*row) for row in rows]

    def close(self) -> None:
        self.conn.close()
