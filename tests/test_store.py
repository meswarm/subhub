"""store 模块测试。"""

from datetime import date

import pytest

from subhub.store import SubscriptionStore, Subscription, advance_billing_date


@pytest.fixture
def store(tmp_path):
    """创建一个使用临时目录的 store。"""
    return SubscriptionStore(tmp_path / "subs.json")


def test_add_and_list(store):
    sub = store.add(
        name="QQ音乐会员",
        account="QQ号12800",
        payment_channel="支付宝",
        amount=12.0,
        currency="CNY",
        billing_cycle="monthly",
        next_billing_date="2026-05-03",
        notes="",
    )
    assert sub.name == "QQ音乐会员"
    assert sub.id is not None
    assert len(store.list_all()) == 1


def test_remove_by_name(store):
    store.add(name="测试服务", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-06-01", notes="")
    removed = store.remove(name="测试服务")
    assert removed is True
    assert len(store.list_all()) == 0


def test_remove_by_id(store):
    sub = store.add(name="测试服务", account="a", payment_channel="b",
                    amount=10.0, currency="CNY", billing_cycle="monthly",
                    next_billing_date="2026-06-01", notes="")
    removed = store.remove(id=sub.id)
    assert removed is True
    assert len(store.list_all()) == 0


def test_update(store):
    store.add(name="ChatGPT", account="google", payment_channel="visa",
              amount=20.0, currency="USD", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    updated = store.update(selector_name="ChatGPT", amount=10.0, billing_cycle="monthly")
    assert updated is not None
    assert updated.amount == 10.0


def test_persistence(tmp_path):
    filepath = tmp_path / "subs.json"
    store1 = SubscriptionStore(filepath)
    store1.add(name="持久化测试", account="a", payment_channel="b",
               amount=5.0, currency="CNY", billing_cycle="monthly",
               next_billing_date="2026-07-01", notes="")

    store2 = SubscriptionStore(filepath)
    assert len(store2.list_all()) == 1
    assert store2.list_all()[0].name == "持久化测试"


def test_get_upcoming(store):
    store.add(name="即将扣款", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-06", notes="")
    store.add(name="不扣款", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    store.add(name="永久会员", account="a", payment_channel="b",
              amount=99.0, currency="CNY", billing_cycle="permanent",
              next_billing_date=None, notes="")

    upcoming = store.get_upcoming(date(2026, 4, 3), advance_days=3)
    assert len(upcoming) == 1
    assert upcoming[0].name == "即将扣款"


def test_get_unique_accounts(store):
    store.add(name="A", account="账号1", payment_channel="支付宝",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    store.add(name="B", account="账号2", payment_channel="微信",
              amount=20.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-06-01", notes="")
    assert set(store.get_unique_accounts()) == {"账号1", "账号2"}
    assert set(store.get_unique_channels()) == {"支付宝", "微信"}


def test_advance_billing_date_monthly():
    assert advance_billing_date("2026-04-03", "monthly") == "2026-05-03"
    # 月末边界：1月31日 → 2月28日
    assert advance_billing_date("2026-01-31", "monthly") == "2026-02-28"


def test_advance_billing_date_quarterly():
    assert advance_billing_date("2026-04-03", "quarterly") == "2026-07-03"
    assert advance_billing_date("2026-11-30", "quarterly") == "2027-02-28"


def test_advance_billing_date_semiannual():
    assert advance_billing_date("2026-04-03", "semiannual") == "2026-10-03"
    assert advance_billing_date("2026-08-31", "semiannual") == "2027-02-28"


def test_advance_billing_date_yearly():
    assert advance_billing_date("2026-04-03", "yearly") == "2027-04-03"


def test_advance_billing_date_weekly():
    assert advance_billing_date("2026-04-03", "weekly") == "2026-04-10"


def test_advance_billing_date_daily():
    assert advance_billing_date("2026-04-03", "daily") == "2026-04-04"


def test_advance_billing_date_permanent():
    assert advance_billing_date(None, "permanent") is None


def test_auto_advance_expired(store):
    store.add(name="已过期月付", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-03-30", notes="")
    store.add(name="未过期", account="a", payment_channel="b",
              amount=20.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")

    advanced = store.auto_advance_expired(date(2026, 4, 3))
    assert len(advanced) == 1
    assert advanced[0].name == "已过期月付"
    # 2026-03-30 → 2026-04-30（>= 2026-04-03，一次推进即够）
    assert advanced[0].next_billing_date == "2026-04-30"


def test_auto_advance_expired_multi_cycles(store):
    """测试严重滞后的订阅会循环推进多个周期。"""
    store.add(name="严重滞后", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-01-15", notes="")

    advanced = store.auto_advance_expired(date(2026, 4, 3))
    assert len(advanced) == 1
    # 2026-01-15 → 02-15 → 03-15 → 04-15（>= 2026-04-03）
    assert advanced[0].next_billing_date == "2026-04-15"


# --- Dismissed persistence tests ---

def test_dismiss_and_get(store):
    sub = store.add(name="测试", account="a", payment_channel="b",
                    amount=10.0, currency="CNY", billing_cycle="monthly",
                    next_billing_date="2026-05-01", notes="")
    store.dismiss_reminder(sub.id, date(2026, 4, 8))
    dismissed = store.get_dismissed_reminders(date(2026, 4, 8))
    assert sub.id in dismissed


def test_dismissed_expires_next_day(store):
    sub = store.add(name="测试", account="a", payment_channel="b",
                    amount=10.0, currency="CNY", billing_cycle="monthly",
                    next_billing_date="2026-05-01", notes="")
    store.dismiss_reminder(sub.id, date(2026, 4, 8))
    # 第二天不应该再出现
    dismissed = store.get_dismissed_reminders(date(2026, 4, 9))
    assert sub.id not in dismissed


def test_clear_dismissed(store):
    sub = store.add(name="测试", account="a", payment_channel="b",
                    amount=10.0, currency="CNY", billing_cycle="monthly",
                    next_billing_date="2026-05-01", notes="")
    store.dismiss_reminder(sub.id, date(2026, 4, 8))
    store.clear_dismissed_reminders()
    dismissed = store.get_dismissed_reminders(date(2026, 4, 8))
    assert len(dismissed) == 0


def test_dismissed_persists_across_instances(tmp_path):
    filepath = tmp_path / "subs.json"
    store1 = SubscriptionStore(filepath)
    sub = store1.add(name="持久化测试", account="a", payment_channel="b",
                     amount=5.0, currency="CNY", billing_cycle="monthly",
                     next_billing_date="2026-07-01", notes="")
    store1.dismiss_reminder(sub.id, date(2026, 4, 8))

    store2 = SubscriptionStore(filepath)
    dismissed = store2.get_dismissed_reminders(date(2026, 4, 8))
    assert sub.id in dismissed


def test_dismissed_filepath_can_be_configured(tmp_path):
    dismissed_path = tmp_path / "state" / "ignored.json"
    store = SubscriptionStore(tmp_path / "subs.json", dismissed_filepath=dismissed_path)
    sub = store.add(name="测试", account="a", payment_channel="b",
                    amount=10.0, currency="CNY", billing_cycle="monthly",
                    next_billing_date="2026-05-01", notes="")
    store.dismiss_reminder(sub.id, date(2026, 4, 8))

    assert dismissed_path.exists()


# --- get_billing_in_month tests ---

def test_get_billing_in_month(store):
    store.add(name="本月扣款", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-15", notes="")
    store.add(name="下月扣款", account="a", payment_channel="b",
              amount=20.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    store.add(name="永久会员", account="a", payment_channel="b",
              amount=99.0, currency="CNY", billing_cycle="permanent",
              next_billing_date=None, notes="")

    billing = store.get_billing_in_month(2026, 4)
    assert len(billing) == 1
    assert billing[0].name == "本月扣款"
