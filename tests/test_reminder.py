"""reminder 模块测试。"""

from datetime import date
from subhub.reminder import check_reminders, check_reminder_windows
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
    from datetime import date as _date
    store.dismiss_reminder(sub.id, _date(2026, 4, 3))
    output = check_reminders(store, today=date(2026, 4, 3), advance_days=3)
    assert output is None
    store.clear_dismissed_reminders()


def test_check_reminders_auto_advances_expired(tmp_path):
    """测试提醒检查时自动推进已过期订阅（循环推进直到不再过期）。"""
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="已过期", account="a", payment_channel="b",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-03-01", notes="")
    # 检查不会提醒（因为推进后日期不在 advance_days 范围内）
    output = check_reminders(store, today=date(2026, 4, 3), advance_days=3)
    assert output is None
    # 但扣款日已被循环推进到 today 之后
    subs = store.list_all()
    assert subs[0].next_billing_date == "2026-05-01"


def test_check_reminder_windows_returns_messages_for_multiple_windows(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="7天提醒", account="a", payment_channel="微信",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-10", notes="")
    store.add(name="3天提醒", account="b", payment_channel="支付宝",
              amount=20.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-06", notes="")

    messages = check_reminder_windows(
        store,
        today=date(2026, 4, 3),
        reminder_days=[7, 3, 2, 1],
    )

    assert len(messages) == 2
    assert any("7天提醒" in message for message in messages)
    assert any("3天提醒" in message for message in messages)


def test_check_reminder_windows_marks_each_window_once(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="单次提醒", account="a", payment_channel="微信",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-10", notes="")

    first = check_reminder_windows(
        store,
        today=date(2026, 4, 3),
        reminder_days=[7, 3, 2, 1],
    )
    second = check_reminder_windows(
        store,
        today=date(2026, 4, 3),
        reminder_days=[7, 3, 2, 1],
    )

    assert len(first) == 1
    assert second == []


def test_check_reminder_windows_sends_different_windows_on_different_days(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="多窗口提醒", account="a", payment_channel="微信",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-10", notes="")

    seven_day = check_reminder_windows(
        store,
        today=date(2026, 4, 3),
        reminder_days=[7, 3, 2, 1],
    )
    three_day = check_reminder_windows(
        store,
        today=date(2026, 4, 7),
        reminder_days=[7, 3, 2, 1],
    )

    assert len(seven_day) == 1
    assert len(three_day) == 1
    assert "多窗口提醒" in seven_day[0]
    assert "多窗口提醒" in three_day[0]


def test_check_reminder_windows_appends_follow_up_prompt(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json")
    store.add(name="待处理服务", account="a", payment_channel="微信",
              amount=10.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-04-06", notes="")

    messages = check_reminder_windows(
        store,
        today=date(2026, 4, 3),
        reminder_days=[7, 3, 2, 1],
    )

    assert len(messages) == 1
    assert "继续续费还是删除" in messages[0]
