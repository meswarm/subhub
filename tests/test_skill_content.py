from pathlib import Path


def test_manage_subscriptions_skill_prefers_context_for_simple_queries():
    content = Path("skills/manage-subscriptions/SKILL.md").read_text(encoding="utf-8")

    assert "预置上下文" in content
    assert "{subscriptions_context}" in content
    assert "普通查询" in content
    assert "不要调用工具" in content
