![最新版本](https://img.shields.io/github/v/release/meswarm/subhub?label=最新版本)
![许可证](https://img.shields.io/github/license/meswarm/subhub?label=许可证)

[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

# SubHub

> 面向 Link 与其他智能体中间件的个人订阅管理 API 服务

SubHub 是一个基于 FastAPI 的个人订阅管理服务，适合接入 Link 等智能体中间件。它提供 HTTP API、主动 webhook 提醒、月度报表和本地 JSON 存储，用于统一管理月付、季付、半年付、年付、永久买断等各类订阅。

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| 框架 | FastAPI + Uvicorn |
| 包管理 | uv + hatchling |
| 数据存储 | JSON file |
| 关键库 | Pydantic, python-dotenv |
| 测试 | pytest |

## 快速开始

### 前置要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装

```bash
git clone https://github.com/meswarm/subhub.git
cd subhub
uv sync
```

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
uv run subhub
```

默认读取 [config.toml](config.toml) 中 `[server]` 的 `host` 和 `port`。如需临时覆盖，仍可使用 `--host` 与 `--port`。

### 运行测试

```bash
uv run pytest
```

## 项目结构

```
subhub/
├── LICENSE                 # MIT license
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
uv run subhub
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

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/your-feature`)
3. 提交更改 (`git commit -m 'feat: add your feature'`)
4. 推送分支 (`git push origin feat/your-feature`)
5. 发起 Pull Request

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
