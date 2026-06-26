from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.services.circuit_service import circuit_from_qasm
from backend.services.compilers.base import CompilationResult
from backend.services.compilers.base import CompilerError
from backend.services.compilers.pandora_compiler import PandoraCompiler
from backend.services.transpilation_service import (
    PANDORA_GATE_THRESHOLD,
    PANDORA_QUBIT_THRESHOLD,
    compile_qasm,
    select_compiler_backend,
)


SMALL_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
"""

UNSUPPORTED_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
cu1(pi/2) q[0],q[1];
"""

TARGET_CONFIG = {
    "topology": {
        "type": "tiled_k_nearest",
        "n_blocks_row": 1,
        "n_blocks_col": 1,
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
        "inter_device_gates": {},
    },
}


def large_gate_qasm() -> str:
    body = "\n".join(f"h q[{index % 2}];" for index in range(PANDORA_GATE_THRESHOLD))
    return f"""OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
{body}
"""


def large_qubit_qasm() -> str:
    qubit_count = PANDORA_QUBIT_THRESHOLD
    return f"""OPENQASM 2.0;
include "qelib1.inc";
qreg q[{qubit_count}];
"""


class _StubCompiler:
    def __init__(self, key: str) -> None:
        self.key = key

    def compile(self, qasm: str, target_config: dict) -> CompilationResult:
        circuit = circuit_from_qasm(qasm)
        return CompilationResult(
            compiler=self.key,
            original_circuit=circuit,
            compiled_circuit=circuit,
            target=object(),
        )


class _StubEstimator:
    key = "stub_estimator"

    def estimate(self, compilation: CompilationResult) -> dict:
        return {"compiled_gate_count": compilation.compiled_circuit.size()}


class TestPandoraRouting(unittest.TestCase):
    def test_small_circuit_defaults_to_qiskit(self) -> None:
        selected, artifacts = select_compiler_backend(SMALL_QASM, "auto")

        self.assertEqual(selected, "qiskit_ftarget")
        self.assertEqual(artifacts["selected_compiler"], "qiskit_ftarget")

    def test_large_gate_count_defaults_to_pandora(self) -> None:
        selected, artifacts = select_compiler_backend(large_gate_qasm(), "auto")

        self.assertEqual(selected, "pandora")
        self.assertEqual(artifacts["selected_compiler"], "pandora")
        self.assertEqual(artifacts["routing_input"]["gate_count"], PANDORA_GATE_THRESHOLD)

    def test_large_qubit_count_defaults_to_pandora(self) -> None:
        selected, artifacts = select_compiler_backend(large_qubit_qasm(), "auto")

        self.assertEqual(selected, "pandora")
        self.assertEqual(artifacts["selected_compiler"], "pandora")
        self.assertEqual(artifacts["routing_input"]["num_qubits"], PANDORA_QUBIT_THRESHOLD)

    def test_manual_backend_bypasses_auto_router(self) -> None:
        selected, artifacts = select_compiler_backend(large_gate_qasm(), "qiskit_ftarget")

        self.assertEqual(selected, "qiskit_ftarget")
        self.assertEqual(artifacts, {"routing_mode": "manual"})

    def test_compile_qasm_uses_pandora_for_large_circuits(self) -> None:
        compiler = _StubCompiler("pandora")
        estimator = _StubEstimator()

        with patch("backend.services.transpilation_service.get_compiler_backend", return_value=compiler) as compiler_lookup:
            with patch("backend.services.transpilation_service.get_resource_estimator", return_value=estimator):
                result = compile_qasm(
                    large_gate_qasm(),
                    target_config={},
                    compiler_backend="auto",
                    resource_estimator="native_qre",
                )

        self.assertEqual(result["compiler"], "pandora")
        self.assertEqual(result["resource_estimator"], estimator.key)
        self.assertEqual(result["artifacts"]["selected_compiler"], "pandora")
        self.assertEqual(result["metrics"]["compiled_gate_count"], PANDORA_GATE_THRESHOLD)
        compiler_lookup.assert_called_once_with("pandora")

    def test_pandora_support_preflight_reports_unsupported_ops_cleanly(self) -> None:
        compiler = PandoraCompiler()

        with self.assertRaises(CompilerError) as ctx:
            compiler.compile(UNSUPPORTED_QASM, target_config=TARGET_CONFIG)

        self.assertIn("Pandora support preflight failed", str(ctx.exception))
        self.assertIn("cu1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
