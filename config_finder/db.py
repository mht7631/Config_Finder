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
CREATE TABLE IF NOT EXISTS test_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER NOT NULL,
    tested_at TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms REAL,
    error TEXT,
    FOREIGN KEY(config_id) REFERENCES configs(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_configs_scheme ON configs(scheme);
CREATE INDEX IF NOT EXISTS idx_configs_host ON configs(host);
CREATE INDEX IF NOT EXISTS idx_configs_status ON configs(tcp_status);
CREATE INDEX IF NOT EXISTS idx_history_config ON test_history(config_id);
CREATE INDEX IF NOT EXISTS idx_history_tested_at ON test_history(tested_at);
"""


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
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

    def update_test(
        self,
        link: str,
        status: str,
        latency_ms: float | None,
        error: str | None,
        tested_at: str | None = None,
    ) -> None:
        from .models import utc_now

        timestamp = tested_at or utc_now()
        row = self.conn.execute(
            "SELECT id FROM configs WHERE link=?",
            (link,),
        ).fetchone()
        if not row:
            return

        config_id = row[0]
        self.conn.execute(
            "UPDATE configs SET tcp_status=?, latency_ms=?, error=? WHERE id=?",
            (status, latency_ms, error, config_id),
        )
        self.conn.execute(
            """
            INSERT INTO test_history
            (config_id, tested_at, status, latency_ms, error)
            VALUES (?, ?, ?, ?, ?)
            """,
            (config_id, timestamp, status, latency_ms, error),
        )
        self.conn.commit()

    def history_summary(self, link: str) -> dict[str, float | int | None]:
        row = self.conn.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(CASE WHEN status='reachable' THEN 1 ELSE 0 END), 0),
                AVG(CASE WHEN status='reachable' THEN latency_ms END),
                MIN(CASE WHEN status='reachable' THEN latency_ms END),
                MAX(CASE WHEN status='reachable' THEN latency_ms END)
            FROM test_history h
            JOIN configs c ON c.id = h.config_id
            WHERE c.link=?
            """,
            (link,),
        ).fetchone()
        total, successes, avg_latency, min_latency, max_latency = row
        return {
            "tests": int(total or 0),
            "successes": int(successes or 0),
            "success_rate": (successes / total * 100.0) if total else None,
            "avg_latency_ms": round(avg_latency, 2) if avg_latency is not None else None,
            "min_latency_ms": round(min_latency, 2) if min_latency is not None else None,
            "max_latency_ms": round(max_latency, 2) if max_latency is not None else None,
        }

    def history_summaries(self, links: list[str]) -> dict[str, dict]:
        if not links:
            return {}
        return {link: self.history_summary(link) for link in links}

    def all(self) -> list[Config]:
        rows = self.conn.execute(
            """SELECT scheme, link, host, port, source, first_seen, last_seen,
                      tcp_status, latency_ms, error
               FROM configs ORDER BY id"""
        ).fetchall()
        return [Config(*row) for row in rows]

    def close(self) -> None:
        self.conn.close()
