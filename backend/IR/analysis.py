from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.IR.models.logical_ir import LogicalIR


T_FAMILY_OPERATIONS = {"T", "TDG", "T_GATE", "TGATE", "T_DAGGER"}


def analyze_logical_ir(logical_ir: LogicalIR) -> dict[str, Any]:
    op_by_id = {operation.op_id: operation for operation in logical_ir.operations}
    successor_map: dict[str, list[str]] = {operation.op_id: [] for operation in logical_ir.operations}
    for operation in logical_ir.operations:
        for dependency in operation.dependencies:
            successor_map.setdefault(dependency, []).append(operation.op_id)

    depth_by_id: dict[str, int] = {}
    for operation in logical_ir.operations:
        depth_by_id[operation.op_id] = 0 if not operation.dependencies else 1 + max(
            depth_by_id[dependency] for dependency in operation.dependencies
        )

    parallel_layers: dict[int, list[str]] = defaultdict(list)
    for op_id, depth in depth_by_id.items():
        parallel_layers[depth].append(op_id)

    critical_path = _critical_path(logical_ir, successor_map, depth_by_id)
    op_kind_counts: dict[str, int] = defaultdict(int)
    gate_counts: dict[str, int] = defaultdict(int)
    remote_operations: list[dict[str, Any]] = []

    qubit_activity = {
        qubit_index: {
            "operation_count": 0,
            "first_op": None,
            "last_op": None,
        }
        for qubit_index in range(logical_ir.logical_qubit_count)
    }

    for operation in logical_ir.operations:
        op_kind_counts[operation.op_kind] += 1
        gate_counts[operation.operation] += 1
        if operation.op_kind == "two_qubit_remote":
            remote_operations.append(
                {
                    "op_id": operation.op_id,
                    "operation": operation.operation,
                    "qargs": operation.qargs,
                    "source_node": operation.metadata.get("source_node"),
                    "target_node": operation.metadata.get("target_node"),
                    "unmodeled_cost": operation.unmodeled_cost.to_dict() if operation.unmodeled_cost else None,
                }
            )
        for qubit_index in operation.qargs:
            activity = qubit_activity[qubit_index]
            activity["operation_count"] += 1
            activity["first_op"] = activity["first_op"] or operation.op_id
            activity["last_op"] = operation.op_id

    return {
        "dag": {
            "node_count": len(logical_ir.operations),
            "edge_count": sum(len(operation.dependencies) for operation in logical_ir.operations),
            "critical_path_length": len(critical_path),
            "critical_path": critical_path,
            "max_dependency_depth": max(depth_by_id.values(), default=0),
            "parallel_layer_count": len(parallel_layers),
            "parallel_layers": {
                str(depth): op_ids
                for depth, op_ids in sorted(parallel_layers.items())
            },
            "successor_map": successor_map,
        },
        "operation_summary": {
            "op_kind_counts": dict(op_kind_counts),
            "gate_counts": dict(gate_counts),
            "t_family_demand": _t_family_demand(dict(gate_counts)),
        },
        "qubit_activity": qubit_activity,
        "remote_operations": {
            "count": len(remote_operations),
            "operations": remote_operations,
            "has_unmodeled_cost": any(operation["unmodeled_cost"] for operation in remote_operations),
        },
    }


def _critical_path(logical_ir: LogicalIR, successor_map: dict[str, list[str]], depth_by_id: dict[str, int]) -> list[str]:
    if not logical_ir.operations:
        return []

    terminal = max(logical_ir.operations, key=lambda operation: depth_by_id[operation.op_id])
    path = [terminal.op_id]
    current = terminal

    while current.dependencies:
        dependency = max(current.dependencies, key=lambda op_id: depth_by_id[op_id])
        path.append(dependency)
        current = next(operation for operation in logical_ir.operations if operation.op_id == dependency)

    path.reverse()
    return path


def _t_family_demand(gate_counts: dict[str, int]) -> dict[str, int]:
    t_count = 0
    for gate_name, count in gate_counts.items():
        if gate_name.upper() in T_FAMILY_OPERATIONS:
            t_count += int(count)
    return {
        "t_count": t_count,
    }
