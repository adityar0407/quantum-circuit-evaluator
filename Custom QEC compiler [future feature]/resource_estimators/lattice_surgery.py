from __future__ import annotations

from typing import Any

from backend.IR.analysis import analyze_logical_ir
from backend.IR.models.qec_ir import QecIR
from backend.IR.qec_lowering import LatticeSurgeryLowerer
from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.analytical_surface_code import LOGICAL_ERROR_PREFactor
from backend.services.resource_estimators.analytical_surface_code import SURFACE_CODE_THRESHOLD
from backend.services.resource_estimators.analytical_surface_code import _count_patches
from backend.services.resource_estimators.analytical_surface_code import _factory_requirement
from backend.services.resource_estimators.analytical_surface_code import _logical_error_per_cycle
from backend.services.resource_estimators.analytical_surface_code import _physical_qubits_per_patch
from backend.services.resource_estimators.analytical_surface_code import _select_code_distance
from backend.services.resource_estimators.base import ResourceEstimatorError
from backend.services.resource_estimators.qre_v3_lattice_surgery import qre_v3_lattice_surgery_status


class LatticeSurgeryEstimator:
    key = "lattice_surgery"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        if compilation.logical_ir is None:
            raise ResourceEstimatorError("Lattice-surgery estimator requires a logical IR.")
        if compilation.estimation_context is None:
            raise ResourceEstimatorError("Lattice-surgery estimator requires an estimation context.")

        logical_ir = compilation.logical_ir
        context = compilation.estimation_context
        physical = context.physical_hardware
        qec = context.qec
        network = context.network
        ir_analysis = logical_ir.metadata.get("analysis") or analyze_logical_ir(logical_ir)
        qec_ir = LatticeSurgeryLowerer().lower(logical_ir, qec)

        qec_operation_counts = qec_ir.operation_counts
        total_patch_cycles = _estimate_lattice_surgery_cycles(qec_operation_counts)
        t_count = qec_operation_counts.get("MAGIC_STATE_INJECTION", 0)
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
        remote_operation_count = qec_operation_counts.get("UNLOWERED_REMOTE_OPERATION", 0)

        return {
            "selected_code_distance": code_distance,
            "physical_qubits_per_patch": physical_qubits_per_patch,
            "total_physical_qubits": total_physical_qubits,
            "total_patch_cycles": total_patch_cycles,
            "estimated_runtime_seconds": total_patch_cycles * physical.cycle_time,
            "logical_error_per_cycle": logical_error_per_cycle,
            "total_logical_failure_probability": total_logical_failure_probability,
            "magic_state_demand": {
                "t_count": t_count,
                "magic_state_type": qec.magic_state_type,
            },
            "factory_requirement": _factory_requirement(t_count, total_patch_cycles),
            "patch_counts": patch_counts,
            "qec_operation_counts": qec_operation_counts,
            "qec_ir_summary": _summarize_qec_ir(qec_ir),
            "qec_lowering_warnings": list(qec_ir.warnings),
            "ir_analysis": ir_analysis,
            "remote_operations": {
                "count": remote_operation_count,
                "has_unmodeled_cost": remote_operation_count > 0,
                "note": (
                    "Remote operations remain explicit in lattice-surgery QecIR, but Bell-pair generation, "
                    "teleportation, distributed measurements, feedforward, retries, latency, and network errors are "
                    "not priced yet."
                ),
            },
            "qre_v3_lattice_surgery": qre_v3_lattice_surgery_status(),
            "lattice_surgery_assumptions": {
                "qec_profile": qec.to_dict(),
                "physical_hardware_profile": physical.to_dict(),
                "network_profile": network.to_dict() if network is not None else None,
                "logical_ir_version": logical_ir.version,
                "logical_ir_compiler": logical_ir.compiler,
                "logical_ir_remote_operation_count": logical_ir.remote_operation_count,
                "qec_ir_schema_version": qec_ir.schema_version,
                "qec_ir_code_family": qec_ir.code_family,
                "estimation_model": "lattice_surgery_v1_qec_ir",
                "threshold_assumption": SURFACE_CODE_THRESHOLD,
                "logical_error_prefactor": LOGICAL_ERROR_PREFactor,
                "runtime_excludes_remote_protocol_overhead": remote_operation_count > 0,
                "local_cx_lowering": "LS_PREPARE_ANCILLA -> JOINT_ZZ -> JOINT_XX -> PATCH_MEASURE -> CLASSICAL_FEEDFORWARD -> PATCH_RESET",
            },
        }


def _estimate_lattice_surgery_cycles(qec_operation_counts: dict[str, int]) -> int:
    cycles = (
        qec_operation_counts.get("PATCH_H", 0)
        + qec_operation_counts.get("PATCH_S", 0)
        + qec_operation_counts.get("PATCH_MEASURE", 0)
        + qec_operation_counts.get("PATCH_RESET", 0)
        + qec_operation_counts.get("PATCH_IDLE", 0)
        + qec_operation_counts.get("LS_PREPARE_ANCILLA", 0)
        + qec_operation_counts.get("JOINT_ZZ", 0)
        + qec_operation_counts.get("JOINT_XX", 0)
        + qec_operation_counts.get("CLASSICAL_FEEDFORWARD", 0)
        + (4 * qec_operation_counts.get("MAGIC_STATE_INJECTION", 0))
        + qec_operation_counts.get("UNLOWERED_REMOTE_OPERATION", 0)
    )
    return max(int(cycles), 1)


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
