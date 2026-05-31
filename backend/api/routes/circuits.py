from fastapi import APIRouter, HTTPException

from backend.api.schemas import CircuitQasmRequest, CircuitSummaryResponse
from backend.services.circuit_service import CircuitValidationError, summarize_qasm

router = APIRouter()


@router.post("/validate", response_model=CircuitSummaryResponse)
def validate_circuit(payload: CircuitQasmRequest) -> CircuitSummaryResponse:
    try:
        return CircuitSummaryResponse(**summarize_qasm(payload.qasm))
    except CircuitValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

