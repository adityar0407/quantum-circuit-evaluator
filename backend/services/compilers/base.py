from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from qiskit import QuantumCircuit


@dataclass(frozen=True)
class CompilationResult:
    compiler: str
    original_circuit: QuantumCircuit
    compiled_circuit: QuantumCircuit
    target: Optional[Any] = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class CompilerError(RuntimeError):
    """Raised when a compiler backend cannot compile a circuit."""


class CompilerBackendUnavailable(CompilerError):
    """Raised when a requested compiler backend is not installed or configured."""


class CompilerBackend(Protocol):
    key: str

    def compile(self, qasm: str, target_config: dict[str, Any]) -> CompilationResult:
        ...
