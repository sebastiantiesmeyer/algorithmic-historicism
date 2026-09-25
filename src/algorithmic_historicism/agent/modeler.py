from __future__ import annotations

from dataclasses import dataclass

from ..tasks.models import ComponentTask


@dataclass(frozen=True)
class ModelingPlan:
    architectural_interpretation: str
    geometric_primitives: list[str]
    symmetry_assumptions: str
    repetition_assumptions: str
    strategy: str
    dimensions_and_ratios: list[str]
    uncertain_features: list[str]
    required_existing_skills: list[str]
    potentially_new_capability: str | None = None


def default_plan(task: ComponentTask) -> ModelingPlan:
    return ModelingPlan(
        architectural_interpretation=f"Massing-first {task.component_type} reconstruction",
        geometric_primitives=["box", "profile", "boolean cutter"],
        symmetry_assumptions="Assume bilateral symmetry unless hints override.",
        repetition_assumptions="Reuse linked duplicates for semantically repeated sub-elements.",
        strategy="Use accepted skill implementation if available; fallback to simplified procedural proxy.",
        dimensions_and_ratios=["respect opening proportion", "keep projection shallow"],
        uncertain_features=["ornament detail may be simplified"],
        required_existing_skills=[task.component_type],
    )
