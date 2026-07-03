from __future__ import annotations

import unittest

from fastapi import HTTPException

from backend.api.routes.circuits import preview_circuit
from backend.api.schemas import CircuitQasmRequest
from backend.services.circuit_service import preview_qasm


BELL_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
"""

INVALID_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2]
h q[0];
"""


class TestCircuitPreview(unittest.TestCase):
    def test_bell_preview_returns_non_empty_qiskit_text_diagram(self) -> None:
        payload = preview_qasm(BELL_QASM)
        self.assertEqual(payload["format"], "qiskit_text")
        self.assertTrue(payload["diagram"].strip())
        self.assertIn("q_0", payload["diagram"])

    def test_bell_preview_metadata_is_correct(self) -> None:
        payload = preview_qasm(BELL_QASM)
        self.assertEqual(payload["num_qubits"], 2)
        self.assertEqual(payload["num_clbits"], 0)
        self.assertEqual(payload["depth"], 2)
        self.assertEqual(payload["gate_count"], 2)
        self.assertEqual(payload["operation_counts"], {"h": 1, "cx": 1})

    def test_invalid_qasm_returns_controlled_validation_error(self) -> None:
        with self.assertRaises(HTTPException) as exc:
            preview_circuit(CircuitQasmRequest(qasm=INVALID_QASM))

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("Invalid OpenQASM input", str(exc.exception.detail))


if __name__ == "__main__":
    unittest.main()
