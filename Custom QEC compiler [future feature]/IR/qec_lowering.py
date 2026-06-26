from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections import defaultdict
from typing import Protocol

from backend.IR.models.logical_ir import LogicalIR
from backend.IR.models.logical_ir import LogicalInstruction
from backend.IR.models.qec_ir import QecIR
from backend.IR.models.qec_ir import QecOperation
from backend.IR.models.qec_ir import QecPatch
from backend.models.estimation_profiles import QecProfile


QEC_IR_VERSION = "0.1"


class QecLoweringError(ValueError):
    """Raised when a logical IR cannot be lowered into a valid QEC IR."""


class QecLowerer(Protocol):
    def lower(self, logical_ir: LogicalIR, qec_profile: QecProfile | None = None) -> QecIR:
        ...


class AnalyticalSurfaceCodeLowerer:
    code_family = "surface_code"

    def lower(self, logical_ir: LogicalIR, qec_profile: QecProfile | None = None) -> QecIR:
        patches = _build_patches(logical_ir)
        patch_lookup = {patch.patch_id: patch for patch in patches}
        patch_for_qubit = {patch.logical_qubit: patch.patch_id for patch in patches if patch.logical_qubit is not None}
        logical_to_qec: dict[str, str] = {}
        operations: list[QecOperation] = []
        warnings: list[str] = []

        for logical_operation in logical_ir.operations:
            qec_operation = _lower_logical_operation(
                logical_operation=logical_operation,
                qec_index=len(operations),
                logical_to_qec=logical_to_qec,
                patch_for_qubit=patch_for_qubit,
            )
            operations.append(qec_operation)
            logical_to_qec[logical_operation.op_id] = qec_operation.op_id
            if qec_operation.lowering_status == "unsupported":
                warnings.append(
                    f"{logical_operation.op_id}:{logical_operation.base_operation} is not supported by "
                    "analytical surface-code lowering and is excluded from encoded cost."
                )
            if qec_operation.lowering_status == "unlowered":
                warnings.append(
                    f"{logical_operation.op_id}:{logical_operation.operation} remains explicit and unlowered; "
                    "remote protocol cost is not included."
                )

        operation_counts = dict(Counter(operation.op_kind for operation in operations))
        operation_layers = _build_operation_layers(operations)
        patch_occupancy = _build_patch_occupancy(operations, patch_lookup)
        qec_ir = QecIR(
            schema_version=QEC_IR_VERSION,
            code_family=self.code_family,
            patches=tuple(patches),
            operations=tuple(operations),
            source_logical_ir_hash=_hash_logical_ir(logical_ir),
            operation_counts=operation_counts,
            operation_layers=operation_layers,
            patch_occupancy=patch_occupancy,
            provenance={
                "lowerer": "AnalyticalSurfaceCodeLowerer",
                "source_logical_ir_version": logical_ir.version,
                "source_compiler": logical_ir.compiler,
                "qec_profile": qec_profile.to_dict() if qec_profile is not None else None,
                "model_scope": (
                    "Patch-level analytical surface-code model. It does not expand stabilizer rounds, detector "
                    "graphs, decoder graphs, or remote teleportation protocols."
                ),
            },
            warnings=tuple(warnings),
        )
        validate_qec_ir(qec_ir)
        return qec_ir


class LatticeSurgeryLowerer:
    code_family = "surface_code_lattice_surgery"

    def lower(self, logical_ir: LogicalIR, qec_profile: QecProfile | None = None) -> QecIR:
        patches = _build_patches(logical_ir)
        patch_lookup = {patch.patch_id: patch for patch in patches}
        patch_for_qubit = {patch.logical_qubit: patch.patch_id for patch in patches if patch.logical_qubit is not None}
        logical_to_qec: dict[str, str] = {}
        operations: list[QecOperation] = []
        warnings: list[str] = []

        for logical_operation in logical_ir.operations:
            lowered_operations = _lower_logical_operation_to_lattice_surgery(
                logical_operation=logical_operation,
                qec_index_start=len(operations),
                logical_to_qec=logical_to_qec,
                patch_for_qubit=patch_for_qubit,
            )
            operations.extend(lowered_operations)
            logical_to_qec[logical_operation.op_id] = lowered_operations[-1].op_id
            if lowered_operations[-1].lowering_status == "unsupported":
                warnings.append(
                    f"{logical_operation.op_id}:{logical_operation.base_operation} is not supported by "
                    "lattice-surgery lowering and is excluded from encoded cost."
                )
            if lowered_operations[-1].lowering_status == "unlowered":
                warnings.append(
                    f"{logical_operation.op_id}:{logical_operation.operation} remains explicit and unlowered; "
                    "remote protocol cost is not included."
                )

        operation_counts = dict(Counter(operation.op_kind for operation in operations))
        operation_layers = _build_operation_layers(operations)
        patch_occupancy = _build_patch_occupancy(operations, patch_lookup)
        qec_ir = QecIR(
            schema_version=QEC_IR_VERSION,
            code_family=self.code_family,
            patches=tuple(patches),
            operations=tuple(operations),
            source_logical_ir_hash=_hash_logical_ir(logical_ir),
            operation_counts=operation_counts,
            operation_layers=operation_layers,
            patch_occupancy=patch_occupancy,
            provenance={
                "lowerer": "LatticeSurgeryLowerer",
                "source_logical_ir_version": logical_ir.version,
                "source_compiler": logical_ir.compiler,
                "qec_profile": qec_profile.to_dict() if qec_profile is not None else None,
                "model_scope": (
                    "Patch-level lattice-surgery schedule. Local CX is expanded into ancilla preparation, "
                    "joint parity measurements, classical feedforward bookkeeping, and ancilla reset. It does not "
                    "expand stabilizer rounds, detector graphs, decoder graphs, or remote teleportation protocols."
                ),
            },
            warnings=tuple(warnings),
        )
        validate_qec_ir(qec_ir)
        return qec_ir


def validate_qec_ir(qec_ir: QecIR) -> None:
    patch_ids = {patch.patch_id for patch in qec_ir.patches}
    op_ids = {operation.op_id for operation in qec_ir.operations}

    if len(patch_ids) != len(qec_ir.patches):
        raise QecLoweringError("QEC IR contains duplicate patch ids.")
    if len(op_ids) != len(qec_ir.operations):
        raise QecLoweringError("QEC IR contains duplicate operation ids.")

    seen_ops: set[str] = set()
    for operation in qec_ir.operations:
        if operation.lowering_status == "unlowered" and operation.op_kind != "UNLOWERED_REMOTE_OPERATION":
            raise QecLoweringError(f"Operation {operation.op_id} is unlowered but is not a remote placeholder.")
        if operation.lowering_status == "unsupported" and operation.op_kind != "UNSUPPORTED_QEC_OPERATION":
            raise QecLoweringError(f"Operation {operation.op_id} is unsupported but has kind {operation.op_kind}.")
        if not operation.source_logical_op_ids:
            raise QecLoweringError(f"Operation {operation.op_id} must retain source logical op provenance.")
        for patch_id in (*operation.input_patches, *operation.output_patches):
            if patch_id not in patch_ids:
                raise QecLoweringError(f"Operation {operation.op_id} references unknown patch {patch_id}.")
        for dependency in operation.dependencies:
            if dependency not in op_ids:
                raise QecLoweringError(f"Operation {operation.op_id} references unknown dependency {dependency}.")
            if dependency not in seen_ops:
                raise QecLoweringError(f"Operation {operation.op_id} dependency {dependency} is not topologically prior.")
        seen_ops.add(operation.op_id)

    counted = Counter(operation.op_kind for operation in qec_ir.operations)
    if dict(counted) != qec_ir.operation_counts:
        raise QecLoweringError("QEC IR operation_counts does not match operations.")


def _build_patches(logical_ir: LogicalIR) -> list[QecPatch]:
    patches = [
        QecPatch(
            patch_id=f"data_q{placement.logical_qubit}",
            patch_kind="data",
            logical_qubit=placement.logical_qubit,
            node_id=placement.node_id,
            metadata={"slot_in_node": placement.slot_in_node},
        )
        for placement in logical_ir.placements
    ]
    if any(operation.op_kind == "two_qubit_local" for operation in logical_ir.operations):
        patches.append(
            QecPatch(
                patch_id="ancilla_lattice_surgery_0",
                patch_kind="ancilla",
                logical_qubit=None,
                node_id=None,
                metadata={"purpose": "local_lattice_surgery_placeholder"},
            )
        )
    if any(_is_magic_state_operation(operation.base_operation) for operation in logical_ir.operations):
        patches.append(
            QecPatch(
                patch_id="factory_t_state_0",
                patch_kind="factory",
                logical_qubit=None,
                node_id=None,
                metadata={"purpose": "magic_state_injection_buffer"},
            )
        )
    if logical_ir.remote_operation_count:
        patches.append(
            QecPatch(
                patch_id="routing_remote_0",
                patch_kind="routing",
                logical_qubit=None,
                node_id=None,
                metadata={"purpose": "remote_operation_bookkeeping"},
            )
        )
    return patches


def _lower_logical_operation(
    *,
    logical_operation: LogicalInstruction,
    qec_index: int,
    logical_to_qec: dict[str, str],
    patch_for_qubit: dict[int, str],
) -> QecOperation:
    patch_ids = tuple(patch_for_qubit[qubit_index] for qubit_index in logical_operation.qargs)
    dependencies = tuple(
        qec_dependency
        for dependency in logical_operation.dependencies
        if (qec_dependency := logical_to_qec.get(dependency)) is not None
    )
    op_kind, lowering_status = _classify_qec_operation(logical_operation)
    metadata = {
        "source_operation": logical_operation.operation,
        "source_base_operation": logical_operation.base_operation,
        "source_op_kind": logical_operation.op_kind,
        "source_qargs": logical_operation.qargs,
        "source_cargs": logical_operation.cargs,
        "source_node_ids": logical_operation.node_ids,
    }
    if logical_operation.unmodeled_cost is not None:
        metadata["unmodeled_cost"] = logical_operation.unmodeled_cost.to_dict()
    if op_kind == "UNLOWERED_REMOTE_OPERATION":
        metadata["remote_operation_label"] = f"UNLOWERED_REMOTE_{logical_operation.base_operation.upper()}"
        metadata["remote_source_node"] = logical_operation.metadata.get("source_node")
        metadata["remote_target_node"] = logical_operation.metadata.get("target_node")
        metadata["remote_limitation"] = (
            "Remote protocol costs for Bell-pair generation, verification, teleportation, distributed logical "
            "measurements, communication qubits, feedforward, latency, network errors, and retries are not lowered yet."
        )
    if op_kind == "LOGICAL_CX":
        metadata["lowering_note"] = (
            "Analytical placeholder for a surface-code lattice-surgery CNOT. Exact joint-measurement schedule is "
            "not expanded in QEC IR v0.1."
        )
    if op_kind == "MAGIC_STATE_INJECTION":
        metadata["magic_state_type"] = "t_state"

    return QecOperation(
        op_id=f"qec_op_{qec_index:05d}",
        op_kind=op_kind,
        input_patches=patch_ids,
        output_patches=patch_ids,
        dependencies=dependencies,
        source_logical_op_ids=(logical_operation.op_id,),
        lowering_status=lowering_status,
        metadata=metadata,
    )


def _lower_logical_operation_to_lattice_surgery(
    *,
    logical_operation: LogicalInstruction,
    qec_index_start: int,
    logical_to_qec: dict[str, str],
    patch_for_qubit: dict[int, str],
) -> list[QecOperation]:
    if logical_operation.base_operation.upper() == "CX" and logical_operation.op_kind == "two_qubit_local":
        return _lower_local_cx_to_lattice_surgery(
            logical_operation=logical_operation,
            qec_index_start=qec_index_start,
            logical_to_qec=logical_to_qec,
            patch_for_qubit=patch_for_qubit,
        )

    qec_operation = _lower_logical_operation(
        logical_operation=logical_operation,
        qec_index=qec_index_start,
        logical_to_qec=logical_to_qec,
        patch_for_qubit=patch_for_qubit,
    )
    if qec_operation.lowering_status == "analytically_modeled" and qec_operation.op_kind != "LOGICAL_CX":
        qec_operation = QecOperation(
            op_id=qec_operation.op_id,
            op_kind=qec_operation.op_kind,
            input_patches=qec_operation.input_patches,
            output_patches=qec_operation.output_patches,
            dependencies=qec_operation.dependencies,
            source_logical_op_ids=qec_operation.source_logical_op_ids,
            lowering_status="fully_lowered",
            metadata=qec_operation.metadata,
        )
    return [qec_operation]


def _lower_local_cx_to_lattice_surgery(
    *,
    logical_operation: LogicalInstruction,
    qec_index_start: int,
    logical_to_qec: dict[str, str],
    patch_for_qubit: dict[int, str],
) -> list[QecOperation]:
    control_patch = patch_for_qubit[logical_operation.qargs[0]]
    target_patch = patch_for_qubit[logical_operation.qargs[1]]
    ancilla_patch = "ancilla_lattice_surgery_0"
    external_dependencies = tuple(
        qec_dependency
        for dependency in logical_operation.dependencies
        if (qec_dependency := logical_to_qec.get(dependency)) is not None
    )
    source = (logical_operation.op_id,)
    base_metadata = {
        "source_operation": logical_operation.operation,
        "source_base_operation": logical_operation.base_operation,
        "source_op_kind": logical_operation.op_kind,
        "source_qargs": logical_operation.qargs,
        "source_node_ids": logical_operation.node_ids,
        "lowering_note": "Local logical CX lowered into a conservative lattice-surgery parity-measurement schedule.",
    }
    schedule = [
        ("LS_PREPARE_ANCILLA", (ancilla_patch,), (ancilla_patch,), external_dependencies),
        ("JOINT_ZZ", (control_patch, ancilla_patch), (control_patch, ancilla_patch), None),
        ("JOINT_XX", (ancilla_patch, target_patch), (ancilla_patch, target_patch), None),
        ("PATCH_MEASURE", (ancilla_patch,), (ancilla_patch,), None),
        ("CLASSICAL_FEEDFORWARD", (control_patch, target_patch), (control_patch, target_patch), None),
        ("PATCH_RESET", (ancilla_patch,), (ancilla_patch,), None),
    ]
    operations: list[QecOperation] = []
    previous_op_id: str | None = None
    for offset, (op_kind, input_patches, output_patches, dependencies) in enumerate(schedule):
        op_id = f"qec_op_{qec_index_start + offset:05d}"
        if dependencies is None:
            op_dependencies = (previous_op_id,) if previous_op_id is not None else ()
        else:
            op_dependencies = dependencies
        operations.append(
            QecOperation(
                op_id=op_id,
                op_kind=op_kind,
                input_patches=input_patches,
                output_patches=output_patches,
                dependencies=tuple(dep for dep in op_dependencies if dep is not None),
                source_logical_op_ids=source,
                lowering_status="fully_lowered",
                metadata={
                    **base_metadata,
                    "lattice_surgery_step": offset + 1,
                    "lattice_surgery_steps_total": len(schedule),
                },
            )
        )
        previous_op_id = op_id
    return operations


def _classify_qec_operation(logical_operation: LogicalInstruction) -> tuple[str, str]:
    base_operation = logical_operation.base_operation.upper()
    if logical_operation.op_kind == "two_qubit_remote":
        return "UNLOWERED_REMOTE_OPERATION", "unlowered"
    if base_operation == "H":
        return "PATCH_H", "analytically_modeled"
    if base_operation in {"S", "SDG"}:
        return "PATCH_S", "analytically_modeled"
    if _is_magic_state_operation(base_operation):
        return "MAGIC_STATE_INJECTION", "analytically_modeled"
    if base_operation == "CX" and logical_operation.op_kind == "two_qubit_local":
        return "LOGICAL_CX", "analytically_modeled"
    if base_operation == "CZ" and logical_operation.op_kind == "two_qubit_local":
        return "JOINT_ZZ", "analytically_modeled"
    if base_operation == "MEASURE":
        return "PATCH_MEASURE", "analytically_modeled"
    if base_operation == "RESET":
        return "PATCH_RESET", "analytically_modeled"
    if base_operation == "BARRIER":
        return "PATCH_IDLE", "analytically_modeled"
    return "UNSUPPORTED_QEC_OPERATION", "unsupported"


def _is_magic_state_operation(base_operation: str) -> bool:
    return base_operation.upper() in {"T", "TDG"}


def _build_operation_layers(operations: list[QecOperation]) -> tuple[tuple[str, ...], ...]:
    depth_by_op: dict[str, int] = {}
    layers: dict[int, list[str]] = defaultdict(list)
    for operation in operations:
        depth = 0
        if operation.dependencies:
            depth = max(depth_by_op[dependency] for dependency in operation.dependencies) + 1
        depth_by_op[operation.op_id] = depth
        layers[depth].append(operation.op_id)
    return tuple(tuple(layers[index]) for index in sorted(layers))


def _build_patch_occupancy(
    operations: list[QecOperation],
    patch_lookup: dict[str, QecPatch],
) -> dict[str, tuple[str, ...]]:
    occupancy: dict[str, list[str]] = {patch_id: [] for patch_id in patch_lookup}
    for operation in operations:
        for patch_id in sorted(set(operation.input_patches + operation.output_patches)):
            occupancy[patch_id].append(operation.op_id)
    return {patch_id: tuple(op_ids) for patch_id, op_ids in occupancy.items()}


def _hash_logical_ir(logical_ir: LogicalIR) -> str:
    payload = json.dumps(logical_ir.to_dict(), sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
