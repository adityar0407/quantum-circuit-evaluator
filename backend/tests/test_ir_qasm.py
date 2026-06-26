from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qiskit import QuantumCircuit

from backend.IR.qasm import export_circuit_to_qasm
from backend.IR.qasm import ingest_qasm_file
from backend.IR.qasm import ingest_qasm_string
from backend.IR.qasm import load_qasm_circuit
from backend.IR.qasm import validate_qasm


QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
"""


class TestIrQasm(unittest.TestCase):
    def test_ingest_qasm_string_strips_outer_whitespace(self) -> None:
        self.assertEqual(ingest_qasm_string(f"\n{QASM}\n"), QASM.strip())

    def test_ingest_qasm_file_reads_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.qasm"
            path.write_text(QASM)
            self.assertEqual(ingest_qasm_file(path), QASM.strip())

    def test_validate_and_load_qasm(self) -> None:
        ok, payload = validate_qasm(QASM)
        self.assertTrue(ok)
        self.assertIsInstance(payload, QuantumCircuit)
        circuit = load_qasm_circuit(QASM)
        self.assertEqual(circuit.num_qubits, 2)

    def test_export_round_trips_qasm(self) -> None:
        circuit = load_qasm_circuit(QASM)
        exported = export_circuit_to_qasm(circuit)
        self.assertIn("OPENQASM 2.0;", exported)


if __name__ == "__main__":
    unittest.main()
