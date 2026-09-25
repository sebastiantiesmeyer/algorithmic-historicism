from pathlib import Path

from algorithmic_historicism.wiki.local import LocalWikiStore


def test_wiki_storage_with_provenance(tmp_path: Path):
    wiki = LocalWikiStore(tmp_path / "wiki")
    wiki.append_observation(
        "rustication",
        "Use segment cutters",
        {"task_id": "t1", "attempt_ids": ["attempt_001"], "date": "2026-09-25", "skill": "routed-rustication"},
    )
    content = (tmp_path / "wiki" / "rustication.md").read_text()
    assert "task_id: t1" in content
    assert "attempt_001" in content
