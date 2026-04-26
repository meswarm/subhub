"""订阅数据存储模块。管理 JSON 文件的 CRUD 操作。"""

import json
import os
import threading
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
    billing_cycle: str       # monthly, quarterly, semiannual, yearly, weekly, daily, permanent, custom
    next_billing_date: Optional[str]  # ISO格式 YYYY-MM-DD，permanent时为None
    notes: str = ""


class SubscriptionStore:
    """基于 JSON 文件的订阅数据管理。线程安全。"""

    def __init__(self, filepath: Path, dismissed_filepath: Path | None = None):
        self._filepath = Path(filepath)
        self._subscriptions: list[Subscription] = []
        self._lock = threading.RLock()
        self._dismissed_filepath = (
            Path(dismissed_filepath)
            if dismissed_filepath is not None
            else self._filepath.parent / "dismissed.json"
        )
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
        # 原子写入：先写临时文件，再 rename，防止写入中断导致数据损坏
        tmp_path = self._filepath.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._filepath)

    def _gen_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def add(self, *, name: str, account: str, payment_channel: str,
            amount: float, currency: str, billing_cycle: str,
            next_billing_date: Optional[str], notes: str = "") -> Subscription:
        """新增一条订阅记录。"""
        with self._lock:
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
        with self._lock:
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
               selector_name: Optional[str] = None, **kwargs) -> Optional[Subscription]:
        """更新订阅字段。通过 id 或 selector_name 定位，kwargs 为要更新的字段。"""
        with self._lock:
            target = None
            for sub in self._subscriptions:
                if (id and sub.id == id) or (selector_name and sub.name == selector_name):
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
        with self._lock:
            return list(self._subscriptions)

    def find(self, *, name: Optional[str] = None,
             billing_cycle: Optional[str] = None) -> list[Subscription]:
        """按条件过滤查询。name 支持模糊匹配。"""
        with self._lock:
            results = self._subscriptions
            if name:
                results = [s for s in results if name.lower() in s.name.lower()]
            if billing_cycle:
                results = [s for s in results if s.billing_cycle == billing_cycle]
            return results

    def get_upcoming(self, today: date, advance_days: int) -> list[Subscription]:
        """获取在 advance_days 天内（含当天）扣款的订阅。"""
        with self._lock:
            target = today + timedelta(days=advance_days)
            target_str = target.isoformat()
            return [
                s for s in self._subscriptions
                if s.next_billing_date == target_str
            ]

    def auto_advance_expired(self, today: date) -> list[Subscription]:
        """自动推进已过期的周期性订阅的扣款日。循环推进直到不再过期。返回被推进的订阅列表。"""
        with self._lock:
            advanced = []
            for sub in self._subscriptions:
                if (sub.next_billing_date
                        and sub.billing_cycle not in ("permanent", "custom")
                        and date.fromisoformat(sub.next_billing_date) < today):
                    # 循环推进直到扣款日 >= 今天，防止长期未打开导致落后多个周期
                    prev = None
                    while (sub.next_billing_date
                           and sub.next_billing_date != prev
                           and date.fromisoformat(sub.next_billing_date) < today):
                        prev = sub.next_billing_date
                        sub.next_billing_date = advance_billing_date(
                            sub.next_billing_date, sub.billing_cycle
                        )
                    advanced.append(sub)
            if advanced:
                self._save()
            return advanced

    def get_unique_accounts(self) -> list[str]:
        """获取所有不重复的登录账号。"""
        with self._lock:
            return list(set(s.account for s in self._subscriptions))

    def get_unique_channels(self) -> list[str]:
        """获取所有不重复的支付渠道。"""
        with self._lock:
            return list(set(s.payment_channel for s in self._subscriptions))

    # --- 提醒关闭状态持久化 ---

    def _load_dismissed(self) -> dict[str, str]:
        """加载已关闭提醒状态。返回 {subscription_id: dismiss_date_str}。"""
        if self._dismissed_filepath.exists():
            try:
                with open(self._dismissed_filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_dismissed(self, dismissed: dict[str, str]):
        """保存已关闭提醒状态。原子写入。"""
        self._dismissed_filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._dismissed_filepath.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(dismissed, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._dismissed_filepath)

    def dismiss_reminder(self, subscription_id: str, today: date):
        """标记一条订阅的提醒为已关闭（当天有效）。"""
        with self._lock:
            dismissed = self._load_dismissed()
            dismissed[subscription_id] = today.isoformat()
            self._save_dismissed(dismissed)

    def get_dismissed_reminders(self, today: date) -> set[str]:
        """获取当天仍有效的已关闭提醒 ID 集合。"""
        with self._lock:
            dismissed = self._load_dismissed()
            today_str = today.isoformat()
            return {sid for sid, d in dismissed.items() if d == today_str}

    def clear_dismissed_reminders(self):
        """清空所有已关闭提醒。"""
        with self._lock:
            self._save_dismissed({})

    # --- 月度实际扣款查询 ---

    def get_billing_in_month(self, year: int, month: int) -> list[Subscription]:
        """获取指定月份内实际有扣款日的订阅列表。"""
        with self._lock:
            result = []
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
            for sub in self._subscriptions:
                if (sub.next_billing_date
                        and sub.billing_cycle not in ("permanent", "custom")):
                    billing = date.fromisoformat(sub.next_billing_date)
                    if first_day <= billing <= last_day:
                        result.append(sub)
            return result


def sort_subscriptions_by_next_billing_date(subs: list[Subscription]) -> list[Subscription]:
    """按下次扣款日升序排序；无扣款日的订阅排在最后。"""

    def sort_key(sub: Subscription):
        if not sub.next_billing_date:
            return (1, date.max)
        return (0, date.fromisoformat(sub.next_billing_date))

    return sorted(subs, key=sort_key)


def advance_billing_date(current_date: Optional[str],
                         billing_cycle: str) -> Optional[str]:
    """根据计费周期推算下一个扣款日期。

    规则：
    - monthly: +1个自然月（处理月末边界）
    - quarterly: +3个自然月
    - semiannual: +6个自然月
    - yearly: +1年
    - weekly: +7天
    - daily: +1天
    - permanent/custom: 返回 None
    """
    if current_date is None or billing_cycle in ("permanent", "custom"):
        return None

    d = date.fromisoformat(current_date)

    if billing_cycle in ("monthly", "quarterly", "semiannual"):
        month_offset = {
            "monthly": 1,
            "quarterly": 3,
            "semiannual": 6,
        }[billing_cycle]
        month = d.month + month_offset
        year = d.year
        if month > 12:
            year += (month - 1) // 12
            month = ((month - 1) % 12) + 1
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
