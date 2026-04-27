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
    connector_local: int = 0,
    
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





## used to build different models of the target for testing different parameters in the main pipeline
def build_flexible_target(
    arch_type: str = 'Fault Tolerant', # 'Superconducting', 'Trapped Ion', 'Neutral Atom', 'Photonic', 'Fault Tolerant'
    n_blocks_row: int = 2,
    n_blocks_col: int = 2,
    n: int = 10,
    m: int = 10,
    k_intra: int = None,
    k_inter: int = 1,
    connector_local: int = 0,
    inter_err: float = 0.05,
    inter_dur: float = 1e-6,
    # Overrides (optional)
    custom_sq_error: float = None,
    custom_2q_error: float = None
) -> Target:
    
    # 1. Define Architecture Profiles
    # Values represent typical orders of magnitude for these systems
    profiles = {
        'Fault Tolerant': {
            'sq_gates': [IGate(), HGate(), SGate(), SdgGate(), TGate(), TdgGate()],
            'two_q_gate': CXGate(),
            'k_intra':2,
            'sq_err': 1e-4, 'sq_dur': 50e-9,
            'intra_err': 1e-3, 'intra_dur': 200e-9
        },
        'Superconducting': {
            'sq_gates': [RZGate(0), SXGate(), XGate()], # Standard IBM basis
            'two_q_gate': CXGate(),
            'k_intra':1,
            'sq_err': 5e-4, 'sq_dur': 30e-9,
            'intra_err': 1e-2, 'intra_dur': 300e-9
        },
        'Trapped Ion': {
            'sq_gates': [RXGate(0), RYGate(0), RZGate(0)], 
            'two_q_gate': RXXGate(0), # Mølmer-Sørensen gate
            'k_intra': None,
            'sq_err': 1e-5, 'sq_dur': 10e-6, # Much slower, but higher fidelity
            'intra_err': 5e-4, 'intra_dur': 100e-6
        },
        'Neutral Atom': {
            'sq_gates': [RXGate(0), RYGate(0), RZGate(0)],
            'two_q_gate': CZGate(),
            'k_intra': None,
            'sq_err': 1e-4, 'sq_dur': 1e-6,
            'intra_err': 1e-2, 'intra_dur': 2e-6
        },
        'Photonic': {
            'sq_gates': [RZGate(0), HGate()],
            'two_q_gate': CZGate(),
            'k_intra': 1,
            'sq_err': 1e-5, 'sq_dur': 1e-12, # Extremely fast, but high loss (simulated as error)
            'intra_err': 1e-1, 'intra_dur': 1e-11
        }
    }
   
    prof = profiles.get(arch_type, profiles['Fault Tolerant'])

    
    # Apply overrides if provided
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