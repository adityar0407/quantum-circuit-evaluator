from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx
from qiskit import QuantumCircuit
from qiskit.circuit.library import SwapGate

from backend.services.compilers.base import CompilerError


@dataclass(frozen=True)
class PandoraRoutingResult:
    circuit: QuantumCircuit
    artifacts: dict[str, Any]


def route_circuit_with_target(circuit: QuantumCircuit, target: Any, topology: dict[str, Any]) -> PandoraRoutingResult:
    if circuit.num_qubits > int(topology["number_of_qubits"]):
        raise CompilerError(
            f"Target has {topology['number_of_qubits']} qubits, but the circuit requires {circuit.num_qubits}."
        )

    supported_operations = {str(name).lower() for name in topology.get("native_gate_set", [])}
    graph = _build_connectivity_graph(topology)
    physical_circuit = QuantumCircuit(target.total_qubits, circuit.num_clbits, name=f"{circuit.name}_pandora")

    logical_to_physical = {logical: logical for logical in range(circuit.num_qubits)}
    physical_to_logical = {physical: logical for logical, physical in logical_to_physical.items()}

    swap_insertions = 0
    routed_two_qubit_ops = 0
    direct_two_qubit_ops = 0
    path_lengths: list[int] = []

    for instruction in circuit.data:
        operation = instruction.operation
        op_name = operation.name.lower()
        qargs = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        cargs = [circuit.find_bit(clbit).index for clbit in instruction.clbits]

        if len(qargs) > 2:
            raise CompilerError(
                f"Pandora-native routing currently supports one- and two-qubit operations only. "
                f"Encountered '{operation.name}' on {len(qargs)} qubits."
            )

        if op_name not in supported_operations and op_name not in {"barrier", "measure"}:
            raise CompilerError(
                f"Pandora-native routing cannot lower unsupported target operation '{operation.name}'."
            )

        if len(qargs) == 0:
            physical_circuit.append(operation, [], [physical_circuit.clbits[index] for index in cargs])
            continue

        if len(qargs) == 1:
            physical_index = logical_to_physical[qargs[0]]
            physical_circuit.append(
                operation,
                [physical_circuit.qubits[physical_index]],
                [physical_circuit.clbits[index] for index in cargs],
            )
            continue

        q0, q1 = qargs
        p0 = logical_to_physical[q0]
        p1 = logical_to_physical[q1]

        if graph.has_edge(p0, p1):
            direct_two_qubit_ops += 1
            physical_circuit.append(operation, [physical_circuit.qubits[p0], physical_circuit.qubits[p1]], [])
            continue

        path = nx.shortest_path(graph, p0, p1)
        if len(path) < 2:
            raise CompilerError(f"Pandora-native routing could not connect qubits {q0} and {q1}.")

        path_lengths.append(len(path) - 1)
        routed_two_qubit_ops += 1

        # Move the first logical qubit along the shortest path until it becomes adjacent to the second.
        for left, right in zip(path[:-2], path[1:-1]):
            _apply_swap(
                physical_circuit,
                left,
                right,
                logical_to_physical,
                physical_to_logical,
            )
            swap_insertions += 1

        p0 = logical_to_physical[q0]
        p1 = logical_to_physical[q1]
        if not graph.has_edge(p0, p1):
            raise CompilerError(
                f"Pandora-native routing failed to make qubits {q0} and {q1} adjacent on topology "
                f"{topology['topology_type']}."
            )

        physical_circuit.append(operation, [physical_circuit.qubits[p0], physical_circuit.qubits[p1]], [])

    return PandoraRoutingResult(
        circuit=physical_circuit,
        artifacts={
            "status": "completed",
            "legalization_backend": "pandora_native_router",
            "topology_type": topology["topology_type"],
            "topology_qubits": topology["number_of_qubits"],
            "routing_swaps": swap_insertions,
            "routed_two_qubit_ops": routed_two_qubit_ops,
            "direct_two_qubit_ops": direct_two_qubit_ops,
            "max_routing_path_length": max(path_lengths, default=1),
            "average_routing_path_length": (sum(path_lengths) / len(path_lengths)) if path_lengths else 1.0,
            "placement": {
                f"q[{logical}]": physical for logical, physical in sorted(logical_to_physical.items())
            },
            "routed_paths": path_lengths,
            "inserted_movement_operations": {"swap": swap_insertions},
            "routing_cost_summary": {
                "swap_count": swap_insertions,
                "routed_two_qubit_ops": routed_two_qubit_ops,
                "direct_two_qubit_ops": direct_two_qubit_ops,
            },
            "operation_counts": dict(physical_circuit.count_ops()),
            "original_gate_count": circuit.size(),
            "legalized_gate_count": physical_circuit.size(),
        },
    )


def _build_connectivity_graph(topology: dict[str, Any]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(int(topology["number_of_qubits"])))
    graph.add_edges_from(
        (int(edge["source"]), int(edge["target"]))
        for edge in topology.get("allowed_coupling_edges_undirected", [])
    )
    if not nx.is_connected(graph):
        raise CompilerError("Pandora-native routing requires a connected target coupling graph.")
    return graph


def _apply_swap(
    circuit: QuantumCircuit,
    left: int,
    right: int,
    logical_to_physical: dict[int, int],
    physical_to_logical: dict[int, int],
) -> None:
    circuit.append(SwapGate(), [circuit.qubits[left], circuit.qubits[right]], [])

    left_logical = physical_to_logical.get(left)
    right_logical = physical_to_logical.get(right)

    if left_logical is not None:
        logical_to_physical[left_logical] = right
    if right_logical is not None:
        logical_to_physical[right_logical] = left

    if left_logical is None:
        physical_to_logical.pop(right, None)
    else:
        physical_to_logical[right] = left_logical

    if right_logical is None:
        physical_to_logical.pop(left, None)
    else:
        physical_to_logical[left] = right_logical
