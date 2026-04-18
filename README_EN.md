![Version](https://img.shields.io/github/v/release/meswarm/subhub?label=Version)
![License](https://img.shields.io/github/license/meswarm/subhub?label=License)

[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

# SubHub

> An API-first personal subscription manager for Link and other agent middleware

SubHub is a FastAPI-based personal subscription management service designed for Link and similar agent middleware. It exposes HTTP APIs, proactive webhook reminders, monthly reports, and local JSON storage to manage monthly, quarterly, semiannual, yearly, weekly, daily, custom, and perpetual subscriptions in one place. The default reply style is optimized for mobile reading: result-first, concise, and limited in unnecessary Markdown decoration.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.12+ |
| Framework | FastAPI + Uvicorn |
| Package Manager | uv + hatchling |
| Task runner | Make |
| Data Storage | JSON file |
| Key Libraries | Pydantic, python-dotenv |
| Testing | pytest |

## Getting Started

### Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager
- GNU Make (usually preinstalled; used to wrap common commands via `Makefile`)

### Installation

```bash
git clone https://github.com/meswarm/subhub.git
cd subhub
make sync
```

`make sync` runs `uv sync`, so you do not need to create or activate a virtual environment by hand.

### Configuration

Edit `config.toml` to customize data path, API listen address, reminder parameters, report currency, and webhook URL.

Example:

```toml
[server]
host = "127.0.0.1"
port = 58000
```

### Running locally

```bash
make run
```

By default, SubHub reads `host` and `port` from `[server]` in `config.toml`. To override: `make run ARGS="--host 0.0.0.0 --port 8080"`.

### Run tests

```bash
make test
```

### Equivalent uv commands

Without Make, or for scripts, use the same steps directly: `uv sync`, `uv run subhub`, and `uv run pytest` (same as the `make` targets above).

## Project Structure

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

## Usage

### Start the API service

```bash
make run
```

### List subscriptions

```bash
curl http://127.0.0.1:58000/api/subscriptions
```

### Create a subscription

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

### Generate a monthly report

```bash
curl "http://127.0.0.1:58000/api/reports/monthly?month=2026-04&mode=budget"
```

### Start Link

```bash
ltool start link/agents/subhub.yaml
```

Before starting Link, make sure the SubHub API is already running and the `endpoint` values in [link/agents/subhub.yaml](link/agents/subhub.yaml) match the `[server]` settings in [config.toml](config.toml).

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feat/your-feature`)
5. Open a Pull Request

## License

MIT — see [LICENSE](LICENSE) for details.
