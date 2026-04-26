# service.subhub 命令说明

> 系统类型：Matrix 订阅管理机器人

---

## 启动方式

在仓库根目录：

```bash
make run
```

等价命令：`uv run subhub`。启动前请先复制 `.env.example` 为 `.env`，并填写 Matrix、LLM 和 R2 配置。

## 环境变量

- `MATRIX_HOMESERVER`：Matrix homeserver 地址
- `MATRIX_USER`：机器人账号
- `MATRIX_PASSWORD`：机器人密码
- `MATRIX_ROOMS`：监听的房间 ID，逗号分隔
- `SUBHUB_LLM_BASE_URL`、`SUBHUB_LLM_API_KEY`、`SUBHUB_LLM_MODEL`、`SUBHUB_SYSTEM_PROMPT_FILE`：LLM 配置
- `SUBHUB_DB_DIR`、`SUBHUB_DB_FILENAME`、`SUBHUB_DISMISSED_FILENAME`：本地 JSON 存储路径
- `SUBHUB_DOWNLOAD_DIR`：附件下载缓存目录
- `R2_ENDPOINT`、`R2_ACCESS_KEY`、`R2_SECRET_KEY`、`R2_BUCKET`、`R2_PUBLIC_URL`：R2 相关配置

建议把系统提示词放到独立的 Markdown 文件里，例如 `prompts/system_prompt.md`，并通过 `SUBHUB_SYSTEM_PROMPT_FILE` 指向它。文件内容应显式引用上下文占位符，否则模型不会自动获得当前订阅列表、账号和支付渠道信息。例如：

```md
你是一个个人订阅管理助手。请始终基于当前上下文回答，优先保持简洁、准确、结果优先。

今天日期：
{today_context}

当前订阅列表：
{subscriptions_context}

常用账号：
{accounts_context}

常用支付渠道：
{channels_context}
```

## 功能范围

管理个人订阅服务，支持以下操作：

- 新增订阅
- 删除订阅
- 修改订阅
- 查询订阅
- 生成月报
- 处理提醒

支持的计费周期：月付、季付、半年付、年付、周付、日付、永久、自定义

支持的货币：CNY、USD、EUR、GBP、JPY

## 输出格式

- 机器人在 Matrix 中以文本消息回复
- 成功与失败结果会尽量保持简洁
- 月报和列表会优先使用 Markdown 表格

## 附件规则

- 机器人只接收 Matrix 文本消息
- 图片、视频、音频和文件通过 `r2://` Markdown 链接传递
- 默认只下载图片；视频、音频和文件不下载也不解析

## 默认路径

- 数据文件：`./db/subscriptions.json`
- 已忽略提醒：`./db/dismissed.json`
- 已发送提醒窗口：`./db/sent-reminders.json`
- 下载缓存：`./downloads`

## 提醒策略

- 默认在扣款前 `7/3/2/1` 天各提醒一次
- 每个提醒窗口只发送一条消息，不会重复刷屏
- 提醒消息会附带追问，提示用户继续续费或删除该订阅

---

## 工作目录

```
/home/txl/Code/meswarm/subhub
```
