# Yangi alifbo boti — 1-bosqich (MVP)

Telegram bot: kirill, eski lotin yoki aralash matnni yangi oʻzbek alifbosiga
(Oʻ→Ö, Gʻ→Ğ, Sh→Ş, Ch→Ç) va qaytarib oʻgiradi. TZ: `Yangi alifbo boti — Texnik topshiriq.docx`.

## Tuzilma

| Fayl | Vazifasi |
|---|---|
| `converter.py` | Oʻgirish yadrosi (TZ 5-boʻlim): `to_new`, `to_old`, `to_cyr`, `convert` (6 yoʻnalish), `detect`. Sof Python |
| `bot.py` | Telegram qatlami (aiogram 3): buyruqlar, matn, inline, tugmalar, `/admin`, webhook/polling |
| `web.py`, `web/` | Sayt: bosh sahifa, onlayn oʻgirgich, `POST /api/convert`, `GET /api/stats` |
| `texts.py` | Interfeys matnlari; yangi alifbodagi interfeys converter orqali hosil qilinadi |
| `storage.py` | Foydalanuvchi sozlamalari va anonim statistika (SQLite; 2-bosqichda PostgreSQL) |
| `tg_utils.py` | Entity → himoyalangan oraliq, uzun matnni boʻlish, spam limiti |
| `config.py` | Muhit oʻzgaruvchilari / `.env` |
| `tests/` | pytest: converter, yordamchilar, storage, bot handlerlari (tarmoqsiz) |

## MVP qamrovi (TZ 8-boʻlim)

| Talab | Holat |
|---|---|
| F1.1 Avtomatik oʻgirish (yozuv aniqlanadi) | ✅ |
| F1.2 Teskari rejim (`/rejim`, «Teskari» tugmasi) | ✅ |
| F1.4 Inline rejim («Yangi alifboda» / «Eski lotinda») | ✅ |
| F1.5 Buyruqlar `/start /help /jadval /rejim /til` | ✅ |
| F1.6 Harflar jadvali | ✅ |
| F1.7 Uzun matn: 4096 dan uzun — boʻlinadi, 10 000 dan uzun — `.txt` fayl | ✅ |
| F1.8 URL, e-mail, @username, #hashtag, kod himoyasi (regex + Telegram entity) | ✅ |
| F1.10 «Nusxa olish», «Teskari», «Xato haqida xabar» tugmalari | ✅ (xato — faqat hisoblagich; matn saqlash F8.4, 2-bosqich) |
| F1.3 Kirillga oʻgirish; `/rejim` — 6 yoʻnalish (ЎЗ/OʻZ/ÖZ) + Avto | ✅ |
| F8.1 Statistika: `/admin` — jami/yangi/faol foydalanuvchilar, 7 kunlik grafik, soʻrovlar | ✅ |
| Ulashish: `/ulashish`, «Loyiha haqida», saytdagi ulashish tugmalari | ✅ |
| Sayt va onlayn oʻgirgich (bot bilan bir xil yadro) | ✅ |
| Spam limiti 30 soʻrov/daqiqa | ✅ (jarayon xotirasida) |

## Ishga tushirish

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/python
cp .env.example .env    # BOT_TOKEN ni yozing
.venv/Scripts/python bot.py
```

`WEBHOOK_URL` boʻsh boʻlsa — polling; berilsa — webhook. Ikkala holatda ham sayt `HOST:PORT` da ishlaydi
(`WEB_ENABLED=0` bilan oʻchiriladi); `/health` — tekshiruv manzili. `SITE_URL` berilsa, botda «🌐 Sayt» tugmasi chiqadi.

Admin: botga `/admin` yuboring — `ADMIN_IDS` boʻsh boʻlsa, bot sizning Telegram ID'ingizni koʻrsatadi.
Uni `.env` dagi `ADMIN_IDS` ga yozib, botni qayta ishga tushiring.
Inline rejim uchun BotFather'da `/setinline` yoqilishi shart.

Docker:

```bash
docker compose up -d --build
```

## Testlar

```bash
.venv/Scripts/python -m pytest -q
```

CI: `.github/workflows/tests.yml` (Python 3.11–3.13).

## Maxfiylik

- Foydalanuvchi matni saqlanmaydi va log'ga yozilmaydi; tugmalar xabar matnining oʻzi bilan ishlaydi.
- Bazada sozlamalar (`mode`, `ui`), foydalanuvchi ID va qoʻshilgan/oxirgi faollik sanasi (nechta odam qoʻshilganini sanash uchun) hamda kunlik hisoblagichlar.
- Sayt API soʻrovlari va IP manzillar log'ga yozilmaydi; saytda faqat umumiy foydalanuvchilar soni koʻrsatiladi (10 tadan oshganda).

## Maʼlum cheklovlar

- Oʻzlashma soʻzlardagi sh/ch (inglizcha nomlar) ham oʻgiriladi — istisnolar lugʻati F1.9 (2-bosqich).
- Yangi → eski oʻgirishda yangi yozuvdagi har bir alohida s+h tutuq bilan ajratiladi (`Ishoq → Is'hoq`, TZ 5.3).
- Eski lotinda bitta apostrof bilan yozilgan `mo'jiza` (tutuq oʻrnida) `möjiza` boʻladi; toʻgʻri yozuv — `mo''jiza`.
- Lotin → kirill bir ma'noli emas: `ts` doim `тс` (ц tiklanmaydi), `ь` qoʻyilmaydi; `sirk` → `сирк`.
- Tutuq belgisi standart `'`; imlo qoidalari tasdiqlangach `TUTUQ` orqali oʻzgartiriladi.
- Spam limiti va statistika bitta jarayonga moʻljallangan; gorizontal kengayishda Redis/PostgreSQL'ga oʻtadi.
