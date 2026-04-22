# Export circuit generated from pennylane to a standard OpenQASM string for easier readability and compatibility with compiler further down the pipeline 

def export_to_qasm(circuit): 
    import pennylane as qml

    qasm_string = qml.to_openqasm(circuit)()
    return qasm_string
