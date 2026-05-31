from __future__ import annotations

from typing import Any

from backend.target_creation.target import FTarget


class TargetBuildError(ValueError):
    """Raised when a target config cannot create a valid FTarget."""


def build_target(config: dict[str, Any]) -> FTarget:
    try:
        return FTarget(config)
    except Exception as exc:
        raise TargetBuildError(f"Invalid target configuration: {exc}") from exc


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
    positions = _node_positions(target)
    edges = list(target.cmap.get_edges())

    return {
        "topology_type": target.type,
        "total_qubits": target.total_qubits,
        "total_edges": len(edges),
        "n_block": target.n_block,
        "operation_names": sorted(target.operation_names),
        "nodes": [
            {
                "id": qubit_id,
                "block": qubit_id // target.n_block,
                "x": positions.get(qubit_id, (None, None))[0],
                "y": positions.get(qubit_id, (None, None))[1],
            }
            for qubit_id in range(target.total_qubits)
        ],
        "edges": [
            {
                "source": int(source),
                "target": int(dest),
                "local": bool(target._is_local_edge(source, dest)),
            }
            for source, dest in edges
        ],
    }

