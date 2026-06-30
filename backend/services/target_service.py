from __future__ import annotations

from typing import Any

from backend.hardware.architecture_presets import resolve_architecture_config
from backend.services.compilers.pandora_topology import build_pandora_topology_payload
from backend.target_creation.target import FTarget


class TargetBuildError(ValueError):
    """Raised when a target config cannot create a valid FTarget."""


def build_target(config: dict[str, Any]) -> FTarget:
    try:
        resolved = _resolve_target_config(config)
        return FTarget(resolved)
    except Exception as exc:
        raise TargetBuildError(f"Invalid target configuration: {exc}") from exc


def _resolve_target_config(config: dict[str, Any]) -> dict[str, Any]:
    if "architecture_preset" not in config:
        return config

    preset_id = str(config["architecture_preset"])
    overrides = {
        key: value
        for key, value in config.items()
        if key not in {"architecture_preset"}
    }
    return resolve_architecture_config(preset_id, overrides=overrides or None)


def _node_positions(target: FTarget) -> dict[int, tuple[float, float]]:
    if target.type in {"heavy_hex", "heavy_square"} and hasattr(target, "pos"):
        return {
            int(node): (float(pos[0]), float(pos[1]))
            for node, pos in target.pos.items()
        }

    if target.type == "tiled_k_nearest":
        positions = {}
        for qubit_id in range(target.total_qubits):
            block_id = qubit_id // target.n_block
            block_row = block_id // target.n_blocks_col
            block_col = block_id % target.n_blocks_col
            local_id = qubit_id % target.n_block
            row = local_id // target.m
            col = local_id % target.m
            positions[qubit_id] = (
                float((block_col * (target.m + 3)) + col),
                float(-((block_row * (target.n + 3)) + row)),
            )
        return positions

    return {}


def preview_target(config: dict[str, Any]) -> dict:
    target = build_target(config)
    topology = export_target_topology(target)

    return {
        "topology_type": topology["topology_type"],
        "total_qubits": topology["total_qubits"],
        "total_edges": topology["total_edges"],
        "n_block": topology["n_block"],
        "operation_names": topology["operation_names"],
        "nodes": topology["nodes"],
        "edges": topology["edges"],
    }


def export_target_topology(target: FTarget) -> dict[str, Any]:
    positions = _node_positions(target)
    payload = build_pandora_topology_payload(target)

    return {
        "architecture_id": payload["architecture_id"],
        "topology_type": payload["topology_type"],
        "total_qubits": payload["number_of_qubits"],
        "number_of_qubits": payload["number_of_qubits"],
        "total_edges": len(payload["allowed_coupling_edges"]),
        "n_block": payload["n_block"],
        "n_blocks_row": payload["n_blocks_row"],
        "n_blocks_col": payload["n_blocks_col"],
        "operation_names": payload["native_gate_set"],
        "native_gate_set": payload["native_gate_set"],
        "allowed_coupling_edges": payload["allowed_coupling_edges"],
        "allowed_coupling_edges_undirected": payload["allowed_coupling_edges_undirected"],
        "qubit_to_node_mapping": payload["qubit_to_node_mapping"],
        "local_edges": payload["local_edges"],
        "remote_inter_node_edges": payload["remote_inter_node_edges"],
        "directed_edge_policy": payload["directed_edge_policy"],
        "architecture_limitations": payload["architecture_limitations"],
        "nodes": [
            {
                "id": qubit_id,
                "block": qubit_id // target.n_block,
                "slot_in_block": qubit_id % target.n_block,
                "node": payload["qubit_to_node_mapping"][qubit_id],
                "x": positions.get(qubit_id, (None, None))[0],
                "y": positions.get(qubit_id, (None, None))[1],
            }
            for qubit_id in range(target.total_qubits)
        ],
        "edges": [
            {
                "source": int(edge["source"]),
                "target": int(edge["target"]),
                "local": bool(target._is_local_edge(edge["source"], edge["target"])),
            }
            for edge in payload["allowed_coupling_edges"]
        ],
    }
