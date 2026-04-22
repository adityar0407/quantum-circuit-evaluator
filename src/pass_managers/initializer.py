from __future__ import annotations

from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import HighLevelSynthesis, UnrollCustomDefinitions
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel

def get_init_pm(basis_gates: list[str] | None = None) -> PassManager:
    """
    Phase 1: Initialization
    Unrolls higher-level mathematical objects and custom gate definitions
    into base quantum instructions.
    """
    passes = [HighLevelSynthesis()]

    if basis_gates is not None:
        passes.append(UnrollCustomDefinitions(sel, basis_gates))

    return PassManager(passes)
