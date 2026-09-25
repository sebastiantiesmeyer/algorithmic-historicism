from pathlib import Path

from algorithmic_historicism.evaluation.composite import CompositeEvaluator


def test_evaluation_gating_on_geometry_failure(tmp_path: Path):
    evaluator = CompositeEvaluator()
    blend = tmp_path / "model.blend"
    render = tmp_path / "render.png"
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"r")
    result = evaluator.evaluate(
        return_code=1,
        blend_path=blend,
        render_path=render,
        reference=reference,
        description="d",
    )
    assert not result.passed
    assert not result.geometry_valid
