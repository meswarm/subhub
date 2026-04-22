最新版本
许可证

[语言-中文](README.md)
[Language-English](README_EN.md)

# SubHub

> 面向 Link 与其他智能体中间件的个人订阅管理 API 服务

SubHub 是一个基于 FastAPI 的个人订阅管理服务，适合接入 Link 等智能体中间件。它提供 HTTP API、主动 webhook 提醒、月度报表和本地 JSON 存储，用于统一管理月付、季付、半年付、年付、永久买断等各类订阅。默认回复风格已针对移动端阅读优化：结果优先、尽量简洁，并限制不必要的 Markdown 装饰。

## 技术栈


| 类别   | 技术                      |
| ---- | ----------------------- |
| 语言   | Python 3.12+            |
| 框架   | FastAPI + Uvicorn       |
| 包管理  | uv + hatchling          |
| 任务入口 | Make                    |
| 数据存储 | JSON file               |
| 关键库  | Pydantic, python-dotenv |
| 测试   | pytest                  |


## 快速开始

### 前置要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器
- GNU Make（一般系统已自带；用于 `Makefile` 封装常用命令）

### 安装

```bash
git clone https://github.com/meswarm/subhub.git
cd subhub
make sync
```

依赖安装由 `make sync` 调用 `uv sync` 完成，无需手动创建或激活虚拟环境。

### 配置

编辑 `config.toml`，可自定义数据路径、API 监听地址、提醒参数、报表货币和 webhook 地址。

示例：

```toml
[server]
host = "127.0.0.1"
port = 58000
```

### 本地运行

```bash
make run
```

默认读取 [config.toml](config.toml) 中 `[server]` 的 `host` 和 `port`。如需临时覆盖：`make run ARGS="--host 0.0.0.0 --port 8080"`。

### 运行测试

```bash
make test
```

### 等效 uv 命令

若无 Make 或需脚本化调用，可直接使用：`uv sync`、`uv run subhub`、`uv run pytest`（与上述 `make` 目标一致）。

## 项目结构

```
subhub/
├── LICENSE                 # MIT license
├── Makefile                # make sync / run / test (wraps uv)
├── config.toml             # Application config
├── docs/                   # Design docs and manuals
├── link/                   # Link agent config and skills
├── pyproject.toml          # Project metadata and dependencies
├── src/subhub/
│   ├── api.py              # FastAPI HTTP API
│   ├── config.py           # Config loader
│   ├── display.py          # Markdown formatting output
│   ├── reminder.py         # Background reminder thread
│   ├── service.py          # Business service layer
│   ├── store.py            # JSON data storage layer
│   ├── webhook.py          # Link webhook client
│   └── main.py             # Entry point
└── tests/                  # Unit tests
```

## 使用方法

### 启动 API 服务

```bash
make run
```

### 查询订阅列表

```bash
curl http://127.0.0.1:58000/api/subscriptions
```

### 新增订阅

```bash
curl -X POST http://127.0.0.1:58000/api/subscriptions \
	-H "Content-Type: application/json" \
	-d '{
		"name": "YouTube Premium",
		"account": "me@example.com",
		"payment_channel": "Visa",
		"amount": 28,
		"currency": "CNY",
		"billing_cycle": "monthly",
		"next_billing_date": "2026-05-01",
		"notes": "家庭组"
	}'
```

### 生成月报

```bash
curl "http://127.0.0.1:58000/api/reports/monthly?month=2026-04&mode=budget"
```

### 接入 Link

```bash
ltool start link/agents/subhub.yaml
```

Link 启动前，请先确认 SubHub API 已运行，并且 [link/agents/subhub.yaml](link/agents/subhub.yaml) 中的 `endpoint` 与 [config.toml](config.toml) 里的 `[server]` 配置一致。

### 测试主动通知

Link 启动后，可直接向 webhook 端点发送一条模拟“即将到期提醒”，验证用户侧是否能收到主动通知：

```bash
curl -X POST "http://127.0.0.1:59001/alert" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "## 订阅扣款提醒\n- 日期：2026-04-20\n- 将在 04-23 扣款：\n\n| 服务名称 | 金额 | 支付渠道 | 登录账号 |\n|----------|------|----------|----------|\n| GitHub Copilot Pro | $10.00 | Visa | me@example.com |"
  }'
```

这条命令用于模拟 SubHub 主动推送“哪些订阅快到期了”的通知效果。

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/your-feature`)
3. 提交更改 (`git commit -m 'feat: add your feature'`)
4. 推送分支 (`git push origin feat/your-feature`)
5. 发起 Pull Request

## 许可证

MIT — 详见 [LICENSE](LICENSE)。