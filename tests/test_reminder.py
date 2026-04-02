"""reminder 模块测试。"""

from datetime import date
from subhub.reminder import check_reminders
from subhub.store import SubscriptionStore


def test_check_reminders_has_upcoming(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="测试服务", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-06", notes="")
    output = check_reminders(store, today=date(2026, 4, 3), advance_days=3)
    assert output is not None
    assert "测试服务" in output


def test_check_reminders_no_upcoming(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="测试服务", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    output = check_reminders(store, today=date(2026, 4, 3), advance_days=3)
    assert output is None


def test_check_reminders_dismissed(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json")
    sub = store.add(name="已确认", account="a", payment_channel="b",
                    amount=10.0, currency="CNY", billing_cycle="monthly",
                    next_billing_date="2026-04-06", notes="")
    from subhub.tools import _dismissed_reminders, clear_dismissed_reminders
    clear_dismissed_reminders()
    _dismissed_reminders.add(sub.id)
    output = check_reminders(store, today=date(2026, 4, 3), advance_days=3)
    assert output is None
    clear_dismissed_reminders()


def test_check_reminders_auto_advances_expired(tmp_path):
    """测试提醒检查时自动推进已过期订阅。"""
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="已过期", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-03-01", notes="")
    # 检查不会提醒（因为推进后日期不在 advance_days 范围内）
    output = check_reminders(store, today=date(2026, 4, 3), advance_days=3)
    assert output is None
    # 但扣款日已被推进
    subs = store.list_all()
    assert subs[0].next_billing_date == "2026-04-01"
