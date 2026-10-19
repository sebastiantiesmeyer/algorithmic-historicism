from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Protocol

from ..evaluation.base import EvaluationResult
from ..skills.candidates import CandidateSkillStore
from ..skills.format import SkillDocument
from ..wiki.workspace import WikiWorkspace
from .frontier import CandidateFrontier, FrontierEntry
from .models import BenchmarkCase, BenchmarkSuite, EvolutionReport, IterationResult, RolloutTrace, SkillProposal


class AgentRunner(Protocol):
    def run(self, case: BenchmarkCase, skill: SkillDocument | None) -> RolloutTrace: ...


class CaseEvaluator(Protocol):
    def evaluate(self, case: BenchmarkCase, trace: RolloutTrace) -> EvaluationResult: ...


class WikiMaintainer(Protocol):
    def consolidate(self, traces: list[RolloutTrace], wiki: WikiWorkspace, iteration: int) -> list[str]: ...


class SkillProposer(Protocol):
    def propose(
        self,
        wiki: WikiWorkspace,
        incumbent: SkillDocument | None,
        iteration: int,
    ) -> SkillProposal | None: ...


class EvolutionEngine:
    def __init__(
        self,
        *,
        workspace: Path,
        wiki_root: Path,
        runner: AgentRunner,
        evaluator: CaseEvaluator,
        maintainer: WikiMaintainer,
        proposer: SkillProposer,
        min_improvement: float = 0.0,
        frontier_capacity: int = 3,
    ):
        self.workspace = workspace
        self.wiki = WikiWorkspace.open(wiki_root, create=True)
        self.candidates = CandidateSkillStore(workspace / "candidates")
        self.skills_root = self.wiki.skills_dir
        self.skills_root.mkdir(parents=True, exist_ok=True)
        self.runner = runner
        self.evaluator = evaluator
        self.maintainer = maintainer
        self.proposer = proposer
        self.min_improvement = min_improvement
        self.frontier_capacity = frontier_capacity

    def _journal(self, payload: dict[str, object]) -> None:
        # Run diagnostics are separate from the training-only learning memory.
        with (self.workspace / "attempts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _rollout(
        self,
        cases: list[BenchmarkCase],
        skill: SkillDocument | None,
        *,
        iteration: int,
        persist: bool,
        condition: str = "evolution",
    ) -> list[RolloutTrace]:
        traces = []
        for case in cases:
            public_case = case.model_copy(update={"expected": ""})
            context = {"case_id": case.case_id, "split": case.split,
                       "iteration": iteration, "condition": condition,
                       "skill_name": skill.name if skill else None}
            self._journal({**context, "status": "started"})
            try:
                trace = self.runner.run(public_case, skill)
                self._journal({**context, "status": "generated",
                               "trace": trace.model_copy(update={"expected": ""}).model_dump(mode="json")})
                evaluation = self.evaluator.evaluate(case, trace)
            except Exception as exc:
                self._journal({**context, "status": "failed", "error_type": type(exc).__name__})
                raise
            trace = trace.model_copy(update={
                "expected": "",
                "score": evaluation.score,
                "evaluation": evaluation.model_dump(mode="json"),
            })
            traces.append(trace)
            self._journal({**context, "status": "completed", "trace": trace.model_dump(mode="json")})
            if persist:
                run_id = re.sub(r"[^a-z0-9]+", "-", self.workspace.name.lower()).strip("-") or "run"
                self.wiki.add_raw_trace(
                    run_id, iteration, trace.case_id, trace.model_dump(mode="json")
                )
        return traces

    @staticmethod
    def _score(traces: list[RolloutTrace]) -> float:
        return sum(trace.score for trace in traces) / len(traces) if traces else 0.0

    def _available_candidate_name(self, requested: str) -> str:
        if not (self.candidates.candidates_root / requested).exists() and not (
            self.skills_root / requested
        ).exists():
            return requested
        revision = 2
        while (self.candidates.candidates_root / f"{requested}-r{revision}").exists() or (
            self.skills_root / f"{requested}-r{revision}"
        ).exists():
            revision += 1
        return f"{requested}-r{revision}"

    def run(
        self,
        suite: BenchmarkSuite,
        *,
        max_iterations: int = 3,
        initial_skill: SkillDocument | None = None,
    ) -> EvolutionReport:
        suite.validate_splits()
        incumbent = initial_skill
        validation = suite.select("validation")
        baseline_score = self._score(
            self._rollout(validation, incumbent, iteration=0, persist=False)
        )
        best_score = baseline_score
        frontier = CandidateFrontier(self.frontier_capacity)
        frontier.add(FrontierEntry(
            name=incumbent.name if incumbent else "no-skill",
            score=baseline_score,
            skill=incumbent,
        ))
        history: list[IterationResult] = []

        for iteration in range(1, max_iterations + 1):
            training_traces = self._rollout(
                suite.select("training"), incumbent, iteration=iteration, persist=True
            )
            self.maintainer.consolidate(training_traces, self.wiki, iteration)
            proposal = self.proposer.propose(self.wiki, incumbent, iteration)
            if proposal is None:
                history.append(IterationResult(
                    iteration=iteration,
                    candidate_name=None,
                    baseline_score=best_score,
                    candidate_score=None,
                    frontier_admitted=False,
                    accepted=False,
                ))
                break

            candidate_name = self._available_candidate_name(proposal.name)
            self.candidates.create(
                candidate_name,
                provenance=f"{suite.name}:iteration-{iteration}",
                description=proposal.description,
                instructions=proposal.instructions,
                parent_skill=incumbent.name if incumbent else None,
                source_patterns=proposal.source_patterns,
            )
            candidate = SkillDocument(
                name=candidate_name,
                description=proposal.description,
                instructions=proposal.instructions,
            )
            candidate_score = self._score(
                self._rollout(validation, candidate, iteration=iteration, persist=False)
            )
            score_before_candidate = best_score
            frontier_admitted = frontier.add(FrontierEntry(
                name=candidate.name,
                score=candidate_score,
                skill=candidate,
                parent=incumbent.name if incumbent else "no-skill",
            ))
            accepted = candidate_score > score_before_candidate + self.min_improvement
            previous_text = incumbent.render() if incumbent else ""
            diff = "".join(difflib.unified_diff(
                previous_text.splitlines(keepends=True),
                candidate.render().splitlines(keepends=True),
                fromfile=incumbent.name if incumbent else "no-skill",
                tofile=candidate.name,
            ))
            self.wiki.append_skill_impact(
                iteration=iteration,
                candidate=candidate_name,
                baseline_score=score_before_candidate,
                candidate_score=candidate_score,
                accepted=accepted,
                rationale=proposal.rationale,
                diff=diff,
            )
            self.candidates.lifecycle_decision(
                candidate_name,
                "ACCEPTED" if accepted else ("FRONTIER" if frontier_admitted else "REJECTED"),
                validation_score=candidate_score,
                baseline_score=score_before_candidate,
                frontier_admitted=frontier_admitted,
            )
            if accepted:
                self.candidates.promote(candidate_name, self.skills_root)
                self.wiki.set_active_skill(
                    suite.name, candidate_name, workspace=str(self.workspace.resolve()),
                    iteration=iteration, validation_score=candidate_score,
                )
                incumbent = candidate
                best_score = candidate_score

            history.append(IterationResult(
                iteration=iteration,
                candidate_name=candidate_name,
                baseline_score=score_before_candidate,
                candidate_score=candidate_score,
                frontier_admitted=frontier_admitted,
                accepted=accepted,
            ))
            if best_score >= 1.0:
                break

        test_cases = suite.select("test")
        baseline_test_score = self._score(
            self._rollout(test_cases, None, iteration=0, persist=False, condition="no-skill")
        )
        test_score = baseline_test_score if incumbent is None else self._score(
            self._rollout(test_cases, incumbent, iteration=0, persist=False, condition="learned-skill")
        )
        return EvolutionReport(
            benchmark=suite.name,
            baseline_validation_score=baseline_score,
            best_validation_score=best_score,
            baseline_test_score=baseline_test_score,
            test_score=test_score,
            accepted_skill=incumbent.name if incumbent else None,
            iterations=history,
        )
