from __future__ import annotations

from typing import Any

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from backend.services.circuit_service import circuit_from_qasm
from backend.services.compilers.base import CompilationResult, CompilerError
from backend.services.target_service import build_target


class QiskitFTargetCompiler:
    key = "qiskit_ftarget"

    def compile(self, qasm: str, target_config: dict[str, Any]) -> CompilationResult:
        circuit = circuit_from_qasm(qasm)
        target = build_target(target_config)

        try:
            pass_manager = generate_preset_pass_manager(
                optimization_level=3,
                target=target,
                seed_transpiler=1738,
            )
            compiled = pass_manager.run(circuit)
        except Exception as exc:
            raise CompilerError(f"Qiskit FTarget compilation failed: {exc}") from exc

        return CompilationResult(
            compiler=self.key,
            original_circuit=circuit,
            compiled_circuit=compiled,
            target=target,
            artifacts={
                "optimization_level": 3,
                "original_layout": _serialize_layout(getattr(getattr(compiled, "layout", None), "initial_layout", None)),
                "final_layout": _serialize_layout(getattr(getattr(compiled, "layout", None), "final_layout", None)),
                "routing_swaps": max(
                    0,
                    int(compiled.count_ops().get("swap", 0)) - int(circuit.count_ops().get("swap", 0)),
                ),
                "target_snapshot": {
                    "topology_type": getattr(target, "type", None),
                    "total_qubits": getattr(target, "total_qubits", None),
                    "n_block": getattr(target, "n_block", None),
                    "operation_names": sorted(getattr(target, "operation_names", [])),
                    "logical_architecture_only": getattr(target, "logical_architecture_only", False),
                },
            },
        )


def _serialize_layout(layout: Any) -> dict[str, int] | None:
    if layout is None:
        return None

    mapping: dict[str, int] = {}
    try:
        items = layout.get_virtual_bits().items()
    except Exception:
        return None

    for virtual_bit, physical_index in items:
        register_name = getattr(getattr(virtual_bit, "_register", None), "name", "q")
        mapping[f"{register_name}[{virtual_bit._index}]"] = int(physical_index)
    return mapping or None
