from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CircuitQasmRequest(BaseModel):
    qasm: str = Field(..., min_length=1)


class CircuitSummaryResponse(BaseModel):
    num_qubits: int
    num_clbits: int
    depth: int
    gate_count: int
    operation_counts: dict[str, int]


class TargetPreviewRequest(BaseModel):
    config: dict[str, Any]


class GraphNode(BaseModel):
    id: int
    block: int
    x: float | None = None
    y: float | None = None


class GraphEdge(BaseModel):
    source: int
    target: int
    local: bool


class TargetPreviewResponse(BaseModel):
    topology_type: str
    total_qubits: int
    total_edges: int
    n_block: int
    operation_names: list[str]
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class TranspileRequest(BaseModel):
    qasm: str = Field(..., min_length=1)
    target_config: dict[str, Any]


class TranspileResponse(BaseModel):
    original: CircuitSummaryResponse
    transpiled: CircuitSummaryResponse
    metrics: dict[str, Any]
