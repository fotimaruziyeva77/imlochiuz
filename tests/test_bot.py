"""Bot handlerlarini haqiqiy aiogram Dispatcher orqali, lekin tarmoqsiz sinash.

FakeSession Telegram API o'rniga turadi va yuborilgan so'rovlarni yozib boradi.
"""

import datetime as dt
from itertools import count

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import (
    AnswerCallbackQuery,
    AnswerInlineQuery,
    GetMe,
    SendDocument,
    SendMessage,
)
from aiogram.types import CallbackQuery, Chat, InlineQuery, Message, MessageEntity, Update, User

from bot import admin_text, build_dispatcher, convert, reverse_direction
from config import Config
from storage import Storage

_ids = count(1)
USER = User(id=1001, is_bot=False, first_name="Ali")
CHAT = Chat(id=1001, type="private")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=42, is_bot=True, first_name="Alifbo", username="alifbo_bot")
        if isinstance(method, (SendMessage, SendDocument)):
            return Message(
                message_id=next(_ids), date=dt.datetime.now(), chat=CHAT,
                text=getattr(method, "text", None),
            )
        return True

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def sent(self, kind=SendMessage):
        return [c for c in self.calls if isinstance(c, kind)]


@pytest.fixture(scope="module")
def dp(tmp_path_factory):
    config = Config(bot_token="42:TEST", admin_ids=frozenset({1001}), rate_limit=1000)
    storage = Storage(str(tmp_path_factory.mktemp("db") / "bot.db"))
    yield build_dispatcher(config, storage)
    storage.close()


@pytest.fixture
def tg():
    session = FakeSession()
    return Bot("42:TEST", session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML)), session


def msg(text, entities=None):
    return Update(
        update_id=next(_ids),
        message=Message(
            message_id=next(_ids), date=dt.datetime.now(), chat=CHAT, from_user=USER,
            text=text, entities=entities,
        ),
    )


def callback(data, text):
    return Update(
        update_id=next(_ids),
        callback_query=CallbackQuery(
            id=str(next(_ids)), from_user=USER, chat_instance="ci", data=data,
            message=Message(message_id=next(_ids), date=dt.datetime.now(), chat=CHAT, text=text),
        ),
    )


async def feed(dp, tg, update):
    bot, session = tg
    session.calls.clear()
    await dp.feed_update(bot, update)
    return session


# --- convert(): rejimlar ----------------------------------------------------

@pytest.mark.parametrize(
    "text, mode, expected",
    [
        ("O'zbekiston", "auto", ("Özbekiston", "old_new")),
        ("Тошкент", "auto", ("Toşkent", "cyr_new")),
        ("Özbekiston", "auto", ("Oʻzbekiston", "new_old")),
        ("Özbekiston", "old_new", ("Özbekiston", "old_new")),
        ("Özbekiston", "new_old", ("Oʻzbekiston", "new_old")),
        ("Тошкент", "cyr_old", ("Toshkent", "cyr_old")),
        ("Toşkent", "new_cyr", ("Тошкент", "new_cyr")),
    ],
)
def test_convert_modes(text, mode, expected):
    assert convert(text, mode) == expected


@pytest.mark.parametrize(
    "text, mode, expected",
    [
        ("Toşkent", "auto", "new_old"),
        ("Тошкент", "auto", "cyr_new"),
        ("Toşkent", "cyr_new", "new_cyr"),
        ("Тошкент", "old_cyr", "cyr_old"),
    ],
)
def test_reverse_direction(text, mode, expected):
    assert reverse_direction(text, mode) == expected


# --- Xabarlar --------------------------------------------------------------

async def test_text_is_converted_with_buttons(dp, tg):
    session = await feed(dp, tg, msg("Тошкент шаҳри, O'zbekiston"))
    [sent] = session.sent()
    assert sent.text == "Toşkent şahri, Özbekiston"
    assert sent.parse_mode is None
    buttons = [b for row in sent.reply_markup.inline_keyboard for b in row]
    assert buttons[0].copy_text.text == sent.text
    assert [b.callback_data for b in buttons[1:]] == ["rev", "err"]


async def test_entities_protected(dp, tg):
    text = "shahar choy() @choy_bot"
    ents = [MessageEntity(type="code", offset=7, length=6), MessageEntity(type="mention", offset=14, length=9)]
    session = await feed(dp, tg, msg(text, ents))
    assert session.sent()[0].text == "şahar choy() @choy_bot"


async def test_unchanged_text(dp, tg):
    session = await feed(dp, tg, msg("salom dunyo"))
    assert "bir xil" in session.sent()[0].text


async def test_long_text_split(dp, tg):
    text = "Тошкент шаҳри. " * 400            # 6000 belgi
    session = await feed(dp, tg, msg(text))
    sent = session.sent()
    assert len(sent) == 2
    assert "".join(m.text for m in sent) == "Toşkent şahri. " * 400
    assert sent[1].reply_markup.inline_keyboard[0][0].callback_data == "copy"   # > 256 belgi


async def test_very_long_text_as_file(dp, tg):
    session = await feed(dp, tg, msg("Тошкент. " * 1200))   # 10 800 belgi
    assert not session.sent()
    [doc] = session.sent(SendDocument)
    assert doc.document.filename == "imlochi.txt"
    assert doc.document.data.decode() == "Toşkent. " * 1200


# --- Buyruqlar --------------------------------------------------------------

async def test_start_mentions_username(dp, tg):
    session = await feed(dp, tg, msg("/start"))
    assert "@alifbo_bot" in session.sent()[0].text


async def test_start_menu_buttons(dp, tg):
    session = await feed(dp, tg, msg("/start"))
    sent = session.sent()[0]
    assert "/jadval" not in sent.text
    rows = sent.reply_markup.inline_keyboard
    assert [[b.callback_data for b in r] for r in rows[:2]] == [
        ["menu:jadval", "menu:rejim"],
        ["menu:til", "menu:help"],
    ]
    assert rows[2][0].url.startswith("https://t.me/share/url")


@pytest.mark.parametrize(
    "section, expected",
    [("jadval", "Ş ş"), ("rejim", "Rejimni tanlang"), ("til", "Interfeys yozuvini"), ("help", "Qanday ishlatiladi")],
)
async def test_menu_buttons_open_sections(dp, tg, section, expected):
    session = await feed(dp, tg, callback(f"menu:{section}", "..."))
    assert expected in session.sent()[0].text


async def test_command_with_bot_suffix(dp, tg):
    session = await feed(dp, tg, msg("/jadval@alifbo_bot"))
    assert "Ş ş" in session.sent()[0].text


async def test_jadval(dp, tg):
    session = await feed(dp, tg, msg("/jadval"))
    assert "Ş ş" in session.sent()[0].text


async def test_rejim_menu_layout(dp, tg):
    session = await feed(dp, tg, msg("/rejim"))
    rows = session.sent()[0].reply_markup.inline_keyboard
    assert [[b.text for b in r] for r in rows] == [
        ["ЎЗ→ÖZ", "ЎЗ→OʻZ"],
        ["OʻZ→ÖZ", "OʻZ→ЎЗ"],
        ["ÖZ→OʻZ", "ÖZ→ЎЗ"],
        ["✅ Avto", "ℹ️ Loyiha haqida"],
    ]
    assert rows[3][1].callback_data == "about"


async def test_rejim_switch_directions(dp, tg):
    await feed(dp, tg, callback("mode:new_old", "..."))
    session = await feed(dp, tg, msg("Özbekiston"))
    assert session.sent()[0].text == "Oʻzbekiston"

    await feed(dp, tg, callback("mode:old_cyr", "..."))
    session = await feed(dp, tg, msg("O'zbekiston"))
    assert session.sent()[0].text == "Ўзбекистон"
    # «Teskari» — tanlangan yo'nalishning aksi (kirill → eski lotin).
    session = await feed(dp, tg, callback("rev", "Ўзбекистон"))
    assert session.sent()[0].text == "Oʻzbekiston"

    await feed(dp, tg, callback("mode:auto", "..."))


async def test_til_new_interface(dp, tg):
    await feed(dp, tg, callback("ui:new", "..."))
    session = await feed(dp, tg, msg("/help"))
    text = session.sent()[0].text
    assert "ögiriş yönalişi" in text and "işlatiladi" in text
    assert "@alifbo_bot" in text
    await feed(dp, tg, callback("ui:old", "..."))


async def test_admin_panel(dp, tg):
    session = await feed(dp, tg, msg("/admin"))
    sent = session.sent()[0]
    assert "Jami foydalanuvchilar: <b>1</b>" in sent.text
    assert "Botda oʻgirish" in sent.text
    assert sent.reply_markup.inline_keyboard[0][0].callback_data == "adm:refresh"


async def test_admin_denied_for_others(dp, tg):
    other = User(id=2002, is_bot=False, first_name="Vali")
    update = Update(update_id=next(_ids), message=Message(
        message_id=next(_ids), date=dt.datetime.now(), chat=Chat(id=2002, type="private"),
        from_user=other, text="/admin"))
    session = await feed(dp, tg, update)
    assert "faqat administratorlar" in session.sent()[0].text


async def test_admin_not_configured_shows_id(dp, tg):
    config = dp["config"]
    dp["config"] = Config(bot_token="42:TEST")
    try:
        session = await feed(dp, tg, msg("/admin"))
    finally:
        dp["config"] = config
    assert "<code>1001</code>" in session.sent()[0].text


def test_admin_text_chart():
    from storage import AdminReport
    rep = AdminReport(
        total=10, new_today=2, new_week=6, new_month=10, active_today=3, active_week=7,
        daily_new=[("2026-10-16", 0), ("2026-10-17", 1), ("2026-10-18", 0), ("2026-10-19", 0),
                   ("2026-10-20", 1), ("2026-10-21", 2), ("2026-10-22", 2)],
        events_today={"convert_old_new": 3, "new_user": 2},
        events_week={"convert_old_new": 5, "convert_cyr_new": 4, "new_user": 6, "web_convert": 1},
    )
    text = admin_text(rep, dt.datetime(2026, 10, 22, 12, 0))
    assert "Jami foydalanuvchilar: <b>10</b>" in text
    assert "10-22  ████████████ 2" in text and "10-16  · 0" in text
    assert "Botda oʻgirish: <b>3</b> / 9" in text
    assert "Saytda oʻgirish: <b>0</b> / 1" in text


async def test_share_and_about(dp, tg):
    session = await feed(dp, tg, msg("/ulashish"))
    sent = session.sent()[0]
    url = sent.reply_markup.inline_keyboard[0][0].url
    assert url.startswith("https://t.me/share/url?url=https%3A//t.me/alifbo_bot")
    session = await feed(dp, tg, callback("about", "..."))
    assert "Imlochi" in session.sent()[0].text


# --- Natija tugmalari -------------------------------------------------------

async def test_reverse_button(dp, tg):
    session = await feed(dp, tg, callback("rev", "Toşkent şahri"))
    assert session.sent()[0].text == "Toshkent shahri"


async def test_copy_button_sends_pre(dp, tg):
    session = await feed(dp, tg, callback("copy", "Toşkent <şahri>"))
    assert "<pre>Toşkent &lt;şahri&gt;</pre>" in session.sent()[0].text


async def test_report_button(dp, tg):
    session = await feed(dp, tg, callback("err", "x"))
    [ans] = [c for c in session.calls if isinstance(c, AnswerCallbackQuery)]
    assert ans.show_alert and "Rahmat" in ans.text


# --- Inline rejim -----------------------------------------------------------

async def test_inline_two_variants(dp, tg):
    update = Update(
        update_id=next(_ids),
        inline_query=InlineQuery(id="q1", from_user=USER, query="Тошкент шаҳри", offset=""),
    )
    session = await feed(dp, tg, update)
    [ans] = [c for c in session.calls if isinstance(c, AnswerInlineQuery)]
    texts = [r.input_message_content.message_text for r in ans.results]
    assert texts == ["Toşkent şahri", "Toshkent shahri", "Тошкент шаҳри"]
    assert [r.title for r in ans.results] == ["Yangi alifboda", "Eski lotinda", "Kirillda"]


async def test_inline_empty_query(dp, tg):
    update = Update(update_id=next(_ids), inline_query=InlineQuery(id="q2", from_user=USER, query="", offset=""))
    session = await feed(dp, tg, update)
    [ans] = [c for c in session.calls if isinstance(c, AnswerInlineQuery)]
    assert ans.results == [] and ans.button.start_parameter == "inline"
