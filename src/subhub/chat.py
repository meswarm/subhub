"""LLM 对话模块。管理多轮对话和 Function Calling。"""

from datetime import date
from openai import OpenAI
from subhub.config import LLMConfig
from subhub.store import SubscriptionStore
from subhub.tools import get_tool_definitions, execute_tool
from subhub.display import format_subscriptions_table


SYSTEM_PROMPT_TEMPLATE = """你是一个个人订阅管理助手，帮助用户管理各类订阅服务。

当前日期：{today}

## 用户当前订阅列表
{subscriptions_table}

## 用户常用信息
- 常用登录账号：{accounts}
- 常用支付渠道：{channels}

## 你的工作规则
1. 用户提到新增订阅时，从对话中提取所有必要字段（服务名称、登录账号、支付渠道、金额、货币单位、计费周期、下次扣款日、备注）。
2. 如果信息不完整，必须追问。追问时列出用户已有的账号和支付渠道供选择。
3. 用户说"今天"、"刚才"时，起始日为 {today}；说"昨天"则为前一天；说"X天前"则推算日期。用户也可能直接指定日期。
4. 下次扣款日(next_billing_date)的推算：根据起始日期和计费周期自动计算。月付 = 起始日+1个自然月，年付 = +1年，周付 = +7天，日付 = +1天。如果用户明确指定了到期日期，则直接使用用户指定的日期。
5. 计费周期如果用户未说明且你不确定，必须追问。
6. 永久/买断制订阅的 next_billing_date 设为 null。
7. 用户表示"知道了"、"已处理"、"我会取消"等确认提醒时，调用 dismiss_reminder 工具。
8. 确认所有信息完整无误后才调用工具执行操作。
9. 回复使用中文，简洁明了。"""


def build_system_prompt(store: SubscriptionStore) -> str:
    """构建包含当前订阅数据的系统提示词。"""
    today = date.today().isoformat()
    subs = store.list_all()
    table = format_subscriptions_table(subs) if subs else "暂无订阅记录"
    accounts = ", ".join(store.get_unique_accounts()) or "暂无"
    channels = ", ".join(store.get_unique_channels()) or "暂无"
    return SYSTEM_PROMPT_TEMPLATE.format(
        today=today, subscriptions_table=table,
        accounts=accounts, channels=channels,
    )


class ChatSession:
    """管理与 LLM 的多轮对话和工具调用。"""

    def __init__(self, llm_config: LLMConfig, store: SubscriptionStore,
                 base_currency: str = "CNY"):
        self.client = OpenAI(api_key=llm_config.api_key, base_url=llm_config.base_url)
        self.model = llm_config.model
        self.store = store
        self.base_currency = base_currency
        self.messages: list[dict] = []
        self._refresh_system_prompt()

    def _refresh_system_prompt(self):
        """每次对话前刷新系统提示词（包含最新订阅数据）。"""
        system_msg = {"role": "system", "content": build_system_prompt(self.store)}
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = system_msg
        else:
            self.messages.insert(0, system_msg)

    def chat(self, user_input: str) -> str:
        """处理用户输入，返回助手回复。支持工具调用循环。"""
        self._refresh_system_prompt()
        self.messages.append({"role": "user", "content": user_input})

        max_iterations = 10  # 防止无限循环
        for _ in range(max_iterations):
            response = self.client.chat.completions.create(
                model=self.model, messages=self.messages,
                tools=get_tool_definitions(), tool_choice="auto",
            )
            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                self.messages.append({
                    "role": "assistant", "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name,
                                      "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    try:
                        result = execute_tool(tc.function.name, tc.function.arguments,
                                              self.store, self.base_currency)
                    except Exception as e:
                        result = f"❌ 工具执行出错：{e}"
                    self.messages.append({
                        "role": "tool", "tool_call_id": tc.id, "content": result,
                    })
                continue

            reply = msg.content or ""
            self.messages.append({"role": "assistant", "content": reply})
            # 保持消息历史在合理长度内
            if len(self.messages) > 42:
                self.messages = [self.messages[0]] + self.messages[-40:]
            return reply

        # 达到最大迭代次数
        return "⚠️ 操作过于复杂，请简化你的请求后重试。"
