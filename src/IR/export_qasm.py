import pennylane as qml

def export_to_qasm(circuit):
    # 1. Execute the circuit once to force the tape to be built
    circuit()
    
    # 2. Now the .tape attribute exists and is no longer 'None'
    qasm_string = circuit.tape.to_openqasm()
    
    return qasm_string