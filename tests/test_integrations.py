from algorithmic_historicism.integrations.evoskill import EvoSkillAdapter
from algorithmic_historicism.integrations.muse import MuseAdapter
from algorithmic_historicism.integrations.wikiskill import WikiSkillAdapter


def test_external_adapter_interfaces():
    evo = EvoSkillAdapter().evaluate_candidate("a", "b", ["c"])
    wiki = WikiSkillAdapter().consolidate("runs/task/trajectory.json")
    muse = MuseAdapter().propose_missing_skill("pediment")
    assert evo["status"] == "adapter-ready"
    assert wiki["status"] == "adapter-ready"
    assert muse["proposal"] == "candidate-pediment"
