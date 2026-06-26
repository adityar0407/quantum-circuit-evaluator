from __future__ import annotations

import importlib.metadata as importlib_metadata
from typing import Any
import warnings

from qdk.estimator import EstimatorParams

from backend.IR.models.logical_ir import LogicalIR
from backend.models.estimation_profiles import EstimationContext


def build_qre_params(
    context: EstimationContext,
    logical_ir: LogicalIR | None = None,
) -> tuple[EstimatorParams, dict[str, Any]]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        params = EstimatorParams()

    physical = context.physical_hardware
    qec = context.qec
    logical = context.logical_architecture
    network = context.network

    qubit_params = params.qubit_params
    qubit_params.instruction_set = "gate-based"
    qubit_params.one_qubit_measurement_time = _seconds_to_time_string(physical.measurement_time)
    qubit_params.one_qubit_measurement_error_rate = physical.measurement_error_rate
    qubit_params.one_qubit_gate_time = _seconds_to_time_string(physical.one_qubit_gate_time)
    qubit_params.one_qubit_gate_error_rate = physical.one_qubit_gate_error_rate
    qubit_params.two_qubit_gate_time = _seconds_to_time_string(physical.two_qubit_gate_time)
    qubit_params.two_qubit_gate_error_rate = physical.two_qubit_gate_error_rate
    qubit_params.t_gate_time = _seconds_to_time_string(physical.one_qubit_gate_time)
    qubit_params.t_gate_error_rate = physical.one_qubit_gate_error_rate
    qubit_params.idle_error_rate = physical.idle_error_rate

    params.qec_scheme.name = qec.qec_scheme
    params.error_budget = qec.error_budget

    assumptions = {
        "logical_architecture": logical.to_dict(),
        "physical_hardware_profile": physical.to_dict(),
        "qec_profile": qec.to_dict(),
        "network_profile": network.to_dict() if network is not None else None,
        "qre_error_budget": qec.error_budget,
        "qre_qec_scheme": qec.qec_scheme,
        "qre_execution_model": "qiskit_compatibility",
        "qre_translation_model": "logical_qiskit",
        "qdk_version": _qdk_version(),
        "compatibility_mode_limitation": (
            "The compatibility path materializes a Qiskit QuantumCircuit from LogicalIR and submits it through "
            "qdk.qiskit.estimate. It is not the default estimator path."
        ),
        "native_qre_flow": "LogicalIR -> qdk.qre.Trace -> LatticeSurgery transform -> Trace.estimate",
        "logical_ir_version": logical_ir.version if logical_ir is not None else None,
        "logical_ir_compiler": logical_ir.compiler if logical_ir is not None else None,
        "logical_ir_remote_operation_count": logical_ir.remote_operation_count if logical_ir is not None else None,
        "logical_ir_analysis": logical_ir.metadata.get("analysis") if logical_ir is not None else None,
        "translation_notes": [
            "FTarget is treated as a logical architecture and routing object only.",
            "Azure QRE physical qubit parameters are sourced from an explicit physical hardware profile, not inferred from FTarget gate metadata.",
            "This explicit compatibility mode sends a Qiskit QuantumCircuit materialized from LogicalIR to qdk.qiskit.estimate.",
            "Remote and inter-node operations are lowered to their base logical gate only for Azure QRE circuit submission.",
            "Remote protocol overhead is not included in Azure QRE resource counts yet.",
        ],
    }

    return params, assumptions

def _seconds_to_time_string(value: float) -> str:
    if value >= 1:
        return f"{value:g} s"
    if value >= 1e-3:
        return f"{value * 1e3:g} ms"
    if value >= 1e-6:
        return f"{value * 1e6:g} us"
    return f"{value * 1e9:g} ns"


def _qdk_version() -> str:
    try:
        return importlib_metadata.version("qdk")
    except importlib_metadata.PackageNotFoundError:
        return "unknown"
