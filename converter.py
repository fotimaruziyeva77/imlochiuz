"""Yangi o'zbek alifbosi uchun o'girish yadrosi (TZ, 5-bo'lim).

Sof Python, tashqi kutubxonasiz. Bot, API va boshqa kanallar faqat shu
moduldagi funksiyalarni chaqiradi:

    to_new(text)  — kirill, eski lotin yoki aralash matn → yangi alifbo
    to_old(text)  — yangi alifbo → eski lotin
    to_cyr(text)  — yangi alifbo yoki eski lotin → kirill
    detect(text)  — matn yozuvini aniqlash

Himoyalangan bo'laklar (URL, e-mail, @username, #hashtag, backtick ichidagi
kod) hech qachon o'zgartirilmaydi. Qo'shimcha himoyalangan oraliqlarni
(masalan, Telegram entity'lari) ``protected`` argumenti orqali berish mumkin.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

__all__ = [
    "TUTUQ",
    "OKINA",
    "APOSTROPHES",
    "to_new",
    "to_old",
    "to_cyr",
    "convert",
    "DIRECTIONS",
    "detect",
    "protected_spans",
]

# Tutuq belgisi. Imlo qoidalari tasdiqlanmagani uchun sozlanadigan parametr
# (TZ, 2-bo'lim): funksiyalarga ``tutuq=`` orqali boshqa belgi berish mumkin.
TUTUQ = "'"

# Eski lotindagi O'/G' uchun rasmiy belgi (U+02BB, o'kina).
OKINA = "ʻ"

# O'/G' dan keyin keladigan va tan olinadigan barcha apostrof variantlari.
APOSTROPHES = frozenset("'‘’ʻʼ`´")

# --- Himoyalangan bo'laklar ------------------------------------------------

_TLDS = "uz|com|ru|org|net|io|info|me|app|dev|gov|edu|tj|kz|kg"
_PROTECTED_RE = re.compile(
    r"""
      (?<![oOgG])```.*?```                        # kod bloki
    | (?<![oOgG])`[^`\n]+`                        # inline kod (o`/g` — apostrof)
    | (?:https?://|ftp://|www\.)[^\s<>"]*[^\s<>".,;:!?)\]}'»]   # URL
    | [\w.+-]+@[\w-]+(?:\.[\w-]+)+                # e-mail
    | (?<![\w@])@\w+                              # @username
    | (?<![\w#])\#\w+                             # #hashtag
    | \b[\w-]+(?:\.[\w-]+)*\.(?:""" + _TLDS + r""")\b(?:/[^\s<>"]*[^\s<>".,;:!?)\]}'»])?   # domen
    """,
    re.VERBOSE | re.DOTALL | re.IGNORECASE,
)


def protected_spans(text: str) -> list[tuple[int, int]]:
    """Matndagi himoyalangan bo'laklar oraliqlari ``[(start, end), ...]``."""
    return [m.span() for m in _PROTECTED_RE.finditer(text)]


def _merge(spans: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(s for s in spans if s[0] < s[1]):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _apply(text: str, convert_range, protected: Sequence[tuple[int, int]] | None) -> str:
    """Himoyalangan bo'laklarni tashlab, qolgan oraliqlarni o'giradi."""
    spans = protected_spans(text)
    if protected:
        spans.extend((max(0, s), min(len(text), e)) for s, e in protected)
    out: list[str] = []
    pos = 0
    for start, end in _merge(spans):
        if pos < start:
            out.append(convert_range(text, pos, start))
        out.append(text[start:end])
        pos = end
    if pos < len(text):
        out.append(convert_range(text, pos, len(text)))
    return "".join(out)


# --- Yordamchi funksiyalar --------------------------------------------------


def _is_letter(ch: str) -> bool:
    return ch.isalpha()


def _upper_context(text: str, i: int, length: int) -> bool:
    """Katta harfdan ko'p harfli natija (Ş→SH, Ё→YO) qanday yozilishini
    aniqlaydi: qo'shni harf ham katta bo'lsa — butunlay katta (SH), aks holda
    faqat birinchi harf katta (Sh)."""
    j = i + length
    if j < len(text) and _is_letter(text[j]):
        return text[j].isupper()
    if i > 0 and _is_letter(text[i - 1]):
        return text[i - 1].isupper()
    return False


def _cased(result: str, upper: bool, all_caps: bool) -> str:
    if not upper:
        return result
    return result.upper() if all_caps else result[0].upper() + result[1:]


# --- Kirill → yangi alifbo (5.2) ---------------------------------------------

_CYR_SIMPLE = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x",
    "ч": "ç", "ш": "ş", "щ": "şç", "ы": "i", "э": "e", "ё": "yo", "ю": "yu",
    "я": "ya", "ў": "ö", "қ": "q", "ғ": "ğ", "ҳ": "h", "ь": "",
}
_CYR_VOWELS = frozenset("аеёиоуўэюяы")
_CYRILLIC = frozenset(_CYR_SIMPLE) | frozenset("ецъ")


def _cyr_letter(text: str, i: int, tutuq: str) -> str:
    ch = text[i]
    low = ch.lower()
    prev = text[i - 1].lower() if i > 0 else ""

    if low == "ъ":
        return tutuq
    if low == "е":
        # So'z boshida, unlidan va ъ/ь dan keyin → ye, aks holda → e.
        if not _is_letter(prev) or prev in _CYR_VOWELS or prev in "ъь":
            res = "ye"
        else:
            res = "e"
    elif low == "ц":
        res = "ts" if prev in _CYR_VOWELS else "s"
    else:
        res = _CYR_SIMPLE[low]

    if not res or not ch.isupper():
        return res
    return _cased(res, True, len(res) > 1 and _upper_context(text, i, 1))


# --- Eski lotin → yangi alifbo (5.1) -----------------------------------------

_OLD_PAIRS = {"o": "ö", "g": "ğ"}   # + apostrof
_OLD_DIGRAPHS = {"s": "ş", "c": "ç"}  # + h


def _to_new_range(text: str, start: int, end: int, tutuq: str, cyrillic: bool = True) -> str:
    out: list[str] = []
    i = start
    while i < end:
        ch = text[i]
        low = ch.lower()
        nxt = text[i + 1] if i + 1 < end else ""

        if low in _OLD_PAIRS and nxt in APOSTROPHES:
            res = _OLD_PAIRS[low]
            out.append(res.upper() if ch.isupper() else res)
            i += 2
        elif low in _OLD_DIGRAPHS and nxt.lower() == "h":
            res = _OLD_DIGRAPHS[low]
            out.append(res.upper() if ch.isupper() else res)
            i += 2
        elif cyrillic and low in _CYRILLIC:
            out.append(_cyr_letter(text, i, tutuq))
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def to_new(
    text: str,
    *,
    tutuq: str = TUTUQ,
    protected: Sequence[tuple[int, int]] | None = None,
) -> str:
    """Kirill, eski lotin yoki aralash matnni yangi alifboga o'giradi."""
    return _apply(text, lambda t, s, e: _to_new_range(t, s, e, tutuq), protected)


# --- Yangi alifbo → eski lotin (5.3) -----------------------------------------

_NEW_TO_OLD = {"ö": "o" + OKINA, "ğ": "g" + OKINA, "ş": "sh", "ç": "ch"}


def _to_old_range(text: str, start: int, end: int, tutuq: str) -> str:
    out: list[str] = []
    for i in range(start, end):
        ch = text[i]
        low = ch.lower()
        res = _NEW_TO_OLD.get(low)
        if res is not None:
            if ch.isupper():
                res = _cased(res, True, _upper_context(text, i, 1))
            out.append(res)
        elif low == "s" and i + 1 < end and text[i + 1].lower() == "h":
            # Yangi yozuvdagi alohida s+h eski yozuvda tutuq bilan ajratiladi.
            out.append(ch + tutuq)
        else:
            out.append(ch)
    return "".join(out)


def to_old(
    text: str,
    *,
    tutuq: str = TUTUQ,
    protected: Sequence[tuple[int, int]] | None = None,
) -> str:
    """Yangi alifbodagi matnni eski lotinga o'giradi."""
    return _apply(text, lambda t, s, e: _to_old_range(t, s, e, tutuq), protected)


# --- Lotin (yangi yoki eski) → kirill (F1.3) ---------------------------------

_LAT_TO_CYR = {
    "a": "а", "b": "б", "d": "д", "f": "ф", "g": "г", "h": "ҳ", "i": "и",
    "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п",
    "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "x": "х",
    "y": "й", "z": "з", "ö": "ў", "ğ": "ғ", "ş": "ш", "ç": "ч",
}
_Y_PAIRS = {"o": "ё", "u": "ю", "a": "я", "e": "е"}
_LAT_VOWELS = frozenset("aeiouö")


def _to_cyr_range(text: str, start: int, end: int, tutuq: str, from_old: bool) -> str:
    # Eski lotin avval yangi alifboga keltiriladi (o'→ö, sh→ş ...),
    # keyin yagona qoidalar bilan kirillga o'giriladi.
    seg = _to_new_range(text, start, end, tutuq, cyrillic=False) if from_old else text[start:end]
    before = text[start - 1] if start > 0 else ""
    out: list[str] = []
    i = 0
    while i < len(seg):
        ch = seg[i]
        low = ch.lower()
        prev = seg[i - 1] if i > 0 else before
        nxt = seg[i + 1] if i + 1 < len(seg) else ""

        if low == "y" and nxt.lower() in _Y_PAIRS:
            res = _Y_PAIRS[nxt.lower()]
            i += 2
        elif low == "e":
            # So'z boshida va unlidan keyin → э, aks holda → е.
            res = "э" if not _is_letter(prev) or prev.lower() in _LAT_VOWELS else "е"
            i += 1
        elif ch in APOSTROPHES or ch == tutuq:
            i += 1
            if not (_is_letter(prev) and _is_letter(nxt)):
                out.append(ch)          # tirnoq sifatida ishlatilgan apostrof
                continue
            # s'h dagi tutuq kirillda kerak emas: Is'hoq → Исҳоқ.
            out.append("" if prev.lower() == "s" and nxt.lower() == "h" else "ъ")
            continue
        elif low in _LAT_TO_CYR:
            res = _LAT_TO_CYR[low]
            i += 1
        else:
            out.append(ch)
            i += 1
            continue
        out.append(res.upper() if ch.isupper() else res)
    return "".join(out)


def to_cyr(
    text: str,
    *,
    tutuq: str = TUTUQ,
    protected: Sequence[tuple[int, int]] | None = None,
    source: str = "old",
) -> str:
    """Yangi alifbo yoki eski lotindagi matnni kirillga o'giradi.

    ``source="old"`` (standart) — matnda eski lotin bo'lishi mumkin, sh/ch/o'/g'
    harf sifatida o'qiladi. ``source="new"`` — matn aniq yangi alifboda, s+h
    alohida harflar: Ishoq → Исҳоқ (eski lotin sifatida esa Ишоқ).

    Cheklov: lotindan kirillga o'girish bir ma'noli emas — "ts" doim "тс"
    bo'ladi (ц tiklanmaydi), yumshatish belgisi (ь) qo'yilmaydi.
    """
    from_old = source != "new"
    return _apply(text, lambda t, s, e: _to_cyr_range(t, s, e, tutuq, from_old), protected)


# --- Yo'nalish bo'yicha o'girish ------------------------------------------

def _cyr_to_old_range(text: str, start: int, end: int, tutuq: str) -> str:
    seg = _to_new_range(text, start, end, tutuq)
    return _to_old_range(seg, 0, len(seg), tutuq)


# "manba_natija": cyr — kirill, old — eski lotin, new — yangi alifbo.
_DIRECTIONS = {
    "cyr_new": _to_new_range,
    "old_new": _to_new_range,
    "cyr_old": _cyr_to_old_range,
    "new_old": _to_old_range,
    "old_cyr": lambda t, s, e, tq: _to_cyr_range(t, s, e, tq, True),
    "new_cyr": lambda t, s, e, tq: _to_cyr_range(t, s, e, tq, False),
}
DIRECTIONS = tuple(_DIRECTIONS)


def convert(
    text: str,
    direction: str,
    *,
    tutuq: str = TUTUQ,
    protected: Sequence[tuple[int, int]] | None = None,
) -> str:
    """Matnni berilgan yo'nalishda o'giradi (``DIRECTIONS`` dan biri).

    Bir necha bosqichli yo'nalishlar (masalan, kirill → eski lotin) har bir
    oraliq ichida bajariladi, shuning uchun ``protected`` oraliqlari to'g'ri qoladi.
    """
    fn = _DIRECTIONS[direction]
    return _apply(text, lambda t, s, e: fn(t, s, e, tutuq), protected)


# --- Yozuvni aniqlash (F1.1) ------------------------------------------------

_NEW_LETTERS = frozenset("öğşçÖĞŞÇ")
_OLD_MARKERS = re.compile(r"[oOgG][" + re.escape("".join(APOSTROPHES)) + r"]|[sScC][hH]")


def detect(text: str) -> str:
    """Matn yozuvini aniqlaydi.

    Natija: ``"cyrillic"``, ``"old_latin"``, ``"new_latin"``, ``"mixed"``
    (bir nechta yozuv aralash), ``"latin"`` (lotin, lekin ikkala alifboda
    bir xil yoziladi, masalan "salom") yoki ``"unknown"`` (harf yo'q).
    """
    chars = list(text)
    for s, e in protected_spans(text):
        chars[s:e] = " " * (e - s)
    plain = "".join(chars)

    has_cyr = any(ch.lower() in _CYRILLIC for ch in plain)
    has_new = any(ch in _NEW_LETTERS for ch in plain)
    has_old = bool(_OLD_MARKERS.search(plain))
    has_latin = any("a" <= ch.lower() <= "z" for ch in plain)

    kinds = [k for k, v in (("cyrillic", has_cyr), ("new_latin", has_new), ("old_latin", has_old)) if v]
    if len(kinds) > 1:
        return "mixed"
    if kinds:
        return kinds[0]
    return "latin" if has_latin else "unknown"
