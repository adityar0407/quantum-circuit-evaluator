from pathlib import Path

# Third-party libraries
import pandas as pd
from qiskit import QuantumCircuit

# Local project imports
from IR.circuit_loader import input_test_circuit
from IR.export_qasm import export_to_qasm
from IR.qasm_ingestor import ingest_qasm_string
from IR.qasm_to_ir import qasm_to_ir
from IR.validate_qasm import validate_qasm
from hardware.architecture_profiles import get_benchmark_architecture_profiles
from hardware.connectivity import get_benchmark_coupling_maps
from metrics.metrics_evaluator import evaluate_circuit_metrics
from pass_managers.cost_eval import create_gate_cost_evaluator
from pass_managers.initializer import get_init_pm
from pass_managers.layout_n_routing import get_layout_routing_pm
from pass_managers.optimizer import get_optimization_pm
from pass_managers.translator import get_translation_pm
from target_creation.target import get_benchmark_target


# Initialize and build circuit
def build_qiskit_circuit_from_ir() -> QuantumCircuit:
    """Build the test circuit through the PennyLane -> QASM -> Qiskit IR flow."""
    
    # Build the circuit from pennylane 
    pl_circuit = input_test_circuit()
    
    # Generate QASM string 
    qasm_string = export_to_qasm(pl_circuit)
    qasm_string = ingest_qasm_string(qasm_string)
    
    # Optional check before converting to Qiskit
    is_valid, result = validate_qasm(qasm_string)
    if not is_valid:
        raise ValueError(f"Invalid QASM: {result}")
    
    # Convert QASM to Qiskit IR
    qc = qasm_to_ir(qasm_string)

    print("QASM string:")
    print(qasm_string)
    print("\nQiskit circuit:")
    print(qc)

    return qc


# Build all connectivity maps 
def benchmark_all_connectivity_maps(qiskit_circuit: QuantumCircuit) -> pd.DataFrame:
    """
    Benchmark the same logical circuit on IBM Fez, IBM Torino, and the custom
    FT-style k-nearest tiled map.
    """
    architectures = get_benchmark_architecture_profiles()

    results = []

    for architecture in architectures:
        coupling_map = architecture.coupling_map
        target_data = get_benchmark_target(
            architecture.profile,
            num_qubits=coupling_map.size(),
            coupling_map=coupling_map,
            backend_name=architecture.backend_name,
            fallback_basis_gates=architecture.fallback_basis_gates,
        )
        target = target_data.target
        basis_gates = target_data.basis_gates
        cost_evaluator = create_gate_cost_evaluator(
            gate_weights=architecture.gate_weights,
            depth_weight=architecture.depth_weight,
            unmapped_gate_penalty=architecture.unmapped_gate_penalty,
        )

        transpiled_circuit = get_init_pm(basis_gates).run(qiskit_circuit)
        transpiled_circuit = get_layout_routing_pm(coupling_map).run(transpiled_circuit)
        transpiled_circuit = get_translation_pm(
            architecture.profile,
            basis_gates=basis_gates,
        ).run(transpiled_circuit)
        transpiled_circuit = get_optimization_pm().run(transpiled_circuit)
        counts = transpiled_circuit.count_ops()
        target_metrics = evaluate_circuit_metrics(
            transpiled_circuit,
            target,
        )

        results.append(
            {
                "architecture": architecture.name,
                "physical_qubits": coupling_map.size(),
                "directed_edges": len(coupling_map.get_edges()),
                "input_depth": qiskit_circuit.depth(),
                "input_gates": qiskit_circuit.size(),
                "transpiled_depth": transpiled_circuit.depth(),
                "transpiled_gates": transpiled_circuit.size(),
                "model_weighted_score": cost_evaluator(transpiled_circuit),
                "cost_model_source": architecture.cost_model_source,
                "independent_error_success_proxy": (
                    target_metrics.independent_error_success_proxy
                ),
                "scheduled_duration_estimate_seconds": (
                    target_metrics.scheduled_duration_estimate_seconds
                ),
                "missing_error_data_count": target_metrics.missing_error_data_count,
                "missing_duration_data_count": target_metrics.missing_duration_data_count,
                "unsupported_operation_count": target_metrics.unsupported_operation_count,
                "cx_count": counts.get("cx", 0),
                "swap_count": counts.get("swap", 0),
                "t_count": counts.get("t", 0) + counts.get("tdg", 0),
                "basis_gates": ", ".join(basis_gates),
                "target_source": target_data.target_source,
                "pass_manager": "local pass managers",
            }
        )

    return pd.DataFrame(results)


# Draw the connectivity maps
def save_connectivity_map_drawings():
    """
    Draw and save all benchmark connectivity maps.

    Saves:
    - IBM Fez heavy-hex
    - IBM Torino heavy-hex
    - Custom FT-style tiled k-nearest
    """
    coupling_maps = get_benchmark_coupling_maps()

    output_dir = Path(__file__).resolve().parent / "metrics"
    output_dir.mkdir(parents=True, exist_ok=True)

    for architecture_name, coupling_map in coupling_maps.items():
        import matplotlib.pyplot as plt

        safe_name = (
            architecture_name.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        filename = output_dir / f"{safe_name}_connectivity.png"

        print(f"Drawing {architecture_name} connectivity map...")
        print("Total qubits:", coupling_map.size())
        print("Total directed edges:", len(coupling_map.get_edges()))
        print("Is connected:", coupling_map.is_connected())

        image = coupling_map.draw()

        if hasattr(image, "savefig"):
            image.savefig(filename, dpi=300, bbox_inches="tight")
        else:
            image.save(filename)

        print(f"Saved connectivity map to: {filename}")
        print()

# Plots
def plot_and_save(
    df: pd.DataFrame,
    title: str,
    filename: str,
    count_t_gates: bool = False,
):
    import matplotlib.pyplot as plt

    num_cols = 3 if count_t_gates else 2
    fig, axes = plt.subplots(1, num_cols, figsize=(6 * num_cols, 5))

    fig.suptitle(title, fontsize=16)

    axes[0].bar(df["architecture"], df["transpiled_depth"])
    axes[0].set_title("Circuit Depth")
    axes[0].set_xlabel("Architecture")
    axes[0].set_ylabel("Depth")
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].grid(True, axis="y", linestyle="--", alpha=0.7)

    axes[1].bar(df["architecture"], df["swap_count"])
    axes[1].set_title("Routing Overhead (SWAP Gates)")
    axes[1].set_xlabel("Architecture")
    axes[1].set_ylabel("SWAP Count")
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.7)

    if count_t_gates:
        axes[2].bar(df["architecture"], df["t_count"])
        axes[2].set_title("T / Tdg Gate Count")
        axes[2].set_xlabel("Architecture")
        axes[2].set_ylabel("T Count")
        axes[2].tick_params(axis="x", rotation=25)
        axes[2].grid(True, axis="y", linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()


def main():
    save_connectivity_map_drawings()

    qc = build_qiskit_circuit_from_ir()

    results_df = benchmark_all_connectivity_maps(qc)

    print("\nBenchmark results:")
    print(results_df.to_string(index=False))

    plot_and_save(
        results_df,
        "Ingested Circuit Connectivity Benchmark",
        "ingested_circuit_connectivity_benchmark.png",
        count_t_gates=True,
    )


if __name__ == "__main__":
    main()








## def test_case():
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





# ## this is code for a basic k-connected quantum computer, next is to iterate by different connectivity mapping configurations on potential interconnected FTQC designs
# def benchmark_dual_circuits(
#     max_k: int = 5, 
#     n_dim: int = 10, 
#     m_dim: int = 10, 
#     count_t_gates: bool = False
# ):
#     """
#     Benchmarks both QFT and Toffoli Cascade circuits mapped to a specific 
#     architecture across varying levels of qubit connectivity.
    
#     Args:
#         max_k: The maximum intra-block distance (k_intra) to test.
#         n_dim: The number of rows in the single block (default 10 for 100 qubits).
#         m_dim: The number of cols in the single block (default 10 for 100 qubits).
#         count_t_gates: If True, adds a third plot to track T and Tdg gate counts.
        
#     Returns:
#         A tuple of pandas DataFrames: (qft_dataframe, toffoli_dataframe).
#     """
#     total_qubits = n_dim * m_dim
#     qft_data = []
#     toffoli_data = []
    
#     clifford_t_basis = ['h', 's', 'cx', 't', 'tdg', 'swap']
#     superconducting_basis = ['rz', 'sx', 'x', 'cx', 'id', 'swap', 't']

#     # 1. Create the base circuits
#     print(f"Generating {total_qubits}-qubit circuits...")
#     qft_circuit = QFT(num_qubits=total_qubits)
#     toffoli_circuit = get_toffoli_cascade(total_qubits)
    
#     # 2. Iterate through connectivity ranges
#     for k in range(2, max_k + 1):
#         print(f"--- Benchmarking Level 2 Transpilation for k_intra = {k} ---")
        
#         # Build the map for a single block
#         cmap = k_nearest_tiled_coupling_map(
#             n_blocks_row=1,
#             n_blocks_col=1,
#             n=n_dim,
#             m=m_dim,
#             k_intra=k,
#             k_inter=1, 
#             connector_local=0
#         )
#         print('Made CMAP')
#         # Generate the Level 2 Pass Manager
#         pm_cliff = generate_preset_pass_manager(
#             optimization_level=2, 
#             basis_gates=clifford_t_basis, 
#             coupling_map=cmap
#         )
#         pm_super = generate_preset_pass_manager(
#             optimization_level=2, 
#             basis_gates=superconducting_basis, 
#             coupling_map=cmap
#         )
#         print('Made pass manager, running on QFT')
#         # --- Process QFT ---

#         transpiled_qft = pm_super.run(qft_circuit)
#         qft_counts = transpiled_qft.count_ops()
        
#         qft_data.append({
#             'k_intra': k,
#             'Circuit Depth': transpiled_qft.depth(),
#             'SWAP Count': qft_counts.get('swap', 0),
#             'T Gate Count': qft_counts.get('t', 0) + qft_counts.get('tdg', 0),
#             'CX Count': qft_counts.get('cx', 0)
#         })
#         print('Done with QFT, making now for Toffoli Cascade')
#         # --- Process Toffoli Cascade ---
#         transpiled_toff = pm_cliff.run(toffoli_circuit)
#         toff_counts = transpiled_toff.count_ops()
        
#         toffoli_data.append({
#             'k_intra': k,
#             'Circuit Depth': transpiled_toff.depth(),
#             'SWAP Count': toff_counts.get('swap', 0),
#             'T Gate Count': toff_counts.get('t', 0) + toff_counts.get('tdg', 0),
#             'CX Count': toff_counts.get('cx', 0)
#         })
        
#     # 3. Compile the DataFrames
#     df_qft = pd.DataFrame(qft_data)
#     df_toffoli = pd.DataFrame(toffoli_data)
    
#     print("\nQFT Benchmark Complete. Results:")
#     print(df_qft.to_string(index=False))
#     print("\nToffoli Benchmark Complete. Results:")
#     print(df_toffoli.to_string(index=False))
    
#     # 4. Helper Function to Plot and Save Data
#     def plot_and_save(df: pd.DataFrame, title: str, filename: str):
#         # Determine layout based on the count_t_gates toggle
#         num_cols = 3 if count_t_gates else 2
#         fig, axes = plt.subplots(1, num_cols, figsize=(6 * num_cols, 5))
        
#         fig.suptitle(title, fontsize=16)
        
#         # Plot 1: Circuit Depth
#         axes[0].plot(df['k_intra'], df['Circuit Depth'], marker='o', color='b', linewidth=2)
#         axes[0].set_title('Circuit Depth')
#         axes[0].set_xlabel('Connectivity Distance (k_intra)')
#         axes[0].set_ylabel('Depth')
#         axes[0].grid(True, linestyle='--', alpha=0.7)
        
#         # Plot 2: SWAP Gates
#         axes[1].plot(df['k_intra'], df['SWAP Count'], marker='s', color='r', linewidth=2)
#         axes[1].set_title('Routing Overhead (SWAP Gates)')
#         axes[1].set_xlabel('Connectivity Distance (k_intra)')
#         axes[1].set_ylabel('SWAP Count')
#         axes[1].grid(True, linestyle='--', alpha=0.7)
        
#         # Plot 3 (Optional): T Gates
#         if count_t_gates:
#             axes[2].plot(df['k_intra'], df['T Gate Count'], marker='^', color='g', linewidth=2)
#             axes[2].set_title('T / Tdg Gate Count')
#             axes[2].set_xlabel('Connectivity Distance (k_intra)')
#             axes[2].set_ylabel('T Count')
#             axes[2].grid(True, linestyle='--', alpha=0.7)
        
#         plt.tight_layout()
#         plt.savefig(filename, dpi=300, bbox_inches='tight') # Saves the figure locally
#         plt.show()

#     # 5. Generate and save both figures
#     plot_and_save(
#         df_qft, 
#         f'QFT ({total_qubits} Qubits) superconducting metrics', 
#         'qft_connectivity_benchmark.png'
#     )
    
#     plot_and_save(
#         df_toffoli, 
#         f'Toffoli Cascade ({total_qubits} Qubits) Cllifford + T metrics', 
#         'toffoli_connectivity_benchmark.png'
#     )
    
#     return df_qft, df_toffoli




# def test_time_of_optimizer():
#     qft_circuit = QFT(num_qubits=100)
#     superconducting_basis = ['rz', 'sx', 'x', 'cx', 'id', 'swap', 't']
#     clifford_t_basis = ['h', 's', 'cx', 't', 'tdg', 'swap']
#     for i in range(1, 3):
#         for k in range(0, 101, 10):
#             start = time.time()

#             if k == 0:
#                 continue
#             cmap = k_nearest_tiled_coupling_map(
#                 n_blocks_row=2,
#                 n_blocks_col=2,
#                 n=10,
#                 m=10,
#                 k_intra=k,
#                 k_inter=i, 
#                 connector_local=0
#             )
            
#             pm = generate_preset_pass_manager(
#                 optimization_level=2, 
#                 basis_gates=superconducting_basis, 
#                 coupling_map=cmap
#             )
#             transpiled_qc = pm.run(qft_circuit)
#             print(f"current connectivity: {k}")
#             cur_time = time.time() - start
#             print(f"Took {cur_time} long!")
#             if cur_time > 60:
#                 print("took longer than a minute...")
#                 break
#     return None


# def get_toffoli_cascade(num_qubits: int) -> QuantumCircuit:
#     """
#     Generates a ladder of Toffoli gates across the entire qubit register.
#     This creates an extreme stress test for routing (SWAPs) and fault-tolerant 
#     gate synthesis (T gates).
#     """
#     qc = QuantumCircuit(num_qubits)
    
#     # Sweep down the register
#     for i in range(num_qubits - 2):
#         qc.ccx(i, i+1, i+2)
        
#     # Sweep back up the register (adds depth and forces variables back across the chip)
#     for i in reversed(range(num_qubits - 2)):
#         qc.ccx(i, i+1, i+2)
        
#     return qc

# if __name__ == "__main__":
#     print('running')
#     test_time_of_optimizer()
    
    # benchmark_dual_circuits(max_k=10, n_dim=10, m_dim=10)
    
# To run the script:
# Ensure your build_pipeline_coupling_map function is loaded, then call:
# results_df = benchmark_qft_connectivity(max_k=5, n_dim=10, m_dim=10)
