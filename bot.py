"""Imlochi — yangi alifbo boti (aiogram 3), 1-bosqich (MVP).

Ishga tushirish:
    python bot.py            # WEBHOOK_URL bo'lmasa — polling, bo'lsa — webhook

Ikkala rejimda ham HOST:PORT da sayt ishlaydi (web.py). O'girish mantiqi
to'liq ``converter.py`` da; bu yerda faqat Telegram qatlami.
Foydalanuvchi matni hech qayerda saqlanmaydi va log'ga yozilmaydi.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from html import escape
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    BufferedInputFile,
    CallbackQuery,
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
    Message,
    TelegramObject,
)

from config import Config, load_config
from converter import convert as convert_text
from converter import detect, to_cyr, to_new, to_old
from storage import AdminReport, Storage, UI_SCRIPTS
from texts import JADVAL, MODE_LEGEND, mode_label, t
from tg_utils import COPY_BUTTON_LIMIT, FILE_THRESHOLD, RateLimiter, entity_spans, split_text
from web import auto_direction, share_url

log = logging.getLogger("alifbo")
router = Router(name="alifbo")


# --- O'girish ----------------------------------------------------------------

def resolve_direction(text: str, mode: str) -> str:
    """Rejimdan aniq yo'nalish: auto — yozuv aniqlanadi, aks holda rejimning o'zi."""
    return auto_direction(text) if mode == "auto" else mode


def reverse_direction(text: str, mode: str) -> str:
    """«Teskari» tugmasi: tanlangan yo'nalishning aksi (auto — natija yozuvidan)."""
    if mode == "auto":
        return "new_old" if detect(text) in ("new_latin", "latin") else auto_direction(text)
    src, dst = mode.split("_")
    return f"{dst}_{src}"


def convert(text: str, mode: str, *, protected=None, tutuq: str = "'") -> tuple[str, str]:
    """Foydalanuvchi rejimiga ko'ra o'giradi. Natija: (matn, yo'nalish)."""
    direction = resolve_direction(text, mode)
    return convert_text(text, direction, protected=protected, tutuq=tutuq), direction


def result_keyboard(chunk: str, ui: str) -> InlineKeyboardMarkup:
    """F1.10: javob ostidagi tugmalar. Tugmalar xabar matnining o'zi bilan
    ishlaydi, shuning uchun natijani serverda saqlash shart emas."""
    if len(chunk) <= COPY_BUTTON_LIMIT:
        copy = InlineKeyboardButton(text=t("btn_copy", ui), copy_text=CopyTextButton(text=chunk))
    else:
        copy = InlineKeyboardButton(text=t("btn_copy", ui), callback_data="copy")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [copy, InlineKeyboardButton(text=t("btn_reverse", ui), callback_data="rev")],
            [InlineKeyboardButton(text=t("btn_report", ui), callback_data="err")],
        ]
    )


async def send_result(message: Message, result: str, ui: str) -> None:
    """F1.7: uzun natija bo'lib yuboriladi, 10 000 belgidan uzuni — fayl."""
    if len(result) > FILE_THRESHOLD:
        await message.answer_document(
            BufferedInputFile(result.encode("utf-8"), filename="imlochi.txt"),
            caption=t("file_caption", ui, length=len(result)),
        )
        return
    for chunk in split_text(result):
        await message.answer(chunk, parse_mode=None, reply_markup=result_keyboard(chunk, ui))


# --- Klaviaturalar -----------------------------------------------------------

# Rejim menyusi: har qatorda bitta manba yozuvidan ikki yo'nalish.
MODE_ROWS = (("cyr_new", "cyr_old"), ("old_new", "old_cyr"), ("new_old", "new_cyr"))


def mode_keyboard(current: str, ui: str) -> InlineKeyboardMarkup:
    def button(mode: str) -> InlineKeyboardButton:
        mark = "✅ " if mode == current else ""
        return InlineKeyboardButton(text=mark + mode_label(mode), callback_data=f"mode:{mode}")

    rows = [[button(a), button(b)] for a, b in MODE_ROWS]
    rows.append([button("auto"), InlineKeyboardButton(text=t("btn_about", ui), callback_data="about")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def share_keyboard(bot_username: str, config: Config, ui: str) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton(text=t("btn_share", ui), url=share_url(bot_username, t("share_text")))]
    if config.site_url:
        row.append(InlineKeyboardButton(text=t("btn_site", ui), url=config.site_url))
    return InlineKeyboardMarkup(inline_keyboard=[row])


def _ui_keyboard(ui: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(f"ui_{u}", ui), callback_data=f"ui:{u}")] for u in UI_SCRIPTS]
    )


def main_menu(bot_username: str, config: Config, ui: str) -> InlineKeyboardMarkup:
    """/start ostidagi asosiy menyu: buyruqlarning tugma ko'rinishi."""
    def cb(key: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=t(f"btn_{key}", ui), callback_data=f"menu:{key}")

    rows = [[cb("jadval"), cb("rejim")], [cb("til"), cb("help")]]
    rows.extend(share_keyboard(bot_username, config, ui).inline_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Buyruqlar (F1.5, F1.6) --------------------------------------------------
# Har bir bo'lim ham buyruq (/jadval), ham /start menyusidagi tugma (menu:jadval)
# orqali ochiladi; ikkalasi bir xil funksiyani chaqiradi.

async def show_start(target: Message, user_id: int, bot: Bot, db: Storage, config: Config) -> None:
    ui = db.get_settings(user_id).ui
    me = await bot.me()
    db.track("start", user_id)
    await target.answer(t("start", ui, username=me.username), reply_markup=main_menu(me.username, config, ui))


async def show_help(target: Message, user_id: int, bot: Bot, db: Storage, config: Config) -> None:
    ui = db.get_settings(user_id).ui
    me = await bot.me()
    db.track("help", user_id)
    await target.answer(t("help", ui, username=me.username), reply_markup=share_keyboard(me.username, config, ui))


async def show_jadval(target: Message, user_id: int, bot: Bot, db: Storage, config: Config) -> None:
    db.track("jadval", user_id)
    await target.answer(JADVAL)


async def show_rejim(target: Message, user_id: int, bot: Bot, db: Storage, config: Config) -> None:
    s = db.get_settings(user_id)
    await target.answer(
        t("rejim", s.ui, current=mode_label(s.mode)) + MODE_LEGEND,
        reply_markup=mode_keyboard(s.mode, s.ui),
    )


async def show_til(target: Message, user_id: int, bot: Bot, db: Storage, config: Config) -> None:
    s = db.get_settings(user_id)
    await target.answer(t("til", s.ui, current=t(f"ui_{s.ui}", s.ui)), reply_markup=_ui_keyboard(s.ui))


async def show_share(target: Message, user_id: int, bot: Bot, db: Storage, config: Config) -> None:
    ui = db.get_settings(user_id).ui
    me = await bot.me()
    db.track("share_menu", user_id)
    await target.answer(t("about", ui), reply_markup=share_keyboard(me.username, config, ui))


SECTIONS = {
    "help": show_help,
    "jadval": show_jadval,
    "rejim": show_rejim,
    "til": show_til,
    "ulashish": show_share,
}


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, db: Storage, config: Config) -> None:
    await show_start(message, message.from_user.id, bot, db, config)


@router.message(Command(*SECTIONS))
async def cmd_section(message: Message, bot: Bot, db: Storage, config: Config) -> None:
    name = message.text.split()[0].lstrip("/").split("@")[0].lower()
    await SECTIONS[name](message, message.from_user.id, bot, db, config)


@router.callback_query(F.data.startswith("menu:"))
async def cb_menu(callback: CallbackQuery, bot: Bot, db: Storage, config: Config) -> None:
    show = SECTIONS.get(callback.data.split(":", 1)[1])
    await callback.answer()
    if show and callback.message:
        await show(callback.message, callback.from_user.id, bot, db, config)


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(callback: CallbackQuery, db: Storage) -> None:
    mode = callback.data.split(":", 1)[1]
    try:
        db.set_mode(callback.from_user.id, mode)
    except ValueError:
        await callback.answer()
        return
    ui = db.get_settings(callback.from_user.id).ui
    await callback.message.edit_text(
        t("rejim_set", ui, current=mode_label(mode)) + MODE_LEGEND,
        reply_markup=mode_keyboard(mode, ui),
    )
    await callback.answer(mode_label(mode))


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery, bot: Bot, db: Storage, config: Config) -> None:
    ui = db.get_settings(callback.from_user.id).ui
    me = await bot.me()
    db.track("about", callback.from_user.id)
    await callback.answer()
    await callback.message.answer(t("about", ui), reply_markup=share_keyboard(me.username, config, ui))


@router.callback_query(F.data.startswith("ui:"))
async def cb_ui(callback: CallbackQuery, db: Storage) -> None:
    ui = callback.data.split(":", 1)[1]
    try:
        db.set_ui(callback.from_user.id, ui)
    except ValueError:
        await callback.answer()
        return
    await callback.message.edit_text(t("til_set", ui, current=t(f"ui_{ui}", ui)))
    await callback.answer()


# --- Admin (F8.1) ------------------------------------------------------------

EVENT_LABELS = {
    "new_user": "Yangi foydalanuvchilar",
    "start": "/start",
    "convert": "Botda oʻgirish",
    "inline": "Inline rejim",
    "web_convert": "Saytda oʻgirish",
    "btn_reverse": "«Teskari» tugmasi",
    "btn_copy": "«Nusxa olish» (uzun)",
    "error_report": "Xato haqida xabar",
    "jadval": "/jadval",
    "help": "/help",
    "about": "Loyiha haqida",
    "share_menu": "/ulashish",
}


def _group_events(events: dict[str, int]) -> dict[str, int]:
    grouped: dict[str, int] = {}
    for name, value in events.items():
        key = "convert" if name.startswith("convert_") else name
        grouped[key] = grouped.get(key, 0) + value
    return grouped


def admin_text(rep: AdminReport, now: dt.datetime) -> str:
    peak = max((n for _, n in rep.daily_new), default=0) or 1
    chart = "\n".join(
        f"{day[5:]}  {'█' * round(n / peak * 12) or '·'} {n}" for day, n in rep.daily_new
    )
    today, week = _group_events(rep.events_today), _group_events(rep.events_week)
    order = [k for k in EVENT_LABELS if k in week] + sorted(k for k in week if k not in EVENT_LABELS)
    events = "\n".join(
        f"{escape(EVENT_LABELS.get(k, k))}: <b>{today.get(k, 0)}</b> / {week[k]}" for k in order
    ) or "—"
    return (
        "📊 <b>Imlochi — statistika</b>\n"
        f"<i>{now:%Y-%m-%d %H:%M}</i>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{rep.total}</b>\n"
        f"➕ Yangi: bugun <b>{rep.new_today}</b> · 7 kun <b>{rep.new_week}</b> · 30 kun <b>{rep.new_month}</b>\n"
        f"🔥 Faol: bugun <b>{rep.active_today}</b> · 7 kun <b>{rep.active_week}</b>\n\n"
        f"📈 <b>Yangi qoʻshilganlar, 7 kun</b>\n<pre>{chart}</pre>\n\n"
        f"📨 <b>Soʻrovlar</b> (bugun / 7 kun)\n{events}"
    )


ADMIN_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm:refresh")]]
)


@router.message(Command("admin", "stats"))
async def cmd_admin(message: Message, db: Storage, config: Config) -> None:
    uid = message.from_user.id
    if not config.admin_ids:
        await message.answer(
            "Admin hali sozlanmagan.\n\n"
            f"Sizning Telegram ID: <code>{uid}</code>\n"
            "Uni <code>.env</code> faylidagi <code>ADMIN_IDS</code> ga yozing va botni qayta ishga tushiring."
        )
        return
    if uid not in config.admin_ids:
        await message.answer(t("no_access"))
        return
    await message.answer(admin_text(db.admin_report(), dt.datetime.now()), reply_markup=ADMIN_KEYBOARD)


@router.callback_query(F.data == "adm:refresh")
async def cb_admin_refresh(callback: CallbackQuery, db: Storage, config: Config) -> None:
    if callback.from_user.id not in config.admin_ids:
        await callback.answer(t("no_access"), show_alert=True)
        return
    text = admin_text(db.admin_report(), dt.datetime.now())
    if callback.message and callback.message.html_text != text:
        await callback.message.edit_text(text, reply_markup=ADMIN_KEYBOARD)
    await callback.answer("Yangilandi")


# --- Natija tugmalari (F1.10) ------------------------------------------------

@router.callback_query(F.data == "copy")
async def cb_copy(callback: CallbackQuery, db: Storage) -> None:
    text = callback.message.text if callback.message else None
    ui = db.get_settings(callback.from_user.id).ui
    db.track("btn_copy", callback.from_user.id)
    await callback.answer()
    if text:
        # <pre> blokini bir bosishda nusxalash mumkin.
        await callback.message.answer(f"{t('copy_hint', ui)}\n<pre>{escape(text)}</pre>")


@router.callback_query(F.data == "rev")
async def cb_reverse(callback: CallbackQuery, db: Storage, config: Config) -> None:
    text = callback.message.text if callback.message else None
    s = db.get_settings(callback.from_user.id)
    await callback.answer()
    if not text:
        return
    result = convert_text(text, reverse_direction(text, s.mode), tutuq=config.tutuq)
    db.track("btn_reverse", callback.from_user.id)
    if result == text:
        await callback.message.answer(t("unchanged", s.ui))
        return
    await send_result(callback.message, result, s.ui)


@router.callback_query(F.data == "err")
async def cb_report(callback: CallbackQuery, db: Storage) -> None:
    # MVP: faqat hisoblagich. Xato bo'lakni ruxsat bilan saqlash — F8.4 (2-bosqich).
    ui = db.get_settings(callback.from_user.id).ui
    db.track("error_report", callback.from_user.id)
    await callback.answer(t("report_thanks", ui), show_alert=True)


# --- Matn (F1.1, F1.2, F1.7, F1.8) -------------------------------------------

@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def on_text(message: Message, db: Storage, config: Config) -> None:
    s = db.get_settings(message.from_user.id)
    spans = entity_spans(message.text, message.entities)
    result, direction = convert(message.text, s.mode, protected=spans, tutuq=config.tutuq)
    db.track(f"convert_{direction}", message.from_user.id)
    if result == message.text:
        await message.answer(t("unchanged", s.ui))
        return
    await send_result(message, result, s.ui)


@router.message(F.chat.type == "private")
async def on_other(message: Message, db: Storage) -> None:
    # Rasm, ovoz va fayllar — 2-bosqich (M2).
    ui = db.get_settings(message.from_user.id).ui if message.from_user else "old"
    await message.answer(t("unsupported", ui))


# --- Inline rejim (F1.4) -----------------------------------------------------

@router.inline_query()
async def on_inline(query: InlineQuery, db: Storage, config: Config) -> None:
    text = query.query.strip()
    ui = db.get_settings(query.from_user.id).ui
    if not text:
        await query.answer(
            [], cache_time=60, is_personal=True,
            button=InlineQueryResultsButton(text=t("inline_help", ui), start_parameter="inline"),
        )
        return
    new = to_new(text, tutuq=config.tutuq)
    variants = (
        ("new", new),
        ("old", to_old(new, tutuq=config.tutuq)),
        ("cyr", to_cyr(new, tutuq=config.tutuq, source="new")),
    )
    db.track("inline", query.from_user.id)
    results = [
        InlineQueryResultArticle(
            id=f"{key}:{abs(hash(value)) % 10**12}",
            title=t(f"inline_{key}", ui),
            description=value[:200],
            input_message_content=InputTextMessageContent(message_text=value, parse_mode=None),
        )
        for key, value in variants
    ]
    await query.answer(results, cache_time=5, is_personal=True)


# --- Middleware --------------------------------------------------------------

class UserTrackerMiddleware(BaseMiddleware):
    """Har bir foydalanuvchini qayd etadi: nechta odam qo'shilgani va faolligi."""

    def __init__(self, db: Storage):
        self.db = db

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is not None and not user.is_bot and self.db.touch_user(user.id):
            self.db.track("new_user")
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Spamga qarshi limit (TZ, 6-bo'lim): bepul tarifda 30 so'rov/daqiqa."""

    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter
        self._warned: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or self.limiter.allow(user.id):
            return await handler(event, data)
        # Ogohlantirish oynada bir marta — aks holda spamga spam bilan javob beramiz.
        now = asyncio.get_running_loop().time()
        if now - self._warned.get(user.id, -1e9) < self.limiter.window:
            if isinstance(event, CallbackQuery):
                await event.answer()
            elif isinstance(event, InlineQuery):
                await event.answer([], cache_time=5, is_personal=True)
            return None
        if len(self._warned) > 50_000:
            self._warned.clear()
        self._warned[user.id] = now
        if isinstance(event, CallbackQuery):
            await event.answer(t("too_many"), show_alert=True)
        elif isinstance(event, InlineQuery):
            await event.answer([], cache_time=5, is_personal=True)
        elif isinstance(event, Message) and event.chat.type == "private":
            await event.answer(t("too_many"))
        return None


# --- Ishga tushirish ---------------------------------------------------------

COMMANDS = [
    BotCommand(command="start", description="Boshlash"),
    BotCommand(command="rejim", description="Oʻgirish yoʻnalishi"),
    BotCommand(command="jadval", description="Oʻzgargan harflar jadvali"),
    BotCommand(command="ulashish", description="Doʻstlarga ulashish"),
    BotCommand(command="til", description="Interfeys yozuvi"),
    BotCommand(command="help", description="Yordam"),
]


def build_dispatcher(config: Config, db: Storage) -> Dispatcher:
    dp = Dispatcher()
    dp["db"] = db
    dp["config"] = config
    dp.update.outer_middleware(UserTrackerMiddleware(db))
    limiter = RateLimitMiddleware(RateLimiter(config.rate_limit))
    for observer in (router.message, router.callback_query, router.inline_query):
        observer.middleware(limiter)
    dp.include_router(router)
    return dp


async def _on_startup(bot: Bot, dispatcher: Dispatcher, config: Config) -> None:
    await bot.set_my_commands(COMMANDS)
    if config.webhook_url:
        await bot.set_webhook(
            config.webhook_url + config.webhook_path,
            secret_token=config.webhook_secret or None,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        log.info("Webhook o'rnatildi")


async def run(config: Config, storage: Storage) -> None:
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    from web import create_web_app

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(config, storage)
    dp.startup.register(_on_startup)
    me = await bot.me()

    runner = None
    if config.webhook_url or config.web_enabled:
        app = create_web_app(storage, config, me.username)
        if config.webhook_url:
            SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=config.webhook_secret or None).register(
                app, path=config.webhook_path
            )
            setup_application(app, dp, bot=bot)
        runner = web.AppRunner(app, access_log=None)   # IP va so'rovlar log'ga yozilmaydi
        await runner.setup()
        await web.TCPSite(runner, config.host, config.port).start()
        log.info("Sayt: http://%s:%s", config.host, config.port)

    try:
        if config.webhook_url:
            await asyncio.Event().wait()
        else:
            await bot.delete_webhook(drop_pending_updates=False)
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if runner is not None:
            await runner.cleanup()
        await bot.session.close()


def main() -> None:
    # Faqat xizmat ma'lumotlari log'ga yoziladi; xabar matni yozilmaydi.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    storage = Storage(config.db_path, salt=config.stats_salt)
    try:
        asyncio.run(run(config, storage))
    except KeyboardInterrupt:
        pass
    finally:
        storage.close()


if __name__ == "__main__":
    main()
