from fastapi import APIRouter, HTTPException

from backend.api.schemas import TranspileRequest, TranspileResponse
from backend.services.circuit_service import CircuitValidationError
from backend.services.target_service import TargetBuildError
from backend.services.transpilation_service import TranspilationError, transpile_qasm

router = APIRouter()


@router.post("/transpile", response_model=TranspileResponse)
def transpile(payload: TranspileRequest) -> TranspileResponse:
    try:
        return TranspileResponse(**transpile_qasm(payload.qasm, payload.target_config))
    except (CircuitValidationError, TargetBuildError, TranspilationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

