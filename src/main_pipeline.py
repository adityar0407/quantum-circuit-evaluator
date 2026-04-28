from pathlib import Path
import time
import math


# Third-party libraries
import pandas as pd
from qiskit import QuantumCircuit

from qiskit.transpiler import Target, InstructionProperties, CouplingMap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.visualization import plot_coupling_map
from qiskit.circuit.library import CXGate, IGate, RZGate, SXGate, XGate
from qiskit.circuit.random import random_circuit


# Local project imports


from examples.iterate_network_configurations import compare_arch, compare_architectures_example
from examples.basic_distance_eval import plot_distance_tradeoffs, study_code_distance_scaling







def example1(num_q = 100, dep = 10):
    test_qc = random_circuit(num_qubits=num_q, depth=dep, measure=False, seed = 1738)
    df_results = compare_architectures_example(test_qc, debug=True)
    print(df_results.to_string())
    compare_arch(df_results)
    
def example2(num_q = 100, dep = 10):
    test_qc = random_circuit(num_qubits=num_q, depth=dep, measure=False, seed = 1738)
    df_results = study_code_distance_scaling(test_qc)
    plot_distance_tradeoffs(df_results)



def main():
    # testing the iterative block code creation
    # cascade_circuit = get_toffoli_cascade(num_qubits=100) # Using the Toffoli cascade circuit as a test case for the architecture comparison

    # compare_results = compare_architectures(cascade_circuit)
    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # compare_results.to_csv(
    #     OUTPUT_DIR / "architecture_comparison_results_sabre.csv",
    #     index=False,
    # )
    example2()


if __name__ == "__main__":
    main()
