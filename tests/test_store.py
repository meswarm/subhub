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
    updated = store.update(name="ChatGPT", amount=10.0, billing_cycle="monthly")
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
    assert advanced[0].next_billing_date == "2026-04-30"
