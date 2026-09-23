"""The fe- subagent roster stays aligned across agent files, the rule, and docs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".cursor" / "agents"
RULE = ROOT / ".cursor" / "rules" / "subagent-routing.mdc"
WORKFLOW = ROOT / "docs" / "rules" / "workflow.md"
OPERATOR = ROOT / "docs" / "context" / "cursor-operator.md"

ROSTER = {
    "fe-explore": {
        "model": "composer-2.5-fast",
        "readonly": True,
        "cascade": ("composer-2.5-fast", "inherit"),
    },
    "fe-implement": {
        "model": "inherit",
        "readonly": False,
        "cascade": ("inherit",),
    },
    "fe-strategy-review": {
        "model": "claude-opus-5-thinking-high",
        "readonly": False,
        "cascade": ("claude-opus-5-thinking-high", "inherit"),
    },
    "fe-ui-review": {
        "model": "claude-4-sonnet",
        "readonly": False,
        "cascade": ("claude-4-sonnet", "inherit"),
    },
}


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    body = text.split("---", 2)[1]
    fields: dict[str, str] = {}
    for line in body.splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _cascade_cell(text: str, agent: str) -> str:
    cascade = text.split("## Cascade", 1)[1]
    for line in cascade.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"| `{agent}`"):
            return stripped
    raise AssertionError(f"{agent} cascade row missing")


def test_agent_files_match_roster():
    names = sorted(path.stem for path in AGENTS.glob("*.md"))
    assert names == sorted(ROSTER)

    for name, expected in ROSTER.items():
        fields = _frontmatter(AGENTS / f"{name}.md")
        assert fields["name"] == name
        assert fields["model"] == expected["model"]
        readonly = fields.get("readonly", "false") == "true"
        assert readonly is expected["readonly"]
        body = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
        for slug in expected["cascade"]:
            assert f"`{slug}`" in body


def test_rule_requires_cascade_and_actual_model_report():
    text = RULE.read_text(encoding="utf-8")
    assert "alwaysApply: true" in text
    assert "the model that actually ran" in text
    assert "Do not invent another model." in text

    for name, expected in ROSTER.items():
        cell = _cascade_cell(text, name)
        rendered = " → ".join(f"`{slug}`" for slug in expected["cascade"])
        assert rendered in cell


def test_docs_repeat_the_same_roster():
    for path in (WORKFLOW, OPERATOR):
        text = path.read_text(encoding="utf-8")
        assert "the model that actually ran" in text
        for name, expected in ROSTER.items():
            assert f"`{name}`" in text
            assert f"`{expected['model']}`" in text
            rendered = " → ".join(f"`{slug}`" for slug in expected["cascade"])
            assert rendered in text
