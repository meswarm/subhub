"""tools 模块测试。"""

import json
import pytest
from subhub.tools import get_tool_definitions, execute_tool
from subhub.store import SubscriptionStore


@pytest.fixture
def store(tmp_path):
    return SubscriptionStore(tmp_path / "subs.json")


def test_tool_definitions_structure():
    defs = get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) == 6
    names = {d["function"]["name"] for d in defs}
    assert names == {
        "add_subscription", "remove_subscription",
        "update_subscription", "list_subscriptions",
        "dismiss_reminder", "generate_monthly_report",
    }


def test_execute_add(store):
    args = json.dumps({
        "name": "QQ音乐会员", "account": "QQ号12800",
        "payment_channel": "支付宝", "amount": 12.0, "currency": "CNY",
        "billing_cycle": "monthly", "next_billing_date": "2026-05-03", "notes": "",
    })
    result = execute_tool("add_subscription", args, store)
    assert "QQ音乐会员" in result
    assert len(store.list_all()) == 1


def test_execute_list(store):
    store.add(name="测试", account="a", payment_channel="b",
              amount=10, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    result = execute_tool("list_subscriptions", "{}", store)
    assert "测试" in result


def test_execute_remove(store):
    store.add(name="待删除", account="a", payment_channel="b",
              amount=10, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    result = execute_tool("remove_subscription", json.dumps({"name": "待删除"}), store)
    assert len(store.list_all()) == 0


def test_execute_update(store):
    store.add(name="ChatGPT", account="google", payment_channel="visa",
              amount=20.0, currency="USD", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    result = execute_tool("update_subscription",
                          json.dumps({"name": "ChatGPT", "amount": 10.0}), store)
    assert store.list_all()[0].amount == 10.0


def test_execute_monthly_report(store):
    store.add(name="QQ音乐", account="a", payment_channel="b",
              amount=12.0, currency="CNY", billing_cycle="monthly",
              next_billing_date="2026-05-01", notes="")
    result = execute_tool("generate_monthly_report",
                          json.dumps({"month": "2026-04"}), store)
    assert "QQ音乐" in result
    assert "合计" in result
