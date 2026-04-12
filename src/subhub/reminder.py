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


class ReminderThread(threading.Thread):
    """后台提醒线程，定时检查扣款提醒和月末报表。"""

    def __init__(self, store: SubscriptionStore, advance_days: int,
                 check_interval_hours: int,
                 output_callback: Callable[[str], None],
                 base_currency: str = "CNY"):
        super().__init__(daemon=True)
        self.store = store
        self.advance_days = advance_days
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
            if self._last_check_date and self._last_check_date != today:
                self.store.clear_dismissed_reminders()
            self._last_check_date = today

            # 扣款提醒
            output = check_reminders(self.store, today, self.advance_days)
            if output:
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
