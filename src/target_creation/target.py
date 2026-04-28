from __future__ import annotations

from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit.library import (
    HGate, SGate, SdgGate, TGate, TdgGate, CXGate, IGate, 
    RZGate, SXGate, XGate, RXGate, RYGate, CZGate, RXXGate
)
from hardware.connectivity import k_nearest_tiled_coupling_map

# Import your existing function (if running in a separate file)
# from hardware.connectivity import k_nearest_tiled_coupling_map

def build_dynamic_ft_target(
    # Topology parameters
    n_blocks_row: int = 2,
    n_blocks_col: int = 2,
    n: int = 10,
    m: int = 10,
    k_intra: int = 2,
    k_inter: int = 1,
    connector_local: int = 1,
    
    # Single-qubit gate properties
    sq_error: float = 1e-4,
    sq_duration: float = 50e-9,
    
    # Intra-block (local) 2-qubit gate properties
    intra_cx_error: float = 1e-3,
    intra_cx_duration: float = 200e-9,
    
    # Inter-block (network/remote) 2-qubit gate properties
    inter_cx_error: float = 1e-2,
    inter_cx_duration: float = 1000e-9,
) -> Target:
    """
    Build a Qiskit Target for a tiled FT architecture with distinct 
    intra-block and inter-block error rates and durations.
    """
    # 1. Generate the underlying topology
    cmap = k_nearest_tiled_coupling_map(
        n_blocks_row=n_blocks_row,
        n_blocks_col=n_blocks_col,
        n=n,
        m=m,
        k_intra=k_intra,
        k_inter=k_inter,
        connector_local=connector_local
    )

    
    
    num_qubits = cmap.size()
    n_block = n * m  # Number of qubits in a single FT computer
    
    # 2. Initialize the Target
    target = Target(num_qubits=num_qubits)
    
    # 3. Define the standard FT single-qubit Gate Set (Clifford + T)
    sq_props = {
        (q,): InstructionProperties(error=sq_error, duration=sq_duration)
        for q in range(num_qubits)
    }
    
    target.add_instruction(IGate(), sq_props)
    target.add_instruction(HGate(), sq_props)
    target.add_instruction(SGate(), sq_props)
    target.add_instruction(SdgGate(), sq_props)
    target.add_instruction(TGate(), sq_props)
    target.add_instruction(TdgGate(), sq_props)

    # 4. Define the 2-qubit operations (CX) mapping based on edge type
    cx_props = {}
    
    for edge in cmap.get_edges():
        q1, q2 = edge
        
        # Determine which block each qubit belongs to using integer division
        block_q1 = q1 // n_block
        block_q2 = q2 // n_block
        
        if block_q1 == block_q2:
            # Intra-block connection (inside the same computer)
            cx_props[(q1, q2)] = InstructionProperties(
                error=intra_cx_error, 
                duration=intra_cx_duration
            )
        else:
            # Inter-block connection (network link between computers)
            cx_props[(q1, q2)] = InstructionProperties(
                error=inter_cx_error, 
                duration=inter_cx_duration
            )
            
    target.add_instruction(CXGate(), cx_props)
    
    return target





# Display labels used in tables/plots.
MODALITY_DISPLAY_NAMES = {
    "superconducting": "Superconducting",
    "trapped_ion": "Trapped Ion",
    "neutral_atom": "Neutral Atom",
    "photonic": "Photonic",
}

REGIME_DISPLAY_NAMES = {
    "nisq": "NISQ",
    "ft": "FT",
}


def get_architecture_display_name(modality: str, regime: str) -> str:
    """Return a human-readable architecture label."""
    modality_name = MODALITY_DISPLAY_NAMES.get(modality, modality.replace("_", " ").title())
    regime_name = REGIME_DISPLAY_NAMES.get(regime, regime.upper())
    return f"{regime_name} {modality_name}"


def _normalize_architecture_request(
    modality: str | None = None,
    regime: str | None = None,
    arch_type: str | None = None,
) -> tuple[str, str]:
    """
    Normalize legacy flat architecture labels into explicit modality/regime axes.

    Legacy flat labels map as follows:
    - Superconducting / Trapped Ion / Neutral Atom / Photonic -> NISQ
    - Fault Tolerant -> FT superconducting-style logical default
    """

    legacy_map = {
        "superconducting": ("superconducting", "nisq"),
        "trapped ion": ("trapped_ion", "nisq"),
        "trapped_ion": ("trapped_ion", "nisq"),
        "neutral atom": ("neutral_atom", "nisq"),
        "neutral_atom": ("neutral_atom", "nisq"),
        "photonic": ("photonic", "nisq"),
        "fault tolerant": ("superconducting", "ft"),
        "fault_tolerant": ("superconducting", "ft"),
        "ft": ("superconducting", "ft"),
    }

    if modality is None and regime is None and arch_type is not None:
        key = arch_type.strip().lower()
        if key in legacy_map:
            return legacy_map[key]
        raise ValueError(f"Unknown legacy architecture label: {arch_type}")

    if modality is None or regime is None:
        raise ValueError("Both modality and regime must be provided.")

    return modality.strip().lower(), regime.strip().lower()

    # 1. Define Architecture Profiles
    # Values represent typical orders of magnitude for these systems

    # superconducting fidelity citation: https://arxiv.org/html/2410.00916v1#:~:text=It%20demonstrated%20the%20highest%20QV,minimizing%20spectator%20errors%20%5B43%5D%20.   
    # used worst-case error rates for generalized benchmarking

def _get_architecture_profiles() -> dict[str, dict[str, dict]]:
    """
    Architecture model definitions.

    Regime determines the compiler abstraction level:
    - NISQ: physical/native-ish gate set and physical-style assumptions
    - FT: logical ISA and logical/distributed assumptions with modality-inspired
    duration/error scales
    """
    # The FT side compiles to a logical ISA rather than physical-native gates.
    logical_sq_gates = [IGate(), HGate(), SGate(), SdgGate(), TGate(), TdgGate()]

    return {
        "superconducting": {
            "nisq": {
                # Standard IBM-style physical/native basis.
                "sq_gates": [RZGate(0), SXGate(), XGate()],
                "two_q_gate": CXGate(),
                "k_intra": 1,
                "sq_err": 1e-4,
                "sq_dur": 50e-9,
                "intra_err": 1e-3,
                "intra_dur": 500e-9,
            },
            "ft": {
                # FT superconducting means logical gates implemented atop a
                # superconducting physical stack, so the logical ISA takes over.
                "sq_gates": logical_sq_gates,
                "two_q_gate": CXGate(),
                "k_intra": 2,
                "sq_err": 1e-5,
                "sq_dur": 50e-9,
                "intra_err": 1e-4,
                "intra_dur": 200e-9,
            },
        },
        "trapped_ion": {
            "nisq": {
                "sq_gates": [RXGate(0), RYGate(0), RZGate(0)],
                "two_q_gate": CXGate(),
                "k_intra": None,
                "sq_err": 1e-5,
                "sq_dur": 10e-6,
                "intra_err": 5e-4,
                "intra_dur": 100e-6,
            },
            "ft": {
                "sq_gates": logical_sq_gates,
                "two_q_gate": CXGate(),
                "k_intra": 2,
                "sq_err": 1e-6,
                "sq_dur": 10e-6,
                "intra_err": 5e-5,
                "intra_dur": 100e-6,
            },
        },
        "neutral_atom": {
            "nisq": {
                "sq_gates": [RXGate(0), RYGate(0), RZGate(0)],
                "two_q_gate": CZGate(),
                "k_intra": None,
                "sq_err": 1e-4,
                "sq_dur": 1e-6,
                "intra_err": 1e-2,
                "intra_dur": 2e-6,
            },
            "ft": {
                "sq_gates": logical_sq_gates,
                "two_q_gate": CXGate(),
                "k_intra": 2,
                "sq_err": 5e-6,
                "sq_dur": 1e-6,
                "intra_err": 5e-4,
                "intra_dur": 5e-6,
            },
        },
        "photonic": {
            "nisq": {
                "sq_gates": [RZGate(0), HGate()],
                "two_q_gate": CZGate(),
                "k_intra": 1,
                "sq_err": 1e-5,
                "sq_dur": 1e-12,
                "intra_err": 1e-1,
                "intra_dur": 1e-11,
            },
            "ft": {
                "sq_gates": logical_sq_gates,
                "two_q_gate": CXGate(),
                "k_intra": 2,
                "sq_err": 1e-6,
                "sq_dur": 1e-12,
                "intra_err": 1e-2,
                "intra_dur": 1e-10,
            },
        },
    }


## used to build different models of the target for testing different parameters in the main pipeline
def build_flexible_target(
    modality: str | None = None,
    regime: str | None = None,
    arch_type: str | None = None,
    n_blocks_row: int = 2,
    n_blocks_col: int = 2,
    n: int = 10,
    m: int = 10,
    k_intra: int = None,
    k_inter: int = 1,
    connector_local: int = 1,
    inter_err: float = 0.05,
    inter_dur: float = 1e-6,
    # Overrides 
    custom_sq_error: float = None,
    custom_2q_error: float = None
) -> Target:

    modality, regime = _normalize_architecture_request(
        modality=modality,
        regime=regime,
        arch_type=arch_type,
    )
    profiles = _get_architecture_profiles()

    if modality not in profiles:
        supported = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown modality: {modality}. Supported modalities: {supported}")
    if regime not in profiles[modality]:
        supported = ", ".join(sorted(profiles[modality]))
        raise ValueError(f"Unknown regime: {regime}. Supported regimes for {modality}: {supported}")

    prof = profiles[modality][regime]

    
    # Apply overrides if provided.
    sq_err = custom_sq_error or prof['sq_err']
    intra_err = custom_2q_error or prof['intra_err']
    if k_intra is None:
        k_intra = prof['k_intra'] if prof['k_intra'] is not None else n*m
    else:
        print(f"Using custom k_intra={k_intra} instead of profile default {prof['k_intra']}") if prof['k_intra'] is not None else 'Fully Connected'
    # 2. Setup Topology
    cmap = k_nearest_tiled_coupling_map(
        n_blocks_row=n_blocks_row, 
        n_blocks_col=n_blocks_col,
        n=n, 
        m=m, 
        k_intra=k_intra, 
        k_inter=k_inter, 
        connector_local=connector_local
    )
    
    target = Target(num_qubits=cmap.size())
    n_block = n * m

    # 3. Add Single-Qubit Gates
    sq_props = {(q,): InstructionProperties(error=sq_err, duration=prof['sq_dur']) 
                for q in range(cmap.size())}
    
    for gate in prof['sq_gates']:
        target.add_instruction(gate, sq_props)

    # 4. Add Two-Qubit Gates (Intra vs Inter)
    # Note: For Networked computing, we assume "Network Link" 
    # can be converted to the native 2Q gate through local operations.
    two_q_gate = prof['two_q_gate']
    two_q_props = {}
    
    # We define network performance (Inter-block)
    # Photonic links are often the bottleneck for all these architectures
    # 1 microsecond latency is common for optical interconnects

    for q1, q2 in cmap.get_edges():
        if (q1 // n_block) == (q2 // n_block):
            # Local Connection
            two_q_props[(q1, q2)] = InstructionProperties(error=intra_err, duration=prof['intra_dur'])
        else:
            # Network Connection
            two_q_props[(q1, q2)] = InstructionProperties(error=inter_err, duration=inter_dur)

    target.add_instruction(two_q_gate, two_q_props)
    
    return target
