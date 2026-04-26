"""SubHub Matrix bot entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from subhub.bot import SubHubBot
from subhub.config import load_config
from subhub.matrix_client import MatrixTextClient


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    logging.getLogger("nio").setLevel(logging.WARNING)
    logging.getLogger("nio.rooms").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def _amain(env_path: str | None) -> None:
    config = load_config(env_path=env_path, require_bot_runtime=True)
    _configure_logging(getattr(config, "log_level", "INFO"))
    logging.info(
        "Starting SubHub bot: rooms=%s db=%s downloads=%s reminders=%s",
        config.matrix.rooms,
        config.data.filepath,
        config.download.root,
        "enabled" if getattr(config.reminder, "enabled", True) else "disabled",
    )
    matrix = MatrixTextClient(
        homeserver=config.matrix.homeserver,
        user=config.matrix.user,
        password=config.matrix.password,
        rooms=config.matrix.rooms,
    )
    bot = SubHubBot(config, matrix)
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass
    task = asyncio.create_task(bot.start())
    await stop_event.wait()
    await bot.stop()
    task.cancel()


def main() -> None:
    parser = argparse.ArgumentParser(description="SubHub Matrix bot")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    args = parser.parse_args()

    try:
        asyncio.run(_amain(args.env))
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
