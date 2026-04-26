from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Callable

MAX_TOOL_CALL_ROUNDS = 10
_IMAGE_TAG_PATTERN = re.compile(r"\[image:(.+?):(.+?)\]")


class LLMEngine:
    def __init__(
        self,
        client,
        model: str,
        system_prompt: str,
        tool_registry,
        context_hooks: dict[str, Callable[[], str]] | None = None,
        skills_prompt: str = "",
        temperature: float = 0.7,
        max_history: int = 20,
        vision_enabled: bool = False,
    ):
        self._client = client
        self._model = model
        self._system_prompt = system_prompt
        self._tool_registry = tool_registry
        self._context_hooks = context_hooks or {}
        self._skills_prompt = skills_prompt
        self._temperature = temperature
        self._max_history = max_history
        self._vision_enabled = vision_enabled
        self._histories: dict[str, list[dict[str, Any]]] = {}

    def _history(self, room_id: str) -> list[dict[str, Any]]:
        return self._histories.setdefault(room_id, [])

    def _trim(self, room_id: str) -> None:
        max_len = self._max_history * 2
        if len(self._history(room_id)) > max_len:
            self._histories[room_id] = self._history(room_id)[-max_len:]

    def _context(self) -> dict[str, str]:
        return {name: hook() for name, hook in self._context_hooks.items()}

    def _messages(self, room_id: str) -> list[dict[str, Any]]:
        prompt = self._system_prompt
        context = self._context()
        if context:
            prompt = prompt.format(**context)
        if self._skills_prompt:
            prompt = f"{prompt}\n\n{self._skills_prompt}"
        return [{"role": "system", "content": prompt}, *self._history(room_id)]

    def _user_content(self, message: str) -> str | list[dict[str, Any]]:
        matches = _IMAGE_TAG_PATTERN.findall(message)
        if not matches or not self._vision_enabled:
            if matches:
                for file_path, _mime in matches:
                    message = message.replace(
                        f"[image:{file_path}:{_mime}]",
                        f"[用户发送了一张图片: {Path(file_path).name}]",
                    )
            return message

        parts: list[dict[str, Any]] = []
        text = _IMAGE_TAG_PATTERN.sub("", message).strip() or "请分析这张图片"
        for file_path, mime in matches:
            data = base64.b64encode(Path(file_path).read_bytes()).decode("utf-8")
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{data}"},
                }
            )
        parts.append({"type": "text", "text": text})
        return parts

    async def chat(self, room_id: str, user_message: str) -> str:
        history = self._history(room_id)
        history.append({"role": "user", "content": self._user_content(user_message)})
        messages = self._messages(room_id)
        tools = (
            self._tool_registry.get_all_definitions()
            if self._tool_registry.has_tools()
            else None
        )

        for _round in range(MAX_TOOL_CALL_ROUNDS):
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": self._temperature,
            }
            if tools:
                kwargs["tools"] = tools
            completion = await self._client.chat.completions.create(**kwargs)
            assistant_message = completion.choices[0].message
            if not assistant_message.tool_calls:
                content = assistant_message.content or ""
                history.append({"role": "assistant", "content": content})
                self._trim(room_id)
                return content
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                }
            )
            for call in assistant_message.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await self._tool_registry.execute_tool(
                    call.function.name, **args
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        content = "抱歉，操作步骤过多，我需要简化处理方式。请重新描述你的需求。"
        history.append({"role": "assistant", "content": content})
        self._trim(room_id)
        return content

    async def format_notification(self, payload: dict[str, Any]) -> str:
        prompt = json.dumps(payload, ensure_ascii=False, indent=2)
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个通知整理助手。输出简洁中文，不要代码块。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content or payload.get("message", "")
