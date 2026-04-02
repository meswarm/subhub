"""订阅数据存储模块。管理 JSON 文件的 CRUD 操作。"""

import json
import uuid
from calendar import monthrange
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class Subscription:
    id: str
    name: str
    account: str
    payment_channel: str
    amount: float
    currency: str
    billing_cycle: str       # monthly, yearly, weekly, daily, permanent, custom
    next_billing_date: Optional[str]  # ISO格式 YYYY-MM-DD，permanent时为None
    notes: str = ""


class SubscriptionStore:
    """基于 JSON 文件的订阅数据管理。"""

    def __init__(self, filepath: Path):
        self._filepath = Path(filepath)
        self._subscriptions: list[Subscription] = []
        self._load()

    def _load(self):
        if self._filepath.exists():
            with open(self._filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._subscriptions = [
                Subscription(**item) for item in data.get("subscriptions", [])
            ]
        else:
            self._subscriptions = []

    def _save(self):
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {"subscriptions": [asdict(s) for s in self._subscriptions]}
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _gen_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def add(self, *, name: str, account: str, payment_channel: str,
            amount: float, currency: str, billing_cycle: str,
            next_billing_date: Optional[str], notes: str = "") -> Subscription:
        """新增一条订阅记录。"""
        sub = Subscription(
            id=self._gen_id(), name=name, account=account,
            payment_channel=payment_channel, amount=amount, currency=currency,
            billing_cycle=billing_cycle, next_billing_date=next_billing_date,
            notes=notes,
        )
        self._subscriptions.append(sub)
        self._save()
        return sub

    def remove(self, *, id: Optional[str] = None,
               name: Optional[str] = None) -> bool:
        """删除订阅。通过 id 或 name 匹配。"""
        before = len(self._subscriptions)
        if id:
            self._subscriptions = [s for s in self._subscriptions if s.id != id]
        elif name:
            self._subscriptions = [s for s in self._subscriptions if s.name != name]
        else:
            return False
        if len(self._subscriptions) < before:
            self._save()
            return True
        return False

    def update(self, *, id: Optional[str] = None,
               name: Optional[str] = None, **kwargs) -> Optional[Subscription]:
        """更新订阅字段。通过 id 或 name 定位，kwargs 为要更新的字段。"""
        target = None
        for sub in self._subscriptions:
            if (id and sub.id == id) or (name and sub.name == name):
                target = sub
                break
        if target is None:
            return None
        valid_fields = {
            "name", "account", "payment_channel", "amount",
            "currency", "billing_cycle", "next_billing_date", "notes"
        }
        for k, v in kwargs.items():
            if k in valid_fields:
                setattr(target, k, v)
        self._save()
        return target

    def list_all(self) -> list[Subscription]:
        """返回所有订阅。"""
        return list(self._subscriptions)

    def find(self, *, name: Optional[str] = None,
             billing_cycle: Optional[str] = None) -> list[Subscription]:
        """按条件过滤查询。name 支持模糊匹配。"""
        results = self._subscriptions
        if name:
            results = [s for s in results if name.lower() in s.name.lower()]
        if billing_cycle:
            results = [s for s in results if s.billing_cycle == billing_cycle]
        return results

    def get_upcoming(self, today: date, advance_days: int) -> list[Subscription]:
        """获取在 advance_days 天后扣款的订阅。"""
        target = today + timedelta(days=advance_days)
        target_str = target.isoformat()
        return [
            s for s in self._subscriptions
            if s.next_billing_date == target_str
        ]

    def auto_advance_expired(self, today: date) -> list[Subscription]:
        """自动推进已过期的周期性订阅的扣款日。返回被推进的订阅列表。"""
        advanced = []
        for sub in self._subscriptions:
            if (sub.next_billing_date
                    and sub.billing_cycle not in ("permanent", "custom")
                    and date.fromisoformat(sub.next_billing_date) < today):
                sub.next_billing_date = advance_billing_date(
                    sub.next_billing_date, sub.billing_cycle
                )
                advanced.append(sub)
        if advanced:
            self._save()
        return advanced

    def get_unique_accounts(self) -> list[str]:
        """获取所有不重复的登录账号。"""
        return list(set(s.account for s in self._subscriptions))

    def get_unique_channels(self) -> list[str]:
        """获取所有不重复的支付渠道。"""
        return list(set(s.payment_channel for s in self._subscriptions))


def advance_billing_date(current_date: Optional[str],
                         billing_cycle: str) -> Optional[str]:
    """根据计费周期推算下一个扣款日期。

    规则：
    - monthly: +1个自然月（处理月末边界）
    - yearly: +1年
    - weekly: +7天
    - daily: +1天
    - permanent/custom: 返回 None
    """
    if current_date is None or billing_cycle in ("permanent", "custom"):
        return None

    d = date.fromisoformat(current_date)

    if billing_cycle == "monthly":
        month = d.month + 1
        year = d.year
        if month > 12:
            month = 1
            year += 1
        max_day = monthrange(year, month)[1]
        day = min(d.day, max_day)
        return date(year, month, day).isoformat()

    elif billing_cycle == "yearly":
        try:
            return date(d.year + 1, d.month, d.day).isoformat()
        except ValueError:  # 2月29日 → 2月28日
            return date(d.year + 1, d.month, 28).isoformat()

    elif billing_cycle == "weekly":
        return (d + timedelta(days=7)).isoformat()

    elif billing_cycle == "daily":
        return (d + timedelta(days=1)).isoformat()

    return None
