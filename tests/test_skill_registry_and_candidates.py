from pathlib import Path

from algorithmic_historicism.skills.candidates import CandidateSkillStore
from algorithmic_historicism.skills.registry import SkillRegistry


def test_skill_registry_lists_accepted(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "accepted-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# accepted")
    registry = SkillRegistry(tmp_path / "skills")
    names = [s.name for s in registry.list_accepted()]
    assert names == ["accepted-skill"]


def test_candidate_skill_lifecycle(tmp_path: Path):
    store = CandidateSkillStore(tmp_path / "skills/.candidates")
    created = store.create("new-skill", provenance="task-1/attempt_001")
    assert (created / "SKILL.md").exists()
    store.lifecycle_decision("new-skill", "CREATE")
    assert "decision: CREATE" in (created / "metadata.yaml").read_text()
