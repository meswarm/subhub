# Mobile-Friendly Agent Output Design

## Goal

Reduce verbose, decorative, and mobile-unfriendly output from the SubHub Link agent so replies stay concise and readable on phones.

## Scope

This change applies to three layers that currently shape the final reply:

1. The main agent prompt in `link/agents/subhub.yaml`
2. The subscription-management skill in `link/agents/skills/manage-subscriptions/SKILL.md`
3. The server-side markdown formatters in `src/subhub/display.py`

## Requirements

### Response style

- Replies must stay concise by default.
- The agent must answer the user's request directly and avoid proactive add-on suggestions unless explicitly asked.
- The agent must avoid closing pleasantries such as “需要我再帮你…” or similar invitation-style endings.
- Emoji should not be used by default.

### Markdown constraints

- Prefer only:
  - level-1 headings
  - level-2 headings
  - unordered lists
  - ordered lists
- Allow tables only when they are the clearest carrier for subscription lists or reports.
- Do not use blockquotes in normal replies.

### Tool-result handling

- When tool-returned markdown is already concise and useful, the agent may return it directly.
- When tool-returned markdown includes decorative or trailing helper copy, that copy should be removed at the source instead of relying on the agent to trim it every time.

## Design

### Agent prompt changes

Add explicit hard rules for concise output, limited markdown, no quotes, minimal emoji, and no extra recommendation/closing language.

### Skill changes

Update the skill response rules so normal query/report/reminder answers lead with the result and only include the minimum necessary clarification.

### Display-layer changes

Simplify reminder and report formatters by removing emoji-heavy titles and footer helper text so API-provided markdown is mobile-friendly by default.

## Testing

- Add formatter tests to lock in the simplified reminder/report output.
- Run targeted tests for `tests/test_display.py`.
- Run the full test suite after the implementation.

## Risks

- Removing helper footers may slightly reduce discoverability of follow-up actions.
- This is acceptable because the user explicitly prefers shorter mobile-friendly output.
