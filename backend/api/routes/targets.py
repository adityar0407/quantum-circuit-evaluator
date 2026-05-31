from fastapi import APIRouter, HTTPException

from backend.api.schemas import TargetPreviewRequest, TargetPreviewResponse
from backend.services.target_service import TargetBuildError, preview_target

router = APIRouter()


@router.post("/preview", response_model=TargetPreviewResponse)
def preview(payload: TargetPreviewRequest) -> TargetPreviewResponse:
    try:
        return TargetPreviewResponse(**preview_target(payload.config))
    except TargetBuildError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

