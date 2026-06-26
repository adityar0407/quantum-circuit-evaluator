from fastapi import APIRouter

from backend.services.resource_estimators.native_qre import QDK_QEC_MODELS
from backend.services.resource_estimators.physical_qdk_adapter import physical_profile_capabilities

router = APIRouter()


@router.get("/resource-estimation")
def resource_estimation_capabilities() -> dict:
    return {
        "physical_hardware": physical_profile_capabilities(),
        "qec_models": sorted(QDK_QEC_MODELS),
        "native_operations": ["BARRIER", "CX", "H", "MEASURE"],
    }
