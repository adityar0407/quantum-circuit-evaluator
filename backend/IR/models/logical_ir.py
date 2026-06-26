from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Literal


LogicalOpKind = Literal[
    "single_qubit",
    "two_qubit_local",
    "two_qubit_remote",
    "measure",
    "barrier",
    "reset",
    "classical_control",
    "other",
]


@dataclass(frozen=True)
class UnmodeledCost:
    category: str
    status: Literal["unmodeled"]
    reason: str
    affects_runtime: bool = True
    affects_error_budget: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LogicalInstruction:
    op_id: str
    op_kind: LogicalOpKind
    operation: str
    base_operation: str
    qargs: list[int]
    cargs: list[int]
    parameters: list[float | str]
    node_ids: list[int | None]
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    unmodeled_cost: UnmodeledCost | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.unmodeled_cost is not None:
            payload["unmodeled_cost"] = self.unmodeled_cost.to_dict()
        return payload


@dataclass(frozen=True)
class LogicalPlacement:
    logical_qubit: int
    node_id: int | None
    slot_in_node: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LogicalIR:
    version: str
    compiler: str
    logical_qubit_count: int
    classical_bit_count: int
    placements: list[LogicalPlacement]
    operations: list[LogicalInstruction]
    operation_counts: dict[str, int]
    remote_operation_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "compiler": self.compiler,
            "logical_qubit_count": self.logical_qubit_count,
            "classical_bit_count": self.classical_bit_count,
            "placements": [placement.to_dict() for placement in self.placements],
            "operations": [operation.to_dict() for operation in self.operations],
            "operation_counts": self.operation_counts,
            "remote_operation_count": self.remote_operation_count,
            "metadata": self.metadata,
            "notes": self.notes,
        }
