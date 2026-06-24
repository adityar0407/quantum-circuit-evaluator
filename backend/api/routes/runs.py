from fastapi import APIRouter, HTTPException

from backend.api.schemas import TranspileRequest, TranspileResponse
from backend.services.circuit_service import CircuitValidationError
from backend.services.target_service import TargetBuildError
from backend.services.transpilation_service import TranspilationError, compile_qasm

router = APIRouter()


def run_compilation(payload: TranspileRequest) -> TranspileResponse:
    try:
        return TranspileResponse(
            **compile_qasm(
                payload.qasm,
                payload.target_config,
                compiler_backend=payload.compiler_backend,
                resource_estimator=payload.resource_estimator,
            )
        )
    except (CircuitValidationError, TargetBuildError, TranspilationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/compile", response_model=TranspileResponse)
def compile_run(payload: TranspileRequest) -> TranspileResponse:
    return run_compilation(payload)


@router.post("/transpile", response_model=TranspileResponse)
def transpile(payload: TranspileRequest) -> TranspileResponse:
    return run_compilation(payload)
