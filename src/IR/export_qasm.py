# Export circuit generated from pennylane to a standard OpenQASM string for easier readability and compatibility with compiler further down the pipeline 
import pennylane as qml 

def export_to_qasm(circuit): 
    qasm_string = qml.to_openqasm(circuit)()
    return qasm_string

