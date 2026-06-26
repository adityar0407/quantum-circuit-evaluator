from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Literal


QecPatchKind = Literal["data", "ancilla", "routing", "factory"]
QecLoweringStatus = Literal["fully_lowered", "analytically_modeled", "unlowered", "unsupported"]


@dataclass(frozen=True)
class QecPatch:
    patch_id: str
    patch_kind: QecPatchKind
    logical_qubit: int | None
    node_id: int | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QecOperation:
    op_id: str
    op_kind: str
    input_patches: tuple[str, ...]
    output_patches: tuple[str, ...]
    dependencies: tuple[str, ...]
    source_logical_op_ids: tuple[str, ...]
    lowering_status: QecLoweringStatus
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QecIR:
    schema_version: str
    code_family: str
    patches: tuple[QecPatch, ...]
    operations: tuple[QecOperation, ...]
    source_logical_ir_hash: str
    operation_counts: dict[str, int]
    operation_layers: tuple[tuple[str, ...], ...]
    patch_occupancy: dict[str, tuple[str, ...]]
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "code_family": self.code_family,
            "patches": [patch.to_dict() for patch in self.patches],
            "operations": [operation.to_dict() for operation in self.operations],
            "source_logical_ir_hash": self.source_logical_ir_hash,
            "operation_counts": self.operation_counts,
            "operation_layers": [list(layer) for layer in self.operation_layers],
            "patch_occupancy": {patch_id: list(op_ids) for patch_id, op_ids in self.patch_occupancy.items()},
            "provenance": self.provenance,
            "warnings": list(self.warnings),
        }
