from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from time import perf_counter

from openai import AsyncOpenAI

from subhub.attachments import AttachmentResolver
from subhub.llm_engine import LLMEngine
from subhub.media_store import R2MediaStore
from subhub.reminder_task import reminder_loop
from subhub.service import SubHubService
from subhub.skills import format_skills_for_prompt, load_skills_from_dir
from subhub.store import SubscriptionStore
from subhub.tools import SubHubToolRegistry, build_subhub_tools

logger = logging.getLogger(__name__)


def _preview_text(text: str, limit: int = 160) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit - 3]}..."


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000


class SubHubBot:
    def __init__(self, config, matrix_client):
        self._config = config
        self._matrix = matrix_client
        self._store = SubscriptionStore(
            config.data.filepath,
            dismissed_filepath=config.data.dismissed_filepath,
        )
        self._service = SubHubService(
            self._store,
            base_currency=config.report.base_currency,
            reminder_days=config.reminder.reminder_days,
        )
        self._tools = SubHubToolRegistry(build_subhub_tools(self._service))
        llm_config = config.llm
        skills_dir = llm_config.skills_dir or Path("skills/manage-subscriptions").resolve()
        skills = load_skills_from_dir(skills_dir)
        media_store = (
            R2MediaStore(config.r2, config.download.root)
            if config.r2.enabled
            else None
        )
        self._attachments = AttachmentResolver(
            config.download,
            media_store,
            llm_config.vision_enabled,
        )
        client = AsyncOpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
        )
        self._llm = LLMEngine(
            client=client,
            model=llm_config.model,
            system_prompt=llm_config.system_prompt,
            tool_registry=self._tools,
            context_hooks={
                "today_context": lambda: self._service.get_context_today()["today"],
                "subscriptions_context": lambda: self._service.get_context_subscriptions()[
                    "markdown"
                ],
                "accounts_context": lambda: self._service.get_context_accounts()["text"],
                "channels_context": lambda: self._service.get_context_channels()["text"],
            },
            skills_prompt=format_skills_for_prompt(skills),
            temperature=llm_config.temperature,
            max_history=llm_config.max_history,
            vision_enabled=llm_config.vision_enabled,
            thinking_enabled=llm_config.thinking_enabled,
        )
        self._matrix.on_message(self._handle_message)

    async def _handle_message(self, room_id: str, sender: str, content: str) -> None:
        total_started_at = perf_counter()
        logger.info(
            "Handling Matrix message from %s in %s: %s",
            sender,
            room_id,
            _preview_text(content),
        )
        typing_started_at = perf_counter()
        await self._matrix.set_typing(room_id, True)
        logger.info(
            "Matrix typing-on completed for %s in %.1f ms",
            room_id,
            _elapsed_ms(typing_started_at),
        )
        try:
            resolve_started_at = perf_counter()
            resolved = await self._attachments.resolve(content)
            logger.info(
                "Attachment resolution completed for %s in %.1f ms",
                room_id,
                _elapsed_ms(resolve_started_at),
            )
            if resolved.content != content:
                logger.info(
                    "Resolved message content for %s: %s",
                    room_id,
                    _preview_text(resolved.content),
                )
            llm_started_at = perf_counter()
            reply = await self._llm.chat(room_id, resolved.content)
            logger.info(
                "LLM reply generation completed for %s in %.1f ms",
                room_id,
                _elapsed_ms(llm_started_at),
            )
            if reply.strip():
                logger.info(
                    "Sending Matrix reply to %s: %s",
                    room_id,
                    _preview_text(reply),
                )
                send_started_at = perf_counter()
                await self._matrix.send_text(room_id, reply)
                logger.info(
                    "Matrix reply send completed for %s in %.1f ms",
                    room_id,
                    _elapsed_ms(send_started_at),
                )
        except Exception:
            logger.exception("Message handling failed")
            await self._matrix.send_text(room_id, "抱歉，处理你的消息时出现了问题。")
        finally:
            typing_started_at = perf_counter()
            await self._matrix.set_typing(room_id, False)
            logger.info(
                "Matrix typing-off completed for %s in %.1f ms",
                room_id,
                _elapsed_ms(typing_started_at),
            )
            logger.info(
                "Matrix message handling completed for %s in %.1f ms",
                room_id,
                _elapsed_ms(total_started_at),
            )

    async def start(self) -> None:
        if not await self._matrix.login():
            raise RuntimeError("Matrix 登录失败")
        tasks = []
        if self._config.reminder.enabled:
            tasks.append(
                asyncio.create_task(
                    reminder_loop(
                        self._config, self._store, self._matrix, self._llm
                    )
                )
            )
        await self._matrix.start_sync()
        for task in tasks:
            task.cancel()

    async def stop(self) -> None:
        await self._matrix.stop()
