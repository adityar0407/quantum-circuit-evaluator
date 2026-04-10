from configs.load_config import load_config
from IR.export_qasm import export_qasm_stub
from metrics.qasm_counter import count_gates_from_qasm
from hardware.connectivity import is_connected
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap

# Import from the custom modules we created
from error_correction.surface_codes import create_gate_cost_evaluator
from qiskit_transpiler import dynamic_weight_transpile

def test_case():
    """
    Runs a dummy circuit through the dynamic transpilation pipeline to test 
    routing, optimization convergence, and early-stopping thresholds.
    """
    print("==================================================")
    print("   Starting Dynamic FT Transpilation Test Case    ")
    print("==================================================\n")

    # deliberately add redundancies and long-range interactions to test the passes.
    qc = QuantumCircuit(4)
    
    # Single qubit operations
    qc.h(0)
    qc.rx(0.5, 1)
    qc.rz(0.2, 1) # rx and rz should be compressed into one basis gate
    
    # Fault-tolerant expensive gate
    qc.t(2)
    
    # Long-range interaction (will require routing SWAPs)
    qc.cx(0, 3) 
    
    # Redundant long-range interaction (should be cancelled by CommutativeCancellation)
    qc.cx(0, 3) 

    print("--- Original Circuit Info ---")
    print(f"Depth: {qc.depth()}")
    print(f"Gate Counts: {qc.count_ops()}\n")

    # A linear map for test
    cmap = CouplingMap.from_line(4)

    # Simulating a Surface Code profile
    ft_weights = {
        't': 50.0, 
        'swap': 30.0, 
        'cx': 2.0, 
        'h': 1.0,
        'rx': 1.0,
        'rz': 1.0,
        'u1': 1.0,
        'u2': 1.0,
        'u3': 1.0 
    }
    
    evaluator = create_gate_cost_evaluator(
        gate_weights=ft_weights, 
        depth_weight=1.5,          # Penalize logical idling time
        unmapped_gate_penalty=5.0  # Catch-all penalty for unexpected gates
    )

    #test threshold
    target_threshold = 85.0 

    
    print("--- Executing Transpiler ---")
    final_qc, final_cost = dynamic_weight_transpile(
        circuit=qc,
        coupling_map=cmap,
        cost_evaluator=evaluator,
        target_weight_threshold=target_threshold,
        max_iterations=10
    )

    print("\n==================================================")
    print("               Final Test Results                 ")
    print("==================================================")
    print(f"Final Circuit Depth: {final_qc.depth()}")
    print(f"Final Gate Counts:   {dict(final_qc.count_ops())}")
    print(f"Final Circuit Cost:  {final_cost}")
    print("==================================================\n")

if __name__ == "__main__":
    test_case()




# depreciated main call
# def main():
#     config = load_config("src/configs/test.yaml")
#     qasm = export_qasm_stub()
#     counts = count_gates_from_qasm(qasm)
    
#     print("Gate counts:", counts)
