from __future__ import annotations

import asyncio
import logging
from datetime import date

from subhub.reminder import check_reminder_windows

logger = logging.getLogger(__name__)


async def format_reminder_with_optional_llm(
    message: str, use_llm: bool, llm_engine
) -> str:
    if use_llm and llm_engine is not None:
        return await llm_engine.format_notification({"message": message})
    return message


async def reminder_loop(config, store, matrix_client, llm_engine=None) -> None:
    interval = max(config.reminder.check_interval_hours, 1) * 3600
    while True:
        try:
            messages = check_reminder_windows(
                store,
                date.today(),
                config.reminder.reminder_days,
            )
            for message in messages:
                text = await format_reminder_with_optional_llm(
                    message,
                    use_llm=config.reminder.use_llm,
                    llm_engine=llm_engine,
                )
                for room_id in matrix_client.rooms:
                    await matrix_client.send_text(room_id, text)
                logger.info(
                    "Sent subscription reminder to %s rooms",
                    len(matrix_client.rooms),
                )
        except Exception:
            logger.exception("Reminder loop failed")
        await asyncio.sleep(interval)
