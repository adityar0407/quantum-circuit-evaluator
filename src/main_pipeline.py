from pathlib import Path
import time
import math
import networkx as nx
import matplotlib.pyplot as plt


# Third-party libraries
import pandas as pd
from qiskit import QuantumCircuit
from qiskit.circuit.random import random_circuit
from qiskit.transpiler import CouplingMap


from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager



# Local project imports

from target_creation.target import FTarget
from examples.iterate_network_configurations import compare_arch, compare_architectures_example, plot_best_time_to_success, fault_tolerant_example
from examples.basic_distance_eval import plot_distance_tradeoffs, study_code_distance_scaling
from examples.shors import Shor

from hardware.connectivity import generate_modular_layout, plot_modular_cmap, re_center, orient_by_triangle, get_perimeter_data_qubits



def make_test_qc(num_q = 100, dep = 10):
    return random_circuit(num_qubits=num_q, depth=dep, measure=False, seed = 1738)



def main():
    # testing the iterative block code creation
    # cascade_circuit = get_toffoli_cascade(num_qubits=100) # Using the Toffoli cascade circuit as a test case for the architecture comparison

    # compare_results = compare_architectures(cascade_circuit)
    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # compare_results.to_csv(
    #     OUTPUT_DIR / "architecture_comparison_results_sabre.csv",
    #     index=False,
    # )
    #example1()
    #example2()
    #example3() 
    test = {"topology": {
        "type": "heavy_hex",
        "n_blocks_row": 4,
        "n_blocks_col": 4,
        "d" : 5,
        "k_inter": 1,
        
    }, "profile":{
        "sq_gates": {
            "HGate": {"error": 1e-4, "duration": 1e-5},
            "TGate": {"error": 2e-4, "duration": 2e-5}
        },
        "two_q_gates": {
            "CXGate": {
                "local_error": 1e-3, "local_duration": 1e-6,
                "inter_error": 5e-2, "inter_duration": 3e-6
            }
        }
        }
    }


    test2 = {"topology": {
        "type": "tiled_k_nearest",
        "n_blocks_row": 4,
        "n_blocks_col": 4,
        "n" : 5,
        "m": 5,
        "k_intra":2,
        "k_inter": 4,
        
    }, "profile":{
        "sq_gates": {
            "HGate": {"error": 1e-4, "duration": 1e-5},
            "TGate": {"error": 2e-4, "duration": 2e-5}
        },
        "two_q_gates": {
            "CXGate": {
                "local_error": 1e-3, "local_duration": 1e-6,
                "inter_error": 5e-2, "inter_duration": 3e-6
            }
        }
        }
    }



    test_qc = make_test_qc(20, 10)
    testing = FTarget(test)
    
    testing.plot()
    # pm = generate_preset_pass_manager(optimization_level=3, target=testing, seed_transpiler=1738)
    # print("Starting Level 3 Transpilation...")
    # transpiled_circuit = pm.run(test_qc, callback=transpilation_tracker)
    # print("Transpilation Complete!")
    # type = 'hex'
    # test = generate_modular_layout(f"heavy_{type}")
    # type = "hex"
    # for x in range(3, 13, 2):
    #     corners, pos = testing_logic(architecture=f"heavy_{type}",d=x)
    #     print(f"distance {x} has  edge qubits {corners}")
    # for x in range(3, 21, 2):
    #     modular_cmap, x, z, positions = generate_modular_layout(architecture=f"heavy_{type}",d=x, rows=1, cols=1)
    #     plot_modular_cmap(modular_cmap, positions, type)

if __name__ == "__main__":
    main()
