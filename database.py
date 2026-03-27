"""
database.py — Gestión de la base de datos SQLite.

Tablas:
  - subscribers       : chat_ids de Telegram suscritos al bot
  - seen_articles     : artículos descargados (cache global con contenido completo)
  - user_sent_articles: artículos ya enviados a cada usuario (tracking individual)
  - user_keywords     : keywords personalizadas por usuario
  - user_sources      : fuentes habilitadas/deshabilitadas por usuario
  - user_settings     : configuración del usuario (intervalo, última consulta)
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

                -- Cache global: artículos descargados con contenido completo.
                -- seen_at impide re-descargar; el contenido se usa para envíos futuros.
                CREATE TABLE IF NOT EXISTS seen_articles (
                    url         TEXT PRIMARY KEY,
                    title       TEXT,
                    source      TEXT,
                    description TEXT,
                    body        TEXT,
                    author      TEXT,
                    published   TEXT,
                    seen_at     TEXT NOT NULL
                );

                -- Tracking individual: qué artículo ya recibió cada usuario.
                CREATE TABLE IF NOT EXISTS user_sent_articles (
                    chat_id INTEGER NOT NULL,
                    url     TEXT    NOT NULL,
                    sent_at TEXT    NOT NULL,
                    PRIMARY KEY (chat_id, url)
                );

                -- Keywords personalizadas por usuario.
                -- Si está vacía para un usuario, se usan las globales de config.py.
                CREATE TABLE IF NOT EXISTS user_keywords (
                    chat_id INTEGER NOT NULL,
                    keyword TEXT    NOT NULL,
                    PRIMARY KEY (chat_id, keyword)
                );

                -- Fuentes habilitadas/deshabilitadas por usuario.
                -- Si está vacía para un usuario, se usan todas las globales.
                CREATE TABLE IF NOT EXISTS user_sources (
                    chat_id     INTEGER NOT NULL,
                    source_name TEXT    NOT NULL,
                    enabled     INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (chat_id, source_name)
                );

                -- Configuración extra por usuario.
                CREATE TABLE IF NOT EXISTS user_settings (
                    chat_id                INTEGER PRIMARY KEY,
                    check_interval_minutes INTEGER,
                    last_checked           TEXT
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

    # ── Artículos (cache global) ───────────────────────────────────────────────

    def is_seen(self, url: str) -> bool:
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT 1 FROM seen_articles WHERE url = ?", (url,)
            ).fetchone() is not None

    def mark_seen(self, article: dict):
        """Guarda el artículo completo en el cache global."""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO seen_articles
                   (url, title, source, description, body, author, published, seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    article["url"],
                    article.get("title", ""),
                    article.get("source", ""),
                    article.get("description", ""),
                    article.get("body", ""),
                    article.get("author", ""),
                    article.get("published", ""),
                    datetime.utcnow().isoformat(),
                )
            )

    def get_unsent_for_user(self, chat_id: int, since_hours: int = 48) -> list[dict]:
        """
        Retorna artículos del cache global (últimas since_hours horas)
        que todavía NO fueron enviados a este usuario.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT url, title, source, description, body, author, published
                   FROM seen_articles
                   WHERE seen_at >= datetime('now', ?)
                     AND url NOT IN (
                         SELECT url FROM user_sent_articles WHERE chat_id = ?
                     )
                   ORDER BY seen_at ASC""",
                (f"-{since_hours} hours", chat_id)
            ).fetchall()
            return [dict(row) for row in rows]

    def mark_sent_to_user(self, chat_id: int, url: str):
        """Registra que este artículo ya fue enviado al usuario."""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO user_sent_articles (chat_id, url, sent_at) VALUES (?, ?, ?)",
                (chat_id, url, datetime.utcnow().isoformat())
            )

    def cleanup_old_articles(self, days: int = 3):
        """Borra artículos del cache más antiguos que N días."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM seen_articles WHERE seen_at < datetime('now', ?)",
                (f"-{days} days",)
            )
            conn.execute(
                "DELETE FROM user_sent_articles WHERE sent_at < datetime('now', ?)",
                (f"-{days} days",)
            )

    # ── Keywords por usuario ──────────────────────────────────────────────────

    def get_user_keywords(self, chat_id: int) -> list[str]:
        """Lista vacía = el usuario no configuró las suyas, usar globales."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT keyword FROM user_keywords WHERE chat_id = ? ORDER BY keyword",
                (chat_id,)
            ).fetchall()
            return [row["keyword"] for row in rows]

    def add_user_keyword(self, chat_id: int, keyword: str) -> bool:
        """Agrega una keyword. Retorna True si era nueva."""
        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO user_keywords (chat_id, keyword) VALUES (?, ?)",
                    (chat_id, keyword.strip())
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_user_keyword(self, chat_id: int, keyword: str) -> bool:
        """Elimina una keyword (case-insensitive). Retorna True si existía."""
        with self._get_conn() as conn:
            result = conn.execute(
                "DELETE FROM user_keywords WHERE chat_id = ? AND LOWER(keyword) = LOWER(?)",
                (chat_id, keyword.strip())
            )
            return result.rowcount > 0

    def reset_user_keywords(self, chat_id: int):
        """Borra todas las keywords del usuario (vuelve a las globales)."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM user_keywords WHERE chat_id = ?", (chat_id,))

    # ── Fuentes por usuario ───────────────────────────────────────────────────

    def get_user_sources(self, chat_id: int) -> dict[str, bool]:
        """Retorna {source_name: enabled}. Vacío = nunca configuró, usar todas."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT source_name, enabled FROM user_sources WHERE chat_id = ? ORDER BY source_name",
                (chat_id,)
            ).fetchall()
            return {row["source_name"]: bool(row["enabled"]) for row in rows}

    def init_user_sources(self, chat_id: int, all_sources: list[str]):
        """Inicializa la lista de fuentes del usuario con todas activas."""
        with self._get_conn() as conn:
            for source in all_sources:
                conn.execute(
                    "INSERT OR IGNORE INTO user_sources (chat_id, source_name, enabled) VALUES (?, ?, 1)",
                    (chat_id, source)
                )

    def set_user_source_enabled(self, chat_id: int, source_name: str, enabled: bool):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE user_sources SET enabled = ? WHERE chat_id = ? AND source_name = ?",
                (1 if enabled else 0, chat_id, source_name)
            )

    def reset_user_sources(self, chat_id: int):
        """Borra config de fuentes del usuario (vuelve a usar todas las globales)."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM user_sources WHERE chat_id = ?", (chat_id,))

    # ── Configuración del usuario ─────────────────────────────────────────────

    def get_user_interval(self, chat_id: int) -> int | None:
        """Retorna intervalo en minutos, o None si usa el global."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT check_interval_minutes FROM user_settings WHERE chat_id = ?",
                (chat_id,)
            ).fetchone()
            return row["check_interval_minutes"] if row else None

    def set_user_interval(self, chat_id: int, minutes: int):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO user_settings (chat_id, check_interval_minutes)
                   VALUES (?, ?)
                   ON CONFLICT(chat_id) DO UPDATE SET check_interval_minutes = excluded.check_interval_minutes""",
                (chat_id, minutes)
            )

    def get_last_checked(self, chat_id: int) -> str | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT last_checked FROM user_settings WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            return row["last_checked"] if row else None

    def update_last_checked(self, chat_id: int):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO user_settings (chat_id, last_checked)
                   VALUES (?, ?)
                   ON CONFLICT(chat_id) DO UPDATE SET last_checked = excluded.last_checked""",
                (chat_id, datetime.utcnow().isoformat())
            )
