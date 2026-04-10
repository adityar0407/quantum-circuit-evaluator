from qiskit.transpiler.passes import BasisTranslator, Optimize1qGatesDecomposition
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
from qiskit.transpiler import PassManager

def get_translation_pm(architecture: str = "IBM standard") -> PassManager:
    """
    Phase 4: Translation
    Forces the circuit into the native Instruction Set Architecture (ISA) of the target backend.
    """
    # Define the basis gates based on the architecture
    if architecture == "IBM standard":
        basis_gates = ["x", "sx", "rz", "ecr", "id", "measure", "reset"]
    elif architecture == "Trapped Ion":
        basis_gates = ['rx', 'ry', 'rz', 'rxx', 'measure', 'reset']
    elif architecture == "Neutral Atom":
        basis_gates = ['rx', 'ry', 'rz', 'cz', 'measure', 'reset']
    else:
        # Default FT / Surface Code assumptions
        basis_gates = ['u1', 'u2', 'u3', 'cx', 'swap', 't', 'tdg', 'h', 's']

    return PassManager([
        # Translates gates using standard mathematical equivalences
        BasisTranslator(sel, target_basis=basis_gates),
        # Cleans up the translation by compressing resulting single-qubit gates
        Optimize1qGatesDecomposition(basis=basis_gates)
    ])