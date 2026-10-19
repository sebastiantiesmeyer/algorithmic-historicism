from pathlib import Path

import pytest

from algorithmic_historicism.skills.format import SkillDocument, load_skill_document, parse_skill_text


def test_skill_document_round_trip(tmp_path: Path):
    document = SkillDocument(
        name="normalize-text",
        description="Normalize short text labels.",
        instructions="# Workflow\n\nNormalize separators.",
    )
    path = tmp_path / "SKILL.md"
    path.write_text(document.render(), encoding="utf-8")

    assert load_skill_document(path) == document


def test_skill_document_requires_portable_frontmatter():
    with pytest.raises(ValueError, match="frontmatter"):
        parse_skill_text("# legacy skill")
