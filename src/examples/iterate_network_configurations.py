## old code

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import time
import math
import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

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
                        'sq_err': 1e-5, 'sq_dur': 1e-6, 'intra_err': 7e-4, 'intra_dur': 2e-6,
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
        
    os.makedirs("example_1", exist_ok=True)

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
                image = target.plot(filename=f"example_1/map_{arch_type.replace(' ', '_')}_{layout_name}.png")

            # Transpile Circuit
            pm = generate_preset_pass_manager(optimization_level=3, target=target, scheduling_method="alap", seed_transpiler=1738)
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
                    "Time till successful run": total_duration / overall_success, 
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
    plot_path = "example_1/architecture_comparison_summary.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\nSummary plots saved to: {plot_path}")
    plt.show()

def plot_best_time_to_success(df: pd.DataFrame):
    """
    Calculates the expected time to a successful run in days and 
    plots the best (minimum) time for each architecture.
    """
    if df.empty:
        return

    # Calculate Expected Time to Success (in seconds)
    # If success chance is 0, the expected time is effectively infinity
    df['Expected Time (s)'] = np.where(
        df['Success Chance'] > 0,
        df['Duration (s)'] / df['Success Chance'],
        np.inf
    )

    # Convert to days (86,400 seconds in a day)
    df['Expected Time (years)'] = df['Expected Time (s)'] / (86400 * 365)

    # Group by architecture to find the absolute minimum expected time
    best_times = df.groupby('Architecture')['Expected Time (years)'].min().reset_index()

    # Filter out architectures that never succeeded (Time = inf)
    best_times = best_times[best_times['Expected Time (years)'] != np.inf]

    if best_times.empty:
        print("No architectures had a success chance > 0. Cannot plot time to success.")
        return

    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Create the bar chart
    bars = ax.bar(best_times['Architecture'], best_times['Expected Time (years)'], color='mediumpurple', edgecolor='black')
    
    ax.set_title('Absolute Best Time to Successful Run by Architecture', fontsize=14, fontweight='bold')
    ax.set_ylabel('Expected Time (years))', fontsize=12, fontweight='bold')
    ax.set_xlabel('Architecture', fontsize=12, fontweight='bold')
    
    # Use a logarithmic scale since the difference between Photonic (fractions of a second) 
    # and Superconducting (could be days) will be massive
    ax.set_yscale('log')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Add text labels on top of the bars for easy reading
    for bar in bars:
        yval = bar.get_height()
        # Format the text depending on how large the number is
        if yval < 0.01:
            label = f"{yval:.1e} years"
        else:
            label = f"{yval:.2f} years"
            
        ax.text(bar.get_x() + bar.get_width()/2, yval * 1.2, label, ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    
    # Save the plot
    os.makedirs("example_1", exist_ok=True)
    plot_path = "example_1/best_time_to_success.png"
    plt.savefig(plot_path, dpi=300)
    print(f"Best Time to Success plot saved to: {plot_path}")
    plt.show()
    

# --- Example Usage ---
# from qiskit.circuit.random import random_circuit
# test_qc = random_circuit(num_qubits=64, depth=10, measure=True)
# df_results = compare_architectures(test_qc, debug=False)
# print(df_results.to_string())
# compare_arch(df_results)


from target_creation.target import FTarget
from metrics.metrics_evaluator import (
    count_network_operations, 
    calculate_circuit_success_chance, 
    get_total_duration
)

def get_grid_dimensions(num_qubits):
    """Finds the most square-like grid dimensions for the network blocks."""
    factors = []
    for i in range(1, int(math.sqrt(num_qubits)) + 1):
        if num_qubits % i == 0:
            factors.append((i, num_qubits // i))
    # Return the most square-like factor pair
    return factors[-1]


def fault_tolerant_example(qc: QuantumCircuit):
    """
    Benchmarks a circuit on a distributed fault-tolerant architecture,
    demonstrating how photonic interconnect limits throttle QEC scaling.
    """
    # Baseline physical error assumptions
    p_phys = 1e-3
    p_th = 1e-2
    t_cycle = 1e-6
    distance = 1
    # The Photonic Bottleneck (Static / Idealized limit)
    photonic_link_err = 5e-3   # 0.5% error per network entanglement
    photonic_link_dur = 50e-6  # 50 microseconds per network routing

    topologies = [
        {
            "type": "tiled_k_nearest",
            "n_blocks_row": 1,
            "n_blocks_col": 1,
            "n": 10, "m": 10,  
            "k_intra": 1, "k_inter": 1, "connector_local": 1
        }, {
            "type": "tiled_k_nearest",
            "n_blocks_row": 2,
            "n_blocks_col": 2,
            "n": 5, "m": 5,  
            "k_intra": 1, "k_inter": 1, "connector_local": 1
        }
    ]

    for x in topologies:
        results = [] # FIX 3: Reset the results list for each topology to prevent zig-zag plots
        while True:
            distance += 2
            if distance > 30:
                break
            # Calculate exponentially suppressed LOCAL logical errors
            p_L_local = 0.1 * (p_phys / p_th)**((distance + 1) / 2)
            t_L_local = distance * t_cycle

            config = {
                "topology": x,
                "profile": {
                    "sq_gates": ["RZGate", "SXGate", "XGate"],
                    "two_q_gates": ["CXGate"],
                    "sq_err": p_L_local,
                    "sq_dur": t_L_local,
                    "intra_err": p_L_local * 1.5, 
                    "intra_dur": t_L_local * 2,
                    "inter_err": photonic_link_err,
                    "inter_dur": photonic_link_dur
                }
            }
            
            name = str(x["n_blocks_row"] * x['n_blocks_col'])
            target = FTarget(config)
            pm = generate_preset_pass_manager(optimization_level=3, target=target, scheduling_method="alap", seed_transpiler=1738)
            
            try:
                transpiled_qc = pm.run(qc)
                
                success_chance = calculate_circuit_success_chance(transpiled_qc, target)
                total_duration = get_total_duration(transpiled_qc)
                
                # FIX 2: Pass dynamic block dimensions to the counting function
                net_ops = count_network_operations(transpiled_qc, x["n"], x["m"]) 
                
                results.append({
                    "Distance (d)": distance,
                    "Local 2Q Error": p_L_local * 1.5,
                    "Success Chance": success_chance,
                    "Total Duration (s)": total_duration,
                    "Network Gates": net_ops["inter_block_gates"]
                })
                print(f"Topology {name} Blocks | d={distance:02d} | Success: {success_chance:6.2%} | Duration: {total_duration:.2e}s")
            except Exception as e:
                print(f"Transpilation failed for d={distance} on topology {name}: {e}")

            if abs(success_chance - 1) < 0.01:
                break

        # Plot exactly once per topology
        df = pd.DataFrame(results)
        plot_photonic_bottleneck(df, photonic_link_err, name)

    return None





def plot_photonic_bottleneck(df: pd.DataFrame, photonic_err: float, network: str):
    """Visualizes how the photonic network caps the maximum circuit success."""
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(df['Distance (d)'], df['Success Chance'], marker='o', color='indigo', linewidth=2, label="Circuit Success Probability")
    
    # Calculate the theoretical maximum success based ONLY on the network gates
    # This proves the local logical qubits became virtually perfect, but the network dragged it down.
    if df['Network Gates'].iloc[-1] > 0:
        theoretical_cap = (1 - photonic_err) ** df['Network Gates'].iloc[-1]
        ax.axhline(y=theoretical_cap, color='red', linestyle='--', linewidth=2, label=f"Photonic Network Ceiling ({theoretical_cap:.2%})")

    ax.set_xlabel('Surface Code Distance (d)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Probability', fontsize=12, fontweight='bold')
    ax.set_title('The Photonic Bottleneck in Distributed FT Quantum Computing', fontsize=14)
    ax.set_xticks(df['Distance (d)'])
    ax.set_ylim(0, max(df['Success Chance'] + 0.01))
    ax.legend(loc="lower right")
    ax.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    os.makedirs("example_3", exist_ok=True)
    plt.savefig(f"example_3/photonic_bottleneck_{network}.png", dpi=300)
    plt.show()

