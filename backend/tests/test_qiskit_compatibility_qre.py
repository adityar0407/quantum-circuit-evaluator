from __future__ import annotations

import unittest

from backend.services.transpilation_service import compile_qasm


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
            "HGate": {"logical_weight": 1, "logical_preference": 1},
        },
        "two_q_gates": {
            "CXGate": {"logical_weight": 3, "routing_preference": 2},
        },
        "inter_device_gates": {
            "SwapGate": {"logical_weight": 5, "routing_preference": 3},
        },
    },
}


class TestQiskitCompatibilityQreEstimator(unittest.TestCase):
    def test_explicit_qiskit_compatibility_mode_returns_qre_metrics(self) -> None:
        result = compile_qasm(
            CLIFFORD_QASM,
            TARGET_CONFIG,
            compiler_backend="qiskit_ftarget",
            resource_estimator="qiskit_compatibility",
        )

        self.assertEqual(result["resource_estimator"], "qiskit_compatibility")
        self.assertEqual(result["metrics"]["qre_mode"], "qiskit_compatibility")
        self.assertEqual(result["metrics"]["qre_input_source"], "qiskit_compatibility")
        self.assertEqual(result["metrics"]["qre_assumptions"]["qre_execution_model"], "qiskit_compatibility")
        self.assertIn("qdk_version", result["metrics"])
        self.assertIn("physical_counts", result["metrics"])


if __name__ == "__main__":
    unittest.main()
