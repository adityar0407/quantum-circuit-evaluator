from __future__ import annotations

from pathlib import Path


FORBIDDEN_PRODUCTION_REFERENCES = (
    "QecIR",
    "qec_ir",
    "qec_lowering",
    "AnalyticalSurfaceCodeLowerer",
    "validate_qec_ir",
    "qec_ir_summary",
    "qec_operation_counts",
    "qec_lowering_warnings",
    "analytical_surface_code",
)


def test_production_backend_does_not_reference_custom_qec_compiler() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    offenders: list[str] = []

    for path in backend_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.name == "test_production_architecture.py":
            continue
        text = path.read_text()
        for reference in FORBIDDEN_PRODUCTION_REFERENCES:
            if reference in text:
                offenders.append(f"{path.relative_to(repo_root)} contains {reference}")

    assert offenders == []
