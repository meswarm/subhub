"""API 模块测试。"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from subhub.api import create_app
from subhub.config import AppConfig, DataConfig, ReminderConfig, ReportConfig, ServerConfig, WebhookConfig
from subhub.store import SubscriptionStore


def _make_client(tmp_path):
    config = AppConfig(
        data=DataConfig(path=str(tmp_path), filename="subs.json"),
        server=ServerConfig(host="127.0.0.1", port=58000),
        reminder=ReminderConfig(advance_days=3, check_interval_hours=1),
        report=ReportConfig(base_currency="CNY"),
        webhook=WebhookConfig(),
    )
    store = SubscriptionStore(tmp_path / "subs.json")
    app = create_app(config=config, store=store)
    return TestClient(app), store


def test_health(tmp_path):
    client, _ = _make_client(tmp_path)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_create_and_list_subscription(tmp_path):
    client, _ = _make_client(tmp_path)

    for item in [
        {
            "name": "稍后扣款",
            "account": "test@gmail.com",
            "payment_channel": "Visa",
            "amount": 15.99,
            "currency": "USD",
            "billing_cycle": "monthly",
            "next_billing_date": "2026-05-10",
            "notes": "",
        },
        {
            "name": "最先扣款",
            "account": "test@gmail.com",
            "payment_channel": "Visa",
            "amount": 9.99,
            "currency": "USD",
            "billing_cycle": "monthly",
            "next_billing_date": "2026-05-01",
            "notes": "",
        },
        {
            "name": "永久订阅",
            "account": "test@gmail.com",
            "payment_channel": "Visa",
            "amount": 199.0,
            "currency": "CNY",
            "billing_cycle": "permanent",
            "next_billing_date": "永久",
            "notes": "",
        },
    ]:
        response = client.post("/api/subscriptions", json=item)
        assert response.status_code == 201

    list_response = client.get("/api/subscriptions")
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert len(items) == 3
    assert [item["name"] for item in items] == ["最先扣款", "稍后扣款", "永久订阅"]


def test_create_permanent_subscription_with_literal_text(tmp_path):
    client, _ = _make_client(tmp_path)

    response = client.post(
        "/api/subscriptions",
        json={
            "name": "买断软件",
            "account": "test@gmail.com",
            "payment_channel": "Visa",
            "amount": 199.0,
            "currency": "CNY",
            "billing_cycle": "permanent",
            "next_billing_date": "永久",
            "notes": "",
        },
    )
    assert response.status_code == 201
    item = response.json()["data"]["item"]
    assert item["billing_cycle"] == "permanent"
    assert item["next_billing_date"] is None


def test_update_and_delete_subscription(tmp_path):
    client, store = _make_client(tmp_path)
    sub = store.add(
        name="Spotify",
        account="user@qq.com",
        payment_channel="支付宝",
        amount=15.0,
        currency="CNY",
        billing_cycle="monthly",
        next_billing_date="2026-05-01",
        notes="",
    )

    patch_response = client.patch(
        f"/api/subscriptions/{sub.id}",
        json={"amount": 18.0, "notes": "家庭版"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["item"]["amount"] == 18.0

    delete_response = client.delete(f"/api/subscriptions/{sub.id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["id"] == sub.id


def test_selector_based_update_and_delete(tmp_path):
    client, store = _make_client(tmp_path)
    store.add(
        name="Notion",
        account="user@example.com",
        payment_channel="Visa",
        amount=8.0,
        currency="USD",
        billing_cycle="monthly",
        next_billing_date="2026-05-02",
        notes="",
    )

    update_response = client.post(
        "/api/subscriptions/update",
        json={"selector_name": "Notion", "notes": "团队版"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["item"]["notes"] == "团队版"

    delete_response = client.post(
        "/api/subscriptions/delete",
        json={"name": "Notion"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["name"] == "Notion"


def test_selector_based_update_can_change_name(tmp_path):
    client, store = _make_client(tmp_path)
    store.add(
        name="旧名称",
        account="user@example.com",
        payment_channel="Visa",
        amount=8.0,
        currency="USD",
        billing_cycle="monthly",
        next_billing_date="2026-05-02",
        notes="",
    )

    update_response = client.post(
        "/api/subscriptions/update",
        json={"selector_name": "旧名称", "name": "新名称"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["item"]["name"] == "新名称"


def test_monthly_report_and_context(tmp_path):
    client, store = _make_client(tmp_path)
    store.add(
        name="YouTube Premium",
        account="a",
        payment_channel="b",
        amount=20.0,
        currency="CNY",
        billing_cycle="monthly",
        next_billing_date="2026-04-20",
        notes="",
    )

    report_response = client.get("/api/reports/monthly", params={"month": "2026-04"})
    assert report_response.status_code == 200
    report = report_response.json()["data"]
    assert report["mode"] == "budget"
    assert "YouTube Premium" in report["markdown"]

    context_response = client.get("/api/context/overview")
    assert context_response.status_code == 200
    overview = context_response.json()["data"]
    assert "YouTube Premium" in overview["subscriptions_markdown"]
    assert overview["accounts_text"] == "a"


def test_dismiss_reminder_and_today_reminders(tmp_path):
    client, store = _make_client(tmp_path)
    sub = store.add(
        name="提醒测试",
        account="acc",
        payment_channel="Visa",
        amount=10.0,
        currency="CNY",
        billing_cycle="monthly",
        next_billing_date=(date.today() + timedelta(days=3)).isoformat(),
        notes="",
    )

    reminders_response = client.get("/api/reminders/today")
    assert reminders_response.status_code == 200
    assert reminders_response.json()["data"]["items"][0]["name"] == "提醒测试"

    dismiss_response = client.post("/api/reminders/dismiss", json={"target": sub.id})
    assert dismiss_response.status_code == 200
    assert "已关闭" in dismiss_response.json()["data"]["message"]

    reminders_response_2 = client.get("/api/reminders/today")
    assert reminders_response_2.status_code == 200
    assert reminders_response_2.json()["data"]["items"] == []
