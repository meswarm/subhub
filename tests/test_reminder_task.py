import pytest

from subhub.reminder_task import format_reminder_with_optional_llm


class FakeEngine:
    async def format_notification(self, payload):
        return f"LLM: {payload['message']}"


@pytest.mark.asyncio
async def test_direct_reminder_formatting():
    text = await format_reminder_with_optional_llm(
        "hello", use_llm=False, llm_engine=None
    )
    assert text == "hello"


@pytest.mark.asyncio
async def test_llm_reminder_formatting():
    text = await format_reminder_with_optional_llm(
        "hello", use_llm=True, llm_engine=FakeEngine()
    )
    assert text == "LLM: hello"
