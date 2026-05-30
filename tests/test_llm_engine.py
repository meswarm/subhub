import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from subhub.llm_engine import LLMEngine
from subhub.skills import format_skills_for_prompt, load_skills_from_dir


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def has_tools(self):
        return True

    def get_all_definitions(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_subscriptions",
                    "description": "list",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        ]

    async def execute_tool(self, name, **params):
        self.calls.append((name, params))
        return json.dumps({"ok": True, "data": {"items": []}}, ensure_ascii=False)


class FakeCompletions:
    def __init__(self):
        self.count = 0
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        self.count += 1
        if self.count == 1:
            tool_call = SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(name="list_subscriptions", arguments="{}"),
            )
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="", tool_calls=[tool_call])
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="暂无订阅", tool_calls=None)
                )
            ]
        )


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_load_and_format_skills(tmp_path):
    skills_dir = tmp_path / "skills" / "manage-subscriptions"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# title\nbody", encoding="utf-8")

    skills = load_skills_from_dir(tmp_path / "skills")

    assert len(skills) == 1
    assert skills[0].name == "manage-subscriptions"
    prompt = format_skills_for_prompt(skills)
    assert "## Skills" in prompt
    assert "body" in prompt


@pytest.mark.asyncio
async def test_llm_engine_executes_tool_calls():
    registry = FakeRegistry()
    engine = LLMEngine(
        client=FakeClient(),
        model="test-model",
        system_prompt="prompt {today_context}",
        tool_registry=registry,
        context_hooks={"today_context": lambda: "2026-04-26"},
        temperature=0.7,
        max_history=20,
        vision_enabled=False,
    )

    reply = await engine.chat("room", "列出订阅")

    assert reply == "暂无订阅"
    assert registry.calls == [("list_subscriptions", {})]


@pytest.mark.asyncio
async def test_llm_engine_logs_llm_and_tool_timings(caplog):
    registry = FakeRegistry()
    engine = LLMEngine(
        client=FakeClient(),
        model="test-model",
        system_prompt="prompt",
        tool_registry=registry,
    )
    caplog.set_level(logging.INFO, logger="subhub.llm_engine")

    await engine.chat("room", "列出订阅")

    messages = [record.getMessage() for record in caplog.records]
    assert any("LLM request round 1 completed" in message for message in messages)
    assert any("Tool call list_subscriptions completed" in message for message in messages)
    assert any("LLM chat completed" in message for message in messages)


@pytest.mark.asyncio
async def test_llm_engine_converts_image_tags_to_placeholders(tmp_path):
    image = tmp_path / "shot.png"
    image.write_bytes(b"fake")

    registry = FakeRegistry()
    engine = LLMEngine(
        client=FakeClient(),
        model="test-model",
        system_prompt="prompt",
        tool_registry=registry,
        vision_enabled=False,
    )

    await engine.chat("room", f"看看这个 [image:{image}:image/png]")

    first_request = engine._client.chat.completions.requests[0]
    assert first_request["messages"][1]["content"].startswith("看看这个 [用户发送了一张图片:")


@pytest.mark.asyncio
async def test_llm_engine_sends_thinking_setting():
    registry = FakeRegistry()
    engine = LLMEngine(
        client=FakeClient(),
        model="test-model",
        system_prompt="prompt",
        tool_registry=registry,
        thinking_enabled=False,
    )

    await engine.chat("room", "列出订阅")

    first_request = engine._client.chat.completions.requests[0]
    assert first_request["extra_body"] == {"enable_thinking": False}
