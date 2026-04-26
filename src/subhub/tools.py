from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from subhub.service import SubHubService


ToolHandler = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


def _json_ok(data: Any) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _json_error(code: str, message: str) -> str:
    return json.dumps(
        {"ok": False, "error": {"code": code, "message": message}},
        ensure_ascii=False,
    )


@dataclass(frozen=True)
class LocalTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **params: Any) -> str:
        try:
            result = self.handler(**params)
            if inspect.isawaitable(result):
                result = await result
            return _json_ok(result)
        except ValueError as exc:
            return _json_error("INVALID_ARGUMENT", str(exc))
        except Exception as exc:
            return _json_error("TOOL_ERROR", str(exc))


class SubHubToolRegistry:
    def __init__(self, tools: list[LocalTool]):
        self._tools = {tool.name: tool for tool in tools}

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools)

    def has_tools(self) -> bool:
        return bool(self._tools)

    def get_all_definitions(self) -> list[dict[str, Any]]:
        return [tool.definition for tool in self._tools.values()]

    async def execute_tool(self, tool_name: str, **params: Any) -> str:
        tool = self._tools.get(tool_name)
        if tool is None:
            return _json_error("TOOL_NOT_FOUND", f"未找到工具: {tool_name}")
        return await tool.execute(**params)


def _object_schema(
    properties: dict[str, Any], required: list[str] | None = None
) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


def build_subhub_tools(service: SubHubService) -> list[LocalTool]:
    cycles = [
        "monthly",
        "quarterly",
        "semiannual",
        "yearly",
        "weekly",
        "daily",
        "permanent",
        "custom",
    ]
    currencies = ["CNY", "USD", "EUR", "GBP", "JPY"]

    def create_subscription(**payload: Any) -> dict[str, Any]:
        return service.add_subscription(payload)

    def update_subscription(
        id: str | None = None,
        selector_name: str | None = None,
        **payload: Any,
    ) -> dict[str, Any]:
        result = service.update_subscription_by_selector(
            subscription_id=id,
            selector_name=selector_name,
            payload=payload,
        )
        if result is None:
            raise ValueError("未找到该订阅")
        return result

    def delete_subscription(
        id: str | None = None, name: str | None = None
    ) -> dict[str, Any]:
        result = service.delete_subscription_by_selector(
            subscription_id=id, name=name
        )
        if result is None:
            raise ValueError("未找到匹配的订阅记录")
        return result

    return [
        LocalTool(
            "get_today_context",
            "获取当前日期上下文。",
            _object_schema({}),
            lambda: service.get_context_today(),
        ),
        LocalTool(
            "get_subscriptions_context",
            "获取当前订阅列表上下文。",
            _object_schema({}),
            lambda: service.get_context_subscriptions(),
        ),
        LocalTool(
            "get_accounts_context",
            "获取常用登录账号上下文。",
            _object_schema({}),
            lambda: service.get_context_accounts(),
        ),
        LocalTool(
            "get_channels_context",
            "获取常用支付渠道上下文。",
            _object_schema({}),
            lambda: service.get_context_channels(),
        ),
        LocalTool(
            "get_today_reminders",
            "获取今天起即将扣款的提醒列表。",
            _object_schema(
                {
                    "advance_days": {
                        "type": "integer",
                        "description": "提前提醒天数，留空时使用默认值",
                    }
                }
            ),
            lambda advance_days=None: service.get_today_reminders(
                advance_days=advance_days
            ),
        ),
        LocalTool(
            "list_subscriptions",
            "查询订阅列表，可按名称或计费周期过滤。",
            _object_schema(
                {
                    "name": {"type": "string", "description": "服务名称关键词"},
                    "billing_cycle": {"type": "string", "enum": cycles},
                }
            ),
            lambda name=None, billing_cycle=None: service.list_subscriptions(
                name=name, billing_cycle=billing_cycle
            ),
        ),
        LocalTool(
            "create_subscription",
            "新增订阅。只能在信息完整且用户确认后调用。",
            _object_schema(
                {
                    "name": {"type": "string"},
                    "account": {"type": "string"},
                    "payment_channel": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string", "enum": currencies},
                    "billing_cycle": {"type": "string", "enum": cycles},
                    "next_billing_date": {"type": "string"},
                    "notes": {"type": "string"},
                },
                [
                    "name",
                    "account",
                    "payment_channel",
                    "amount",
                    "currency",
                    "billing_cycle",
                    "next_billing_date",
                ],
            ),
            create_subscription,
        ),
        LocalTool(
            "update_subscription",
            "更新订阅。优先传 id；如果只有名称，传 selector_name。",
            _object_schema(
                {
                    "id": {"type": "string"},
                    "selector_name": {"type": "string"},
                    "name": {"type": "string"},
                    "account": {"type": "string"},
                    "payment_channel": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string", "enum": currencies},
                    "billing_cycle": {"type": "string", "enum": cycles},
                    "next_billing_date": {"type": "string"},
                    "notes": {"type": "string"},
                }
            ),
            update_subscription,
        ),
        LocalTool(
            "delete_subscription",
            "删除订阅。删除前必须确认。",
            _object_schema({"id": {"type": "string"}, "name": {"type": "string"}}),
            delete_subscription,
        ),
        LocalTool(
            "generate_monthly_report",
            "生成月报。mode=budget 为预算折算，mode=actual 为实际扣款。",
            _object_schema(
                {
                    "month": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["budget", "actual"],
                        "default": "budget",
                    },
                }
            ),
            lambda month=None, mode="budget": service.get_monthly_report(
                month=month, mode=mode
            ),
        ),
        LocalTool(
            "dismiss_reminder",
            "关闭提醒。target 可为订阅 id、订阅名称或 all。",
            _object_schema({"target": {"type": "string"}}, ["target"]),
            lambda target: service.dismiss_reminder(target),
        ),
    ]
