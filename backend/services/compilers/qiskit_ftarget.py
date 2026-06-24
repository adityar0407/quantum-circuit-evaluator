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
                scheduling_method="alap",
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
        )
