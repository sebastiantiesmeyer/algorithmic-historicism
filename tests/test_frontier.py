from algorithmic_historicism.evolution.frontier import CandidateFrontier, FrontierEntry


def test_frontier_keeps_bounded_top_scoring_programs():
    frontier = CandidateFrontier(capacity=2)

    assert frontier.add(FrontierEntry("base", 0.4, None))
    assert frontier.add(FrontierEntry("candidate-a", 0.7, None, parent="base"))
    assert not frontier.add(FrontierEntry("candidate-b", 0.3, None, parent="base"))
    assert frontier.add(FrontierEntry("candidate-c", 0.8, None, parent="candidate-a"))

    assert [entry.name for entry in frontier.entries] == ["candidate-c", "candidate-a"]
