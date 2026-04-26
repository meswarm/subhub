import json

import pytest

from subhub.service import SubHubService
from subhub.store import SubscriptionStore
from subhub.tools import SubHubToolRegistry, build_subhub_tools


@pytest.fixture
def registry(tmp_path):
    store = SubscriptionStore(
        tmp_path / "subs.json",
        dismissed_filepath=tmp_path / "dismissed.json",
    )
    service = SubHubService(store=store, base_currency="CNY", reminder_advance_days=3)
    return SubHubToolRegistry(build_subhub_tools(service))


def test_tool_definitions_are_openai_compatible(registry):
    definitions = registry.get_all_definitions()
    names = {item["function"]["name"] for item in definitions}
    assert "create_subscription" in names
    assert "list_subscriptions" in names
    assert "get_today_reminders" in names
    assert all(item["type"] == "function" for item in definitions)


@pytest.mark.asyncio
async def test_create_and_list_subscription(registry):
    created = await registry.execute_tool(
        "create_subscription",
        name="YouTube Premium",
        account="me@example.com",
        payment_channel="Visa",
        amount=28,
        currency="CNY",
        billing_cycle="monthly",
        next_billing_date="2026-05-01",
        notes="家庭组",
    )
    created_data = json.loads(created)
    assert created_data["ok"] is True
    assert created_data["data"]["item"]["name"] == "YouTube Premium"

    listed = json.loads(await registry.execute_tool("list_subscriptions"))
    assert listed["ok"] is True
    assert listed["data"]["total"] == 1


@pytest.mark.asyncio
async def test_unknown_tool_returns_json_error(registry):
    result = json.loads(await registry.execute_tool("missing_tool"))
    assert result["ok"] is False
    assert result["error"]["code"] == "TOOL_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_today_reminders_tool(registry):
    result = json.loads(await registry.execute_tool("get_today_reminders"))
    assert result["ok"] is True
    assert "items" in result["data"]
