from __future__ import annotations

from typing import Any
import warnings

from qdk.estimator import EstimatorParams

from backend.IR.models.logical_ir import LogicalIR
from backend.IR.models.qec_ir import QecIR
from backend.models.estimation_profiles import EstimationContext


def build_qre_params(
    context: EstimationContext,
    logical_ir: LogicalIR | None = None,
    qec_ir: QecIR | None = None,
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
    qre_custom_qec_fields = _apply_custom_qec_scheme(params, qec)
    params.error_budget = qec.error_budget

    assumptions = {
        "logical_architecture": logical.to_dict(),
        "physical_hardware_profile": physical.to_dict(),
        "qec_profile": qec.to_dict(),
        "network_profile": network.to_dict() if network is not None else None,
        "qre_error_budget": qec.error_budget,
        "qre_qec_scheme": qec.qec_scheme,
        "qre_qec_profile_mode": qec.qre_profile_mode,
        "qre_custom_qec_fields": qre_custom_qec_fields,
        "qre_execution_model": "qec_aware",
        "qre_translation_model": "logical_qiskit",
        "current_qre_limitation": (
            "The installed QDK Qiskit interface does not directly estimate QecIR operations. "
            "QecIR supplies QEC parameters, operation counts, warnings, and traceability while QRE prices a "
            "Qiskit QuantumCircuit reconstructed from LogicalIR."
        ),
        "future_native_qre_flow": "LogicalIR -> QecIR -> QRE ISA/Trace -> QRE estimate",
        "logical_ir_version": logical_ir.version if logical_ir is not None else None,
        "logical_ir_compiler": logical_ir.compiler if logical_ir is not None else None,
        "logical_ir_remote_operation_count": logical_ir.remote_operation_count if logical_ir is not None else None,
        "logical_ir_analysis": logical_ir.metadata.get("analysis") if logical_ir is not None else None,
        "qec_ir": _summarize_qec_ir(qec_ir),
        "translation_notes": [
            "FTarget is treated as a logical architecture and routing object only.",
            "Azure QRE physical qubit parameters are sourced from an explicit physical hardware profile, not inferred from FTarget gate metadata.",
            "QEC assumptions are sourced from an explicit QEC profile before calling QRE.",
            "LogicalIR is lowered to QecIR before Azure QRE parameter construction, but QRE does not directly price QecIR operations in the current installed interface.",
            "Azure QRE receives a Qiskit QuantumCircuit materialized from LogicalIR because the installed QDK Qiskit entry point estimates gate-based circuits.",
            "The QRE result combines QecIR-derived assumptions and traceability with QRE pricing of the reconstructed logical Qiskit circuit.",
            "Remote and inter-node operations remain explicit unlowered operations in QecIR and are lowered to their base logical gate only for Azure QRE circuit submission.",
            "Remote protocol overhead is not included in Azure QRE resource counts yet.",
        ],
    }

    return params, assumptions


def _apply_custom_qec_scheme(params: EstimatorParams, qec: Any) -> dict[str, Any]:
    if qec.qre_profile_mode != "custom":
        return {}

    applied: dict[str, Any] = {}
    for field in (
        "error_correction_threshold",
        "crossing_prefactor",
        "distance_coefficient_power",
        "logical_cycle_time",
        "physical_qubits_per_logical_qubit",
        "max_code_distance",
    ):
        value = getattr(qec, field)
        if value is not None:
            setattr(params.qec_scheme, field, value)
            applied[field] = value
    return applied


def _summarize_qec_ir(qec_ir: QecIR | None) -> dict[str, Any] | None:
    if qec_ir is None:
        return None
    return {
        "schema_version": qec_ir.schema_version,
        "code_family": qec_ir.code_family,
        "source_logical_ir_hash": qec_ir.source_logical_ir_hash,
        "patch_count": len(qec_ir.patches),
        "operation_count": len(qec_ir.operations),
        "operation_counts": qec_ir.operation_counts,
        "layer_count": len(qec_ir.operation_layers),
        "warnings": list(qec_ir.warnings),
    }


def _seconds_to_time_string(value: float) -> str:
    if value >= 1:
        return f"{value:g} s"
    if value >= 1e-3:
        return f"{value * 1e3:g} ms"
    if value >= 1e-6:
        return f"{value * 1e6:g} us"
    return f"{value * 1e9:g} ns"

