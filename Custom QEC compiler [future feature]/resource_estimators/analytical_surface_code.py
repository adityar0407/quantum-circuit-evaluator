from __future__ import annotations

import math
from typing import Any

from backend.IR.analysis import analyze_logical_ir
from backend.IR.models.qec_ir import QecIR
from backend.IR.qec_lowering import AnalyticalSurfaceCodeLowerer
from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.base import ResourceEstimatorError


SURFACE_CODE_THRESHOLD = 1e-2
LOGICAL_ERROR_PREFactor = 0.1
MIN_CODE_DISTANCE = 3


class AnalyticalSurfaceCodeEstimator:
    key = "analytical_surface_code"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        if compilation.logical_ir is None:
            raise ResourceEstimatorError("Analytical surface-code estimator requires a logical IR.")
        if compilation.estimation_context is None:
            raise ResourceEstimatorError("Analytical surface-code estimator requires an estimation context.")

        logical_ir = compilation.logical_ir
        context = compilation.estimation_context
        physical = context.physical_hardware
        qec = context.qec
        network = context.network
        ir_analysis = logical_ir.metadata.get("analysis") or analyze_logical_ir(logical_ir)
        qec_ir = AnalyticalSurfaceCodeLowerer().lower(logical_ir, qec)

        qec_operation_counts = qec_ir.operation_counts
        t_count = qec_operation_counts.get("MAGIC_STATE_INJECTION", 0)
        total_patch_cycles = _estimate_patch_cycles(qec_operation_counts)
        code_distance = _select_code_distance(
            physical_error_rate=max(physical.two_qubit_gate_error_rate, physical.measurement_error_rate),
            target_failure_probability=qec.logical_error_target,
            total_patch_cycles=max(total_patch_cycles, 1),
            logical_qubits=max(logical_ir.logical_qubit_count, 1),
            fixed_code_distance=qec.fixed_code_distance,
            policy=qec.code_distance_policy,
        )
        physical_qubits_per_patch = _physical_qubits_per_patch(code_distance)
        patch_counts = _count_patches(qec_ir)
        data_patches = patch_counts["data_patches"]
        ancilla_patches = patch_counts["ancilla_patches"]
        routing_patches = patch_counts["routing_patches"]
        factory_patches = patch_counts["factory_patches"]
        total_patches = patch_counts["total_patches"]
        total_physical_qubits = total_patches * physical_qubits_per_patch

        logical_error_per_cycle = _logical_error_per_cycle(
            physical_error_rate=max(physical.two_qubit_gate_error_rate, physical.measurement_error_rate),
            code_distance=code_distance,
        )
        total_logical_failure_probability = min(
            1.0,
            logical_error_per_cycle * total_patch_cycles * max(total_patches, 1),
        )
        estimated_runtime_seconds = total_patch_cycles * physical.cycle_time
        factory_requirement = _factory_requirement(t_count, total_patch_cycles)
        remote_operation_count = qec_operation_counts.get("UNLOWERED_REMOTE_OPERATION", 0)
        remote_runtime_excluded = remote_operation_count > 0
        unsupported_operation_count = qec_operation_counts.get("UNSUPPORTED_QEC_OPERATION", 0)

        return {
            "selected_code_distance": code_distance,
            "physical_qubits_per_patch": physical_qubits_per_patch,
            "total_physical_qubits": total_physical_qubits,
            "data_region_physical_qubits": data_patches * physical_qubits_per_patch,
            "ancilla_physical_qubits": ancilla_patches * physical_qubits_per_patch,
            "routing_physical_qubits": routing_patches * physical_qubits_per_patch,
            "factory_physical_qubits": factory_patches * physical_qubits_per_patch,
            "logical_error_per_cycle": logical_error_per_cycle,
            "total_logical_failure_probability": total_logical_failure_probability,
            "total_patch_cycles": total_patch_cycles,
            "estimated_runtime_seconds": estimated_runtime_seconds,
            "magic_state_demand": {
                "t_count": t_count,
                "magic_state_type": qec.magic_state_type,
            },
            "factory_requirement": factory_requirement,
            "patch_counts": {
                "data_patches": data_patches,
                "ancilla_patches": ancilla_patches,
                "routing_patches": routing_patches,
                "factory_patches": factory_patches,
                "total_patches": total_patches,
            },
            "qec_operation_counts": qec_operation_counts,
            "qec_ir_summary": _summarize_qec_ir(qec_ir),
            "qec_lowering_warnings": list(qec_ir.warnings),
            "unsupported_qec_operations": unsupported_operation_count,
            "ir_analysis": ir_analysis,
            "remote_operations": {
                "count": remote_operation_count,
                "has_unmodeled_cost": remote_operation_count > 0,
                "note": (
                    "Remote logical operations are counted explicitly, but teleportation/Bell-pair/feedforward overhead "
                    "is not yet included in the analytical runtime or failure model."
                ),
            },
            "surface_code_assumptions": {
                "qec_profile": qec.to_dict(),
                "physical_hardware_profile": physical.to_dict(),
                "network_profile": network.to_dict() if network is not None else None,
                "logical_ir_version": logical_ir.version,
                "logical_ir_compiler": logical_ir.compiler,
                "logical_ir_remote_operation_count": logical_ir.remote_operation_count,
                "logical_ir_critical_path_length": ir_analysis["dag"]["critical_path_length"],
                "logical_ir_parallel_layer_count": ir_analysis["dag"]["parallel_layer_count"],
                "qec_ir_schema_version": qec_ir.schema_version,
                "qec_ir_code_family": qec_ir.code_family,
                "estimation_model": "analytical_surface_code_v2_qec_ir",
                "threshold_assumption": SURFACE_CODE_THRESHOLD,
                "logical_error_prefactor": LOGICAL_ERROR_PREFactor,
                "runtime_excludes_remote_protocol_overhead": remote_runtime_excluded,
            },
        }


def _estimate_patch_cycles(qec_operation_counts: dict[str, int]) -> int:
    patch_ops = (
        qec_operation_counts.get("PATCH_H", 0)
        + qec_operation_counts.get("PATCH_S", 0)
        + qec_operation_counts.get("PATCH_MEASURE", 0)
        + qec_operation_counts.get("PATCH_RESET", 0)
        + qec_operation_counts.get("PATCH_IDLE", 0)
    )
    logical_cx = qec_operation_counts.get("LOGICAL_CX", 0)
    joint_measurements = qec_operation_counts.get("JOINT_XX", 0) + qec_operation_counts.get("JOINT_ZZ", 0)
    magic_state_injections = qec_operation_counts.get("MAGIC_STATE_INJECTION", 0)
    remote_unlowered = qec_operation_counts.get("UNLOWERED_REMOTE_OPERATION", 0)

    # Conservative lower-bound cycle model. Remote-protocol overhead is intentionally
    # excluded and reported separately as unmodeled.
    cycles = (
        patch_ops
        + (3 * logical_cx)
        + (2 * joint_measurements)
        + (4 * magic_state_injections)
        + remote_unlowered
    )
    return max(int(cycles), 1)


def _select_code_distance(
    *,
    physical_error_rate: float,
    target_failure_probability: float,
    total_patch_cycles: int,
    logical_qubits: int,
    fixed_code_distance: int | None,
    policy: str,
) -> int:
    if fixed_code_distance is not None:
        return _make_odd_at_least_three(fixed_code_distance)

    if policy == "fixed":
        return MIN_CODE_DISTANCE

    for distance in range(MIN_CODE_DISTANCE, 64, 2):
        per_cycle = _logical_error_per_cycle(physical_error_rate=physical_error_rate, code_distance=distance)
        total_failure = per_cycle * total_patch_cycles * logical_qubits
        if total_failure <= target_failure_probability:
            return distance

    return 63


def _logical_error_per_cycle(*, physical_error_rate: float, code_distance: int) -> float:
    ratio = max(min(physical_error_rate / SURFACE_CODE_THRESHOLD, 1.0), 1e-12)
    exponent = (code_distance + 1) / 2
    return LOGICAL_ERROR_PREFactor * (ratio**exponent)


def _physical_qubits_per_patch(code_distance: int) -> int:
    return 2 * (code_distance**2)


def _factory_requirement(t_count: int, total_patch_cycles: int) -> dict[str, Any]:
    factories = math.ceil(t_count / max(total_patch_cycles, 1)) if t_count else 0
    return {
        "required_factories": factories,
        "factory_throughput_per_cycle": 1 if factories else 0,
        "t_states_per_factory_window": t_count,
    }


def _make_odd_at_least_three(value: int) -> int:
    candidate = max(int(value), MIN_CODE_DISTANCE)
    if candidate % 2 == 0:
        candidate += 1
    return candidate


def _count_patches(qec_ir: QecIR) -> dict[str, int]:
    data_patches = sum(1 for patch in qec_ir.patches if patch.patch_kind == "data")
    ancilla_patches = sum(1 for patch in qec_ir.patches if patch.patch_kind == "ancilla")
    routing_patches = sum(1 for patch in qec_ir.patches if patch.patch_kind == "routing")
    factory_patches = sum(1 for patch in qec_ir.patches if patch.patch_kind == "factory")
    return {
        "data_patches": data_patches,
        "ancilla_patches": ancilla_patches,
        "routing_patches": routing_patches,
        "factory_patches": factory_patches,
        "total_patches": data_patches + ancilla_patches + routing_patches + factory_patches,
    }


def _summarize_qec_ir(qec_ir: QecIR) -> dict[str, Any]:
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
