from __future__ import annotations

from backend.services.resource_estimators.base import ResourceEstimator, ResourceEstimatorError


def get_resource_estimator(key: str) -> ResourceEstimator:
    estimators = _build_estimators()

    try:
        return estimators[key]
    except KeyError as exc:
        supported = ", ".join(sorted(estimators))
        raise ResourceEstimatorError(f"Unsupported resource estimator '{key}'. Supported estimators: {supported}") from exc


def _build_estimators() -> dict[str, ResourceEstimator]:
    estimators: dict[str, ResourceEstimator] = {}

    try:
        from backend.services.resource_estimators.native_qre import NativeQreEstimator

        estimators[NativeQreEstimator.key] = NativeQreEstimator()
    except ModuleNotFoundError:
        pass

    try:
        from backend.services.resource_estimators.qiskit_compatibility import QiskitCompatibilityQreEstimator

        estimators[QiskitCompatibilityQreEstimator.key] = QiskitCompatibilityQreEstimator()
    except ModuleNotFoundError:
        pass

    if not estimators:
        raise ResourceEstimatorError(
            "No resource estimators are available because the QDK dependencies are not installed in this environment."
        )

    return estimators
