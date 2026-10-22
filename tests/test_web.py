import pytest
from aiohttp.test_utils import TestClient, TestServer

from config import Config
from storage import Storage
from web import create_web_app


@pytest.fixture
async def client(tmp_path):
    db = Storage(str(tmp_path / "web.db"))
    db.touch_user(1)
    db.touch_user(2)
    app = create_web_app(db, Config(bot_token="1:x", web_rate_limit=5), "imlochiuz_bot")
    async with TestClient(TestServer(app)) as c:
        c.db = db
        yield c
    db.close()


async def test_index_has_bot_links(client):
    resp = await client.get("/")
    html = await resp.text()
    assert resp.status == 200
    assert "https://t.me/imlochiuz_bot" in html
    assert "https://t.me/share/url?url=https%3A//t.me/imlochiuz_bot&amp;text=" in html
    assert "{{" not in html


async def test_static_logo(client):
    resp = await client.get("/static/logo.webp")
    assert resp.status == 200 and resp.content_type == "image/webp"


@pytest.mark.parametrize(
    "direction, text, result, used",
    [
        ("auto", "Тошкент шаҳри", "Toşkent şahri", "cyr_new"),
        ("auto", "O'zbekiston", "Özbekiston", "old_new"),
        ("auto", "Özbekiston", "Oʻzbekiston", "new_old"),
        ("new_cyr", "Özbekiston", "Ўзбекистон", "new_cyr"),
    ],
)
async def test_api_convert(client, direction, text, result, used):
    resp = await client.post("/api/convert", json={"text": text, "direction": direction})
    assert resp.status == 200
    assert await resp.json() == {"result": result, "direction": used}


async def test_api_convert_errors(client):
    assert (await client.post("/api/convert", data="not json")).status == 400
    assert (await client.post("/api/convert", json={"direction": "auto"})).status == 400
    assert (await client.post("/api/convert", json={"text": "x", "direction": "bad"})).status == 400
    assert (await client.post("/api/convert", json={"text": "a" * 10_001})).status == 413


async def test_api_rate_limit(client):
    codes = [(await client.post("/api/convert", json={"text": "choy"})).status for _ in range(6)]
    assert codes == [200] * 5 + [429]


async def test_api_stats_and_tracking(client):
    await client.post("/api/convert", json={"text": "choy"})
    assert await (await client.get("/api/stats")).json() == {"users": 2}
    assert client.db.admin_report().events_today == {"web_convert": 1}


async def test_health(client):
    assert await (await client.get("/health")).text() == "ok"
