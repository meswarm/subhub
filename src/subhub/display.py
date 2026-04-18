"""Markdown 格式化显示模块。"""

from subhub.store import Subscription, sort_subscriptions_by_next_billing_date

CURRENCY_SYMBOLS = {
    "CNY": "¥", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
}

CYCLE_NAMES = {
    "monthly": "月付", "quarterly": "季付", "semiannual": "半年付", "yearly": "年付", "weekly": "周付",
    "daily": "日付", "permanent": "永久", "custom": "自定义",
}

# 简单静态汇率（相对 CNY）
EXCHANGE_RATES_TO_CNY = {
    "CNY": 1.0, "USD": 7.2, "EUR": 7.8, "GBP": 9.1, "JPY": 0.048,
}


def _format_amount(amount: float, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    return f"{symbol}{amount:.2f}"


def _to_base_currency(amount: float, currency: str, base: str) -> float:
    """简单汇率换算。先转 CNY，再转目标货币。"""
    cny = amount * EXCHANGE_RATES_TO_CNY.get(currency, 1.0)
    return cny / EXCHANGE_RATES_TO_CNY.get(base, 1.0)


def _monthly_cost(sub: Subscription) -> float:
    """将订阅金额折算为月度费用。"""
    if sub.billing_cycle == "monthly":
        return sub.amount
    elif sub.billing_cycle == "quarterly":
        return round(sub.amount / 3, 2)
    elif sub.billing_cycle == "semiannual":
        return round(sub.amount / 6, 2)
    elif sub.billing_cycle == "yearly":
        return round(sub.amount / 12, 2)
    elif sub.billing_cycle == "weekly":
        return round(sub.amount * 4.33, 2)
    elif sub.billing_cycle == "daily":
        return round(sub.amount * 30, 2)
    return 0.0  # permanent/custom 不计入


def format_subscriptions_table(subs: list[Subscription]) -> str:
    """格式化订阅列表为 Markdown 表格。"""
    if not subs:
        return "📋 暂无订阅记录。"
    ordered_subs = sort_subscriptions_by_next_billing_date(subs)
    lines = [
        "| 服务名称 | 登录账号 | 支付渠道 | 金额 | 周期 | 下次扣款日 | 备注 |",
        "|----------|----------|----------|------|------|-----------|------|",
    ]
    for s in ordered_subs:
        amount_str = _format_amount(s.amount, s.currency)
        cycle_str = CYCLE_NAMES.get(s.billing_cycle, s.billing_cycle)
        date_str = s.next_billing_date or "—"
        notes_str = s.notes or ""
        lines.append(
            f"| {s.name} | {s.account} | {s.payment_channel} "
            f"| {amount_str} | {cycle_str} | {date_str} | {notes_str} |"
        )
    return "\n".join(lines)


def format_reminder_table(subs: list[Subscription], remind_date: str,
                          today: str) -> str:
    """格式化提醒内容为 Markdown 表格。"""
    if not subs:
        return ""
    rd_short = remind_date[5:]
    header = "## 订阅扣款提醒\n"
    header += f"- 日期：{today}\n"
    header += f"- 将在 {rd_short} 扣款：\n\n"
    lines = [
        "| 服务名称 | 金额 | 支付渠道 | 登录账号 |",
        "|----------|------|----------|----------|",
    ]
    for s in subs:
        amount_str = _format_amount(s.amount, s.currency)
        lines.append(
            f"| {s.name} | {amount_str} | {s.payment_channel} | {s.account} |"
        )
    return header + "\n".join(lines)


def format_monthly_report(subs: list[Subscription], month: str,
                          base_currency: str = "CNY") -> str:
    """生成月度订阅预算报表（将各周期折算为月费）。"""
    # 过滤掉永久/买断和自定义
    recurring = [s for s in subs if s.billing_cycle not in ("permanent", "custom")]

    if not recurring:
        return f"## {month} 月度订阅预算报表\n\n暂无周期性订阅。"

    symbol = CURRENCY_SYMBOLS.get(base_currency, base_currency)
    header = f"## {month} 月度订阅预算报表\n\n"
    lines = [
        f"| 服务名称 | 原始金额 | 周期 | 折算月费({symbol}) |",
        f"|----------|----------|------|------------------|",
    ]
    total = 0.0
    for s in recurring:
        orig = _format_amount(s.amount, s.currency)
        cycle = CYCLE_NAMES.get(s.billing_cycle, s.billing_cycle)
        monthly = _monthly_cost(s)
        converted = _to_base_currency(monthly, s.currency, base_currency)
        total += converted
        lines.append(f"| {s.name} | {orig} | {cycle} | {symbol}{converted:.2f} |")

    lines.append(f"| **合计** | | | **{symbol}{total:.2f}** |")
    return header + "\n".join(lines)


def format_actual_billing_report(subs: list[Subscription], month: str,
                                  base_currency: str = "CNY") -> str:
    """生成月度实际扣款报表（仅包含本月有扣款日的订阅）。"""
    if not subs:
        return f"## {month} 实际扣款报表\n\n本月无扣款记录。"

    symbol = CURRENCY_SYMBOLS.get(base_currency, base_currency)
    header = f"## {month} 实际扣款报表\n\n"
    lines = [
        f"| 服务名称 | 金额 | 扣款日 | 折算({symbol}) |",
        f"|----------|------|--------|----------------|",
    ]
    total = 0.0
    for s in subs:
        orig = _format_amount(s.amount, s.currency)
        billing_date = s.next_billing_date or "—"
        converted = _to_base_currency(s.amount, s.currency, base_currency)
        total += converted
        lines.append(f"| {s.name} | {orig} | {billing_date} | {symbol}{converted:.2f} |")

    lines.append(f"| **合计** | | | **{symbol}{total:.2f}** |")
    return header + "\n".join(lines)
