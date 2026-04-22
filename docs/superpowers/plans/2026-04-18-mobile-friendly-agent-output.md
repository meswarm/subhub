# Mobile-Friendly Agent Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SubHub agent replies more concise and mobile-friendly by tightening prompt rules, skill rules, and formatter output.

**Architecture:** Keep the change localized to the three existing response-shaping layers: agent prompt, skill response rules, and display formatters. Lock formatter behavior with tests so future prompt changes do not reintroduce verbose helper text.

**Tech Stack:** Python 3.12, pytest, YAML agent config, Markdown formatter helpers

---

### Task 1: Lock simplified formatter output with tests

**Files:**

- Modify: `tests/test_display.py`
- Modify: `src/subhub/display.py`
- Test: `tests/test_display.py`
- **Step 1: Write the failing test**

```python
def test_format_reminder_table_is_concise():
    subs = [
        Subscription(
            id="1",
            name="GitHub Copilot Pro",
            account="me@example.com",
            payment_channel="Visa",
            amount=10,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date="2026-05-07",
            notes="",
        )
    ]

    text = format_reminder_table(subs, remind_date="2026-05-07", today="2026-05-01")

    assert text.startswith("## 订阅扣款提醒")
    assert "⚠️" not in text
    assert "回复\"知道了\"可关闭本次提醒" not in text
```

- **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_display.py::test_format_reminder_table_is_concise -v`
Expected: FAIL because the current formatter still uses emoji and footer helper text.

- **Step 3: Write minimal implementation**

```python
header = "## 订阅扣款提醒\n"
header += f"- 日期：{today}\n"
header += f"- 将在 {rd_short} 扣款：\n\n"
return header + "\n".join(lines)
```

- **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_display.py::test_format_reminder_table_is_concise -v`
Expected: PASS

- **Step 5: Commit**

```bash
git add tests/test_display.py src/subhub/display.py
git commit -m "refactor: simplify reminder output for mobile"
```

### Task 2: Lock simplified report output with tests

**Files:**

- Modify: `tests/test_display.py`
- Modify: `src/subhub/display.py`
- Test: `tests/test_display.py`
- **Step 1: Write the failing tests**

```python
def test_format_monthly_report_is_concise():
    subs = [
        Subscription(
            id="1",
            name="Netflix",
            account="me@example.com",
            payment_channel="Visa",
            amount=18,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date="2026-05-01",
            notes="",
        )
    ]

    text = format_monthly_report(subs, month="2026-05")

    assert text.startswith("## 2026-05 月度订阅预算报表")
    assert "📊" not in text
    assert "你可以让我分析一下这份报表" not in text


def test_format_actual_billing_report_is_concise():
    subs = [
        Subscription(
            id="1",
            name="Netflix",
            account="me@example.com",
            payment_channel="Visa",
            amount=18,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date="2026-05-01",
            notes="",
        )
    ]

    text = format_actual_billing_report(subs, month="2026-05")

    assert text.startswith("## 2026-05 实际扣款报表")
    assert "📊" not in text
    assert "这是本月实际发生的扣款统计" not in text
```

- **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_display.py::test_format_monthly_report_is_concise tests/test_display.py::test_format_actual_billing_report_is_concise -v`
Expected: FAIL because the current reports still use emoji titles and footer helper text.

- **Step 3: Write minimal implementation**

```python
if not recurring:
    return f"## {month} 月度订阅预算报表\n\n暂无周期性订阅。"

header = f"## {month} 月度订阅预算报表\n\n"
return header + "\n".join(lines)
```

```python
if not subs:
    return f"## {month} 实际扣款报表\n\n本月无扣款记录。"

header = f"## {month} 实际扣款报表\n\n"
return header + "\n".join(lines)
```

- **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_display.py::test_format_monthly_report_is_concise tests/test_display.py::test_format_actual_billing_report_is_concise -v`
Expected: PASS

- **Step 5: Commit**

```bash
git add tests/test_display.py src/subhub/display.py
git commit -m "refactor: simplify report markdown output"
```

### Task 3: Tighten agent and skill response rules

**Files:**

- Modify: `link/agents/subhub.yaml`
- Modify: `link/agents/skills/manage-subscriptions/SKILL.md`
- Modify: `README.md`
- Modify: `README_EN.md`
- **Step 1: Update the agent prompt**

```yaml
  9. 回复使用中文，简洁明了，先给结果，不添加寒暄、问候或主动延伸建议。
  10. Markdown 默认只使用一级标题、二级标题、无序列表、有序列表；表格仅在确有必要时使用。
  11. 不使用引用格式，不默认使用表情符号。
  12. 涉及列表、报表、查询结果时，优先输出精简后的 markdown 或结构化结果，避免重复解释。
```

- **Step 2: Update the skill response rules**

```markdown
- Always reply in Chinese.
- Keep replies concise and result-first.
- Do not add greetings, closing pleasantries, or proactive suggestions unless the user asks.
- Do not use blockquotes.
- Avoid emoji unless the user explicitly wants them.
```

- **Step 3: Update README files**

```markdown
- Agent output is optimized for mobile reading: concise, result-first, and limited in markdown styling.
```

- **Step 4: Run focused checks**

Run: `uv run pytest tests/test_display.py -v`
Expected: PASS

- **Step 5: Commit**

```bash
git add link/agents/subhub.yaml link/agents/skills/manage-subscriptions/SKILL.md README.md README_EN.md
git commit -m "docs: tighten agent response style rules"
```

