"""提醒模块。后台线程定时检查即将扣款的订阅。"""

import threading
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional, Callable

from subhub.store import SubscriptionStore
from subhub.display import format_reminder_table, format_monthly_report


def check_reminders(store: SubscriptionStore, today: date,
                    advance_days: int) -> Optional[str]:
    """检查是否有需要提醒的即将扣款订阅。返回提醒文本或 None。"""
    # 先自动推进已过期的周期性订阅
    store.auto_advance_expired(today)

    upcoming = store.get_upcoming(today, advance_days)
    dismissed = store.get_dismissed_reminders(today)
    upcoming = [s for s in upcoming if s.id not in dismissed]
    if not upcoming:
        return None
    target_date = today + timedelta(days=advance_days)
    return format_reminder_table(
        upcoming, remind_date=target_date.isoformat(), today=today.isoformat(),
    )


def check_reminder_windows(
    store: SubscriptionStore, today: date, reminder_days: list[int]
) -> list[str]:
    """检查多个提醒窗口。每个订阅在每个窗口当天只发送一次。"""
    store.auto_advance_expired(today)
    messages: list[str] = []

    for days_before in reminder_days:
        upcoming = store.get_upcoming(today, days_before)
        unsent = []
        for sub in upcoming:
            if store.has_sent_reminder(sub.id, days_before, today):
                continue
            unsent.append(sub)

        if not unsent:
            continue

        target_date = today + timedelta(days=days_before)
        message = format_reminder_table(
            unsent,
            remind_date=target_date.isoformat(),
            today=today.isoformat(),
        )
        if message:
            message += "\n\n请回复你想继续续费还是删除该订阅；我会先展示完整信息，待你确认后再执行。"
            messages.append(message)

        for sub in unsent:
            store.mark_reminder_sent(sub.id, days_before, today)

    return messages


class ReminderThread(threading.Thread):
    """后台提醒线程，定时检查扣款提醒和月末报表。"""

    def __init__(self, store: SubscriptionStore, reminder_days: list[int],
                 check_interval_hours: int,
                 output_callback: Callable[[str], None],
                 base_currency: str = "CNY"):
        super().__init__(daemon=True)
        self.store = store
        self.reminder_days = list(reminder_days)
        self.check_interval_seconds = check_interval_hours * 3600
        self.output_callback = output_callback
        self.base_currency = base_currency
        self._stop_event = threading.Event()
        self._last_check_date: Optional[date] = None
        self._month_report_sent: Optional[str] = None

    def _is_last_day_of_month(self, d: date) -> bool:
        return d.day == monthrange(d.year, d.month)[1]

    def run(self):
        while not self._stop_event.is_set():
            today = date.today()
            self._last_check_date = today

            # 扣款提醒
            for output in check_reminder_windows(self.store, today, self.reminder_days):
                self.output_callback(output)

            # 月末最后一天自动生成月度报表
            month_str = today.strftime("%Y-%m")
            if (self._is_last_day_of_month(today)
                    and self._month_report_sent != month_str):
                subs = self.store.list_all()
                report = format_monthly_report(
                    subs, month=month_str,
                    base_currency=self.base_currency,
                )
                self.output_callback(report)
                self._month_report_sent = month_str

            self._stop_event.wait(self.check_interval_seconds)

    def stop(self):
        self._stop_event.set()
