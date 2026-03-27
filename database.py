"""
database.py — Gestión de la base de datos SQLite.

Tablas:
  - subscribers  : chat_ids de Telegram suscritos al bot
  - seen_articles: URLs ya procesadas (evita duplicados)
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = "newsbot.db"


class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Crea las tablas si no existen."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    chat_id    INTEGER PRIMARY KEY,
                    username   TEXT,
                    joined_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS seen_articles (
                    url        TEXT PRIMARY KEY,
                    title      TEXT,
                    source     TEXT,
                    seen_at    TEXT NOT NULL
                );
            """)
        logger.info("Base de datos inicializada en %s", self.path)

    # ── Suscriptores ──────────────────────────────────────────────────────────

    def subscribe(self, chat_id: int, username: str = None) -> bool:
        """Registra un suscriptor. Retorna True si es nuevo."""
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT chat_id FROM subscribers WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO subscribers (chat_id, username, joined_at) VALUES (?, ?, ?)",
                (chat_id, username or "", datetime.utcnow().isoformat())
            )
            return True

    def unsubscribe(self, chat_id: int) -> bool:
        """Da de baja a un suscriptor. Retorna True si existía."""
        with self._get_conn() as conn:
            result = conn.execute(
                "DELETE FROM subscribers WHERE chat_id = ?", (chat_id,)
            )
            return result.rowcount > 0

    def get_subscribers(self) -> list[int]:
        """Retorna lista de chat_ids activos."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT chat_id FROM subscribers").fetchall()
            return [row["chat_id"] for row in rows]

    def subscriber_count(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]

    # ── Artículos vistos ──────────────────────────────────────────────────────

    def is_seen(self, url: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT url FROM seen_articles WHERE url = ?", (url,)
            ).fetchone()
            return row is not None

    def mark_seen(self, url: str, title: str = "", source: str = ""):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO seen_articles (url, title, source, seen_at)
                   VALUES (?, ?, ?, ?)""",
                (url, title, source, datetime.utcnow().isoformat())
            )

    def cleanup_old_articles(self, days: int = 15):
        """Borra artículos vistos hace más de N días para no inflar la DB."""
        with self._get_conn() as conn:
            conn.execute(
                """DELETE FROM seen_articles
                   WHERE seen_at < datetime('now', ?)""",
                (f"-{days} days",)
            )
