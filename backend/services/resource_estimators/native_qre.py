from __future__ import annotations

import importlib.metadata as importlib_metadata
import math
import re
from typing import Any

from qdk.qre.models import qec as qdk_qec_models
from qdk.qre import LatticeSurgery
from qdk.qre import Trace
from qdk.qre import instruction_ids

from backend.IR.models.logical_ir import LogicalIR
from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.base import ResourceEstimatorError
from backend.services.resource_estimators.physical_qdk_adapter import physical_profile_to_qdk_model


SUPPORTED_NATIVE_OPERATIONS = {
    "BARRIER",
    "CX",
    "H",
    "MEASURE",
    "RESET",
    "RX",
    "RY",
    "RZ",
    "S",
    "SDG",
    "T",
    "TDG",
    "X",
    "Z",
}
NATIVE_SINGLE_QUBIT_INSTRUCTIONS = {
    "H": instruction_ids.H,
    "X": instruction_ids.PAULI_X,
    "Z": instruction_ids.PAULI_Z,
    "S": instruction_ids.S,
    "SDG": instruction_ids.S_DAG,
    "T": instruction_ids.T,
    "TDG": instruction_ids.T_DAG,
}
NATIVE_ROTATION_INSTRUCTIONS = {
    "RX": instruction_ids.RX,
    "RY": instruction_ids.RY,
    "RZ": instruction_ids.RZ,
}
QDK_QEC_MODELS = {
    "surface_code": qdk_qec_models.SurfaceCode,
    "surface_code_low_move": qdk_qec_models.SurfaceCodeLowMove,
    "three_aux": qdk_qec_models.ThreeAux,
    "one_dimensional_yoked_surface_code": qdk_qec_models.OneDimensionalYokedSurfaceCode,
    "two_dimensional_yoked_surface_code": qdk_qec_models.TwoDimensionalYokedSurfaceCode,
}

QEC_MODEL_PARAMETER_TYPES = {
    "surface_code": {
        "crossing_prefactor": float,
        "error_correction_threshold": float,
        "one_qubit_gate_depth": int,
        "two_qubit_gate_depth": int,
        "code_cycle_override": int,
        "code_cycle_offset": int,
        "distance": int,
    },
    "surface_code_low_move": {
        "crossing_prefactor": float,
        "error_correction_threshold": float,
        "code_cycle_override": int,
        "code_cycle_offset": int,
        "distance": int,
    },
    "three_aux": {
        "distance": int,
        "single_rail": bool,
    },
    "one_dimensional_yoked_surface_code": {
        "crossing_prefactor": float,
        "error_correction_threshold": float,
    },
    "two_dimensional_yoked_surface_code": {
        "crossing_prefactor": float,
        "error_correction_threshold": float,
    },
}


class NativeQreEstimator:
    key = "native_qre"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        if compilation.estimation_context is None:
            raise ResourceEstimatorError("Native QRE estimator requires an estimation context.")
        if compilation.logical_ir is None:
            raise ResourceEstimatorError("Native QRE estimator requires LogicalIR v1.")

        trace, adapter_summary = logical_ir_to_native_qre_trace(compilation.logical_ir)
        lattice_surgery_trace = LatticeSurgery().transform(trace)
        if lattice_surgery_trace is None:
            raise ResourceEstimatorError("Native QRE lattice-surgery transform returned no trace.")

        context = compilation.estimation_context
        physical = context.physical_hardware
        qec = context.qec
        physical_model = physical_profile_to_qdk_model(physical)
        architecture_context = physical_model.model.context()
        qec_model, qec_model_summary = _build_qec_model(qec.qec_model_name, qec.qec_model_source, qec.qec_model_parameters)
        surface_code_isa = next(
            iter(
                qec_model.provided_isa(architecture_context.isa, architecture_context)
            )
        )
        result = lattice_surgery_trace.estimate(surface_code_isa, max_error=qec.error_budget)
        if result is None:
            raise ResourceEstimatorError("Native QRE returned no feasible estimate for the generated trace.")

        return {
            "physical_qubits": result.qubits,
            "runtime": result.runtime,
            "runtime_unit": "ns",
            "logical_error": result.error,
            "qre_mode": self.key,
            "qre_input_source": "native_trace",
            "qdk_version": _qdk_version(),
            "native_qre_trace": adapter_summary,
            "native_qre_lattice_surgery": {
                "trace_depth": lattice_surgery_trace.depth,
                "trace_num_gates": lattice_surgery_trace.num_gates,
                "trace_total_qubits": lattice_surgery_trace.total_qubits,
                "trace_json": lattice_surgery_trace.to_json(),
            },
            "qre_assumptions": {
                "qre_execution_model": "native_qre",
                "qre_translation_model": "logical_ir_to_native_trace",
                "qdk_version": _qdk_version(),
                "estimator_mode": self.key,
                "input_representation": "qdk.qre.Trace",
                "qre_transform": "qdk.qre.LatticeSurgery().transform(trace)",
                "qec_scheme": qec.qec_scheme,
                "qec_model": qec_model_summary,
                "max_error": qec.error_budget,
                "physical_hardware_profile": physical.to_dict(),
                "physical_hardware": physical_model.metadata,
                "logical_ir_version": compilation.logical_ir.version,
                "logical_ir_compiler": compilation.logical_ir.compiler,
                "supported_native_operations": sorted(SUPPORTED_NATIVE_OPERATIONS),
                "translation_notes": [
                    "Native mode builds qdk.qre.Trace directly from LogicalIR.",
                    "Native mode applies qdk.qre.LatticeSurgery().transform(trace).",
                    "Native mode calls Trace.estimate(...) and does not call qdk.qiskit.estimate.",
                    "Supported native operations are explicitly validated through Trace, LatticeSurgery transform, and Trace.estimate before being exposed.",
                    "Reset is represented as QDK MEAS_RESET_Z because this QDK version exposes measurement-reset instructions rather than a plain reset instruction.",
                ],
            },
        }


def logical_ir_to_native_qre_trace(logical_ir: LogicalIR) -> tuple[Trace, dict[str, Any]]:
    trace = Trace(logical_ir.logical_qubit_count)
    mapped_operations: list[dict[str, Any]] = []
    skipped_operations: list[dict[str, Any]] = []
    source_operations = [operation.to_dict() for operation in logical_ir.operations]

    for operation in logical_ir.operations:
        base_operation = operation.base_operation.upper()
        qre_parameters: list[float] = []
        if operation.op_kind == "two_qubit_remote":
            raise ResourceEstimatorError(
                f"Native QRE does not support remote operation {operation.operation} at {operation.op_id}. "
                "Remote protocol lowering is not implemented."
            )
        if base_operation == "BARRIER":
            skipped_operations.append({"op_id": operation.op_id, "operation": base_operation, "reason": "barrier"})
            continue
        if base_operation in NATIVE_SINGLE_QUBIT_INSTRUCTIONS and operation.op_kind == "single_qubit":
            trace.add_operation(NATIVE_SINGLE_QUBIT_INSTRUCTIONS[base_operation], operation.qargs)
        elif base_operation in NATIVE_ROTATION_INSTRUCTIONS and operation.op_kind == "single_qubit":
            qre_parameters = [_native_rotation_parameter(operation)]
            trace.add_operation(
                NATIVE_ROTATION_INSTRUCTIONS[base_operation],
                operation.qargs,
                qre_parameters,
            )
        elif base_operation == "CX" and operation.op_kind == "two_qubit_local":
            trace.add_operation(instruction_ids.CX, operation.qargs)
        elif base_operation == "MEASURE" and operation.op_kind == "measure":
            trace.add_operation(instruction_ids.MEAS_Z, operation.qargs)
        elif base_operation == "RESET" and operation.op_kind == "reset":
            trace.add_operation(instruction_ids.MEAS_RESET_Z, operation.qargs)
        else:
            raise ResourceEstimatorError(
                f"Native QRE does not support operation {base_operation} at {operation.op_id}. "
                f"Supported operations: {', '.join(sorted(SUPPORTED_NATIVE_OPERATIONS))}."
            )
        mapped_operations.append(
            {
                "op_id": operation.op_id,
                "operation": base_operation,
                "qargs": operation.qargs,
                "parameters": operation.parameters,
                "qre_parameters": qre_parameters,
                "qre_instruction": _qre_instruction_label(base_operation),
            }
        )

    return trace, {
        "source": "LogicalIR",
        "compute_qubits": logical_ir.logical_qubit_count,
        "mapped_operation_count": len(mapped_operations),
        "skipped_operation_count": len(skipped_operations),
        "mapped_operations": mapped_operations,
        "skipped_operations": skipped_operations,
        "source_operations": source_operations,
        "trace_json": trace.to_json(),
        "mapping_notes": [
            "X maps to qdk.qre.instruction_ids.PAULI_X.",
            "Z maps to qdk.qre.instruction_ids.PAULI_Z.",
            "S and SDG map to qdk.qre.instruction_ids.S and S_DAG.",
            "T and TDG map to qdk.qre.instruction_ids.T and T_DAG; the installed QDK lattice-surgery transform accepts and estimates them without exposing a separate factory-model input in this API.",
            "RX, RY, and RZ map to qdk.qre rotation instruction IDs with one angle parameter.",
            "RESET maps to qdk.qre.instruction_ids.MEAS_RESET_Z because the installed QDK exposes measurement-reset instructions rather than a plain reset instruction.",
        ],
    }


def _native_rotation_parameter(operation: Any) -> float:
    if not operation.parameters:
        raise ResourceEstimatorError(f"Native QRE rotation {operation.operation} at {operation.op_id} requires one angle parameter.")
    value = operation.parameters[0]
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not re.fullmatch(r"[0-9eE+\\-*/(). pi]+", text):
        raise ResourceEstimatorError(f"Native QRE rotation {operation.operation} at {operation.op_id} has unsupported angle parameter: {text}.")
    try:
        return float(eval(text, {"__builtins__": {}}, {"pi": math.pi}))
    except Exception as exc:
        raise ResourceEstimatorError(f"Native QRE rotation {operation.operation} at {operation.op_id} has invalid angle parameter: {text}.") from exc


def _qre_instruction_label(base_operation: str) -> str:
    if base_operation in NATIVE_SINGLE_QUBIT_INSTRUCTIONS:
        return {
            "H": "H",
            "X": "PAULI_X",
            "Z": "PAULI_Z",
            "S": "S",
            "SDG": "S_DAG",
            "T": "T",
            "TDG": "T_DAG",
        }[base_operation]
    if base_operation in NATIVE_ROTATION_INSTRUCTIONS:
        return base_operation
    if base_operation == "CX":
        return "CX"
    if base_operation == "MEASURE":
        return "MEAS_Z"
    if base_operation == "RESET":
        return "MEAS_RESET_Z"
    return base_operation


def _build_qec_model(model_name: str, source: str, raw_parameters: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    normalized_name = model_name.strip().lower()
    if normalized_name not in QDK_QEC_MODELS:
        supported = ", ".join(sorted(QDK_QEC_MODELS))
        raise ResourceEstimatorError(f"Native QRE does not support QEC model {model_name}. Supported models: {supported}.")

    normalized_source = source.strip().lower()
    if normalized_source not in {"azure_builtin", "custom"}:
        raise ResourceEstimatorError("QEC model source must be either azure_builtin or custom.")

    parameters = {}
    if normalized_source == "custom":
        parameters = _coerce_qec_parameters(normalized_name, raw_parameters)

    model_class = QDK_QEC_MODELS[normalized_name]
    try:
        model = model_class(**parameters)
    except Exception as exc:
        raise ResourceEstimatorError(f"Failed to build QDK QEC model {normalized_name}: {exc}") from exc

    return model, {
        "source": normalized_source,
        "name": normalized_name,
        "class": model_class.__name__,
        "parameters": parameters,
        "attributes": _qec_model_attributes(model),
    }


def _coerce_qec_parameters(model_name: str, raw_parameters: dict[str, Any]) -> dict[str, Any]:
    allowed = QEC_MODEL_PARAMETER_TYPES[model_name]
    parameters: dict[str, Any] = {}
    for key, raw_value in raw_parameters.items():
        if raw_value is None or raw_value == "":
            continue
        if key not in allowed:
            supported = ", ".join(sorted(allowed))
            raise ResourceEstimatorError(f"QEC model {model_name} does not support parameter {key}. Supported parameters: {supported}.")
        parameters[key] = _coerce_parameter_value(key, raw_value, allowed[key])
    return parameters


def _coerce_parameter_value(key: str, value: Any, parameter_type: type) -> Any:
    try:
        if parameter_type is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes"}:
                    return True
                if lowered in {"false", "0", "no"}:
                    return False
            raise ValueError("expected boolean")
        return parameter_type(value)
    except (TypeError, ValueError) as exc:
        raise ResourceEstimatorError(f"Invalid QEC parameter {key}: {value}") from exc


def _qec_model_attributes(model: Any) -> dict[str, Any]:
    attributes = {}
    for key in (
        "distance",
        "crossing_prefactor",
        "error_correction_threshold",
        "one_qubit_gate_depth",
        "two_qubit_gate_depth",
        "code_cycle_override",
        "code_cycle_offset",
        "single_rail",
    ):
        if hasattr(model, key):
            attributes[key] = getattr(model, key)
    return attributes


def _qdk_version() -> str:
    try:
        return importlib_metadata.version("qdk")
    except importlib_metadata.PackageNotFoundError:
        return "unknown"
