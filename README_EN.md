![Version](https://img.shields.io/github/v/release/meswarm/subhub?label=Version)
![License](https://img.shields.io/github/license/meswarm/subhub?label=License)

[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)
[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)

# SubHub

> A Matrix-native personal subscription management bot

SubHub manages subscriptions, reminders, and monthly reports through Matrix text messages. It uses local JSON storage, embedded LLM tool calls, and optional R2 attachment handling. It no longer exposes an HTTP API, webhook runtime, or `config.toml`.

## Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.12+ |
| Runtime | Matrix bot + OpenAI-compatible LLM |
| Package Manager | uv + hatchling |
| Task runner | Make |
| Data Storage | JSON file |
| Key Libraries | python-dotenv, matrix-nio, openai, aiohttp, aiofiles, aioboto3 |
| Testing | pytest, pytest-asyncio |

## Getting Started

### Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager
- GNU Make

### Installation

```bash
git clone https://github.com/meswarm/subhub.git
cd subhub
make sync
```

### Configuration

Copy `.env.example` to `.env` and fill in at least:

- `MATRIX_HOMESERVER`
- `MATRIX_USER`
- `MATRIX_PASSWORD`
- `MATRIX_ROOMS`
- `SUBHUB_LLM_BASE_URL`
- `SUBHUB_LLM_API_KEY`
- `SUBHUB_LLM_MODEL`
- `SUBHUB_SYSTEM_PROMPT`

Default data files are `./db/subscriptions.json` and `./db/dismissed.json`. You can override them with `SUBHUB_DB_DIR`, `SUBHUB_DB_FILENAME`, and `SUBHUB_DISMISSED_FILENAME`.

SubHub only accepts Matrix text messages. Images, videos, audio, and files are carried as `r2://` Markdown links in text. By default, only images are downloaded; videos, audio, and regular files are not downloaded or parsed.

### Run locally

```bash
make run
```

SubHub reads `.env`, signs into Matrix, and listens to the rooms listed in `MATRIX_ROOMS`.

### Run tests

```bash
make test
```

### Project layout

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

## Typical use

Subscription management, reports, and reminder acknowledgements are handled naturally in Matrix rooms. The bot routes requests through local tools, produces reports, and formats reminder messages when needed.

## License

MIT — see [LICENSE](LICENSE) for details.
