from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit.library import HGate, SGate, SdgGate, TGate, TdgGate, CXGate, IGate
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