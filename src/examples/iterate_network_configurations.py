## old code

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import time
import math
import pandas as pd
import matplotlib.pyplot as plt
import os

# Assuming these are available in your project structure
from target_creation.target import FTarget
from metrics.metrics_evaluator import (
    count_network_operations, 
    calculate_circuit_success_chance, 
    get_total_duration
)

def find_factors_optimized(num):
    """Returns sorted pairs of factors for a given number."""
    factors = set()
    for i in range(1, int(math.sqrt(num)) + 1):
        if num % i == 0:
            factors.add(tuple(sorted((i, num // i))))
    return sorted(list(factors))

def compare_architectures_example(qc: QuantumCircuit, debug: bool = False):
    num_qubits = qc.num_qubits
    results = []

    # 1. Base Profiles defined explicitly
    base_profiles = {

        # using a photonic link at state of the art levels say over very small distance
        'Superconducting': {
            'type': 'tiled_k_nearest', 'k_intra': 1, 'k_inter': 1, 'connector_local': 1,
            'profile': {'sq_gates': ["RZGate", "SXGate", "XGate"], 'two_q_gates': ["CXGate"], 
                        'sq_err': 1e-5, 'sq_dur': 50e-9, 'intra_err': 2e-3, 'intra_dur': 25e-9,
            'inter_err': 5e-2, 'inter_dur': 5e-11}
        },
        'Trapped Ion': {
            'type': 'tiled_k_nearest', 'k_intra': num_qubits, 'k_inter': 1, 'connector_local': 1, # k_intra > block size for all-to-all
            'profile': {'sq_gates': ["RXGate", "RYGate", "RZGate"], 'two_q_gates': ["CXGate"], 
                        'sq_err': 1e-5, 'sq_dur': 10e-6, 'intra_err': 5e-4, 'intra_dur': 100e-6,
            'inter_err': 5e-2, 'inter_dur': 5e-11}
        },
        'Neutral Atom': {
            'type': 'tiled_k_nearest', 'k_intra': num_qubits, 'k_inter': 1, 'connector_local': 1,
            'profile': {'sq_gates': ["RXGate", "RYGate", "RZGate"], 'two_q_gates': ["CZGate"], 
                        'sq_err': 1e-4, 'sq_dur': 1e-6, 'intra_err': 7e-4, 'intra_dur': 2e-6,
            'inter_err': 5e-2, 'inter_dur': 5e-11}
        },
        'Photonic': {
            'type': 'tiled_k_nearest', 'k_intra': 1, 'k_inter': 1, 'connector_local': 1,
            'profile': {'sq_gates': ["RZGate", "HGate"], 'two_q_gates': ["CZGate"], 
                        'sq_err': 1e-5, 'sq_dur': 1e-12, 'intra_err': 1e-1, 'intra_dur': 1e-11,
            'inter_err': 5e-2, 'inter_dur': 5e-11}
        }
    }
    print('running example with following profiles:')
    print(pd.DataFrame(base_profiles))

    # 2. Get Layout Factors
    factor_list = find_factors_optimized(num_qubits)
    
    # We want a high number of qubits broken into blocks. 
    # Skipping the first 2 factors (e.g. 1xN, 2x(N/2)) to force network routing.
    # If the circuit is too small, fallback to whatever we have.
    start_idx = 2 if len(factor_list) > 3 else (len(factor_list) - 1)
    selected_block_factors = factor_list[start_idx:]

    architectures = []
    for n_blocks, n_qubits_per_block in selected_block_factors:
        # Get the most "square" factor for the internal qubits
        n, m = find_factors_optimized(n_qubits_per_block).pop() 
        # Get the most "square" factor for the block layout itself
        br, bc = find_factors_optimized(n_blocks).pop() 

        # Rotate matrices for better network connections
        if br == 1 and bc > 1 and n < m:
            n, m = m, n
        elif bc == 1 and br > 1 and m < n:
            n, m = m, n

        architectures.append((br, bc, n, m))
        
    os.makedirs("example_2", exist_ok=True)

    # 3. Transpile and Evaluate
    for (br, bc, n, m) in architectures:
        for arch_type, base_config in base_profiles.items():
            layout_name = f"{br*bc}cores_{n}x{m}q"
            print(f"\n--- Evaluating {arch_type} ({layout_name}) ---")
            
            # Dynamically build the config dictionary for FTarget
            config = {
                "topology": {
                    "type": base_config["type"],
                    "n_blocks_row": br,
                    "n_blocks_col": bc,
                    "n": n,
                    "m": m,
                    "k_intra": base_config["k_intra"],
                    "k_inter": base_config["k_inter"],
                    "connector_local": base_config["connector_local"]
                },
                "profile": base_config["profile"],
            }

            cur_time = time.time()
            target = FTarget(config)

            # Optional: Save Map Plot
            if debug:
                image = target.plot(filename=f"example_2/map_{arch_type.replace(' ', '_')}_{layout_name}.png")

            # Transpile Circuit
            pm = generate_preset_pass_manager(optimization_level=3, target=target, scheduling_method="alap")
            try:
                transpiled_qc = pm.run(qc)
                transpile_time = time.time() - cur_time
                print(f"Transpilation complete in {transpile_time:.2f} seconds.")
                
                # Metrics
                overall_success = calculate_circuit_success_chance(transpiled_qc, target)
                total_duration = get_total_duration(transpiled_qc)
                two_q_counts = count_network_operations(transpiled_qc, n, m)
                
                results.append({
                    "Architecture": arch_type,
                    "Layout": layout_name,
                    "Total Blocks": br*bc,
                    "Qubits/Block": n*m,
                    "Success Chance": overall_success,
                    "Duration (s)": total_duration,
                    "Depth": transpiled_qc.depth(),
                    "Total 2Q Gates": two_q_counts["total_2q_gates"],
                    "Network (Inter-block) Gates": two_q_counts["inter_block_gates"],
                    "Transpile Time (s)": round(transpile_time, 2)
                })
            except Exception as e:
                print(f"Transpilation failed for {arch_type} {layout_name}: {e}")

    return pd.DataFrame(results)

def compare_arch(df: pd.DataFrame):
    """Generates comparative plots based on the benchmarking DataFrame."""
    if df.empty:
        print("No data to plot.")
        return

    # Create a unified label for the x-axis
    df['Label'] = df['Architecture'] + "\n(" + df['Layout'] + ")"
    
    # Setup subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Distributed Quantum Architecture Benchmarking', fontsize=18, fontweight='bold')

    # 1. Success Chance
    ax = axes[0, 0]
    bars = ax.bar(df['Label'], df['Success Chance'], color='skyblue')
    ax.set_title('Overall Circuit Success Probability', fontsize=14)
    ax.set_ylabel('Probability')
    ax.tick_params(axis='x', rotation=45)
    ax.set_yscale('log') # Log scale is usually better for fidelity

    # 2. Duration
    ax = axes[0, 1]
    ax.bar(df['Label'], df['Duration (s)'], color='lightcoral')
    ax.set_title('Total Execution Duration (Seconds)', fontsize=14)
    ax.set_ylabel('Time (s)')
    ax.tick_params(axis='x', rotation=45)
    ax.set_yscale('log') 

    # 3. Transpiled Depth
    ax = axes[1, 0]
    ax.bar(df['Label'], df['Depth'], color='lightgreen')
    ax.set_title('Transpiled Circuit Depth', fontsize=14)
    ax.set_ylabel('Depth Count')
    ax.tick_params(axis='x', rotation=45)

    # 4. Network Gates vs Total 2Q Gates (Stacked/Overlay)
    ax = axes[1, 1]
    ax.bar(df['Label'], df['Total 2Q Gates'], color='lightgray', label='Total 2Q Gates')
    ax.bar(df['Label'], df['Network (Inter-block) Gates'], color='orange', label='Network Gates')
    ax.set_title('Network Overhead (Inter-block vs Total 2Q)', fontsize=14)
    ax.set_ylabel('Gate Count')
    ax.legend()
    ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plot_path = "example_2/architecture_comparison_summary.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\nSummary plots saved to: {plot_path}")
    plt.show()

# --- Example Usage ---
# from qiskit.circuit.random import random_circuit
# test_qc = random_circuit(num_qubits=64, depth=10, measure=True)
# df_results = compare_architectures(test_qc, debug=False)
# print(df_results.to_string())
# compare_arch(df_results)

def fault_tolerant_example(Circuit: QuantumCircuit):
    pass




def compile_ft_circuits():
    pass