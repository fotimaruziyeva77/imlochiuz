import time

import pytest

from converter import OKINA, detect, protected_spans, to_cyr, to_new, to_old


# --- TZ, 9-bo'lim: namunaviy test holatlari ---------------------------------

@pytest.mark.parametrize(
    "src, expected",
    [
        ("O'zbekiston", "Özbekiston"),
        ("qo'ng'iroq", "qönğiroq"),
        ("kulrang bodring", "kulrang bodring"),
        ("Тошкент шаҳри", "Toşkent şahri"),
        ("ЧОЙХОНА", "ÇOYXONA"),
        ("съезд", "s'yezd"),
        ("https://shop.uz/choy", "https://shop.uz/choy"),
    ],
)
def test_tz_examples(src, expected):
    assert to_new(src) == expected


def test_tz_example_reverse():
    assert to_old("Ishoq") == "Is'hoq"


# --- 5.1. Eski lotin → yangi -------------------------------------------------

@pytest.mark.parametrize(
    "src, expected",
    [
        ("tog'", "toğ"),
        ("shahar", "şahar"),
        ("choy", "çoy"),
        ("rang", "rang"),
        ("Shahar", "Şahar"),
        ("SHAHAR", "ŞAHAR"),
        ("O'ZBEKISTON", "ÖZBEKISTON"),
        ("CHOY", "ÇOY"),
        ("ta'lim", "ta'lim"),
        ("mo''jiza", "mö'jiza"),
        ("Is'hoq", "Is'hoq"),
    ],
)
def test_old_latin(src, expected):
    assert to_new(src) == expected


@pytest.mark.parametrize("apo", ["'", "‘", "’", "ʻ", "ʼ", "`", "´"])
def test_all_apostrophe_variants(apo):
    assert to_new(f"O{apo}g{apo}il") == "Öğil"


# --- 5.2. Kirill → yangi -----------------------------------------------------

@pytest.mark.parametrize(
    "src, expected",
    [
        ("ўғил", "öğil"),
        ("қўл", "qöl"),
        ("ҳаво", "havo"),
        ("Ер", "Yer"),
        ("ЕР", "YER"),
        ("кел", "kel"),
        ("оила", "oila"),
        ("поезд", "poyezd"),
        ("милиция", "militsiya"),
        ("цирк", "sirk"),
        ("Цирк", "Sirk"),
        ("ёз", "yoz"),
        ("Юлдуз", "Yulduz"),
        ("ЯНГИ", "YANGI"),
        ("Янги", "Yangi"),
        ("щётка", "şçyotka"),
        ("мактаб", "maktab"),
        ("мағриб", "mağrib"),
        ("пальто", "palto"),
        ("маъно", "ma'no"),
        ("ЎЗБЕКИСТОН", "ÖZBEKISTON"),
        ("Ўзбекистон", "Özbekiston"),
    ],
)
def test_cyrillic(src, expected):
    assert to_new(src) == expected


def test_cyrillic_sentence():
    src = "Ўзбекистон Республикаси — мустақил давлат."
    assert to_new(src) == "Özbekiston Respublikasi — mustaqil davlat."


def test_mixed_text():
    assert to_new("Тошкент shahri va o'zbek тили") == "Toşkent şahri va özbek tili"


def test_custom_tutuq():
    assert to_new("маъно", tutuq="ʼ") == "maʼno"


# --- 5.3. Yangi → eski -------------------------------------------------------

@pytest.mark.parametrize(
    "src, expected",
    [
        ("Özbekiston", f"O{OKINA}zbekiston"),
        ("toğ", f"tog{OKINA}"),
        ("şahar", "shahar"),
        ("Şahar", "Shahar"),
        ("ŞAHAR", "SHAHAR"),
        ("ÇOYXONA", "CHOYXONA"),
        ("Ç", "Ch"),
        ("rang", "rang"),
        ("ISHOQ", "IS'HOQ"),
    ],
)
def test_to_old(src, expected):
    assert to_old(src) == expected


@pytest.mark.parametrize(
    "word",
    ["Özbekiston", "qönğiroq", "Toşkent şahri", "çoy", "mö'jiza", "Is'hoq", "ÇOYXONA"],
)
def test_roundtrip_new_old_new(word):
    assert to_new(to_old(word)) == word


# --- 5.4. Himoyalangan bo'laklar ---------------------------------------------

@pytest.mark.parametrize(
    "fragment",
    [
        "https://shop.uz/choy",
        "http://example.com/a?ch=1&sh=2",
        "www.shop.uz/choy",
        "shop.uz",
        "choyxona@mail.uz",
        "@choyxona_bot",
        "#choy",
        "`shahar_choy()`",
        "```\nshahar = 'choy'\n```",
    ],
)
def test_protected_fragments_unchanged(fragment):
    text = f"shahar {fragment} choy"
    assert to_new(text) == f"şahar {fragment} çoy"
    assert to_old(f"şahar {fragment} çoy") == text


def test_url_trailing_punctuation_not_protected():
    assert to_new("Qarang: https://shop.uz/choy. Choy!") == "Qarang: https://shop.uz/choy. Çoy!"


def test_backtick_as_apostrophe_is_not_code():
    assert to_new("o`zbek va bo`lim") == "özbek va bölim"


def test_extra_protected_spans():
    text = "shahar choy"
    assert to_new(text, protected=[(7, 11)]) == "şahar choy"


def test_protected_spans_found():
    text = "@user #tag http://a.uz"
    assert [text[s:e] for s, e in protected_spans(text)] == ["@user", "#tag", "http://a.uz"]


# --- F1.1. Yozuvni aniqlash --------------------------------------------------

@pytest.mark.parametrize(
    "text, kind",
    [
        ("Тошкент", "cyrillic"),
        ("O'zbekiston", "old_latin"),
        ("shahar", "old_latin"),
        ("Özbekiston", "new_latin"),
        ("Тошкент shahri", "mixed"),
        ("salom", "latin"),
        ("123 !", "unknown"),
        ("https://shop.uz/choy", "unknown"),
    ],
)
def test_detect(text, kind):
    assert detect(text) == kind


# --- Chegaraviy holatlar -----------------------------------------------------

def test_empty():
    assert to_new("") == ""
    assert to_old("") == ""


def test_whitespace_and_newlines_preserved():
    src = "shahar\n\n  choy\t'"
    assert to_new(src) == "şahar\n\n  çoy\t'"


def test_long_text_fast():
    text = ("Тошкент шаҳри — O'zbekiston poytaxti, https://tashkent.uz #shahar. " * 160)[:10_000]
    t0 = time.perf_counter()
    result = to_new(text)
    assert time.perf_counter() - t0 < 1.0
    assert "Toşkent şahri" in result and "Özbekiston" in result


# --- F1.3. Lotin → kirill ----------------------------------------------------

@pytest.mark.parametrize(
    "src, expected",
    [
        ("Özbekiston", "Ўзбекистон"),
        ("O'zbekiston", "Ўзбекистон"),
        ("Toşkent şahri", "Тошкент шаҳри"),
        ("Toshkent shahri", "Тошкент шаҳри"),
        ("ÇOYXONA", "ЧОЙХОНА"),
        ("Yer", "Ер"),
        ("yoz", "ёз"),
        ("Yulduz", "Юлдуз"),
        ("YANGI", "ЯНГИ"),
        ("poyezd", "поезд"),
        ("ekin", "экин"),
        ("kel", "кел"),
        ("shoir", "шоир"),
        ("yöl", "йўл"),
        ("qöl", "қўл"),
        ("ma'no", "маъно"),
        ("s'yezd", "съезд"),
        ("Is'hoq", "Исҳоқ"),
        ("Ishoq", "Ишоқ"),
        ("mö'jiza", "мўъжиза"),
        ("'salom'", "'салом'"),
    ],
)
def test_to_cyr(src, expected):
    assert to_cyr(src) == expected


def test_to_cyr_source_new_keeps_s_h():
    assert to_cyr("Ishoq", source="new") == "Исҳоқ"
    assert to_cyr("Işoq", source="new") == "Ишоқ"


def test_to_cyr_protected():
    assert to_cyr("choy https://shop.uz/choy @choy") == "чой https://shop.uz/choy @choy"


@pytest.mark.parametrize("word", ["Özbekiston", "Toşkent şahri", "ÇOYXONA", "qönğiroq", "maktab", "Yer"])
def test_roundtrip_new_cyr_new(word):
    assert to_new(to_cyr(word)) == word


# --- Yo'nalishlar ------------------------------------------------------------

from converter import DIRECTIONS, convert  # noqa: E402


@pytest.mark.parametrize(
    "direction, src, expected",
    [
        ("cyr_new", "Тошкент шаҳри", "Toşkent şahri"),
        ("cyr_old", "Тошкент шаҳри", "Toshkent shahri"),
        ("cyr_old", "Исҳоқ", "Is'hoq"),
        ("cyr_old", "Ўзбекистон", f"O{OKINA}zbekiston"),
        ("old_new", "O'zbekiston", "Özbekiston"),
        ("old_cyr", "O'zbekiston", "Ўзбекистон"),
        ("old_cyr", "Ishoq", "Ишоқ"),
        ("new_old", "Özbekiston", f"O{OKINA}zbekiston"),
        ("new_cyr", "Özbekiston", "Ўзбекистон"),
        ("new_cyr", "Ishoq", "Исҳоқ"),
        ("old_cyr", "цирк va choy", "цирк ва чой"),    # kirill o'zgarmaydi
    ],
)
def test_convert_directions(direction, src, expected):
    assert convert(src, direction) == expected


def test_convert_cyr_old_keeps_protected_span():
    text = "шаҳар shahar_choy() шаҳар"
    assert convert(text, "cyr_old", protected=[(6, 19)]) == "shahar shahar_choy() shahar"


def test_directions_list():
    assert set(DIRECTIONS) == {"cyr_new", "cyr_old", "old_new", "old_cyr", "new_old", "new_cyr"}
