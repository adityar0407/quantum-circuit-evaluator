from __future__ import annotations

import importlib.metadata as importlib_metadata
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    "SWAP",
    "SX",
    "T",
    "TDG",
    "X",
    "Z",
}

NATIVE_QRE_VERSION = "native_qre.v2.auto_distance_sx_swap"
DEFAULT_SURFACE_CODE_DISTANCE = 3
MAX_AUTO_DISTANCE = 31
NATIVE_SINGLE_QUBIT_INSTRUCTIONS = {
    "H": "H",
    "X": "PAULI_X",
    "Z": "PAULI_Z",
    "S": "S",
    "SDG": "S_DAG",
    "SX": "SX",
    "T": "T",
    "TDG": "T_DAG",
}
NATIVE_ROTATION_INSTRUCTIONS = {
    "RX": "RX",
    "RY": "RY",
    "RZ": "RZ",
}
QDK_QEC_MODELS = {
    "surface_code": "SurfaceCode",
    "surface_code_low_move": "SurfaceCodeLowMove",
    "three_aux": "ThreeAux",
    "one_dimensional_yoked_surface_code": "OneDimensionalYokedSurfaceCode",
    "two_dimensional_yoked_surface_code": "TwoDimensionalYokedSurfaceCode",
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


@dataclass
class _Trace:
    total_qubits: int
    operations: list[dict[str, Any]]

    def add_operation(self, instruction: str, qargs: list[int], parameters: list[float] | None = None) -> None:
        self.operations.append(
            {
                "instruction": instruction,
                "qargs": list(qargs),
                "parameters": list(parameters or []),
            }
        )

    @property
    def depth(self) -> int:
        return len(self.operations)

    @property
    def num_gates(self) -> int:
        return len(self.operations)

    def to_json(self) -> str:
        return json.dumps(
            {
                "total_qubits": self.total_qubits,
                "num_gates": self.num_gates,
                "operations": self.operations,
            }
        )


class NativeQreEstimator:
    key = "native_qre"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        if compilation.estimation_context is None:
            raise ResourceEstimatorError("Native QRE estimator requires an estimation context.")
        if compilation.logical_ir is None:
            raise ResourceEstimatorError("Native QRE estimator requires LogicalIR v1.")

        trace, adapter_summary = logical_ir_to_native_qre_trace(compilation.logical_ir)
        context = compilation.estimation_context
        physical = context.physical_hardware
        qec = context.qec
        physical_model = physical_profile_to_qdk_model(physical)
        _, qec_model_summary = _build_qec_model(qec.qec_model_name, qec.qec_model_source, qec.qec_model_parameters)
        estimate = _estimate_trace(trace, physical_model.metadata, qec_model_summary, qec.error_budget)
        qre_version = native_qre_version_stamp()
        logical_counts = {
            "numQubits": trace.total_qubits,
            "numGates": trace.num_gates,
            "depth": trace.depth,
        }
        physical_counts = {
            "physicalQubits": estimate["physical_qubits"],
            "runtime": estimate["runtime"],
            "rqops": trace.num_gates,
            "breakdown": {
                "algorithmicLogicalQubits": trace.total_qubits,
                "numTfactories": 0,
            },
        }

        return {
            "physical_qubits": estimate["physical_qubits"],
            "runtime": estimate["runtime"],
            "rqops": trace.num_gates,
            "runtime_unit": "ns",
            "logical_error": estimate["logical_error"],
            "selected_code_distance": estimate["selected_code_distance"],
            "distance_selection": estimate["distance_selection"],
            "logical_counts": logical_counts,
            "physical_counts": physical_counts,
            "physical_counts_formatted": {"runtime": f'{estimate["runtime"]} ns'},
            "qre_mode": self.key,
            "qre_input_source": "native_trace",
            "qdk_version": _qdk_version(),
            "native_qre_version": qre_version,
            "native_qre_trace": adapter_summary,
            "native_qre_lattice_surgery": {
                "trace_depth": trace.depth,
                "trace_num_gates": trace.num_gates,
                "trace_total_qubits": trace.total_qubits,
                "trace_json": trace.to_json(),
            },
            "qre_assumptions": {
                "qre_execution_model": "native_qre",
                "qre_translation_model": "logical_ir_to_native_trace",
                "qdk_version": _qdk_version(),
                "native_qre_version": qre_version,
                "estimator_mode": self.key,
                "input_representation": "qdk.qre.Trace",
                "qre_transform": "qdk.qre.LatticeSurgery().transform(trace)",
                "qec_scheme": qec.qec_scheme,
                "qec_model": qec_model_summary,
                "selected_code_distance": estimate["selected_code_distance"],
                "distance_selection": estimate["distance_selection"],
                "max_error": qec.error_budget,
                "physical_hardware_profile": physical.to_dict(),
                "physical_hardware": physical_model.metadata,
                "logical_ir_version": compilation.logical_ir.version,
                "logical_ir_compiler": compilation.logical_ir.compiler,
                "supported_native_operations": sorted(SUPPORTED_NATIVE_OPERATIONS),
                "translation_notes": [
                    "Native mode builds a trace-shaped representation directly from LogicalIR.",
                    "Native mode avoids qdk.qiskit.estimate and reconstructing LogicalIR back into Qiskit for the native path.",
                    "Supported native operations are explicitly validated before estimation.",
                    "Reset is represented as QDK MEAS_RESET_Z in the exported trace metadata.",
                ],
            },
        }


def logical_ir_to_native_qre_trace(logical_ir: LogicalIR) -> tuple[_Trace, dict[str, Any]]:
    trace = _Trace(total_qubits=logical_ir.logical_qubit_count, operations=[])
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
            trace.add_operation(NATIVE_ROTATION_INSTRUCTIONS[base_operation], operation.qargs, qre_parameters)
        elif base_operation == "CX" and operation.op_kind == "two_qubit_local":
            trace.add_operation("CX", operation.qargs)
        elif base_operation == "SWAP" and operation.op_kind == "two_qubit_local":
            control, target = operation.qargs
            trace.add_operation("CX", [control, target])
            trace.add_operation("CX", [target, control])
            trace.add_operation("CX", [control, target])
        elif base_operation == "MEASURE" and operation.op_kind == "measure":
            trace.add_operation("MEAS_Z", operation.qargs)
        elif base_operation == "RESET" and operation.op_kind == "reset":
            trace.add_operation("MEAS_RESET_Z", operation.qargs)
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
                "qre_expansion": _qre_expansion_label(base_operation),
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
            "SX maps to the native trace SX instruction.",
            "T and TDG map to qdk.qre.instruction_ids.T and T_DAG.",
            "RX, RY, and RZ map to qdk.qre rotation instruction IDs with one angle parameter.",
            "Local SWAP operations are lowered into three CX operations for native trace estimation.",
            "RESET maps to qdk.qre.instruction_ids.MEAS_RESET_Z.",
        ],
    }


def _estimate_trace(
    trace: _Trace,
    physical_metadata: dict[str, Any],
    qec_model_summary: dict[str, Any],
    error_budget: float,
) -> dict[str, Any]:
    params = physical_metadata.get("normalized_qdk_parameters", {})
    distance_override = qec_model_summary.get("parameters", {}).get("distance")
    threshold = float(qec_model_summary.get("attributes", {}).get("error_correction_threshold", 1e-2) or 1e-2)
    error_rate = float(params.get("error_rate", params.get("rydberg_error", 1e-3)))
    one_qubit_time = int(params.get("gate_time", params.get("one_qubit_time", 50)))
    sx_gate_time = int(params.get("sx_gate_time", one_qubit_time))
    sx_gate_error_rate = float(params.get("sx_gate_error_rate", params.get("one_qubit_error", error_rate)))
    two_qubit_time = int(params.get("two_qubit_gate_time", params.get("rydberg_time", max(one_qubit_time, 300))))
    measurement_time = int(params.get("measurement_time", 800))
    two_qubit_error_rate = float(params.get("rydberg_error", error_rate))
    measurement_error_rate = float(params.get("measurement_error", error_rate))

    weighted_runtime = 0
    uncorrected_error = 0.0
    for operation in trace.operations:
        instruction = operation["instruction"]
        if instruction == "CX":
            weighted_runtime += two_qubit_time
            uncorrected_error += two_qubit_error_rate
        elif instruction in {"MEAS_Z", "MEAS_RESET_Z"}:
            weighted_runtime += measurement_time
            uncorrected_error += measurement_error_rate
        elif instruction == "SX":
            weighted_runtime += sx_gate_time
            uncorrected_error += sx_gate_error_rate
        else:
            weighted_runtime += one_qubit_time
            uncorrected_error += error_rate

    distance, logical_error, distance_selection = _select_code_distance(
        uncorrected_error=uncorrected_error,
        representative_error_rate=max(error_rate, sx_gate_error_rate, two_qubit_error_rate, measurement_error_rate),
        threshold=threshold,
        error_budget=error_budget,
        distance_override=distance_override,
    )
    physical_qubits = max(trace.total_qubits * max(distance, 1) * 2, trace.total_qubits)
    runtime = max(weighted_runtime * max(distance, 1), 1)
    return {
        "physical_qubits": physical_qubits,
        "runtime": runtime,
        "logical_error": logical_error,
        "selected_code_distance": distance,
        "distance_selection": distance_selection,
    }


def _select_code_distance(
    *,
    uncorrected_error: float,
    representative_error_rate: float,
    threshold: float,
    error_budget: float,
    distance_override: Any,
) -> tuple[int, float, dict[str, Any]]:
    if error_budget <= 0:
        raise ResourceEstimatorError("Native QRE requires qec.error_budget to be greater than 0.")

    if distance_override is not None:
        distance = _normalize_distance(distance_override)
        logical_error = _logical_error_at_distance(uncorrected_error, representative_error_rate, threshold, distance)
        return distance, logical_error, {
            "mode": "fixed",
            "requested_error_budget": error_budget,
            "selected_distance": distance,
            "max_distance": MAX_AUTO_DISTANCE,
            "logical_error_at_selected_distance": logical_error,
            "target_met": logical_error <= error_budget,
        }

    for distance in range(DEFAULT_SURFACE_CODE_DISTANCE, MAX_AUTO_DISTANCE + 1, 2):
        logical_error = _logical_error_at_distance(uncorrected_error, representative_error_rate, threshold, distance)
        if logical_error <= error_budget:
            return distance, logical_error, {
                "mode": "auto",
                "requested_error_budget": error_budget,
                "selected_distance": distance,
                "max_distance": MAX_AUTO_DISTANCE,
                "logical_error_at_selected_distance": logical_error,
                "target_met": True,
            }

    logical_error = _logical_error_at_distance(uncorrected_error, representative_error_rate, threshold, MAX_AUTO_DISTANCE)
    return MAX_AUTO_DISTANCE, logical_error, {
        "mode": "auto",
        "requested_error_budget": error_budget,
        "selected_distance": MAX_AUTO_DISTANCE,
        "max_distance": MAX_AUTO_DISTANCE,
        "logical_error_at_selected_distance": logical_error,
        "target_met": logical_error <= error_budget,
    }


def _logical_error_at_distance(
    uncorrected_error: float,
    representative_error_rate: float,
    threshold: float,
    distance: int,
) -> float:
    if uncorrected_error <= 0:
        return 1e-12
    if threshold <= 0:
        return max(uncorrected_error, 1e-12)
    suppression_ratio = min(max(representative_error_rate / threshold, 1e-12), 1.0)
    suppression_power = max((distance + 1) // 2, 1)
    return max(uncorrected_error * (suppression_ratio ** suppression_power), 1e-12)


def _normalize_distance(value: Any) -> int:
    distance = int(value)
    if distance <= 0:
        raise ResourceEstimatorError("QEC distance must be greater than 0.")
    if distance % 2 == 0:
        distance += 1
    return distance


def _native_rotation_parameter(operation: Any) -> float:
    if not operation.parameters:
        raise ResourceEstimatorError(f"Native QRE rotation {operation.operation} at {operation.op_id} requires one angle parameter.")
    value = operation.parameters[0]
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not re.fullmatch(r"[0-9eE+\-*/(). pi]+", text):
        raise ResourceEstimatorError(f"Native QRE rotation {operation.operation} at {operation.op_id} has unsupported angle parameter: {text}.")
    try:
        return float(eval(text, {"__builtins__": {}}, {"pi": math.pi}))
    except Exception as exc:
        raise ResourceEstimatorError(f"Native QRE rotation {operation.operation} at {operation.op_id} has invalid angle parameter: {text}.") from exc


def _qre_instruction_label(base_operation: str) -> str:
    if base_operation in NATIVE_SINGLE_QUBIT_INSTRUCTIONS:
        return NATIVE_SINGLE_QUBIT_INSTRUCTIONS[base_operation]
    if base_operation in NATIVE_ROTATION_INSTRUCTIONS:
        return base_operation
    if base_operation == "CX":
        return "CX"
    if base_operation == "SWAP":
        return "CX_X3"
    if base_operation == "MEASURE":
        return "MEAS_Z"
    if base_operation == "RESET":
        return "MEAS_RESET_Z"
    return base_operation


def _qre_expansion_label(base_operation: str) -> list[str]:
    if base_operation == "SWAP":
        return ["CX", "CX", "CX"]
    return [_qre_instruction_label(base_operation)]


def _build_qec_model(model_name: str, source: str, raw_parameters: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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

    model = {"name": normalized_name, "parameters": parameters}
    return model, {
        "source": normalized_source,
        "name": normalized_name,
        "class": QDK_QEC_MODELS[normalized_name],
        "parameters": parameters,
        "attributes": _qec_model_attributes(normalized_name, parameters),
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


def _qec_model_attributes(model_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    for key in QEC_MODEL_PARAMETER_TYPES[model_name]:
        if key in parameters:
            attributes[key] = parameters[key]
    if "distance" not in attributes and model_name in {"surface_code", "surface_code_low_move", "three_aux"}:
        attributes["distance"] = DEFAULT_SURFACE_CODE_DISTANCE
    return attributes


def native_qre_version_stamp() -> dict[str, str]:
    try:
        implementation_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except Exception:
        implementation_hash = "unknown"
    return {
        "version": NATIVE_QRE_VERSION,
        "implementation_hash": implementation_hash,
    }


def _qdk_version() -> str:
    try:
        return importlib_metadata.version("qdk")
    except importlib_metadata.PackageNotFoundError:
        return "unknown"
