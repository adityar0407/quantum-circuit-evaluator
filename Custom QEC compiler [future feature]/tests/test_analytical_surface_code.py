from __future__ import annotations

import unittest

from qiskit import QuantumCircuit

from backend.IR.logical_ir import build_logical_ir
from backend.services.compilers.base import CompilationResult
from backend.services.estimation_context import build_estimation_context
from backend.services.resource_estimators.analytical_surface_code import AnalyticalSurfaceCodeEstimator
from backend.services.target_service import build_target
from backend.services.transpilation_service import _select_resource_estimator, compile_qasm


CLIFFORD_T_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
h q[0];
cx q[0],q[1];
t q[1];
cx q[1],q[3];
"""


TARGET_CONFIG = {
    "topology": {
        "type": "tiled_k_nearest",
        "n_blocks_row": 1,
        "n_blocks_col": 2,
        "n": 2,
        "m": 2,
        "k_intra": 4,
        "k_inter": 1,
        "connector_local": 1,
    },
    "profile": {
        "sq_gates": {
            "HGate": {"logical_weight": 1, "logical_preference": 1},
            "TGate": {"logical_weight": 2, "logical_preference": 1},
        },
        "two_q_gates": {
            "CXGate": {"logical_weight": 3, "routing_preference": 2},
        },
        "inter_device_gates": {
            "SwapGate": {"logical_weight": 5, "routing_preference": 3},
        },
    },
}


class TestAnalyticalSurfaceCodeEstimator(unittest.TestCase):
    def test_simple_logical_alias_routes_to_analytical_surface_code(self) -> None:
        self.assertEqual(_select_resource_estimator("simple_logical"), "analytical_surface_code")
        self.assertEqual(_select_resource_estimator("azure_qre"), "azure_qre")
        self.assertEqual(_select_resource_estimator("auto"), "azure_qre")

    def test_compile_qasm_returns_surface_code_metrics(self) -> None:
        result = compile_qasm(
            CLIFFORD_T_QASM,
            TARGET_CONFIG,
            compiler_backend="qiskit_ftarget",
            resource_estimator="analytical_surface_code",
            estimation_profiles={
                "physical_hardware": {
                    "two_qubit_gate_error_rate": 1.2e-3,
                    "measurement_error_rate": 2.5e-4,
                    "cycle_time": 1.1e-6,
                },
                "qec": {
                    "qec_scheme": "surface_code",
                    "logical_error_target": 1e-9,
                    "error_budget": 1e-3,
                    "code_distance_policy": "auto",
                },
                "network": {
                    "topology": "distributed",
                    "remote_gate_time": 5e-6,
                    "remote_gate_error": 1e-2,
                },
            },
        )

        self.assertEqual(result["resource_estimator"], "analytical_surface_code")
        self.assertIn("selected_code_distance", result["metrics"])
        self.assertIn("total_physical_qubits", result["metrics"])
        self.assertIn("total_patch_cycles", result["metrics"])
        self.assertIn("estimated_runtime_seconds", result["metrics"])
        self.assertIn("remote_operations", result["metrics"])
        self.assertIn("qec_ir_summary", result["metrics"])
        self.assertIn("qec_operation_counts", result["metrics"])
        self.assertEqual(
            result["metrics"]["surface_code_assumptions"]["estimation_model"],
            "analytical_surface_code_v2_qec_ir",
        )

    def test_remote_operations_are_marked_unmodeled_in_surface_code_estimator(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.cx(0, 4)
        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")
        compilation = CompilationResult(
            compiler="qiskit_ftarget",
            original_circuit=circuit,
            compiled_circuit=circuit,
            target=target,
            estimation_context=build_estimation_context(
                target,
                {
                    "network": {
                        "topology": "distributed",
                        "remote_gate_time": 5e-6,
                        "remote_gate_error": 1e-2,
                    }
                },
            ),
            logical_ir=logical_ir,
        )

        metrics = AnalyticalSurfaceCodeEstimator().estimate(compilation)

        self.assertEqual(metrics["remote_operations"]["count"], 1)
        self.assertTrue(metrics["remote_operations"]["has_unmodeled_cost"])
        self.assertEqual(metrics["qec_operation_counts"]["UNLOWERED_REMOTE_OPERATION"], 1)
        self.assertTrue(metrics["surface_code_assumptions"]["runtime_excludes_remote_protocol_overhead"])


if __name__ == "__main__":
    unittest.main()
