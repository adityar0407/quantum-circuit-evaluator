# Standard library
from pathlib import Path
import time
import math

# Third-party libraries
import pandas as pd
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# Local project imports
from hardware.connectivity import (
    load_ibm_fez_coupling_map,
    load_ibm_torino_coupling_map,
)
from IR.circuit_loader import get_toffoli_cascade
from target_creation.target import (
    build_ibm_superconducting_target,
    build_flexible_target,
    get_architecture_display_name,
)
from metrics.metrics_evaluator import calculate_circuit_success_chance, get_total_duration, count_network_operations

OUTPUT_DIR = Path(__file__).resolve().parent / "metrics"
MAP_DRAWINGS_DIR = OUTPUT_DIR / "map drawings"





# Find all factor pairs of n so we can reuse the same circuit width across different single-device and multi-device layout assumptions.
def _find_factors_optimized(n: int) -> list[tuple[int, int]]:
    """Return sorted factor pairs for a positive integer."""
    factors = set()
    for i in range(1, int(math.sqrt(n)) + 1):
        if n % i == 0:
            factors.add(tuple(sorted((i, n // i))))
    return sorted(factors)

# Pick one balanced rectangular shape for a modeled single-device architecture. This is used for abstract NISQ baselines that are not tied to a concrete backend.
def _choose_single_device_shape(num_qubits: int) -> tuple[int, int]:
    """Choose one rectangular single-device shape for modeled NISQ runs."""
    return _find_factors_optimized(num_qubits).pop()


# Generate FT logical/distributed layouts whose total logical-qubit capacity exactly matches the circuit width. Each tuple is:
# (block_rows, block_cols, qubits_per_block_rows, qubits_per_block_cols).
def _enumerate_ft_layouts(num_qubits: int) -> list[tuple[int, int, int, int]]:
    """
    Enumerate tiled logical/distributed FT layouts whose total logical qubit
    capacity matches the circuit width.
    """
    layouts = []

    for n_blocks, n_qubits_per_block in _find_factors_optimized(num_qubits):
        n, m = _find_factors_optimized(n_qubits_per_block).pop()
        br, bc = _find_factors_optimized(n_blocks).pop()

        if br == 1 and bc > 1 and n < m:
            n, m = m, n
        elif bc == 1 and br > 1 and m < n:
            n, m = m, n

        layouts.append((br, bc, n, m))

    return layouts

# Run one benchmark case end-to-end: draw the topology, transpile the circuit, evaluate timing/success metrics, and return one row for the output CSV.
# baseline_name is used only for concrete NISQ backend baselines like Fez/Torino.
def _run_target_benchmark(
    qc: QuantumCircuit,
    architecture_name: str,
    modality: str,
    regime: str,
    target,
    block_name: str,
    n: int,
    m: int,
    total_computers: int,
    baseline_name: str | None = None,
) -> dict:
    """Run one benchmark row and return the CSV record."""
    MAP_DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)

    image = target.build_coupling_map().draw()
    image_filename = MAP_DRAWINGS_DIR / f"map_{block_name}.png"
    if hasattr(image, "savefig"):
        image.savefig(image_filename, dpi=300, bbox_inches="tight")
    else:
        image.save(image_filename)

    cur_time = time.time()
    pm = generate_preset_pass_manager(
        optimization_level=3,
        target=target,
        scheduling_method="alap",
    )

    transpiled_qc = pm.run(qc)
    transpile_time = time.time() - cur_time
    print(f"Transpilation complete in {transpile_time:.2f} seconds.")

    overall_success = calculate_circuit_success_chance(transpiled_qc, target)
    total_duration_seconds = get_total_duration(transpiled_qc)
    two_q_gate_counts = count_network_operations(transpiled_qc, n, m)
    shots_for_success = int(1 / overall_success) if overall_success > 0 else float("inf")

    return {
        "architecture": architecture_name,
        "baseline_name": baseline_name,
        "modality": modality,
        "regime": regime,
        "qubits_per_computer": n * m,
        "total_computers": total_computers,
        "overall_success_chance": overall_success,
        "shots_for_success": shots_for_success,
        "duration_seconds": total_duration_seconds,
        "transpiled_depth": transpiled_qc.depth(),
        "total_two_qubit_gates": two_q_gate_counts["total_2q_gates"],
        "inter_block_gates": two_q_gate_counts["inter_block_gates"],
        "transpile_time_sec": round(transpile_time, 2),
    }


def compare_architectures(qc: QuantumCircuit, debug: bool = False):
    num_qubits = qc.num_qubits
    results = []
    
# Keep the debug path small so we can sanity-check the benchmark structure without running the full NISQ/FT comparison grid.
    if debug:
        nisq_model_modalities = []
        ft_modalities = ["superconducting"]
    else:
        nisq_model_modalities = ["trapped_ion", "neutral_atom", "photonic"]
        ft_modalities = ["superconducting", "trapped_ion", "neutral_atom", "photonic"]
        
# Use one balanced single-device shape for modeled NISQ baselines that are not tied to a concrete backend instance.
    single_n, single_m = _choose_single_device_shape(num_qubits)

# Concrete superconducting NISQ baselines. These are the IBM heavy-hex devices that define the physical-device side of the comparison.
    superconducting_baselines = [
        ("IBM Fez", load_ibm_fez_coupling_map()),
        ("IBM Torino", load_ibm_torino_coupling_map()),
    ]
    
# Benchmark the concrete IBM superconducting NISQ baselines first.
    for baseline_name, coupling_map in superconducting_baselines:
        architecture_name = f"NISQ Superconducting ({baseline_name})"
        block_name = f"nisq_superconducting_{baseline_name.lower().replace(' ', '_')}"
        print(f"\n--- Evaluating {architecture_name} ---")
        target = build_ibm_superconducting_target(coupling_map)
        results.append(
            _run_target_benchmark(
                qc=qc,
                architecture_name=architecture_name,
                modality="superconducting",
                regime="nisq",
                target=target,
                block_name=block_name,
                n=coupling_map.size(),
                m=1,
                total_computers=1,
                baseline_name=baseline_name,
            )
        )

# Modeled NISQ baselines for other physical modalities. These remain abstract single-device comparisons rather than concrete backend instances.
    for modality in nisq_model_modalities:
        architecture_name = get_architecture_display_name(modality, "nisq")
        block_name = f"nisq_{modality}_single_device_{single_n}x{single_m}"
        print(
            f"\n--- Evaluating {architecture_name} single-device model with "
            f"{single_n}x{single_m} qubits ---"
        )

        target = build_flexible_target(
            modality=modality,
            regime="nisq",
            n_blocks_row=1,
            n_blocks_col=1,
            n=single_n,
            m=single_m,
            k_intra=None,
            k_inter=1,
            connector_local=1,
        )
        results.append(
            _run_target_benchmark(
                qc=qc,
                architecture_name=architecture_name,
                modality=modality,
                regime="nisq",
                target=target,
                block_name=block_name,
                n=single_n,
                m=single_m,
                total_computers=1,
            )
        )

# FT side: logical/distributed layouts parameterized by modality-specific timing and error assumptions, but compiled under the FT logical regime.
    ft_layouts = _enumerate_ft_layouts(num_qubits)

# Sweep over FT layouts and modality-dependent FT assumptions to study how logical/distributed execution changes depth, duration, and inter-block overhead.
    for br, bc, n, m in ft_layouts:
        for modality in ft_modalities:
            architecture_name = get_architecture_display_name(modality, "ft")
            block_name = f"ft_{modality}_{br*bc}cores_{n}x{m}qubits"
            print(
                f"\n--- Evaluating {architecture_name} architecture with "
                f"{br*bc} blocks of size {n}x{m} ---"
            )

            target = build_flexible_target(
                modality=modality,
                regime="ft",
                n_blocks_row=br,
                n_blocks_col=bc,
                n=n,
                m=m,
                k_intra=None,
                k_inter=2,
                connector_local=2,
            )
            results.append(
                _run_target_benchmark(
                    qc=qc,
                    architecture_name=architecture_name,
                    modality=modality,
                    regime="ft",
                    target=target,
                    block_name=block_name,
                    n=n,
                    m=m,
                    total_computers=br * bc,
                )
            )

    return pd.DataFrame(results)




    


def main():
    # testing the iterative block code creation
    cascade_circuit = get_toffoli_cascade(num_qubits=100) # Using the Toffoli cascade circuit as a test case for the architecture comparison

    compare_results = compare_architectures(cascade_circuit)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    compare_results.to_csv(
        OUTPUT_DIR / "architecture_comparison_results_sabre.csv",
        index=False,
    )



if __name__ == "__main__":
    main()
