import time
import os
import math
import pandas as pd
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from target_creation.target import FTarget
from metrics.metrics_evaluator import calculate_circuit_success_chance, get_total_duration

def calculate_logical_profile(d: int, p_phys: float = 1e-3, p_th: float = 1e-2, t_cycle: float = 1e-6):
    """
    "Following standard surface code resource estimation methodologies 
    [Fowler et al., 2012; Litinski, 2019], we model the logical error rate of our target blocks as an exponential decay 
    with respect to code distance, while bounding logical gate duration by the O(d) 
    syndrome cycles required for lattice surgery."
    """
    # Exponential suppression of errors
    logical_err = 0.1 * (p_phys / p_th)**((d + 1) / 2)
    
    # Lattice surgery / syndrome extraction takes d cycles
    logical_dur = d * t_cycle
    
    return logical_err, logical_dur

def study_code_distance_scaling(logical_qc: QuantumCircuit, distances: list = [3, 5, 7, 9, 11]):
    results = []
    num_logical_qubits = logical_qc.num_qubits
    
    # Let's arrange our logical blocks in a simple row/grid for the macroscopic network
    # We use 1x1 size for n and m because the node IS the logical qubit now.
    bc = num_logical_qubits
    br = 1 

    print(f"\n--- Studying Surface Code Scaling for {num_logical_qubits} Logical Qubits ---")

    for d in distances:
        # 1. Calculate the FT metrics for this specific distance
        p_L, t_L = calculate_logical_profile(d)
        
        # 2. Build the Logical FTarget
        # Here, the topology represents the routing BETWEEN logical blocks.
        config = {
            "topology": {
                "type": "tiled_k_nearest", # A standard grid of blocks
                "n_blocks_row": br,
                "n_blocks_col": bc,
                "n": 1, # 1 logical node per block representation
                "m": 1,
                "k_intra": 1,
                "k_inter": 1,
                "connector_local": 1
            },
            "profile": {
                "sq_gates": ["RZGate", "SXGate", "XGate"],
                "two_q_gates": ["CXGate"],
                "sq_err": p_L,          # Updated based on d
                "sq_dur": t_L,          # Updated based on d
                "intra_err": p_L * 1.5, # Assume local logical 2Q gates are slightly worse
                "intra_dur": t_L * 2,
                "inter_err": p_L * 5,    
                "inter_dur": t_L * 10
            }
        }

        target = FTarget(config)
        pm = generate_preset_pass_manager(optimization_level=3, target=target, scheduling_method="alap", seed_transpiler=1738)
        
        try:
            transpiled_qc = pm.run(logical_qc)
            
            # Extract your metrics
            success_chance = calculate_circuit_success_chance(transpiled_qc, target)
            total_duration = get_total_duration(transpiled_qc)
            
            results.append({
                "Distance (d)": d,
                "Logical Error / Gate": p_L,
                "Logical Gate Time (s)": t_L,
                "Success Chance": success_chance,
                "Total Duration (s)": total_duration
            })
            print(f"d={d} -> Success: {success_chance:.2%}, Duration: {total_duration:.2e} s")
            
        except Exception as e:
            print(f"Transpilation failed for d={d}: {e}")

    df = pd.DataFrame(results)
    plot_distance_tradeoffs(df)
    return df

def plot_distance_tradeoffs(df: pd.DataFrame):
    """Plots the inverse relationship between success probability and circuit duration."""
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color = 'tab:blue'
    ax1.set_xlabel('Surface Code Distance (d)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Circuit Success Probability', color=color, fontsize=12, fontweight='bold')
    ax1.plot(df['Distance (d)'], df['Success Chance'], marker='o', color=color, linewidth=2)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(df['Distance (d)'])

    # Instantiate a second axes that shares the same x-axis
    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('Total Execution Duration (s)', color=color, fontsize=12, fontweight='bold')  
    ax2.plot(df['Distance (d)'], df['Total Duration (s)'], marker='s', color=color, linewidth=2, linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('Fault-Tolerant Tradeoff: Success Probability vs. Execution Time', fontsize=14)
    fig.tight_layout()
    os.makedirs("example_2", exist_ok=True)
    plt.savefig("example_2/code_distance_tradeoff.png", dpi=300)
    plt.show()

