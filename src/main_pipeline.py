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
from target_creation.target import (
    build_flexible_target,
    get_architecture_display_name,
)
from metrics.metrics_evaluator import calculate_circuit_success_chance, get_total_duration, count_network_operations

OUTPUT_DIR = Path(__file__).resolve().parent / "metrics"
MAP_DRAWINGS_DIR = OUTPUT_DIR / "map drawings"

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
    fez_cmap = load_ibm_fez_coupling_map()
    torino_cmap = load_ibm_torino_coupling_map()

    ft_cmap = k_nearest_tiled_coupling_map(
        n_blocks_row=2,
        n_blocks_col=2,
        n=10,
        m=10,
        k_intra=2,
        k_inter=1,
        connector_local=1,
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

    MAP_DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)

    for architecture_name, coupling_map in coupling_maps.items():
        import matplotlib.pyplot as plt

        safe_name = (
            architecture_name.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        filename = MAP_DRAWINGS_DIR / f"{safe_name}_connectivity.png"

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

# Build a simple IBM-style superconducting NISQ target from a concrete heavy-hex coupling map. Connectivity is backend-derived; gate times and errors here are
# still modeled assumptions rather than backend-calibrated values.
def _build_ibm_superconducting_target(
    coupling_map: CouplingMap,
    sq_error: float = 1e-4,
    sq_duration: float = 50e-9,
    cx_error: float = 1e-3,
    cx_duration: float = 500e-9,
) -> Target:
    num_qubits = coupling_map.size()
    target = Target(num_qubits=num_qubits)

    sq_props = {
        (q,): InstructionProperties(error=sq_error, duration=sq_duration)
        for q in range(num_qubits)
    }
    target.add_instruction(IGate(), sq_props)
    target.add_instruction(RZGate(0), sq_props)
    target.add_instruction(SXGate(), sq_props)
    target.add_instruction(XGate(), sq_props)

    cx_props = {
        (q1, q2): InstructionProperties(error=cx_error, duration=cx_duration)
        for q1, q2 in coupling_map.get_edges()
    }
    target.add_instruction(CXGate(), cx_props)

    return target

# Run one benchmark case end-to-end: draw the topology, transpile the circuit, evaluate timing/success metrics, and return one row for the output CSV.
# baseline_name is used only for concrete NISQ backend baselines like Fez/Torino.
def _run_target_benchmark(
    qc: QuantumCircuit,
    architecture_name: str,
    modality: str,
    regime: str,
    target: Target,
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
        target = _build_ibm_superconducting_target(coupling_map)
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
