from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvoSkillAdapter:
    name: str = "evoskill-adapter"

    def evaluate_candidate(self, accepted_skill: str, candidate_skill: str, benchmark_cases: list[str]) -> dict:
        return {
            "accepted_skill": accepted_skill,
            "candidate_skill": candidate_skill,
            "benchmark_cases": benchmark_cases,
            "status": "adapter-ready",
        }
