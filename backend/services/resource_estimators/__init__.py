from __future__ import annotations

from backend.services.resource_estimators.base import ResourceEstimator, ResourceEstimatorError
from backend.services.resource_estimators.native_qre import NativeQreEstimator
from backend.services.resource_estimators.qiskit_compatibility import QiskitCompatibilityQreEstimator


def get_resource_estimator(key: str) -> ResourceEstimator:
    estimators: dict[str, ResourceEstimator] = {
        NativeQreEstimator.key: NativeQreEstimator(),
        QiskitCompatibilityQreEstimator.key: QiskitCompatibilityQreEstimator(),
    }

    try:
        return estimators[key]
    except KeyError as exc:
        supported = ", ".join(sorted(estimators))
        raise ResourceEstimatorError(f"Unsupported resource estimator '{key}'. Supported estimators: {supported}") from exc
