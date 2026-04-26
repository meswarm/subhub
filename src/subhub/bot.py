from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from openai import AsyncOpenAI

from subhub.attachments import AttachmentResolver
from subhub.llm_engine import LLMEngine
from subhub.media_store import MediaStoreConfig, R2MediaStore
from subhub.reminder_task import reminder_loop
from subhub.service import SubHubService
from subhub.skills import format_skills_for_prompt, load_skills_from_dir
from subhub.store import SubscriptionStore
from subhub.tools import SubHubToolRegistry, build_subhub_tools

logger = logging.getLogger(__name__)


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
            reminder_advance_days=config.reminder.advance_days,
        )
        self._tools = SubHubToolRegistry(build_subhub_tools(self._service))
        llm_config = config.llm
        skills_dir = Path(getattr(llm_config, "skills_dir", "skills/manage-subscriptions"))
        skills = load_skills_from_dir(skills_dir)
        media_store = R2MediaStore(MediaStoreConfig(root=config.download.root))
        self._attachments = AttachmentResolver(
            config.download,
            media_store,
            getattr(llm_config, "vision_enabled", False),
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
            temperature=getattr(llm_config, "temperature", 0.7),
            max_history=getattr(llm_config, "max_history", 20),
            vision_enabled=getattr(llm_config, "vision_enabled", False),
        )
        self._matrix.on_message(self._handle_message)

    async def _handle_message(self, room_id: str, sender: str, content: str) -> None:
        logger.info("Handling Matrix message from %s in %s", sender, room_id)
        await self._matrix.set_typing(room_id, True)
        try:
            resolved = await self._attachments.resolve(content)
            reply = await self._llm.chat(room_id, resolved.content)
            if reply.strip():
                await self._matrix.send_text(room_id, reply)
        except Exception:
            logger.exception("Message handling failed")
            await self._matrix.send_text(room_id, "抱歉，处理你的消息时出现了问题。")
        finally:
            await self._matrix.set_typing(room_id, False)

    async def start(self) -> None:
        if not await self._matrix.login():
            raise RuntimeError("Matrix 登录失败")
        tasks = []
        if getattr(self._config.reminder, "enabled", True):
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
