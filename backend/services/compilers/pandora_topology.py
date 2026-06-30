from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit

from backend.services.compilers.base import CompilerError


def build_pandora_topology_payload(target: Any) -> dict[str, Any]:
    edges = [(int(source), int(target_node)) for source, target_node in target.cmap.get_edges()]
    unique_undirected = sorted({tuple(sorted((source, target_node))) for source, target_node in edges})
    qubit_to_node = {
        int(qubit_id): int(qubit_id // target.n_block)
        for qubit_id in range(int(target.total_qubits))
    }
    local_edges = [
        {"source": source, "target": target_node}
        for source, target_node in edges
        if bool(target._is_local_edge(source, target_node))
    ]
    remote_edges = [
        {"source": source, "target": target_node}
        for source, target_node in edges
        if not bool(target._is_local_edge(source, target_node))
    ]

    return {
        "architecture_id": str(target.type),
        "topology_type": str(target.type),
        "number_of_qubits": int(target.total_qubits),
        "allowed_coupling_edges": [{"source": source, "target": target_node} for source, target_node in edges],
        "allowed_coupling_edges_undirected": [
            {"source": source, "target": target_node} for source, target_node in unique_undirected
        ],
        "native_gate_set": sorted(getattr(target, "operation_names", [])),
        "qubit_to_node_mapping": qubit_to_node,
        "local_edges": local_edges,
        "remote_inter_node_edges": remote_edges,
        "directed_edge_policy": "bidirectional_explicit"
        if _is_bidirectional(edges)
        else "directed",
        "architecture_limitations": _architecture_limitations(target),
        "n_block": int(target.n_block),
        "n_blocks_row": int(getattr(target, "n_blocks_row", 1)),
        "n_blocks_col": int(getattr(target, "n_blocks_col", 1)),
        "nodes": [
            {
                "id": int(qubit_id),
                "node": int(qubit_id // target.n_block),
                "slot_in_node": int(qubit_id % target.n_block),
            }
            for qubit_id in range(int(target.total_qubits))
        ],
    }


def validate_compiled_circuit_against_architecture(
    circuit: QuantumCircuit,
    topology: dict[str, Any],
) -> dict[str, Any]:
    allowed_directed = {
        (int(edge["source"]), int(edge["target"]))
        for edge in topology.get("allowed_coupling_edges", [])
    }
    allowed_undirected = {
        tuple(sorted((int(edge["source"]), int(edge["target"]))))
        for edge in topology.get("allowed_coupling_edges_undirected", [])
    }
    native_gate_set = {str(name).lower() for name in topology.get("native_gate_set", [])}
    illegal_edges: list[dict[str, Any]] = []
    unsupported_gates: list[dict[str, Any]] = []
    local_two_qubit = 0
    remote_two_qubit = 0

    for index, instruction in enumerate(circuit.data):
        op_name = instruction.operation.name.lower()
        qargs = [circuit.find_bit(qubit).index for qubit in instruction.qubits]

        if op_name not in native_gate_set and op_name not in {"barrier", "measure"}:
            unsupported_gates.append({"index": index, "operation": op_name})

        if len(qargs) != 2:
            continue

        edge = (qargs[0], qargs[1])
        undirected_edge = tuple(sorted(edge))
        if edge not in allowed_directed and undirected_edge not in allowed_undirected:
            illegal_edges.append({"index": index, "operation": op_name, "edge": list(edge)})
            continue

        qmap = topology.get("qubit_to_node_mapping", {})
        if qmap.get(qargs[0]) == qmap.get(qargs[1]):
            local_two_qubit += 1
        else:
            remote_two_qubit += 1

    if illegal_edges:
        raise CompilerError(
            "Pandora output contains illegal two-qubit edges for the selected architecture: "
            f"{illegal_edges}"
        )
    if unsupported_gates:
        raise CompilerError(
            "Pandora output contains operations outside the architecture native gate set: "
            f"{unsupported_gates}"
        )

    return {
        "validated": True,
        "illegal_two_qubit_edges": [],
        "unsupported_native_gates": [],
        "local_two_qubit_operations": local_two_qubit,
        "remote_two_qubit_operations": remote_two_qubit,
    }


def validate_pandora_comparison_ready(compilation_artifacts: dict[str, Any]) -> None:
    if not compilation_artifacts.get("topology_aware", False):
        raise CompilerError("Architecture comparison mode rejects topology-ignorant Pandora results.")

    if "topology_validation" not in compilation_artifacts:
        raise CompilerError("Architecture comparison mode requires validated Pandora topology results.")

    if not compilation_artifacts["topology_validation"].get("validated", False):
        raise CompilerError("Architecture comparison mode requires Pandora topology validation to pass.")


def _is_bidirectional(edges: list[tuple[int, int]]) -> bool:
    edge_set = set(edges)
    return all((target_node, source) in edge_set for source, target_node in edge_set)


def _architecture_limitations(target: Any) -> list[str]:
    limitations = [
        "Pandora-native routing currently supports only one- and two-qubit operations.",
        "Pandora output is rejected if two-qubit gates do not respect the selected architecture edges.",
    ]
    if getattr(target, "type", "") == "tiled_k_nearest":
        limitations.append("Inter-node routing is modeled through graph swaps; network cost is not yet physically priced.")
    if getattr(target, "type", "") in {"heavy_hex", "heavy_square"}:
        limitations.append("Surface-code-style topology is validated as a coupling graph, not pulse-level calibration data.")
    if getattr(target, "type", "") == "custom_coupling_map":
        limitations.append("Custom coupling maps are validated structurally but are not yet supported by Pandora auto-selection.")
    return limitations
