from __future__ import annotations

from typing import Any, Protocol

from backend.services.compilers.base import CompilationResult


class ResourceEstimatorError(RuntimeError):
    """Raised when a resource estimator cannot evaluate a compilation result."""


class ResourceEstimatorUnavailable(ResourceEstimatorError):
    """Raised when a requested estimator is not installed or configured."""


class ResourceEstimator(Protocol):
    key: str

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        ...
