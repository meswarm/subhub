"""SubHub HTTP API。供 Link 中间件和其他外部系统调用。"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import JSONResponse

from subhub.config import AppConfig, load_config
from subhub.reminder import ReminderThread
from subhub.service import SubHubService
from subhub.store import SubscriptionStore
from subhub.webhook import send_text


class SubscriptionCreateRequest(BaseModel):
    name: str
    account: str
    payment_channel: str
    amount: float
    currency: str
    billing_cycle: str
    next_billing_date: Optional[str] = None
    notes: str = ""


class SubscriptionUpdateRequest(BaseModel):
    name: Optional[str] = None
    account: Optional[str] = None
    payment_channel: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    next_billing_date: Optional[str] = None
    notes: Optional[str] = None


class DeleteByNameRequest(BaseModel):
    name: str


class SubscriptionUpdateBySelectorRequest(SubscriptionUpdateRequest):
    id: Optional[str] = None
    selector_name: Optional[str] = None


class SubscriptionDeleteBySelectorRequest(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class DismissReminderRequest(BaseModel):
    target: str


def create_app(config: AppConfig | None = None,
               store: SubscriptionStore | None = None) -> FastAPI:
    if config is None:
        config = load_config()
    if store is None:
        store = SubscriptionStore(
            config.data.filepath,
            dismissed_filepath=config.data.dismissed_filepath,
        )

    service = SubHubService(
        store=store,
        base_currency=config.report.base_currency,
        reminder_advance_days=config.reminder.advance_days,
    )

    def webhook_callback(text: str):
        response = send_text(config.webhook, text)
        if not response.ok:
            print(f"Webhook 推送失败: {response.error}")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        reminder = None
        if config.webhook.enabled:
            reminder = ReminderThread(
                store=store,
                advance_days=config.reminder.advance_days,
                check_interval_hours=config.reminder.check_interval_hours,
                output_callback=webhook_callback,
                base_currency=config.report.base_currency,
            )
            reminder.start()
        app.state.reminder_thread = reminder
        try:
            yield
        finally:
            if reminder is not None:
                reminder.stop()

    app = FastAPI(title="SubHub API", version="0.1.0", lifespan=lifespan)
    app.state.service = service

    def ok(data: dict | list | str | None = None, status_code: int = 200):
        return JSONResponse(status_code=status_code, content={"ok": True, "data": data})

    def fail(status_code: int, code: str, message: str):
        return JSONResponse(
            status_code=status_code,
            content={
                "ok": False,
                "error": {"code": code, "message": message},
            },
        )

    @app.get("/api/health")
    def health():
        return ok({"status": "ok"})

    @app.get("/api/subscriptions")
    def list_subscriptions(name: Optional[str] = None,
                           billing_cycle: Optional[str] = None):
        return ok(service.list_subscriptions(name=name, billing_cycle=billing_cycle))

    @app.get("/api/subscriptions/{subscription_id}")
    def get_subscription(subscription_id: str):
        item = service.get_subscription(subscription_id)
        if item is None:
            return fail(404, "NOT_FOUND", "未找到该订阅")
        return ok(item)

    @app.post("/api/subscriptions")
    def create_subscription(body: SubscriptionCreateRequest):
        try:
            return ok(service.add_subscription(body.model_dump()), status_code=201)
        except ValueError as exc:
            return fail(400, "INVALID_ARGUMENT", str(exc))

    @app.patch("/api/subscriptions/{subscription_id}")
    def update_subscription(subscription_id: str, body: SubscriptionUpdateRequest):
        try:
            updated = service.update_subscription(
                subscription_id, body.model_dump(exclude_unset=True)
            )
        except ValueError as exc:
            return fail(400, "INVALID_ARGUMENT", str(exc))
        if updated is None:
            return fail(404, "NOT_FOUND", "未找到该订阅")
        return ok(updated)

    @app.delete("/api/subscriptions/{subscription_id}")
    def delete_subscription(subscription_id: str):
        result = service.delete_subscription(subscription_id)
        if result is None:
            return fail(404, "NOT_FOUND", "未找到该订阅")
        return ok(result)

    @app.post("/api/subscriptions/delete-by-name")
    def delete_subscription_by_name(body: DeleteByNameRequest):
        result = service.delete_subscription_by_name(body.name)
        if result is None:
            return fail(404, "NOT_FOUND", "未找到匹配的订阅记录")
        return ok(result)

    @app.post("/api/subscriptions/update")
    def update_subscription_by_selector(body: SubscriptionUpdateBySelectorRequest):
        if not body.id and not body.selector_name:
            return fail(400, "INVALID_ARGUMENT", "必须提供 id 或 selector_name")
        payload = body.model_dump(exclude_unset=True)
        subscription_id = payload.pop("id", None)
        selector_name = payload.pop("selector_name", None)
        try:
            updated = service.update_subscription_by_selector(
                subscription_id=subscription_id,
                selector_name=selector_name,
                payload=payload,
            )
        except ValueError as exc:
            return fail(400, "INVALID_ARGUMENT", str(exc))
        if updated is None:
            return fail(404, "NOT_FOUND", "未找到该订阅")
        return ok(updated)

    @app.post("/api/subscriptions/delete")
    def delete_subscription_by_selector(body: SubscriptionDeleteBySelectorRequest):
        if not body.id and not body.name:
            return fail(400, "INVALID_ARGUMENT", "必须提供 id 或 name")
        result = service.delete_subscription_by_selector(subscription_id=body.id, name=body.name)
        if result is None:
            return fail(404, "NOT_FOUND", "未找到匹配的订阅记录")
        return ok(result)

    @app.get("/api/reports/monthly")
    def monthly_report(month: Optional[str] = None, mode: str = "budget"):
        try:
            return ok(service.get_monthly_report(month=month, mode=mode))
        except ValueError as exc:
            return fail(400, "INVALID_ARGUMENT", str(exc))

    @app.post("/api/reminders/dismiss")
    def dismiss_reminder(body: DismissReminderRequest):
        result = service.dismiss_reminder(body.target)
        if not result:
            return fail(404, "NOT_FOUND", "未找到匹配的订阅")
        return ok(result)

    @app.get("/api/reminders/today")
    def today_reminders(advance_days: Optional[int] = None):
        return ok(service.get_today_reminders(advance_days=advance_days))

    @app.get("/api/context/today")
    def context_today():
        return ok(service.get_context_today())

    @app.get("/api/context/subscriptions")
    def context_subscriptions():
        return ok(service.get_context_subscriptions())

    @app.get("/api/context/accounts")
    def context_accounts():
        return ok(service.get_context_accounts())

    @app.get("/api/context/channels")
    def context_channels():
        return ok(service.get_context_channels())

    @app.get("/api/context/overview")
    def context_overview():
        return ok(service.get_context_overview())

    return app
