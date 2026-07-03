from fastapi import APIRouter, HTTPException

from backend.api.schemas import CircuitPreviewResponse, CircuitQasmRequest, CircuitSummaryResponse
from backend.services.circuit_service import CircuitValidationError, preview_qasm, summarize_qasm

router = APIRouter()


@router.post("/validate", response_model=CircuitPreviewResponse)
def validate_circuit(payload: CircuitQasmRequest) -> CircuitPreviewResponse:
    try:
        return CircuitPreviewResponse(**preview_qasm(payload.qasm))
    except CircuitValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/preview", response_model=CircuitPreviewResponse)
def preview_circuit(payload: CircuitQasmRequest) -> CircuitPreviewResponse:
    try:
        return CircuitPreviewResponse(**preview_qasm(payload.qasm))
    except CircuitValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
