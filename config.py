"""Sozlamalar muhit o'zgaruvchilaridan o'qiladi (TZ, 6-bo'lim: tokenlar kodda emas).

Mahalliy ishga tushirish uchun loyiha ildizidagi ``.env`` fayli ham o'qiladi
(muhitda allaqachon berilgan qiymatlar ustun turadi).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    bot_token: str
    webhook_url: str = ""          # bo'sh bo'lsa — polling rejimi
    webhook_path: str = "/webhook"
    webhook_secret: str = ""
    host: str = "0.0.0.0"
    port: int = 8080
    db_path: str = "alifbo.db"
    stats_salt: str = ""
    admin_ids: frozenset[int] = field(default_factory=frozenset)
    rate_limit: int = 30           # so'rov/daqiqa, bepul tarif
    tutuq: str = "'"
    site_url: str = ""             # saytning ommaviy manzili (bot tugmalarida ko'rsatiladi)
    web_enabled: bool = True       # polling rejimida ham saytni ishga tushirish
    web_rate_limit: int = 60       # sayt API: so'rov/daqiqa, IP bo'yicha


def load_config() -> Config:
    _load_dotenv(Path(__file__).with_name(".env"))
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        raise SystemExit("BOT_TOKEN muhit o'zgaruvchisi berilmagan (.env.example ga qarang).")
    admins = frozenset(
        int(x) for x in os.environ.get("ADMIN_IDS", "").replace(" ", "").split(",") if x
    )
    return Config(
        bot_token=token,
        webhook_url=os.environ.get("WEBHOOK_URL", "").rstrip("/"),
        webhook_path=os.environ.get("WEBHOOK_PATH", "/webhook"),
        webhook_secret=os.environ.get("WEBHOOK_SECRET", ""),
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        db_path=os.environ.get("DB_PATH", "alifbo.db"),
        stats_salt=os.environ.get("STATS_SALT", ""),
        admin_ids=admins,
        rate_limit=int(os.environ.get("RATE_LIMIT", "30")),
        tutuq=os.environ.get("TUTUQ", "'") or "'",
        site_url=os.environ.get("SITE_URL", "").rstrip("/"),
        web_enabled=os.environ.get("WEB_ENABLED", "1").lower() not in ("0", "false", "no"),
        web_rate_limit=int(os.environ.get("WEB_RATE_LIMIT", "60")),
    )
