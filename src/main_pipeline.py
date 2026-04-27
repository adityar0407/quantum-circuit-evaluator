# Standard library
from pathlib import Path
import time
import math

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
from target_creation.target import build_dynamic_ft_target, build_flexible_target
from metrics.metrics_evaluator import calculate_circuit_success_chance, get_total_duration, count_network_operations



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


def compare_architectures(qc: QuantumCircuit, debug: bool = False):
    num_qubits = qc.num_qubits
    results = []


    #code to find all combinations for factors of the given number of qubits. 
    def find_factors_optimized(n):
        factors = set()
        for i in range(1, int(math.sqrt(n)) + 1):
            if n % i == 0:
                factors.add(tuple(sorted((i, n // i))))
                
        return sorted(list(factors))

    if debug:
        computer_types = ['Fault Tolerant']
    else:
        computer_types = ['Superconducting', 'Trapped Ion', 'Neutral Atom', 'Photonic']
    architectures = []
    for n_blocks, n_qubits_per_block in find_factors_optimized(num_qubits):
        n, m = find_factors_optimized(n_qubits_per_block).pop() # Get last pair of factors for the block size
        
        br, bc = find_factors_optimized(n_blocks).pop() # Get last pair of factors for the number of blocks

        # horizontal row of blocks (Shared edge is vertical, length = n)
        if br == 1 and bc > 1:
            if n < m:
                n, m = m, n  # Swap so the taller side (n) handles the connections
                
        # Vertical column of blocks (Shared edge is horizontal, length = m)
        elif bc == 1 and br > 1:
            if m < n:
                n, m = m, n  # Swap so the wider side (m) handles the connections

    
        architectures.append((br, bc, n, m))
        
    for (br, bc , n , m) in architectures:
        for arch_type in computer_types:
            block_name = f"{arch_type}_{br*bc}cores_{n}x{m}qubits"
            print(f"\n--- Evaluating {arch_type} architecture with {br*bc} blocks of size {n}x{m} ---")
            cur_time = time.time()
            target = build_flexible_target(
                arch_type=arch_type,
                n_blocks_row=br,
                n_blocks_col=bc,
                n=n,
                m=m,
                k_intra= None, 
                k_inter=2, #2nd nearest_neighbor inter-block connectivity 
                connector_local=2, #connect the 3rd qubit in each block for inter-block connectivity
            )

            image = target.build_coupling_map().draw()
            image_filename = f"map_{block_name}.png"
            if hasattr(image, "savefig"):
                image.savefig(image_filename, dpi=300, bbox_inches="tight")
            else:
                image.save(image_filename)
            
            pm = generate_preset_pass_manager(
                optimization_level=3, 
                target=target,
                scheduling_method="alap"
            )
            
            transpiled_qc = pm.run(qc)
            transpile_time = time.time() - cur_time
            print(f"Transpilation complete in {transpile_time:.2f} seconds.")
            overall_success = calculate_circuit_success_chance(transpiled_qc, target)
            total_duration_seconds = get_total_duration(transpiled_qc)

            two_q_gate_counts = count_network_operations(transpiled_qc, n, m)
            shots_for_success = int(1 / overall_success) if overall_success > 0 else float('inf')

            results.append({
                "architecture": f"{arch_type} computers",
                "qubits_per_computer": n * m,
                "total_computers": br*bc,
                "overall_success_chance": overall_success,
                "shots_for_success": shots_for_success,
                "duration_seconds": total_duration_seconds,
                "time_for_success_sec": total_duration_seconds * shots_for_success if overall_success > 0 else float('inf'),
                "transpiled_depth": transpiled_qc.depth(),
                "total_two_qubit_gates": two_q_gate_counts["total_2q_gates"],
                "inter_block_gates": two_q_gate_counts["inter_block_gates"],
                "transpile_time_sec": round(transpile_time, 2)
            })

            
    return pd.DataFrame(results)




    


def main():
    # testing the iterative block code creation
    cascade_circuit = get_toffoli_cascade(num_qubits=100) # Using the Toffoli cascade circuit as a test case for the architecture comparison

    compare_results = compare_architectures(cascade_circuit)
    compare_results.to_csv("architecture_comparison_results_sabre.csv", index=False)

    

    
  



if __name__ == "__main__":
    main()


