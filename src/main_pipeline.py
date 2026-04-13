from configs.load_config import load_config
from metrics.qasm_counter import count_gates_from_qasm
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap

# Import from the custom modules we created
from hardware.connectivity import k_nearest_tiled_coupling_map
import pandas as pd
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import time


# def test_case():
#     """
#     Runs a dummy circuit through the dynamic transpilation pipeline to test 
#     routing, optimization convergence, and early-stopping thresholds.
#     """
#     print("==================================================")
#     print("   Starting Dynamic FT Transpilation Test Case    ")
#     print("==================================================\n")

#     # deliberately add redundancies and long-range interactions to test the passes.
#     qc = QuantumCircuit(4)
    
#     # Single qubit operations
#     qc.h(0)
#     qc.rx(0.5, 1)
#     qc.rz(0.2, 1) # rx and rz should be compressed into one basis gate
    
#     # Fault-tolerant expensive gate
#     qc.t(2)
    
#     # Long-range interaction (will require routing SWAPs)
#     qc.cx(0, 3) 
    
#     # Redundant long-range interaction (should be cancelled by CommutativeCancellation)
#     qc.cx(0, 3) 

#     print("--- Original Circuit Info ---")
#     print(f"Depth: {qc.depth()}")
#     print(f"Gate Counts: {qc.count_ops()}\n")

#     # A linear map for test
#     cmap = CouplingMap.from_line(4)

#     # Simulating a Surface Code profile
#     ft_weights = {
#         't': 50.0, 
#         'swap': 30.0, 
#         'cx': 2.0, 
#         'h': 1.0,
#         'rx': 1.0,
#         'rz': 1.0,
#         'u1': 1.0,
#         'u2': 1.0,
#         'u3': 1.0 
#     }
    
#     evaluator = create_gate_cost_evaluator(
#         gate_weights=ft_weights, 
#         depth_weight=1.5,          # Penalize logical idling time
#         unmapped_gate_penalty=5.0  # Catch-all penalty for unexpected gates
#     )

#     #test threshold
#     target_threshold = 85.0 

    
#     print("--- Executing Transpiler ---")
#     final_qc, final_cost = dynamic_weight_transpile(
#         circuit=qc,
#         coupling_map=cmap,
#         cost_evaluator=evaluator,
#         target_weight_threshold=target_threshold,
#         max_iterations=10
#     )

#     print("\n==================================================")
#     print("               Final Test Results                 ")
#     print("==================================================")
#     print(f"Final Circuit Depth: {final_qc.depth()}")
#     print(f"Final Gate Counts:   {dict(final_qc.count_ops())}")
#     print(f"Final Circuit Cost:  {final_cost}")
#     print("==================================================\n")





## this is code for a basic k-connected quantum computer, next is to iterate by different connectivity mapping configurations on potential interconnected FTQC designs
def benchmark_dual_circuits(
    max_k: int = 5, 
    n_dim: int = 10, 
    m_dim: int = 10, 
    count_t_gates: bool = False
):
    """
    Benchmarks both QFT and Toffoli Cascade circuits mapped to a specific 
    architecture across varying levels of qubit connectivity.
    
    Args:
        max_k: The maximum intra-block distance (k_intra) to test.
        n_dim: The number of rows in the single block (default 10 for 100 qubits).
        m_dim: The number of cols in the single block (default 10 for 100 qubits).
        count_t_gates: If True, adds a third plot to track T and Tdg gate counts.
        
    Returns:
        A tuple of pandas DataFrames: (qft_dataframe, toffoli_dataframe).
    """
    total_qubits = n_dim * m_dim
    qft_data = []
    toffoli_data = []
    
    clifford_t_basis = ['h', 's', 'cx', 't', 'tdg', 'swap']
    superconducting_basis = ['rz', 'sx', 'x', 'cx', 'id', 'swap', 't']

    # 1. Create the base circuits
    print(f"Generating {total_qubits}-qubit circuits...")
    qft_circuit = QFT(num_qubits=total_qubits)
    toffoli_circuit = get_toffoli_cascade(total_qubits)
    
    # 2. Iterate through connectivity ranges
    for k in range(2, max_k + 1):
        print(f"--- Benchmarking Level 2 Transpilation for k_intra = {k} ---")
        
        # Build the map for a single block
        cmap = k_nearest_tiled_coupling_map(
            n_blocks_row=1,
            n_blocks_col=1,
            n=n_dim,
            m=m_dim,
            k_intra=k,
            k_inter=1, 
            connector_local=0
        )
        print('Made CMAP')
        # Generate the Level 2 Pass Manager
        pm_cliff = generate_preset_pass_manager(
            optimization_level=2, 
            basis_gates=clifford_t_basis, 
            coupling_map=cmap
        )
        pm_super = generate_preset_pass_manager(
            optimization_level=2, 
            basis_gates=superconducting_basis, 
            coupling_map=cmap
        )
        print('Made pass manager, running on QFT')
        # --- Process QFT ---

        transpiled_qft = pm_super.run(qft_circuit)
        qft_counts = transpiled_qft.count_ops()
        
        qft_data.append({
            'k_intra': k,
            'Circuit Depth': transpiled_qft.depth(),
            'SWAP Count': qft_counts.get('swap', 0),
            'T Gate Count': qft_counts.get('t', 0) + qft_counts.get('tdg', 0),
            'CX Count': qft_counts.get('cx', 0)
        })
        print('Done with QFT, making now for Toffoli Cascade')
        # --- Process Toffoli Cascade ---
        transpiled_toff = pm_cliff.run(toffoli_circuit)
        toff_counts = transpiled_toff.count_ops()
        
        toffoli_data.append({
            'k_intra': k,
            'Circuit Depth': transpiled_toff.depth(),
            'SWAP Count': toff_counts.get('swap', 0),
            'T Gate Count': toff_counts.get('t', 0) + toff_counts.get('tdg', 0),
            'CX Count': toff_counts.get('cx', 0)
        })
        
    # 3. Compile the DataFrames
    df_qft = pd.DataFrame(qft_data)
    df_toffoli = pd.DataFrame(toffoli_data)
    
    print("\nQFT Benchmark Complete. Results:")
    print(df_qft.to_string(index=False))
    print("\nToffoli Benchmark Complete. Results:")
    print(df_toffoli.to_string(index=False))
    
    # 4. Helper Function to Plot and Save Data
    def plot_and_save(df: pd.DataFrame, title: str, filename: str):
        # Determine layout based on the count_t_gates toggle
        num_cols = 3 if count_t_gates else 2
        fig, axes = plt.subplots(1, num_cols, figsize=(6 * num_cols, 5))
        
        fig.suptitle(title, fontsize=16)
        
        # Plot 1: Circuit Depth
        axes[0].plot(df['k_intra'], df['Circuit Depth'], marker='o', color='b', linewidth=2)
        axes[0].set_title('Circuit Depth')
        axes[0].set_xlabel('Connectivity Distance (k_intra)')
        axes[0].set_ylabel('Depth')
        axes[0].grid(True, linestyle='--', alpha=0.7)
        
        # Plot 2: SWAP Gates
        axes[1].plot(df['k_intra'], df['SWAP Count'], marker='s', color='r', linewidth=2)
        axes[1].set_title('Routing Overhead (SWAP Gates)')
        axes[1].set_xlabel('Connectivity Distance (k_intra)')
        axes[1].set_ylabel('SWAP Count')
        axes[1].grid(True, linestyle='--', alpha=0.7)
        
        # Plot 3 (Optional): T Gates
        if count_t_gates:
            axes[2].plot(df['k_intra'], df['T Gate Count'], marker='^', color='g', linewidth=2)
            axes[2].set_title('T / Tdg Gate Count')
            axes[2].set_xlabel('Connectivity Distance (k_intra)')
            axes[2].set_ylabel('T Count')
            axes[2].grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight') # Saves the figure locally
        plt.show()

    # 5. Generate and save both figures
    plot_and_save(
        df_qft, 
        f'QFT ({total_qubits} Qubits) superconducting metrics', 
        'qft_connectivity_benchmark.png'
    )
    
    plot_and_save(
        df_toffoli, 
        f'Toffoli Cascade ({total_qubits} Qubits) Cllifford + T metrics', 
        'toffoli_connectivity_benchmark.png'
    )
    
    return df_qft, df_toffoli




def test_time_of_optimizer():
    qft_circuit = QFT(num_qubits=100)
    superconducting_basis = ['rz', 'sx', 'x', 'cx', 'id', 'swap', 't']
    clifford_t_basis = ['h', 's', 'cx', 't', 'tdg', 'swap']
    for i in range(1, 3):
        for k in range(0, 101, 10):
            start = time.time()

            if k == 0:
                continue
            cmap = k_nearest_tiled_coupling_map(
                n_blocks_row=2,
                n_blocks_col=2,
                n=10,
                m=10,
                k_intra=k,
                k_inter=i, 
                connector_local=0
            )
            
            pm = generate_preset_pass_manager(
                optimization_level=2, 
                basis_gates=superconducting_basis, 
                coupling_map=cmap
            )
            transpiled_qc = pm.run(qft_circuit)
            print(f"current connectivity: {k}")
            cur_time = time.time() - start
            print(f"Took {cur_time} long!")
            if cur_time > 60:
                print("took longer than a minute...")
                break
    return None


def get_toffoli_cascade(num_qubits: int) -> QuantumCircuit:
    """
    Generates a ladder of Toffoli gates across the entire qubit register.
    This creates an extreme stress test for routing (SWAPs) and fault-tolerant 
    gate synthesis (T gates).
    """
    qc = QuantumCircuit(num_qubits)
    
    # Sweep down the register
    for i in range(num_qubits - 2):
        qc.ccx(i, i+1, i+2)
        
    # Sweep back up the register (adds depth and forces variables back across the chip)
    for i in reversed(range(num_qubits - 2)):
        qc.ccx(i, i+1, i+2)
        
    return qc

if __name__ == "__main__":
    print('running')
    test_time_of_optimizer()
    
    # benchmark_dual_circuits(max_k=10, n_dim=10, m_dim=10)
    
# To run the script:
# Ensure your build_pipeline_coupling_map function is loaded, then call:
# results_df = benchmark_qft_connectivity(max_k=5, n_dim=10, m_dim=10)

# depreciated main call
# def main():
#     config = load_config("src/configs/test.yaml")
#     qasm = export_qasm_stub()
#     counts = count_gates_from_qasm(qasm)
    
#     print("Gate counts:", counts)
