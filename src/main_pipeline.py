# Standard library
from pathlib import Path
import time

# Third-party libraries
import pandas as pd
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.visualization import plot_coupling_map

# Local project imports
from IR.circuit_loader import input_test_circuit, get_toffoli_cascade, get_trotterized_spin_chain
from IR.export_qasm import export_to_qasm
from IR.qasm_ingestor import ingest_qasm_string
from IR.qasm_to_ir import qasm_to_ir
from IR.validate_qasm import validate_qasm
from hardware.connectivity import (
    get_benchmark_coupling_maps,
    load_ibm_fez_coupling_map,
    load_ibm_torino_coupling_map,
    k_nearest_tiled_coupling_map,
)
from target_creation.target import build_dynamic_ft_target



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
    fez_cmap = load_ibm_fez_coupling_map()
    torino_cmap = load_ibm_torino_coupling_map()

    ft_cmap = k_nearest_tiled_coupling_map(
        n_blocks_row=2,
        n_blocks_col=2,
        n=10,
        m=10,
        k_intra=2,
        k_inter=1,
        connector_local=0,
    )

    coupling_maps = {
        "IBM Fez heavy-hex": fez_cmap,
        "IBM Torino heavy-hex": torino_cmap,
        "Custom FT-style tiled k-nearest": ft_cmap,
    }

    basis_gates_by_architecture = {
    "IBM Fez heavy-hex": ["rz", "sx", "x", "cx", "id", "swap"],
    "IBM Torino heavy-hex": ["rz", "sx", "x", "cx", "id", "swap"],
    "Custom FT-style tiled k-nearest": ["h", "s", "sdg", "cx", "t", "tdg", "swap"],
}


    results = []

    for architecture_name, coupling_map in coupling_maps.items():
        basis_gates = basis_gates_by_architecture[architecture_name]
        
        pass_manager = generate_preset_pass_manager(
            optimization_level=2,
            basis_gates=basis_gates,
            coupling_map=coupling_map,
        )


        transpiled_circuit = pass_manager.run(qiskit_circuit)
        counts = transpiled_circuit.count_ops()

        results.append(
            {
                "architecture": architecture_name,
                "physical_qubits": coupling_map.size(),
                "directed_edges": len(coupling_map.get_edges()),
                "input_depth": qiskit_circuit.depth(),
                "input_gates": qiskit_circuit.size(),
                "transpiled_depth": transpiled_circuit.depth(),
                "transpiled_gates": transpiled_circuit.size(),
                "cx_count": counts.get("cx", 0),
                "swap_count": counts.get("swap", 0),
                "t_count": counts.get("t", 0) + counts.get("tdg", 0),
                "basis_gates": ", ".join(basis_gates),
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


## TODO find a better place for this to go
def calculate_circuit_success_chance(transpiled_qc: QuantumCircuit, target) -> float:
    """Calculate overall circuit fidelity based on the specific mapped edges."""
    success_chance = 1.0
    
    for instruction in transpiled_qc.data:
        op_name = instruction.operation.name
        
        # Skip operations that don't have physical error rates
        if op_name in ["barrier", "measure", "delay"]:
            continue
            
        # Get the physical qubit indices this gate was mapped to
        phys_qubits = tuple(transpiled_qc.find_bit(q).index for q in instruction.qubits)
        
        # Retrieve the specific error for this physical gate from our Target
        # The Target object is a nested mapping: target[instruction_name][qargs]
        if op_name in target and phys_qubits in target[op_name]:
            props = target[op_name][phys_qubits]
            
            # props is an InstructionProperties object, which has an .error attribute
            if props and props.error is not None:
                success_chance *= (1 - props.error)
            
    return success_chance

def benchmark_network_degradation(qc: QuantumCircuit):
    results = []

    # 1. Test different cluster layouts (all totaling exactly 900 qubits)
    # Format: (n_blocks_row, n_blocks_col, n, m)
    architectures = [
        (1, 1, 30, 30), # 1 massive computer (900 qubits)
        (3, 3, 10, 10), # 9 connected computers (100 qubits each)
        (5, 5, 6, 6),   # 25 connected computers (36 qubits each)
    ]
    
    # 2. Test Inter-connectiveness (Nearest neighbor vs Next-nearest block connections)
    k_inter_values = [1, 2] 
    
    # 3. Test Inter-connectiveness probabilities (Local error rates inside the blocks)
    inter_cx_errors = [0.05] 



    for (br, bc, n, m) in architectures:
        for k_inter in k_inter_values:
            # Skip k_inter>1 if we only have 1 monolithic block (no network exists)
            if br * bc == 1 and k_inter > 1:
                continue 
            config_name = f"{br*bc}cores_{n}x{m}qubits_kinter{k_inter}"
            for inter_err in inter_cx_errors:
                
                
                print(f"\n--- Evaluating: {config_name}inter{inter_err} ---")
                
                current_time = time.time()
                
                # Build the dynamic Target
                target = build_dynamic_ft_target(
                    n_blocks_row=br, 
                    n_blocks_col=bc,
                    n=n, m=m, 
                    k_intra=1,
                    k_inter=br + bc,
                    intra_cx_error=0.001,
                    inter_cx_error=inter_err
                )
                
                # Draw and save the connectivity map for this specific architecture
                image = target.build_coupling_map().draw()
                image_filename = f"map_{config_name}.png"
                if hasattr(image, "savefig"):
                    image.savefig(image_filename, dpi=300, bbox_inches="tight")
                else:
                    image.save(image_filename)
                
                print("Target and map built. Running level 3 transpiler with ALAP scheduling...")
                
                # Use "alap" scheduling so Qiskit calculates the .duration attribute
                pm = generate_preset_pass_manager(
                    optimization_level=3, 
                    target=target,
                    scheduling_method="alap"
                )
                
                transpiled_qc = pm.run(qc)
                
                transpile_time = time.time() - current_time
                print(f"Transpilation complete in {transpile_time:.2f} seconds.")
                
                # Extract the newly requested metrics
                overall_success = calculate_circuit_success_chance(transpiled_qc, target)
                total_duration_seconds = transpiled_qc.duration
                
                results.append({
                    "architecture": f"{br*bc} computers",
                    "qubits_per_computer": n * m,
                    "k_inter": k_inter,
                    "intra_error_rate": inter_err,
                    "overall_success_chance": overall_success,
                    "duration_seconds": total_duration_seconds,
                    "transpiled_depth": transpiled_qc.depth(),
                    "cx_count": transpiled_qc.count_ops().get("cx", 0),
                    "transpile_time_sec": round(transpile_time, 2)
                })
        
    return results



def main():
    # testing benchmark_network_degradation with the toffoli cascade circuit
    cascade_circuit = get_toffoli_cascade(num_qubits=900) # Using
    results = benchmark_network_degradation(cascade_circuit)
    print("\nNetwork Degradation Benchmark Results:")
    print(pd.DataFrame(results).to_string(index=False))


    # save_connectivity_map_drawings()

    # # qc = build_qiskit_circuit_from_ir()

    # # using toffoli cascade
    # cascade_circuit = get_toffoli_cascade(num_qubits=100)
    # results_df = benchmark_all_connectivity_maps(cascade_circuit)

    # print("\nBenchmark results:")
    # print(results_df.to_string(index=False))

    # plot_and_save(
    #     results_df,
    #     "Ingested Circuit Connectivity Benchmark",
    #     "ingested_circuit_connectivity_benchmark.png",
    #     count_t_gates=True,
    # )



if __name__ == "__main__":
    main()


# def build_cost_weighted_target(coupling_map):
#     target = Target()
    
#     # Add single-qubit gates (assuming perfect/equal cost for all qubits for this example)
#     for gate in [RZGate(), SXGate(), XGate(), IGate()]:
#         target.add_instruction(gate, { (q,): None for q in range(coupling_map.size()) })

#     # Define the two-qubit gate (e.g., CX)
#     cx_properties = {}
    
#     for edge in coupling_map.get_edges():
#         q1, q2 = edge
        
#         # Make the connection between qubit 0 and 1 very costly (e.g., 50% error rate)
#         if (q1, q2) == (0, 1) or (q1, q2) == (1, 0):
#             cx_properties[(q1, q2)] = InstructionProperties(error=0.50)
#         else:
#             # Standard edges get a normal/low cost (e.g., 1% error rate)
#             cx_properties[(q1, q2)] = InstructionProperties(error=0.01)

#     target.add_instruction(CXGate(), cx_properties)
    
#     return target





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

