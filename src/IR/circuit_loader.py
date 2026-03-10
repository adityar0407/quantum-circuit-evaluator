# Load a circuit of your choice defined by Pennylane 
import pennylane as qml

def input_test_circuit (): 
    dev = qml.device("default.qubit", wires = 2)
    @qml.qnode(dev)
    def circuit():
        qml.Hadamard(wires = 0)
        qml.CNOT(wires = [0,1])
        return qml.state()
    return circuit
