from __future__ import annotations

from typing import Any

from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.analytical_surface_code import AnalyticalSurfaceCodeEstimator


class SimpleLogicalEstimator:
    key = "simple_logical"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        return AnalyticalSurfaceCodeEstimator().estimate(compilation)
