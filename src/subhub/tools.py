"""LLM Function Calling 工具定义与执行。"""

import json
from datetime import date
from typing import Optional
from subhub.store import SubscriptionStore
from subhub.display import format_subscriptions_table, format_monthly_report


def get_tool_definitions() -> list[dict]:
    """返回 OpenAI tools 格式的工具定义。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "add_subscription",
                "description": "新增一条订阅记录。所有字段必须提供完整信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "服务名称"},
                        "account": {"type": "string", "description": "登录账号"},
                        "payment_channel": {"type": "string", "description": "支付渠道"},
                        "amount": {"type": "number", "description": "金额"},
                        "currency": {"type": "string", "description": "货币单位，如 CNY、USD"},
                        "billing_cycle": {
                            "type": "string",
                            "enum": ["monthly", "yearly", "weekly", "daily", "permanent", "custom"],
                        },
                        "next_billing_date": {
                            "type": ["string", "null"],
                            "description": "下次扣款日期 YYYY-MM-DD，永久制填 null",
                        },
                        "notes": {"type": "string", "description": "备注"},
                    },
                    "required": ["name", "account", "payment_channel", "amount",
                                 "currency", "billing_cycle", "next_billing_date"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remove_subscription",
                "description": "删除一条订阅记录。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "服务名称"},
                        "id": {"type": "string", "description": "记录ID"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_subscription",
                "description": "更新订阅记录的字段。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "服务名称（定位用）"},
                        "id": {"type": "string", "description": "记录ID（定位用）"},
                        "new_name": {"type": "string", "description": "新服务名称"},
                        "account": {"type": "string"},
                        "payment_channel": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                        "billing_cycle": {"type": "string"},
                        "next_billing_date": {"type": ["string", "null"]},
                        "notes": {"type": "string"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_subscriptions",
                "description": "查询订阅列表。无参数返回全部。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "按名称模糊搜索"},
                        "billing_cycle": {"type": "string", "description": "按周期过滤"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "dismiss_reminder",
                "description": "关闭订阅扣款提醒。用户确认时调用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "订阅名称、ID 或 'all'",
                        },
                    },
                    "required": ["target"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_monthly_report",
                "description": "生成月度订阅费用统计报表。当用户询问本月费用、订阅总额或要求生成报表时调用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {
                            "type": "string",
                            "description": "月份，格式 YYYY-MM，默认当前月",
                        },
                    },
                },
            },
        },
    ]


_dismissed_reminders: set[str] = set()


def get_dismissed_reminders() -> set[str]:
    return _dismissed_reminders


def clear_dismissed_reminders():
    _dismissed_reminders.clear()


def execute_tool(tool_name: str, arguments_json: str,
                 store: SubscriptionStore,
                 base_currency: str = "CNY") -> str:
    """执行工具调用并返回结果字符串。"""
    args = json.loads(arguments_json) if arguments_json else {}

    if tool_name == "add_subscription":
        sub = store.add(
            name=args["name"], account=args["account"],
            payment_channel=args["payment_channel"], amount=args["amount"],
            currency=args["currency"], billing_cycle=args["billing_cycle"],
            next_billing_date=args.get("next_billing_date"),
            notes=args.get("notes", ""),
        )
        return f"✅ 已添加订阅：{sub.name}（ID: {sub.id}）"

    elif tool_name == "remove_subscription":
        success = store.remove(id=args.get("id"), name=args.get("name"))
        if success:
            return f"✅ 已删除订阅：{args.get('name') or args.get('id')}"
        return "❌ 未找到匹配的订阅记录"

    elif tool_name == "update_subscription":
        update_fields = {}
        field_map = {
            "new_name": "name", "account": "account",
            "payment_channel": "payment_channel", "amount": "amount",
            "currency": "currency", "billing_cycle": "billing_cycle",
            "next_billing_date": "next_billing_date", "notes": "notes",
        }
        for arg_key, field_key in field_map.items():
            if arg_key in args:
                update_fields[field_key] = args[arg_key]
        updated = store.update(id=args.get("id"), name=args.get("name"), **update_fields)
        if updated:
            return f"✅ 已更新订阅：{updated.name}"
        return "❌ 未找到匹配的订阅记录"

    elif tool_name == "list_subscriptions":
        subs = store.find(name=args.get("name"), billing_cycle=args.get("billing_cycle"))
        if not subs:
            return "📋 没有找到匹配的订阅记录。"
        return format_subscriptions_table(subs)

    elif tool_name == "dismiss_reminder":
        target = args["target"]
        if target == "all":
            for sub in store.list_all():
                _dismissed_reminders.add(sub.id)
            return "✅ 已关闭所有扣款提醒"
        for sub in store.list_all():
            if sub.name == target or sub.id == target:
                _dismissed_reminders.add(sub.id)
                return f"✅ 已关闭 {sub.name} 的扣款提醒"
        return "❌ 未找到匹配的订阅"

    elif tool_name == "generate_monthly_report":
        month = args.get("month") or date.today().strftime("%Y-%m")
        subs = store.list_all()
        return format_monthly_report(subs, month=month,
                                     base_currency=base_currency)

    return f"❌ 未知工具：{tool_name}"
