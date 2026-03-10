def extract_metadata(circuit):
    return {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "depth": circuit.depth(),
        "gate_count": circuit.size(),
    }
    
