![Version](https://img.shields.io/github/v/release/meswarm/subhub?label=Version)
![License](https://img.shields.io/github/license/meswarm/subhub?label=License)

[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

# SubHub

> 面向 Matrix 的个人订阅管理机器人

SubHub 通过 Matrix 文本消息管理订阅、提醒和月报，使用本地 JSON 存储、嵌入式 LLM 工具调用，以及可选的 R2 附件解析。它不再提供 HTTP API、webhook 或 `config.toml`。

## 技术栈

| 类别 | 技术 |
|---|---|
| 语言 | Python 3.12+ |
| 运行时 | Matrix bot + OpenAI-compatible LLM |
| 包管理 | uv + hatchling |
| 任务入口 | Make |
| 数据存储 | JSON file |
| 关键库 | python-dotenv, matrix-nio, openai, aiohttp, aiofiles, aioboto3 |
| 测试 | pytest, pytest-asyncio |

## 快速开始

### 前置要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器
- GNU Make

### 安装

```bash
git clone https://github.com/meswarm/subhub.git
cd subhub
make sync
```

### 配置

复制 `.env.example` 为 `.env`，填写至少这些项：

- `MATRIX_HOMESERVER`
- `MATRIX_USER`
- `MATRIX_PASSWORD`
- `MATRIX_ROOMS`
- `SUBHUB_LLM_BASE_URL`
- `SUBHUB_LLM_API_KEY`
- `SUBHUB_LLM_MODEL`
- `SUBHUB_SYSTEM_PROMPT`

默认数据文件为 `./db/subscriptions.json`，提醒忽略状态为 `./db/dismissed.json`。可通过 `SUBHUB_DB_DIR`、`SUBHUB_DB_FILENAME`、`SUBHUB_DISMISSED_FILENAME` 调整。

SubHub 只接收 Matrix 文本消息。图片、视频、音频和文件通过文本中的 `r2://` Markdown 链接传递；默认只下载图片，视频、音频和普通文件不下载也不解析。

### 本地运行

```bash
make run
```

SubHub 会读取 `.env`，以 Matrix 机器人身份登录并监听 `MATRIX_ROOMS` 中配置的房间。

### 运行测试

```bash
make test
```

### 目录结构

```
subhub/
├── Makefile
├── README.md
├── README_EN.md
├── docs/
├── pyproject.toml
├── skills/
├── src/subhub/
└── tests/
```

## 常见操作

订阅管理、月报和提醒确认都通过自然语言在 Matrix 房间里完成。底层会调用本地工具、生成报表，并在需要时整理提醒文本。

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
