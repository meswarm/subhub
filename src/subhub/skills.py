from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    content: str


def load_skills_from_dir(skills_dir: Path | None) -> list[Skill]:
    if skills_dir is None or not skills_dir.exists():
        return []

    roots = (
        [skills_dir]
        if (skills_dir / "SKILL.md").exists()
        else [path for path in skills_dir.iterdir() if path.is_dir()]
    )

    skills: list[Skill] = []
    for root in roots:
        path = root / "SKILL.md"
        if path.exists():
            skills.append(Skill(name=root.name, content=path.read_text(encoding="utf-8")))
    return skills


def format_skills_for_prompt(skills: list[Skill]) -> str:
    if not skills:
        return ""

    sections = ["## Skills"]
    for skill in skills:
        sections.append(f"### {skill.name}\n{skill.content}")
    return "\n\n".join(sections)
