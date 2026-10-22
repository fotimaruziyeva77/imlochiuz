import datetime as dt

import pytest

from storage import Settings, Storage
from texts import JADVAL, TEXTS, t


@pytest.fixture
def db(tmp_path):
    day = [dt.date(2026, 10, 21)]
    s = Storage(str(tmp_path / "t.db"), salt="s", today=lambda: day[0])
    s.day = day
    yield s
    s.close()


def test_default_settings(db):
    assert db.get_settings(1) == Settings("auto", "old")


def test_set_settings(db):
    db.set_mode(1, "new_old")
    db.set_ui(1, "new")
    db.set_mode(1, "cyr_new")
    assert db.get_settings(1) == Settings("cyr_new", "new")
    with pytest.raises(ValueError):
        db.set_mode(1, "bad")


def test_legacy_mode_names(db):
    db._db.execute("INSERT INTO user_settings (user_id, mode, ui) VALUES (5, 'old', 'old')")
    assert db.get_settings(5).mode == "new_old"


def test_users_and_admin_report(db):
    assert db.touch_user(1) is True
    assert db.touch_user(1) is False          # o'sha kuni qayta
    db.touch_user(2)
    db.day[0] = dt.date(2026, 10, 22)
    assert db.touch_user(1) is False          # eski foydalanuvchi, yangi kun
    assert db.touch_user(3) is True
    db.track("convert_old_new", 3)

    rep = db.admin_report()
    assert rep.total == 3
    assert rep.new_today == 1 and rep.new_week == 3 and rep.new_month == 3
    assert rep.active_today == 2 and rep.active_week == 3
    assert rep.daily_new[-2:] == [("2026-10-21", 2), ("2026-10-22", 1)]
    assert len(rep.daily_new) == 7
    assert rep.events_today == {"convert_old_new": 1}
    assert db.user_ids() == [1, 2, 3]


def test_stats_daily_and_weekly(db):
    db.track("convert_new", 1)
    db.track("convert_new", 1)
    db.track("inline", 2)
    db.day[0] = dt.date(2026, 10, 22)
    db.track("convert_new", 3)

    today = db.report(1)
    assert today["users"] == 1 and today["events"] == {"convert_new": 1}

    week = db.report(7)
    assert week["users"] == 3
    assert week["events"] == {"convert_new": 3, "inline": 1}


def test_stats_store_no_raw_user_id(db, tmp_path):
    db.track("start", 123456789)
    rows = db._db.execute("SELECT user_hash FROM daily_users").fetchall()
    assert rows and "123456789" not in rows[0][0]


def test_ui_texts_converted_to_new():
    assert "Assalomu" in t("start", "old", username="bot")
    new = t("start", "new", username="choy_bot")
    assert "yangi özbek alifbosi" in new
    assert "@choy_bot" in new          # username o'zgarmaydi
    assert "<b>" in new and "<code>" in new


@pytest.mark.parametrize("key", sorted(TEXTS))
def test_all_texts_render(key):
    for ui in ("old", "new"):
        assert t(key, ui, username="u", current="x", length=1)


def test_t_keeps_kwargs_unconverted():
    from texts import mode_label
    assert "OʻZ→ÖZ" in t("rejim", "new", current=mode_label("old_new"))
    assert mode_label("cyr_new") == "ЎЗ→ÖZ" and mode_label("new_cyr") == "ÖZ→ЎЗ"


def test_jadval_mentions_all_letters():
    for letter in ("Ö", "Ğ", "Ş", "Ç", "ng", "Tutuq"):
        assert letter in JADVAL
