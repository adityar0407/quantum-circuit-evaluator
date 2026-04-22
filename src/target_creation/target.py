from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from qiskit.transpiler import Target, InstructionProperties, CouplingMap
from qiskit.circuit import Parameter, Reset
from qiskit.circuit.library import (
    CXGate,
    CZGate,
    HGate,
    IGate,
    Measure,
    RXGate,
    RXXGate,
    RYGate,
    RZGate,
    SdgGate,
    SGate,
    SwapGate,
    SXGate,
    TdgGate,
    TGate,
    XGate,
)

NON_BASIS_OPERATION_NAMES = {"barrier", "delay", "if_else", "measure", "reset"}


@dataclass(frozen=True)
class BenchmarkTarget:
    """Target data used by the benchmark pipeline."""

    target: Target
    basis_gates: list[str]
    target_source: str

GATE_NAME_TO_INSTRUCTION = {
    "cx": CXGate(),
    "cz": CZGate(),
    "h": HGate(),
    "id": IGate(),
    "rx": RXGate(Parameter("theta")),
    "rxx": RXXGate(Parameter("theta")),
    "ry": RYGate(Parameter("theta")),
    "rz": RZGate(Parameter("phi")),
    "s": SGate(),
    "sdg": SdgGate(),
    "swap": SwapGate(),
    "sx": SXGate(),
    "t": TGate(),
    "tdg": TdgGate(),
    "x": XGate(),
    "reset": Reset(),
}


def instruction_from_gate(gate: Any):
    """Return a Qiskit instruction from either a gate name, class, or instance."""
    if isinstance(gate, str):
        try:
            return GATE_NAME_TO_INSTRUCTION[gate]
        except KeyError as exc:
            raise ValueError(f"Unsupported gate for target creation: {gate}") from exc

    if hasattr(gate, "name") and hasattr(gate, "num_qubits"):
        return gate

    try:
        return gate()
    except TypeError:
        if gate in (RXGate, RYGate, RXXGate):
            return gate(Parameter("theta"))
        if gate is RZGate:
            return gate(Parameter("phi"))
        raise


def create_custom_target(
    num_qubits: int,
    basis_gates: Sequence[Any],
    gate_specs: Mapping[str, Mapping[str, float]] | None = None,
    coupling_map: CouplingMap = None,
    verbose: bool = False,
) -> Target:
    """
    Creates a highly customizable Qiskit Target for user-defined architectures.
    
    Args:
        num_qubits: Total number of qubits in the system.
        basis_gates: List of Qiskit gate classes (e.g., [RXGate, CXGate]).
        gate_specs: Optional dictionary mapping gate names to 'duration' and
                    'error'. Missing specs remain undefined in the target.
        coupling_map: The allowed connectivity. If None, assumes all-to-all.
        
    Returns:
        A configured Qiskit Target object.
    """
    target = Target(num_qubits=num_qubits)
    gate_specs = gate_specs or {}
    instructions = [instruction_from_gate(gate) for gate in basis_gates]

    if verbose:
        print(f"Creating custom target with {num_qubits} qubits and basis gates: {[gate.name for gate in instructions]}")
        print("if no coupling map is provided, the target will assume all-to-all connectivity between qubits.")
        print("if no specs are provided for a given gate, duration/error will be undefined.")
    # Define the edges for 2-qubit gates based on the coupling map
    if coupling_map:
        ## TODO: see if adi can create a callable for the coupling map so i don't ahve to call get_edges in here too
        edges = list(coupling_map.get_edges())
    else:
        # All-to-all connectivity if no map is provided
        edges = [(i, j) for i in range(num_qubits) for j in range(num_qubits) if i != j]
        
    for instruction in instructions:
        gate_name = instruction.name
        
        specs = gate_specs.get(gate_name)
        if specs is None:
            props = InstructionProperties()
        else:
            props = InstructionProperties(
                duration=specs.get("duration"),
                error=specs.get("error"),
            )
        
        if instruction.num_qubits == 1:
            # Apply 1-qubit gates to all individual qubits
            instruction_map = {(q,): props for q in range(num_qubits)}
        elif instruction.num_qubits == 2:
            # Apply 2-qubit gates only to connected edges
            instruction_map = {edge: props for edge in edges}
        else:
            continue # Skip 3+ qubit gates for this simple builder. TODO: maybe add support for multi-qubit gates in the future.
            
        target.add_instruction(instruction, instruction_map)
        
    # Measurement support is included, but no duration/error is assumed here.
    measure_props = InstructionProperties()
    target.add_instruction(Measure(), {(q,): measure_props for q in range(num_qubits)})
        
    return target


def basis_gates_from_target(target: Target) -> list[str]:
    """Return operation names that are suitable for basis translation."""
    basis = []
    for name in sorted(target.operation_names):
        if name in NON_BASIS_OPERATION_NAMES or name.startswith("measure"):
            continue
        basis.append(name)
    return basis


def _try_load_backend_target(backend_name: str) -> BenchmarkTarget | None:
    """Load an IBM backend target if IBM Runtime is installed and configured."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError:
        return None

    try:
        service = QiskitRuntimeService()
        backend = service.backend(backend_name)
        target = backend.target
    except Exception:
        return None

    return BenchmarkTarget(
        target=target,
        basis_gates=basis_gates_from_target(target),
        target_source=f"{backend_name} backend.target",
    )


def get_benchmark_target(
    architecture: str,
    num_qubits: int,
    coupling_map: CouplingMap = None,
    backend_name: str | None = None,
    fallback_basis_gates: Sequence[str] | None = None,
) -> BenchmarkTarget:
    """
    Return target data for a benchmark architecture.

    IBM profiles prefer backend-derived targets. Fallback targets encode only
    basis and connectivity; their durations/errors are intentionally undefined.
    """
    architecture_key = architecture.lower()
    fallback_basis_gates = list(fallback_basis_gates or [])

    if architecture_key == "ibm_heavy_hex" and backend_name is not None:
        backend_target = _try_load_backend_target(backend_name)
        if backend_target is not None:
            return backend_target

    if architecture_key in {"superconducting", "ibm_heavy_hex", "ft_style_logical"}:
        target = create_custom_target(
            num_qubits=num_qubits,
            basis_gates=fallback_basis_gates,
            gate_specs=None,
            coupling_map=coupling_map,
        )
        return BenchmarkTarget(
            target=target,
            basis_gates=fallback_basis_gates,
            target_source="fallback basis/connectivity-only target",
        )

    raise ValueError(f"Unknown architecture profile: {architecture}")
