"""Imlochi sayti: bosh sahifa, onlayn o'girgich va kichik JSON API.

Sayt ham bot bilan bir xil ``converter.py`` yadrosini ishlatadi, shuning uchun
o'girish qoidalari hamma kanalda bir xil. Matn saqlanmaydi va log'ga yozilmaydi.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from aiohttp import web

from config import Config
from converter import DIRECTIONS, convert, detect
from storage import Storage
from tg_utils import FILE_THRESHOLD, RateLimiter

WEB_DIR = Path(__file__).with_name("web")
MAX_TEXT = FILE_THRESHOLD


def auto_direction(text: str) -> str:
    """Avto rejim: kirill → yangi, yangi alifbo → eski lotin, qolgani → yangi."""
    kind = detect(text)
    if kind == "cyrillic":
        return "cyr_new"
    if kind == "new_latin":
        return "new_old"
    return "old_new"


def share_url(bot_username: str, text: str) -> str:
    return f"https://t.me/share/url?url={quote(f'https://t.me/{bot_username}')}&text={quote(text)}"


SHARE_TEXT = "Imlochi — yangi oʻzbek alifbosiga (Ö, Ğ, Ş, Ç) bir zumda oʻgiruvchi bot"


def _client_ip(request: web.Request) -> str:
    # Reverse proxy ortida haqiqiy IP X-Forwarded-For'da keladi.
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or (request.remote or "?")


def create_web_app(db: Storage, config: Config, bot_username: str) -> web.Application:
    app = web.Application(client_max_size=256 * 1024)
    limiter = RateLimiter(limit=config.web_rate_limit)
    index_html = (
        (WEB_DIR / "index.html")
        .read_text(encoding="utf-8")
        .replace("{{BOT_USERNAME}}", bot_username)
        .replace("{{SHARE_URL}}", share_url(bot_username, SHARE_TEXT).replace("&", "&amp;"))
        .replace("{{SITE_URL}}", config.site_url or "")
    )

    async def index(_request: web.Request) -> web.Response:
        return web.Response(text=index_html, content_type="text/html")

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    async def api_convert(request: web.Request) -> web.Response:
        if not limiter.allow(hash(_client_ip(request))):
            return web.json_response({"error": "too_many_requests"}, status=429)
        try:
            body = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return web.json_response({"error": "invalid_json"}, status=400)
        text = body.get("text") if isinstance(body, dict) else None
        direction = body.get("direction", "auto") if isinstance(body, dict) else None
        if not isinstance(text, str):
            return web.json_response({"error": "text_required"}, status=400)
        if len(text) > MAX_TEXT:
            return web.json_response({"error": "text_too_long", "max": MAX_TEXT}, status=413)
        if direction == "auto":
            direction = auto_direction(text)
        if direction not in DIRECTIONS:
            return web.json_response({"error": "bad_direction", "allowed": ["auto", *DIRECTIONS]}, status=400)
        result = convert(text, direction, tutuq=config.tutuq)
        db.track("web_convert")
        return web.json_response({"result": result, "direction": direction})

    async def api_stats(_request: web.Request) -> web.Response:
        # Saytda faqat umumiy son ko'rsatiladi.
        return web.json_response({"users": db.admin_report().total})

    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_post("/api/convert", api_convert)
    app.router.add_get("/api/stats", api_stats)
    app.router.add_static("/static/", WEB_DIR / "static", append_version=True)
    return app
