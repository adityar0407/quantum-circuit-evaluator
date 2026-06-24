from __future__ import annotations

from typing import Any

from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.base import ResourceEstimatorUnavailable


class AzureQreEstimator:
    key = "azure_qre"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        raise ResourceEstimatorUnavailable(
            "Azure QRE estimator is not wired yet. "
            "Next step: add a QRE JSON trace/ISA adapter and call a QDK QRE wrapper."
        )
