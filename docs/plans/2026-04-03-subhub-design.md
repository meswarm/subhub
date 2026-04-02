# SubHub — 个人订阅管理系统设计文档

> 日期：2026-04-03
> 状态：已批准

## 概述

SubHub 是一个基于终端的个人订阅管理工具。用户通过与 LLM（qwen3.5-flash）的自然语言对话来管理订阅，LLM 通过 Function Calling 调用底层 CRUD 工具。系统常驻运行，内置提醒机制，在扣款前 3 天主动通知用户。

## 技术栈

- **语言**：Python 3.12+
- **包管理**：uv
- **LLM**：qwen3.5-flash（阿里百炼 OpenAI 兼容 API）
- **LLM 调用方式**：OpenAI Function Calling（tools 格式）
- **存储**：JSON 文件
- **配置**：config.toml + .env

## 项目结构

```
subhub/
├── config.toml              # 配置（数据路径、模型、提醒间隔等）
├── .env                     # 敏感信息（DASHSCOPE_API_KEY）
├── .gitignore
├── pyproject.toml            # Python 项目配置
├── docs/plans/               # 设计文档
└── src/subhub/
    ├── __init__.py
    ├── main.py               # 入口：启动聊天 + 提醒线程
    ├── config.py             # 加载 config.toml + .env
    ├── store.py              # JSON 数据 CRUD
    ├── tools.py              # Function Calling 工具定义 + 执行
    ├── chat.py               # LLM 对话循环
    ├── reminder.py           # 后台提醒线程
    └── display.py            # Markdown 表格格式化输出
```

## 数据模型

### 订阅记录（JSON）

```json
{
  "subscriptions": [
    {
      "id": "a1b2c3d4",
      "name": "QQ音乐会员",
      "account": "QQ号12800",
      "payment_channel": "支付宝",
      "amount": 12.0,
      "currency": "CNY",
      "billing_cycle": "monthly",
      "next_billing_date": "2026-05-03",
      "notes": ""
    },
    {
      "id": "e5f6g7h8",
      "name": "便携下载软件",
      "account": "主Google账号",
      "payment_channel": "4402visa卡",
      "amount": 99.0,
      "currency": "CNY",
      "billing_cycle": "permanent",
      "next_billing_date": null,
      "notes": "永久会员，买断制"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 自动生成 | 8位短UUID，唯一标识 |
| name | string | 是 | 服务名称 |
| account | string | 是 | 登录账号 |
| payment_channel | string | 是 | 支付渠道 |
| amount | float | 是 | 金额 |
| currency | string | 是 | 货币单位（CNY/USD等） |
| billing_cycle | string | 是 | 计费周期：monthly/yearly/weekly/daily/permanent/custom |
| next_billing_date | string/null | 条件必填 | ISO日期，permanent时为null |
| notes | string | 否 | 备注 |

## 配置文件

### config.toml

```toml
[data]
path = "/home/txl/Code/meswarm/notes/vault/subhub"
filename = "subscriptions.json"

[llm]
model = "qwen3.5-flash"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

[reminder]
advance_days = 3          # 提前几天提醒
check_interval_hours = 1  # 提醒间隔（小时）
```

### .env

```
DASHSCOPE_API_KEY=sk-xxx
```

## LLM 工具定义

### 1. add_subscription
新增订阅记录。所有字段由LLM从对话中提取，缺失时追问。

### 2. remove_subscription
删除订阅。参数：`name` 或 `id`。

### 3. update_subscription
修改订阅字段。参数：`name` 或 `id` + 要修改的字段键值对。

### 4. list_subscriptions
查询订阅列表。可选过滤：按名称模糊匹配、按计费周期过滤等。

### 5. dismiss_reminder
关闭当天的提醒。参数：`name` 或 `id` 或 `"all"`。

## 系统提示词

每轮对话动态构建 system prompt：

```
你是一个个人订阅管理助手。当前日期：{today}。

用户的当前订阅列表：
{subscriptions_table}

用户常用的登录账号：{账号列表}
用户常用的支付渠道：{渠道列表}

规则：
1. 用户提到新增订阅时，提取所有必要字段。缺少信息必须追问。
2. 追问时列出已有的账号/渠道供用户选择。
3. 用户说"今天"/"昨天"/"X天前"时，根据当前日期推算。
4. 确认所有信息后才调用工具。
5. 永久/买断制订阅的 next_billing_date 设为 null。
6. 用户表示"知道了"/"已处理"等确认提醒时，调用 dismiss_reminder。
```

## 提醒机制

- 后台线程，每 `check_interval_hours` 小时执行一次
- 检查逻辑：当前日期 + `advance_days` 天 = 某订阅的 next_billing_date
- 匹配到则输出 Markdown 表格到终端（不经过 LLM）
- 维护当天已 dismiss 的订阅 ID 集合（内存中，次日重置）
- 用户通过 LLM 对话回复确认 → LLM 调用 dismiss_reminder 工具

### 提醒输出格式

```markdown
⚠️ 订阅扣款提醒 (2026-04-03)
以下订阅将在 3 天后 (04-06) 扣款：

| 服务名称 | 金额 | 支付渠道 | 登录账号 |
|----------|------|----------|----------|
| QQ音乐会员 | ¥12.00 | 支付宝 | QQ号12800 |

💡 回复"知道了"可关闭本次提醒。
```

## 对话流程

```
用户输入 → chat.py 构建 messages（含动态 system prompt）
         → 发送到 LLM API
         → LLM 返回文本 或 tool_calls
         → 如果是 tool_calls：执行工具，将结果返回 LLM，LLM 生成最终回复
         → 如果是文本：直接展示
         → 等待下一轮输入
```

## 依赖

- `openai`：LLM API 客户端
- `tomllib`：读取 config.toml（Python 3.11+ 内置）
- `python-dotenv`：加载 .env 文件

## 后续迭代方向（当前不实现）

- 接入 Telegram Bot
- 月度订阅费用统计报表
- 自动续费日期推算（月付自动+1月等）
