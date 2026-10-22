"""Sozlamalar, foydalanuvchilar va anonim statistika (F8.1).

Foydalanuvchi matni hech qachon saqlanmaydi. ``users`` jadvalida faqat
Telegram ID va qo'shilgan/oxirgi faollik sanasi turadi (botga nechta odam
qo'shilganini sanash va keyinchalik e'lon yuborish uchun — F8.3).

MVP uchun SQLite; 2-bosqichda PostgreSQL'ga o'tkaziladi (interfeys o'zgarmaydi).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
import threading
from dataclasses import dataclass

from converter import DIRECTIONS

MODES = ("auto",) + DIRECTIONS
UI_SCRIPTS = ("old", "new")

# Avvalgi versiyadagi rejim nomlari.
_LEGACY_MODES = {"new": "old_new", "old": "new_old"}


@dataclass(frozen=True)
class Settings:
    mode: str = "auto"   # auto — yozuv avtomatik aniqlanadi; aks holda DIRECTIONS dan biri
    ui: str = "old"      # interfeys yozuvi: eski lotin yoki yangi alifbo


@dataclass(frozen=True)
class AdminReport:
    total: int
    new_today: int
    new_week: int
    new_month: int
    active_today: int
    active_week: int
    daily_new: list[tuple[str, int]]       # oxirgi 7 kun: (sana, yangi foydalanuvchilar)
    events_today: dict[str, int]
    events_week: dict[str, int]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    mode    TEXT NOT NULL DEFAULT 'auto',
    ui      TEXT NOT NULL DEFAULT 'old'
);
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS users_first_seen ON users(first_seen);
CREATE INDEX IF NOT EXISTS users_last_seen ON users(last_seen);
CREATE TABLE IF NOT EXISTS stats (
    day   TEXT NOT NULL,
    event TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, event)
);
CREATE TABLE IF NOT EXISTS daily_users (
    day       TEXT NOT NULL,
    user_hash TEXT NOT NULL,
    PRIMARY KEY (day, user_hash)
);
"""


class Storage:
    def __init__(self, path: str = "alifbo.db", salt: str = "", today=None):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)
        self._lock = threading.Lock()
        self._salt = salt
        self._today = today or dt.date.today
        self._seen: dict[int, str] = {}   # user_id → bugun yozilgan sana (keraksiz yozuvlarni kamaytiradi)

    def close(self) -> None:
        self._db.close()

    # --- Sozlamalar ---

    def get_settings(self, user_id: int) -> Settings:
        row = self._db.execute(
            "SELECT mode, ui FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return Settings()
        mode = _LEGACY_MODES.get(row[0], row[0])
        return Settings(mode if mode in MODES else "auto", row[1] if row[1] in UI_SCRIPTS else "old")

    def set_mode(self, user_id: int, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(mode)
        self._upsert(user_id, "mode", mode)

    def set_ui(self, user_id: int, ui: str) -> None:
        if ui not in UI_SCRIPTS:
            raise ValueError(ui)
        self._upsert(user_id, "ui", ui)

    def _upsert(self, user_id: int, column: str, value: str) -> None:
        with self._lock, self._db:
            self._db.execute(
                f"INSERT INTO user_settings (user_id, {column}) VALUES (?, ?) "
                f"ON CONFLICT(user_id) DO UPDATE SET {column} = excluded.{column}",
                (user_id, value),
            )

    # --- Foydalanuvchilar ---

    def touch_user(self, user_id: int) -> bool:
        """Foydalanuvchi faolligini qayd etadi. Yangi qo'shilgan bo'lsa ``True``."""
        day = self._today().isoformat()
        if self._seen.get(user_id) == day:
            return False
        with self._lock, self._db:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO users (user_id, first_seen, last_seen) VALUES (?, ?, ?)",
                (user_id, day, day),
            )
            is_new = cur.rowcount == 1
            if not is_new:
                self._db.execute("UPDATE users SET last_seen = ? WHERE user_id = ?", (day, user_id))
        if len(self._seen) > 100_000:
            self._seen.clear()
        self._seen[user_id] = day
        return is_new

    def user_ids(self) -> list[int]:
        return [r[0] for r in self._db.execute("SELECT user_id FROM users ORDER BY first_seen")]

    # --- Statistika ---

    def _hash(self, user_id: int) -> str:
        return hashlib.sha256(f"{self._salt}:{user_id}".encode()).hexdigest()[:16]

    def track(self, event: str, user_id: int | None = None) -> None:
        day = self._today().isoformat()
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO stats (day, event, count) VALUES (?, ?, 1) "
                "ON CONFLICT(day, event) DO UPDATE SET count = count + 1",
                (day, event),
            )
            if user_id is not None:
                self._db.execute(
                    "INSERT OR IGNORE INTO daily_users (day, user_hash) VALUES (?, ?)",
                    (day, self._hash(user_id)),
                )

    def _since(self, days: int) -> str:
        return (self._today() - dt.timedelta(days=days - 1)).isoformat()

    def _events(self, days: int) -> dict[str, int]:
        return dict(
            self._db.execute(
                "SELECT event, SUM(count) FROM stats WHERE day >= ? GROUP BY event ORDER BY event",
                (self._since(days),),
            ).fetchall()
        )

    def report(self, days: int = 1) -> dict:
        """Oxirgi ``days`` kun (bugun ham) uchun ko'rsatkichlar."""
        since = self._since(days)
        users = self._db.execute(
            "SELECT COUNT(DISTINCT user_hash) FROM daily_users WHERE day >= ?", (since,)
        ).fetchone()[0]
        return {"since": since, "users": users, "events": self._events(days)}

    def admin_report(self) -> AdminReport:
        def count(sql: str, *args) -> int:
            return self._db.execute(sql, args).fetchone()[0]

        new_by_day = dict(
            self._db.execute(
                "SELECT first_seen, COUNT(*) FROM users WHERE first_seen >= ? GROUP BY first_seen",
                (self._since(7),),
            ).fetchall()
        )
        today = self._today()
        daily = [
            (d, new_by_day.get(d, 0))
            for d in ((today - dt.timedelta(days=i)).isoformat() for i in range(6, -1, -1))
        ]
        return AdminReport(
            total=count("SELECT COUNT(*) FROM users"),
            new_today=count("SELECT COUNT(*) FROM users WHERE first_seen >= ?", self._since(1)),
            new_week=count("SELECT COUNT(*) FROM users WHERE first_seen >= ?", self._since(7)),
            new_month=count("SELECT COUNT(*) FROM users WHERE first_seen >= ?", self._since(30)),
            active_today=count("SELECT COUNT(*) FROM users WHERE last_seen >= ?", self._since(1)),
            active_week=count("SELECT COUNT(*) FROM users WHERE last_seen >= ?", self._since(7)),
            daily_new=daily,
            events_today=self._events(1),
            events_week=self._events(7),
        )
