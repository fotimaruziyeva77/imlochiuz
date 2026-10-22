"""Bot interfeysi matnlari (HTML).

Matnlar eski lotinda yozilgan. Foydalanuvchi /til orqali yangi alifboni
tanlasa, ``t()`` ularni converter orqali o'giradi — interfeys uchun alohida
tarjima kerak emas. Qonun kuchga kirgach standart yozuv "new" ga almashtiriladi.
"""

from __future__ import annotations

from converter import to_new

TEXTS = {
    "start": (
        "Assalomu alaykum! Men <b>yangi oʻzbek alifbosi</b> yordamchisiman.\n\n"
        "Menga istalgan matnni yuboring — kirill, eski lotin yoki aralash boʻlsa ham "
        "yangi alifboga oʻgirib beraman (Oʻ→Ö, Gʻ→Ğ, Sh→Ş, Ch→Ç).\n\n"
        "Istalgan chatda ham ishlayman: <code>@{username} matn</code> deb yozing.\n\n"
        "Quyidagi tugmalardan foydalaning 👇"
    ),
    "help": (
        "<b>Qanday ishlatiladi</b>\n\n"
        "1. Matn yuboring — yangi alifbodagi variantini qaytaraman. "
        "Yozuv avtomatik aniqlanadi: kirill va eski lotin → yangi alifbo, "
        "yangi alifbo → eski lotin.\n"
        "2. Javob ostidagi tugmalar: <b>Nusxa olish</b>, <b>Teskari</b> "
        "(boshqa yoʻnalishda oʻgirish), <b>Xato haqida xabar</b>.\n"
        "3. Istalgan chatda: <code>@{username} matn</code> → «Yangi alifboda», "
        "«Eski lotinda» yoki «Kirillda» variantini tanlang.\n\n"
        "Havolalar, e-mail, @username, #hashtag va kod oʻzgartirilmaydi.\n"
        "Uzun natija bir nechta xabarga boʻlinadi, 10 000 belgidan uzuni fayl qilib yuboriladi.\n\n"
        "<b>Buyruqlar</b>\n"
        "/jadval — oʻzgargan harflar jadvali\n"
        "/rejim — oʻgirish yoʻnalishi (kirill, eski lotin, yangi alifbo)\n"
        "/ulashish — doʻstlarga ulashish\n"
        "/til — interfeys yozuvi\n\n"
        "Maxfiylik: matningiz oʻgirilgach hech qayerda saqlanmaydi."
    ),
    "rejim": "<b>Rejimni tanlang</b>\n\nHozirgi rejim: {current}",
    "rejim_set": "✅ Rejim oʻzgartirildi: {current}",
    "mode_auto": "Avto",
    "til": "<b>Interfeys yozuvini tanlang</b>\n\nHozirgi: {current}",
    "til_set": "Interfeys yozuvi: {current}",
    "ui_old": "Eski lotin",
    "ui_new": "Yangi alifbo",
    "unchanged": "✅ Bu matnda oʻzgaradigan harf yoʻq — u ikkala alifboda bir xil yoziladi.",
    "file_caption": "Natija uzun boʻlgani uchun fayl qilib yuborildi ({length} belgi).",
    "unsupported": (
        "Hozircha faqat matn qabul qilinadi. Rasm, ovozli xabar va fayllarni "
        "oʻgirish keyingi yangilanishda qoʻshiladi."
    ),
    "btn_copy": "📋 Nusxa olish",
    "btn_reverse": "🔁 Teskari",
    "btn_report": "⚠️ Xato haqida xabar",
    "copy_hint": "Matnni bosing — nusxa olinadi:",
    "report_thanks": "Rahmat! Xabaringiz qayd etildi. Xatolar istisnolar lugʻati orqali tuzatiladi.",
    "too_many": "Juda koʻp soʻrov. Iltimos, bir daqiqadan soʻng qayta urinib koʻring.",
    "inline_new": "Yangi alifboda",
    "inline_old": "Eski lotinda",
    "inline_cyr": "Kirillda",
    "inline_help": "Qanday ishlatiladi?",
    "no_access": "Bu buyruq faqat administratorlar uchun.",
    "btn_share": "📤 Doʻstlarga ulashish",
    "btn_jadval": "🔤 Harflar jadvali",
    "btn_rejim": "🔁 Oʻgirish yoʻnalishi",
    "btn_til": "🅰️ Interfeys yozuvi",
    "btn_help": "❓ Yordam",
    "btn_site": "🌐 Sayt",
    "btn_about": "ℹ️ Loyiha haqida",
    "share_text": "Imlochi — yangi oʻzbek alifbosiga (Ö, Ğ, Ş, Ç) bir zumda oʻgiruvchi bot",
    "about": (
        "<b>Imlochi — yangi oʻzbek alifbosi yordamchisi</b>\n\n"
        "OʻRQ-1184-son Qonun (21.10.2026) toʻrtta harfni oʻzgartirdi: "
        "Oʻ→Ö, Gʻ→Ğ, Sh→Ş, Ch→Ç. Qonun rasman eʼlon qilinganidan 6 oy oʻtgach kuchga kiradi.\n\n"
        "Imlochi matnni kirill, eski lotin va yangi alifbo oʻrtasida istalgan "
        "yoʻnalishda oʻgiradi, istalgan chatda inline rejimda ishlaydi. Bot bepul.\n\n"
        "<b>Tez orada:</b> rasm va hujjatdan oʻgirish, ovozli xabar, imlo tekshiruvi, "
        "yangi harflarni oʻrganish mashqlari.\n\n"
        "Foydali boʻlsa, doʻstlaringizga ulashing 👇"
    ),
}

# Rejim tugmalarida yozuvlar belgisi — o'girilmaydi (har doim asl ko'rinishida).
SCRIPT_LABELS = {"cyr": "ЎЗ", "old": "OʻZ", "new": "ÖZ"}
MODE_LEGEND = "\n\n<i>ЎЗ — kirill · OʻZ — eski lotin · ÖZ — yangi alifbo</i>"

# Yangi alifboga o'girilmaydigan matnlar (harflarni solishtirib ko'rsatadi).
JADVAL = (
    "<b>Yangi alifbo: oʻzgargan harflar</b>\n"
    "<i>OʻRQ-1184-son Qonun, 21.10.2026</i>\n\n"
    "<pre>"
    "Eski    Yangi   Misol\n"
    "Oʻ oʻ   Ö ö     oʻzbek  → özbek\n"
    "Gʻ gʻ   Ğ ğ     togʻ    → toğ\n"
    "Sh sh   Ş ş     shahar  → şahar\n"
    "Ch ch   Ç ç     choy    → çoy"
    "</pre>\n\n"
    "<b>ng</b> — alohida harf sifatida alifbodan chiqarildi, lekin yozuvda "
    "n+g boʻlib qoladi: <i>rang, bodring</i> — oʻzgarmaydi.\n\n"
    "<b>Tutuq belgisi</b> saqlanadi: <i>taʼlim, maʼno</i>. Uning aniq koʻrinishi "
    "yangi imlo qoidalarida belgilanadi.\n\n"
    "Alifboda 28 ta harf va 1 ta tutuq belgisi bor. Qonun rasman eʼlon qilinganidan "
    "6 oy oʻtgach kuchga kiradi."
)


def t(key: str, ui: str = "old", **kwargs) -> str:
    """Interfeys matni foydalanuvchi tanlagan yozuvda.

    Avval shablon o'giriladi, keyin qiymatlar qo'yiladi — shuning uchun
    ``kwargs`` (username, rejim nomi va h.k.) o'zgarmay qoladi.
    """
    text = to_new(TEXTS[key]) if ui == "new" else TEXTS[key]
    return text.format(**kwargs) if kwargs else text


def mode_label(mode: str) -> str:
    if mode == "auto":
        return "Avto"
    src, dst = mode.split("_")
    return f"{SCRIPT_LABELS[src]}→{SCRIPT_LABELS[dst]}"
