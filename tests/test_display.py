"""display 模块测试。"""

from subhub.display import (
    format_subscriptions_table, format_reminder_table, format_monthly_report,
)
from subhub.store import Subscription


def _make_sub(**kwargs):
    defaults = dict(
        id="abc123", name="测试", account="账号", payment_channel="支付宝",
        amount=10.0, currency="CNY", billing_cycle="monthly",
        next_billing_date="2026-05-01", notes=""
    )
    defaults.update(kwargs)
    return Subscription(**defaults)


def test_format_subscriptions_table():
    subs = [
        _make_sub(name="QQ音乐", amount=12.0, currency="CNY"),
        _make_sub(name="ChatGPT", amount=20.0, currency="USD"),
    ]
    table = format_subscriptions_table(subs)
    assert "QQ音乐" in table
    assert "ChatGPT" in table
    assert "¥12.00" in table
    assert "$20.00" in table


def test_format_reminder_table():
    subs = [_make_sub(name="QQ音乐", amount=12.0)]
    table = format_reminder_table(subs, remind_date="2026-04-06", today="2026-04-03")
    assert "⚠️" in table
    assert "QQ音乐" in table
    assert "04-06" in table


def test_format_empty():
    table = format_subscriptions_table([])
    assert "暂无" in table


def test_format_monthly_report():
    subs = [
        _make_sub(name="QQ音乐", amount=12.0, currency="CNY", billing_cycle="monthly"),
        _make_sub(name="ChatGPT", amount=20.0, currency="USD", billing_cycle="monthly"),
        _make_sub(name="永久软件", amount=99.0, currency="CNY", billing_cycle="permanent"),
    ]
    report = format_monthly_report(subs, month="2026-04", base_currency="CNY")
    assert "QQ音乐" in report
    assert "ChatGPT" in report
    assert "永久软件" not in report  # 永久/买断不计入月度费用
    assert "合计" in report
    assert "2026-04" in report
