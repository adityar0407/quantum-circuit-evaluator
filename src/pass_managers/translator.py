from __future__ import annotations

from qiskit.transpiler.passes import BasisTranslator, Optimize1qGatesDecomposition
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
from qiskit.transpiler import PassManager

ARCHITECTURE_BASIS_GATES = {
    "superconducting": ["rz", "sx", "x", "cx", "id", "swap"],
    "ibm_heavy_hex": ["rz", "sx", "x", "cx", "id", "swap"],
    "ft_style_logical": ["h", "s", "sdg", "cx", "t", "tdg", "swap"],
    "trapped_ion": ["rx", "ry", "rz", "rxx", "measure", "reset"],
    "neutral_atom": ["rx", "ry", "rz", "cz", "measure", "reset"],
}


def get_basis_gates(architecture: str) -> list[str]:
    """Return the native basis gates for a supported architecture profile."""
    try:
        return ARCHITECTURE_BASIS_GATES[architecture.lower()]
    except KeyError as exc:
        supported = ", ".join(sorted(ARCHITECTURE_BASIS_GATES))
        raise ValueError(
            f"Unknown architecture profile: {architecture}. Supported profiles: {supported}"
        ) from exc


def get_translation_pm(
    architecture: str = "superconducting",
    basis_gates: list[str] | None = None,
) -> PassManager:
    """
    Phase 4: Translation
    Forces the circuit into the native Instruction Set Architecture (ISA) of the target backend.
    """
    target_basis = basis_gates or get_basis_gates(architecture)

    return PassManager([
        # Translates gates using standard mathematical equivalences
        BasisTranslator(sel, target_basis=target_basis),
        # Cleans up the translation by compressing resulting single-qubit gates
        Optimize1qGatesDecomposition(basis=target_basis)
    ])
