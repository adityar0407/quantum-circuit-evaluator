from __future__ import annotations

from collections import Counter
from typing import Any

from qiskit import QuantumCircuit

from backend.IR.analysis import analyze_logical_ir
from backend.IR.models.logical_ir import LogicalIR
from backend.IR.models.logical_ir import LogicalInstruction
from backend.IR.models.logical_ir import LogicalPlacement
from backend.IR.models.logical_ir import UnmodeledCost


LOGICAL_IR_VERSION = "0.1"


def build_logical_ir(
    circuit: QuantumCircuit,
    target: Any | None,
    compiler: str,
    artifacts: dict[str, Any] | None = None,
    original_circuit: QuantumCircuit | None = None,
) -> LogicalIR:
    placements = [_build_placement(qubit_index, target) for qubit_index in range(circuit.num_qubits)]
    operation_counts: Counter[str] = Counter()
    operations: list[LogicalInstruction] = []
    remote_operation_count = 0
    last_touch: dict[tuple[str, int], str] = {}

    for index, instruction in enumerate(circuit.data):
        base_operation = instruction.operation.name.upper()
        qargs = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        cargs = [circuit.find_bit(clbit).index for clbit in instruction.clbits]
        node_ids = [_node_for_qubit(qubit_index, target) for qubit_index in qargs]
        op_kind = _classify_operation(base_operation, qargs, cargs, target)
        is_remote = op_kind == "two_qubit_remote"
        operation = f"REMOTE_{base_operation}" if is_remote else base_operation

        dependencies: list[str] = []
        for qubit_index in qargs:
            dep = last_touch.get(("q", qubit_index))
            if dep and dep not in dependencies:
                dependencies.append(dep)
        for clbit_index in cargs:
            dep = last_touch.get(("c", clbit_index))
            if dep and dep not in dependencies:
                dependencies.append(dep)

        op_id = f"op_{index:05d}"
        metadata = {
            "instruction_index": index,
            "remote": is_remote,
        }
        if len(node_ids) == 2 and is_remote:
            metadata["source_node"] = node_ids[0]
            metadata["target_node"] = node_ids[1]

        parameters = [_serialize_parameter(param) for param in instruction.operation.params]
        unmodeled_cost = None
        if is_remote:
            remote_operation_count += 1
            unmodeled_cost = UnmodeledCost(
                category="remote_execution_overhead",
                status="unmodeled",
                reason=(
                    "Remote logical operations are preserved explicitly, but Bell-pair generation, teleportation, "
                    "local Bell measurement, and classical feedforward costs are not yet lowered into the IR cost model."
                ),
            )

        logical_instruction = LogicalInstruction(
            op_id=op_id,
            op_kind=op_kind,
            operation=operation,
            base_operation=base_operation,
            qargs=qargs,
            cargs=cargs,
            parameters=parameters,
            node_ids=node_ids,
            dependencies=dependencies,
            metadata=metadata,
            unmodeled_cost=unmodeled_cost,
        )
        operations.append(logical_instruction)
        operation_counts[operation] += 1

        for qubit_index in qargs:
            last_touch[("q", qubit_index)] = op_id
        for clbit_index in cargs:
            last_touch[("c", clbit_index)] = op_id

    compiler_metadata = _build_compiler_metadata(
        compiler=compiler,
        artifacts=artifacts or {},
        target=target,
        circuit=circuit,
        original_circuit=original_circuit,
    )

    logical_ir = LogicalIR(
        version=LOGICAL_IR_VERSION,
        compiler=compiler,
        logical_qubit_count=circuit.num_qubits,
        classical_bit_count=circuit.num_clbits,
        placements=placements,
        operations=operations,
        operation_counts=dict(operation_counts),
        remote_operation_count=remote_operation_count,
        metadata={
            "compiler": compiler,
            "topology_type": getattr(target, "type", None) if target is not None else None,
            "compiler_metadata": compiler_metadata,
        },
        notes=[
            "Cross-node two-qubit operations are preserved as explicit REMOTE_* logical operations.",
            "Logical IR dependencies are inferred conservatively from qubit and classical-bit access order.",
        ],
    )
    validate_logical_ir(logical_ir)
    analysis = analyze_logical_ir(logical_ir)
    return LogicalIR(
        version=logical_ir.version,
        compiler=logical_ir.compiler,
        logical_qubit_count=logical_ir.logical_qubit_count,
        classical_bit_count=logical_ir.classical_bit_count,
        placements=logical_ir.placements,
        operations=logical_ir.operations,
        operation_counts=logical_ir.operation_counts,
        remote_operation_count=logical_ir.remote_operation_count,
        metadata={**logical_ir.metadata, "analysis": analysis},
        notes=logical_ir.notes,
    )


def validate_logical_ir(logical_ir: LogicalIR) -> None:
    placement_lookup = {placement.logical_qubit: placement for placement in logical_ir.placements}
    op_ids = {operation.op_id for operation in logical_ir.operations}

    if len(op_ids) != len(logical_ir.operations):
        raise ValueError("Logical IR contains duplicate op ids.")

    for qubit_index in range(logical_ir.logical_qubit_count):
        if qubit_index not in placement_lookup:
            raise ValueError(f"Logical IR is missing placement data for logical qubit {qubit_index}.")

    for index, operation in enumerate(logical_ir.operations):
        for qubit_index in operation.qargs:
            if qubit_index not in placement_lookup:
                raise ValueError(f"Operation {operation.op_id} references unknown logical qubit {qubit_index}.")
        for dependency in operation.dependencies:
            if dependency not in op_ids:
                raise ValueError(f"Operation {operation.op_id} references unknown dependency {dependency}.")
        if operation.op_kind == "two_qubit_remote":
            if len(operation.node_ids) != 2 or operation.node_ids[0] == operation.node_ids[1]:
                raise ValueError(f"Remote operation {operation.op_id} must span two distinct nodes.")
            if operation.unmodeled_cost is None:
                raise ValueError(f"Remote operation {operation.op_id} must declare unmodeled cost metadata.")
        if operation.op_kind == "two_qubit_local":
            if len(operation.node_ids) == 2 and operation.node_ids[0] != operation.node_ids[1]:
                raise ValueError(f"Local two-qubit operation {operation.op_id} spans multiple nodes.")
        op_position = int(operation.op_id.split("_")[1])
        if op_position != index:
            raise ValueError("Logical IR op ids must remain in topological order.")


def serialize_logical_ir(logical_ir: LogicalIR) -> dict[str, Any]:
    return logical_ir.to_dict()


def _build_placement(qubit_index: int, target: Any | None) -> LogicalPlacement:
    node_id = _node_for_qubit(qubit_index, target)
    slot_in_node = None
    if target is not None and hasattr(target, "n_block"):
        slot_in_node = int(qubit_index % target.n_block)
    return LogicalPlacement(logical_qubit=qubit_index, node_id=node_id, slot_in_node=slot_in_node)


def _classify_operation(base_operation: str, qargs: list[int], cargs: list[int], target: Any | None) -> str:
    lowered = base_operation.lower()
    if lowered == "measure":
        return "measure"
    if lowered == "barrier":
        return "barrier"
    if lowered == "reset":
        return "reset"
    if cargs and lowered != "measure":
        return "classical_control"
    if len(qargs) == 1:
        return "single_qubit"
    if len(qargs) == 2:
        if _is_remote_operation(qargs, target):
            return "two_qubit_remote"
        return "two_qubit_local"
    return "other"


def _is_remote_operation(qargs: list[int], target: Any | None) -> bool:
    if target is None or len(qargs) != 2:
        return False
    if not hasattr(target, "_is_local_edge"):
        return False
    return not bool(target._is_local_edge(qargs[0], qargs[1]))


def _node_for_qubit(qubit_index: int, target: Any | None) -> int | None:
    if target is None or not hasattr(target, "n_block"):
        return None
    return int(qubit_index // target.n_block)


def _serialize_parameter(value: Any) -> float | str:
    if isinstance(value, (int, float)):
        return float(value)
    return str(value)


def _build_compiler_metadata(
    *,
    compiler: str,
    artifacts: dict[str, Any],
    target: Any | None,
    circuit: QuantumCircuit,
    original_circuit: QuantumCircuit | None,
) -> dict[str, Any]:
    if compiler == "qiskit_ftarget":
        return {
            "original_layout": artifacts.get("original_layout"),
            "final_layout": artifacts.get("final_layout"),
            "routing_swaps": artifacts.get("routing_swaps", 0),
            "optimization_level": artifacts.get("optimization_level"),
            "target_snapshot": artifacts.get("target_snapshot")
            or {
                "topology_type": getattr(target, "type", None) if target is not None else None,
                "operation_names": sorted(getattr(target, "operation_names", [])) if target is not None else [],
            },
        }

    if compiler == "pandora":
        return {
            "rewrite_passes": artifacts.get("rewrite_passes", []),
            "removed_operations": artifacts.get("removed_operations", {}),
            "unsupported_operations": artifacts.get("unsupported_operations", []),
            "database_mode": artifacts.get("database_mode", False),
            "topology_aware": artifacts.get("topology_aware", False),
            "topology_lowering": artifacts.get("topology_lowering"),
            "topology_validation": artifacts.get("topology_validation"),
            "target_topology": artifacts.get("target_topology"),
            "support_scan": artifacts.get("support_scan"),
        }

    return {
        "compiled_gate_count": circuit.size(),
        "original_gate_count": original_circuit.size() if original_circuit is not None else None,
    }
