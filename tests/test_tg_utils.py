from dataclasses import dataclass

from converter import to_new
from tg_utils import FILE_THRESHOLD, MESSAGE_LIMIT, RateLimiter, entity_spans, split_text


@dataclass
class Ent:
    type: str
    offset: int
    length: int


# --- F1.8: Telegram entity'lari ----------------------------------------------

def test_entity_spans_code_is_protected():
    # Telegram backtick'larni olib tashlab, code entity beradi.
    text = "shahar choy_func() choy"
    spans = entity_spans(text, [Ent("code", 7, 11)])
    assert to_new(text, protected=spans) == "şahar choy_func() çoy"


def test_entity_spans_utf16_offsets_with_emoji():
    text = "😀 shahar @choy"
    # 😀 UTF-16 da 2 birlik: "@choy" offset'i 10, Python'da 9.
    spans = entity_spans(text, [Ent("mention", 10, 5)])
    assert spans == [(9, 14)]
    assert text[9:14] == "@choy"


def test_entity_spans_ignores_formatting():
    assert entity_spans("shahar", [Ent("bold", 0, 6), Ent("text_link", 0, 6)]) == []


def test_entity_spans_none():
    assert entity_spans("x", None) == []


# --- F1.7: uzun matn ---------------------------------------------------------

def test_split_short():
    assert split_text("salom") == ["salom"]
    assert split_text("") == []


def test_split_long_preserves_text_and_limit():
    text = ("Özbekiston — mustaqil davlat.\n" * 30 + "\n") * 12   # ~11 000 belgi
    chunks = split_text(text)
    assert "".join(chunks) == text
    assert all(len(c) <= MESSAGE_LIMIT for c in chunks)
    assert len(chunks) >= 3


def test_split_without_spaces():
    text = "a" * 9000
    chunks = split_text(text)
    assert [len(c) for c in chunks] == [4096, 4096, 808]


def test_10000_chars_roundtrip():
    # 9.1: 10 000 belgilik matn xatosiz qaytariladi.
    src = ("Тошкент шаҳри ва O'zbekiston. " * 400)[:10_000]
    result = to_new(src)
    assert len(result) <= FILE_THRESHOLD
    assert "".join(split_text(result)) == result


# --- Spam limiti -------------------------------------------------------------

def test_rate_limiter():
    now = [0.0]
    rl = RateLimiter(limit=3, window=60, clock=lambda: now[0])
    assert [rl.allow(1) for _ in range(4)] == [True, True, True, False]
    assert rl.allow(2)                       # boshqa foydalanuvchi alohida
    now[0] = 60.0
    assert rl.allow(1)                       # oyna o'tgach yana ruxsat
