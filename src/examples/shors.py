import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import QFT

def M2mod15():
    """M2 (mod 15) using swap gates."""
    U = QuantumCircuit(4)
    U.swap(2, 3)
    U.swap(1, 2)
    U.swap(0, 1)
    U = U.to_gate()
    U.name = "M_2"
    return U

def M4mod15():
    """M4 (mod 15) using swap gates."""
    U = QuantumCircuit(4)
    U.swap(1, 3)
    U.swap(0, 2)
    U = U.to_gate()
    U.name = "M_4"
    return U

def a2kmodN(a, k, N):
    """Compute a^{2^k} (mod N) by repeated squaring."""
    for _ in range(k):
        a = int(np.mod(a**2, N))
    return a

def Shor():
    """Generates the Shor's algorithm circuit for N=15, a=2."""
    N = 15
    a = 2

    num_target = 4  
    num_control = 8 

    k_list = range(num_control)
    b_list = [a2kmodN(a, k, N) for k in k_list]

    control = QuantumRegister(num_control, name="C")
    target = QuantumRegister(num_target, name="T")
    output = ClassicalRegister(num_control, name="out")
    circuit = QuantumCircuit(control, target, output)

    # Initialize target register to |1>
    circuit.x(target[0])

    # Apply Hadamard to control qubits and controlled multiplications
    for k in range(num_control):
        circuit.h(control[k])
        b = b_list[k]
        if b == 2:
            circuit.append(M2mod15().control(), [control[k]] + list(target))
        elif b == 4:
            circuit.append(M4mod15().control(), [control[k]] + list(target))
        # b == 1 is the identity, so we skip it to minimize depth

    # Apply Inverse QFT
    circuit.append(QFT(num_control, inverse=True).to_gate(), control)
    
    # Measure
    

    return circuit


    # print("Generating Shor's Algorithm Circuit (N=15, a=2)...")
    # logical_circuit = Shor()

    # # 1. Define your fault-tolerant hardware constraints
    # print("Initializing FTarget backend...")
    # config = {
    #     "topology": {
    #                 'type': 'tiled_k_nearest',
    #                 "n_blocks_row": 1,
    #                 "n_blocks_col": 1,
    #                 "n": 5,
    #                 "m": 5,
    #                 "k_intra": 1,
    #                 "k_inter": 1,
    #                 "connector_local": 1
    #             },
    #     "profile": {
    #         "sq_gates": ["RZGate", "SXGate", "XGate"],
    #         "two_q_gates": ["CXGate"],
    #         "sq_err": 1e-4,
    #         "sq_dur": 1e-6,
    #         "intra_err": 1.5e-4,
    #         "intra_dur": 2e-6,
    #         "inter_err": 5e-3,
    #         "inter_dur": 50e-6
    #     }
    # }
    
    # # Instantiate your custom target
    # target = FTarget(config)
    
    

    # print("Transpiling circuit to FT instruction set...")
    # # 2. Create the pass manager and compile
    # # We use optimization_level=3 for maximum gate reduction
    # pm = generate_preset_pass_manager(optimization_level=3, target=target)
    
    # try:
    #     transpiled_circuit = pm.run(logical_circuit)
        
    #     # 3. Print the statistics
    #     print("\n--- Compilation Results ---")
    #     print(f"Original Depth:   {logical_circuit.depth()}")
    #     print(f"Transpiled Depth: {transpiled_circuit.depth()}")
    #     print("Transpiled Gate Counts:")
    #     for gate, count in transpiled_circuit.count_ops().items():
    #         print(f"  - {gate}: {count}")

    #     # 4. Draw the final transpiled circuit
    #     print("\nDrawing transpiled circuit (Close the window to exit)...")
        
    #     # We use idle_wires=False to hide unused qubits in the heavy-hex grid
    #     fig = transpiled_circuit.draw('mpl', style='iqp', idle_wires=False, fold=20)
        
    #     # Save a copy for your report
    #     fig.savefig("transpiled_shor_ftarget.png", dpi=300, bbox_inches="tight")
        
    #     # Show it on screen


    # except Exception as e:
    #     print(f"\nTranspilation failed: {e}")
    #     print("Ensure your FTarget provides all necessary basis gates (e.g., SWAP decomposition).")
