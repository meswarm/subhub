"""SubHub 应用服务层。为聊天层、HTTP API 和守护进程提供统一业务能力。"""

from dataclasses import asdict
from datetime import date
from typing import Optional

from subhub.display import (
    CYCLE_NAMES,
    _format_amount,
    _monthly_cost,
    _to_base_currency,
    format_actual_billing_report,
    format_monthly_report,
    format_subscriptions_table,
)
from subhub.store import Subscription, SubscriptionStore
from subhub.store import sort_subscriptions_by_next_billing_date


_VALID_BILLING_CYCLES = {
    "monthly", "quarterly", "semiannual", "yearly", "weekly", "daily", "permanent", "custom",
}


class SubHubService:
    """封装订阅管理核心业务逻辑。"""

    def __init__(self, store: SubscriptionStore,
                 base_currency: str = "CNY",
                 reminder_advance_days: int = 3):
        self.store = store
        self.base_currency = base_currency
        self.reminder_advance_days = reminder_advance_days

    def serialize_subscription(self, sub: Subscription) -> dict:
        return asdict(sub)

    def _subscription_snapshot(self) -> dict:
        return self.get_context_subscriptions()

    def list_subscriptions(self, name: Optional[str] = None,
                           billing_cycle: Optional[str] = None) -> dict:
        items = sort_subscriptions_by_next_billing_date(
            self.store.find(name=name, billing_cycle=billing_cycle)
        )
        return {
            "items": [self.serialize_subscription(s) for s in items],
            "total": len(items),
        }

    def get_subscription(self, subscription_id: str) -> Optional[dict]:
        for sub in self.store.list_all():
            if sub.id == subscription_id:
                return self.serialize_subscription(sub)
        return None

    def add_subscription(self, payload: dict) -> dict:
        self._validate_subscription_payload(payload, partial=False)
        next_billing_date = self._normalize_next_billing_date(
            payload.get("billing_cycle"), payload.get("next_billing_date")
        )
        sub = self.store.add(
            name=payload["name"],
            account=payload["account"],
            payment_channel=payload["payment_channel"],
            amount=float(payload["amount"]),
            currency=payload["currency"],
            billing_cycle=payload["billing_cycle"],
            next_billing_date=next_billing_date,
            notes=payload.get("notes", ""),
        )
        return {
            "message": "已添加订阅",
            "item": self.serialize_subscription(sub),
            "subscriptions": self._subscription_snapshot(),
        }

    def update_subscription(self, subscription_id: str, payload: dict) -> Optional[dict]:
        self._validate_subscription_payload(payload, partial=True)
        update_fields = {k: v for k, v in payload.items() if v is not None}
        if "amount" in update_fields:
            update_fields["amount"] = float(update_fields["amount"])
        if "billing_cycle" in payload or "next_billing_date" in payload:
            update_fields["next_billing_date"] = self._normalize_next_billing_date(
                payload.get("billing_cycle"), payload.get("next_billing_date")
            )
        updated = self.store.update(id=subscription_id, **update_fields)
        if updated is None:
            return None
        return {
            "message": "已更新订阅",
            "item": self.serialize_subscription(updated),
        }

    def update_subscription_by_selector(self, *, subscription_id: Optional[str] = None,
                                        selector_name: Optional[str] = None,
                                        payload: dict | None = None) -> Optional[dict]:
        payload = payload or {}
        self._validate_subscription_payload(payload, partial=True)
        update_fields = {k: v for k, v in payload.items() if v is not None}
        if "amount" in update_fields:
            update_fields["amount"] = float(update_fields["amount"])
        if "billing_cycle" in payload or "next_billing_date" in payload:
            update_fields["next_billing_date"] = self._normalize_next_billing_date(
                payload.get("billing_cycle"), payload.get("next_billing_date")
            )
        updated = self.store.update(
            id=subscription_id,
            selector_name=selector_name,
            **update_fields,
        )
        if updated is None:
            return None
        return {
            "message": "已更新订阅",
            "item": self.serialize_subscription(updated),
        }

    def delete_subscription(self, subscription_id: str) -> Optional[dict]:
        deleted_item = self.get_subscription(subscription_id)
        if deleted_item is None:
            return None
        if not self.store.remove(id=subscription_id):
            return None
        return {
            "message": "已删除订阅",
            "id": subscription_id,
            "item": deleted_item,
            "subscriptions": self._subscription_snapshot(),
        }

    def delete_subscription_by_name(self, name: str) -> Optional[dict]:
        matches = [
            self.serialize_subscription(sub)
            for sub in self.store.list_all()
            if sub.name == name
        ]
        if not matches:
            return None
        if not self.store.remove(name=name):
            return None
        return {
            "message": "已删除订阅",
            "name": name,
            "items": matches,
            "subscriptions": self._subscription_snapshot(),
        }

    def delete_subscription_by_selector(self, *, subscription_id: Optional[str] = None,
                                        name: Optional[str] = None) -> Optional[dict]:
        if subscription_id:
            return self.delete_subscription(subscription_id)
        if name:
            return self.delete_subscription_by_name(name)
        return None

    def dismiss_reminder(self, target: str, today: Optional[date] = None) -> dict:
        today = today or date.today()
        if target == "all":
            for sub in self.store.list_all():
                self.store.dismiss_reminder(sub.id, today)
            return {"message": "已关闭所有扣款提醒"}

        for sub in self.store.list_all():
            if sub.name == target or sub.id == target:
                self.store.dismiss_reminder(sub.id, today)
                return {
                    "message": f"已关闭 {sub.name} 的扣款提醒",
                    "item": self.serialize_subscription(sub),
                }
        return {}

    def get_monthly_report(self, month: Optional[str] = None,
                           mode: str = "budget") -> dict:
        month = month or date.today().strftime("%Y-%m")
        year, mon = self._parse_month(month)

        if mode == "actual":
            subs = self.store.get_billing_in_month(year, mon)
            markdown = format_actual_billing_report(
                subs, month=month, base_currency=self.base_currency,
            )
            items = []
            total = 0.0
            for sub in subs:
                converted = _to_base_currency(sub.amount, sub.currency, self.base_currency)
                total += converted
                items.append({
                    "id": sub.id,
                    "name": sub.name,
                    "amount": sub.amount,
                    "currency": sub.currency,
                    "billing_cycle": sub.billing_cycle,
                    "next_billing_date": sub.next_billing_date,
                    "converted_amount": round(converted, 2),
                })
            title = f"{month} 实际扣款报表"
        elif mode == "budget":
            subs = self.store.list_all()
            recurring = [s for s in subs if s.billing_cycle not in ("permanent", "custom")]
            markdown = format_monthly_report(
                subs, month=month, base_currency=self.base_currency,
            )
            items = []
            total = 0.0
            for sub in recurring:
                monthly_cost = _monthly_cost(sub)
                converted = _to_base_currency(monthly_cost, sub.currency, self.base_currency)
                total += converted
                items.append({
                    "id": sub.id,
                    "name": sub.name,
                    "amount": sub.amount,
                    "currency": sub.currency,
                    "billing_cycle": sub.billing_cycle,
                    "cycle_name": CYCLE_NAMES.get(sub.billing_cycle, sub.billing_cycle),
                    "monthly_cost_base_currency": round(converted, 2),
                })
            title = f"{month} 月度订阅预算报表"
        else:
            raise ValueError("mode 仅支持 budget 或 actual")

        return {
            "month": month,
            "mode": mode,
            "title": title,
            "items": items,
            "summary": {
                "total_base_currency": round(total, 2),
                "base_currency": self.base_currency,
            },
            "markdown": markdown,
        }

    def get_context_today(self) -> dict:
        return {"today": date.today().isoformat()}

    def get_context_subscriptions(self) -> dict:
        subs = sort_subscriptions_by_next_billing_date(self.store.list_all())
        return {
            "items": [self.serialize_subscription(s) for s in subs],
            "markdown": format_subscriptions_table(subs) if subs else "暂无订阅记录",
        }

    def get_context_accounts(self) -> dict:
        accounts = sorted(self.store.get_unique_accounts())
        return {
            "items": accounts,
            "text": ", ".join(accounts) if accounts else "暂无",
        }

    def get_context_channels(self) -> dict:
        channels = sorted(self.store.get_unique_channels())
        return {
            "items": channels,
            "text": ", ".join(channels) if channels else "暂无",
        }

    def get_context_overview(self) -> dict:
        subscriptions = self.get_context_subscriptions()
        accounts = self.get_context_accounts()
        channels = self.get_context_channels()
        return {
            "today": date.today().isoformat(),
            "subscriptions": subscriptions["items"],
            "subscriptions_markdown": subscriptions["markdown"],
            "accounts": accounts["items"],
            "accounts_text": accounts["text"],
            "channels": channels["items"],
            "channels_text": channels["text"],
        }

    def get_today_reminders(self, today: Optional[date] = None,
                            advance_days: Optional[int] = None) -> dict:
        today = today or date.today()
        advance_days = advance_days if advance_days is not None else self.reminder_advance_days
        self.store.auto_advance_expired(today)
        upcoming = self.store.get_upcoming(today, advance_days)
        dismissed = self.store.get_dismissed_reminders(today)
        items = []
        for sub in upcoming:
            if sub.id in dismissed:
                continue
            items.append({
                "id": sub.id,
                "name": sub.name,
                "account": sub.account,
                "payment_channel": sub.payment_channel,
                "amount": _format_amount(sub.amount, sub.currency),
                "currency": sub.currency,
                "next_billing_date": sub.next_billing_date,
                "days_left": advance_days,
            })
        message = None
        if items:
            names = "、".join(item["name"] for item in items)
            target_date = items[0]["next_billing_date"]
            message = f"订阅提醒：{names} 将于 {target_date} 扣款。"
        return {
            "date": today.isoformat(),
            "items": items,
            "message": message,
        }

    def _parse_month(self, month: str) -> tuple[int, int]:
        try:
            year_str, mon_str = month.split("-", 1)
            year = int(year_str)
            mon = int(mon_str)
        except ValueError as exc:
            raise ValueError("month 格式必须为 YYYY-MM") from exc
        if mon < 1 or mon > 12:
            raise ValueError("month 格式必须为 YYYY-MM")
        return year, mon

    def _validate_subscription_payload(self, payload: dict, partial: bool):
        required = [
            "name", "account", "payment_channel", "amount",
            "currency", "billing_cycle", "next_billing_date",
        ]
        if not partial:
            missing = [field for field in required if field not in payload]
            if missing:
                raise ValueError(f"缺少必要字段: {', '.join(missing)}")

        if "billing_cycle" in payload and payload["billing_cycle"] not in _VALID_BILLING_CYCLES:
            raise ValueError("billing_cycle 不合法")

        if payload.get("billing_cycle") != "permanent":
            if (not partial or "next_billing_date" in payload) and payload.get("next_billing_date") in (None, ""):
                raise ValueError("非永久订阅必须提供 next_billing_date")

    def _normalize_next_billing_date(self,
                                     billing_cycle: Optional[str],
                                     next_billing_date: Optional[str]) -> Optional[str]:
        if billing_cycle == "permanent":
            if next_billing_date in (None, "", "永久", "permanent"):
                return None
            return next_billing_date
        return next_billing_date
