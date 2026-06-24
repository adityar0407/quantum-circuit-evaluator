from __future__ import annotations

from backend.services.resource_estimators.azure_qre import AzureQreEstimator
from backend.services.resource_estimators.base import ResourceEstimator, ResourceEstimatorError
from backend.services.resource_estimators.simple_logical import SimpleLogicalEstimator


def get_resource_estimator(key: str) -> ResourceEstimator:
    estimators: dict[str, ResourceEstimator] = {
        SimpleLogicalEstimator.key: SimpleLogicalEstimator(),
        AzureQreEstimator.key: AzureQreEstimator(),
    }

    try:
        return estimators[key]
    except KeyError as exc:
        supported = ", ".join(sorted(estimators))
        raise ResourceEstimatorError(f"Unsupported resource estimator '{key}'. Supported estimators: {supported}") from exc
