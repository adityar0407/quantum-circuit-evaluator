from __future__ import annotations

import unittest

from backend.services.transpilation_service import _select_resource_estimator, compile_qasm


CLIFFORD_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
"""


TARGET_CONFIG = {
    "topology": {
        "type": "tiled_k_nearest",
        "n_blocks_row": 2,
        "n_blocks_col": 2,
        "n": 3,
        "m": 3,
        "k_intra": 1,
        "k_inter": 1,
        "connector_local": 1,
    },
    "profile": {
        "sq_gates": {
            "HGate": {"error": 0.0001, "duration": 0.00001},
            "TGate": {"error": 0.0002, "duration": 0.00002},
        },
        "two_q_gates": {
            "CXGate": {"local_error": 0.001, "local_duration": 0.000001},
        },
        "inter_device_gates": {
            "SwapGate": {"inter_error": 0.05, "inter_duration": 0.00001},
        },
    },
}


class TestAzureQreEstimator(unittest.TestCase):
    def test_simple_logical_alias_routes_to_qre(self) -> None:
        self.assertEqual(_select_resource_estimator("simple_logical"), "azure_qre")
        self.assertEqual(_select_resource_estimator("azure_qre"), "azure_qre")
        self.assertEqual(_select_resource_estimator("auto"), "azure_qre")

    def test_compile_qasm_returns_qre_metrics(self) -> None:
        result = compile_qasm(
            CLIFFORD_QASM,
            TARGET_CONFIG,
            compiler_backend="qiskit_ftarget",
            resource_estimator="simple_logical",
        )

        self.assertEqual(result["resource_estimator"], "azure_qre")
        self.assertIn("physical_qubits", result["metrics"])
        self.assertIn("runtime", result["metrics"])
        self.assertIn("logical_counts", result["metrics"])
        self.assertIn("physical_counts", result["metrics"])
        self.assertIn("job_params", result["metrics"])
        self.assertIsInstance(result["metrics"]["logical_counts"], dict)
        self.assertTrue(result["metrics"]["measurement_added_for_qre"])
        self.assertEqual(result["metrics"]["qre_assumptions"]["ftarget_modality"], "logical_clifford_t")
        self.assertEqual(result["metrics"]["qre_assumptions"]["qre_qec_scheme"], "surface_code")
        self.assertTrue(result["metrics"]["qre_assumptions"]["translation_notes"])


if __name__ == "__main__":
    unittest.main()
