![License](https://img.shields.io/github/license/OWNER/REPO)

[![语言-中文](https://img.shields.io/badge/语言-中文-green)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

# SubHub

> A terminal-based personal subscription manager powered by LLM Function Calling

SubHub manages all your subscription services through natural language conversation. It features an AI assistant driven by LLM, supporting CRUD operations, automatic billing date calculation, proactive renewal reminders (3 days in advance), and monthly cost summary reports. Whether monthly, yearly, or perpetual — SubHub handles them all.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.12+ |
| LLM | qwen3.5-flash (OpenAI-compatible API) |
| Package Manager | uv + hatchling |
| Data Storage | JSON file |
| Testing | pytest |

## Getting Started

### Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/OWNER/REPO.git
cd subhub
uv pip install -e .
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your DashScope API Key
```

Customize data path, reminder parameters, and report currency in `config.toml`.

### Running locally

```bash
uv run subhub
```

## Project Structure

```
subhub/
├── config.toml             # Application config
├── .env.example            # Environment variable template
├── pyproject.toml          # Project metadata & dependencies
├── src/subhub/
│   ├── config.py           # Config loader
│   ├── store.py            # JSON data storage layer
│   ├── display.py          # Markdown formatting output
│   ├── tools.py            # LLM Function Calling tools
│   ├── reminder.py         # Background reminder thread
│   ├── chat.py             # LLM conversation module
│   └── main.py             # Entry point
└── tests/                  # Unit tests
```

## Usage

Start the app and interact with the assistant using natural language:

```
You: I just subscribed to QQ Music, 12 CNY/month via Alipay, account QQ12800
Assistant: ✅ Subscription added: QQ Music

You: Show me all my subscriptions
Assistant: | Service | Amount | Cycle | Next Billing | ...

You: How much am I spending this month?
Assistant: 📊 2026-04 Monthly Subscription Report ...
```

### Key Features

- **CRUD** — Manage subscriptions with natural language
- **Smart Date Calculation** — Auto-compute next billing date (monthly +1 month, yearly +1 year, etc.)
- **Billing Reminders** — Alerts 3 days before renewal, checks hourly, stops after acknowledgment
- **Monthly Reports** — Auto-generated at month-end, multi-currency support
- **Perpetual Memberships** — One-time purchases managed alongside recurring subscriptions

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feat/your-feature`)
5. Open a Pull Request

## License

MIT — see [LICENSE](LICENSE) for details.
