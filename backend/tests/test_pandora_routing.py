from __future__ import annotations

import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

from qiskit import QuantumCircuit

from backend.IR.logical_ir import build_logical_ir
from backend.services.circuit_service import circuit_from_qasm
from backend.services.compilers.base import CompilationResult
from backend.services.compilers.base import CompilerError
from backend.services.compilers.pandora_compiler import PandoraCompiler
from backend.services.compilers.pandora_topology import validate_compiled_circuit_against_architecture
from backend.services.compilers.pandora_topology import validate_pandora_comparison_ready
from backend.services.run_export import build_reproducible_run_export
from backend.services.target_service import build_target, export_target_topology
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
            "SwapGate": {"logical_weight": 3, "routing_preference": 2},
        },
        "inter_device_gates": {},
    },
}

LINEAR_TARGET_CONFIG = {
    "topology": {
        "type": "tiled_k_nearest",
        "n_blocks_row": 1,
        "n_blocks_col": 1,
        "n": 4,
        "m": 1,
        "k_intra": 1,
        "k_inter": 1,
        "connector_local": 1,
    },
    "profile": {
        "sq_gates": {
            "HGate": {"logical_weight": 1, "logical_preference": 1},
            "XGate": {"logical_weight": 1, "logical_preference": 1},
        },
        "two_q_gates": {
            "CXGate": {"logical_weight": 3, "routing_preference": 2},
            "SwapGate": {"logical_weight": 3, "routing_preference": 2},
        },
        "inter_device_gates": {},
    },
}

HEAVY_HEX_TARGET_CONFIG = {
    "topology": {
        "type": "heavy_hex",
        "d": 3,
        "n_blocks_row": 1,
        "n_blocks_col": 1,
        "k_inter": 1,
    },
    "profile": {
        "sq_gates": {
            "HGate": {"logical_weight": 1, "logical_preference": 1},
            "XGate": {"logical_weight": 1, "logical_preference": 1},
        },
        "two_q_gates": {
            "CXGate": {"logical_weight": 3, "routing_preference": 2},
            "SwapGate": {"logical_weight": 3, "routing_preference": 2},
        },
        "inter_device_gates": {},
    },
}

HEAVY_SQUARE_TARGET_CONFIG = {
    "topology": {
        "type": "heavy_square",
        "d": 3,
        "n_blocks_row": 1,
        "n_blocks_col": 1,
        "k_inter": 1,
    },
    "profile": {
        "sq_gates": {
            "HGate": {"logical_weight": 1, "logical_preference": 1},
            "XGate": {"logical_weight": 1, "logical_preference": 1},
        },
        "two_q_gates": {
            "CXGate": {"logical_weight": 3, "routing_preference": 2},
            "SwapGate": {"logical_weight": 3, "routing_preference": 2},
        },
        "inter_device_gates": {},
    },
}

CUSTOM_TARGET_CONFIG = {
    "topology": {"type": "custom_coupling_map", "coupling_map": [[0, 1], [1, 0], [1, 2], [2, 1]]},
    "profile": {
        "sq_gates": {
            "HGate": {"logical_weight": 1, "logical_preference": 1},
            "XGate": {"logical_weight": 1, "logical_preference": 1},
        },
        "two_q_gates": {
            "CXGate": {"logical_weight": 3, "routing_preference": 2},
        },
        "inter_device_gates": {},
    },
}

REMOTE_CX_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
cx q[0],q[3];
"""


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
        return {
            "compiled_gate_count": compilation.compiled_circuit.size(),
            "native_qre_trace": {"mapped_operations": [], "skipped_operations": [], "source_operations": []},
            "qre_assumptions": {},
        }


class _FailingCompiler:
    key = "pandora"

    def compile(self, qasm: str, target_config: dict) -> CompilationResult:
        del qasm, target_config
        raise CompilerError("pandora native router does not support this circuit yet")


class TestPandoraRouting(unittest.TestCase):
    def test_small_supported_ftarget_defaults_to_pandora(self) -> None:
        selected, artifacts = select_compiler_backend(SMALL_QASM, TARGET_CONFIG, "auto")

        self.assertEqual(selected, "pandora")
        self.assertEqual(artifacts["selected_compiler"], "pandora")
        self.assertEqual(artifacts["selected_reason"], "pandora_supported_ftarget_topology")

    def test_large_gate_count_defaults_to_pandora(self) -> None:
        selected, artifacts = select_compiler_backend(large_gate_qasm(), TARGET_CONFIG, "auto")

        self.assertEqual(selected, "pandora")
        self.assertEqual(artifacts["selected_compiler"], "pandora")
        self.assertEqual(artifacts["routing_input"]["gate_count"], PANDORA_GATE_THRESHOLD)

    def test_large_qubit_count_defaults_to_pandora(self) -> None:
        selected, artifacts = select_compiler_backend(large_qubit_qasm(), TARGET_CONFIG, "auto")

        self.assertEqual(selected, "pandora")
        self.assertEqual(artifacts["selected_compiler"], "pandora")
        self.assertEqual(artifacts["routing_input"]["num_qubits"], PANDORA_QUBIT_THRESHOLD)

    def test_manual_backend_bypasses_auto_router(self) -> None:
        selected, artifacts = select_compiler_backend(large_gate_qasm(), TARGET_CONFIG, "qiskit_ftarget")

        self.assertEqual(selected, "qiskit_ftarget")
        self.assertEqual(artifacts, {"routing_mode": "manual"})

    def test_unsupported_ftarget_topology_falls_back_to_qiskit(self) -> None:
        custom_target = {
            "topology": {"type": "custom_coupling_map", "coupling_map": [[0, 1], [1, 0]]},
            "profile": TARGET_CONFIG["profile"],
        }

        selected, artifacts = select_compiler_backend(SMALL_QASM, custom_target, "auto")

        self.assertEqual(selected, "qiskit_ftarget")
        self.assertEqual(artifacts["selected_reason"], "pandora_topology_unsupported")
        self.assertFalse(artifacts["routing_input"]["pandora_candidate"])

    def test_compile_qasm_uses_pandora_for_large_circuits(self) -> None:
        compiler = _StubCompiler("pandora")
        estimator = _StubEstimator()

        with patch("backend.services.transpilation_service.get_compiler_backend", return_value=compiler) as compiler_lookup:
            with patch("backend.services.transpilation_service.get_resource_estimator", return_value=estimator):
                result = compile_qasm(
                    large_gate_qasm(),
                    target_config=TARGET_CONFIG,
                    compiler_backend="auto",
                    resource_estimator="native_qre",
                )

        self.assertEqual(result["compiler"], "pandora")
        self.assertEqual(result["resource_estimator"], estimator.key)
        self.assertEqual(result["artifacts"]["selected_compiler"], "pandora")
        self.assertEqual(result["metrics"]["compiled_gate_count"], PANDORA_GATE_THRESHOLD)
        compiler_lookup.assert_called_once_with("pandora")

    def test_compile_qasm_falls_back_to_qiskit_when_pandora_attempt_fails(self) -> None:
        estimator = _StubEstimator()

        with patch(
            "backend.services.transpilation_service.get_compiler_backend",
            side_effect=[_FailingCompiler(), _StubCompiler("qiskit_ftarget")],
        ):
            with patch("backend.services.transpilation_service.get_resource_estimator", return_value=estimator):
                result = compile_qasm(
                    SMALL_QASM,
                    target_config=TARGET_CONFIG,
                    compiler_backend="auto",
                    resource_estimator="native_qre",
                )

        self.assertEqual(result["compiler"], "qiskit_ftarget")
        self.assertEqual(result["artifacts"]["selected_compiler"], "qiskit_ftarget")
        self.assertEqual(result["artifacts"]["selected_reason"], "pandora_attempt_failed_fallback_to_qiskit")
        self.assertIn("compiler_fallback", result["artifacts"])
        self.assertIn("pandora native router", result["artifacts"]["compiler_fallback"]["reason"])

    def test_pandora_support_preflight_reports_unsupported_ops_cleanly(self) -> None:
        compiler = PandoraCompiler()

        with self.assertRaises(CompilerError) as ctx:
            compiler.compile(UNSUPPORTED_QASM, target_config=TARGET_CONFIG)

        self.assertIn("Pandora-native routing", str(ctx.exception))
        self.assertIn("cu1", str(ctx.exception))

    def test_pandora_receives_architecture_constraints_in_artifacts(self) -> None:
        compiler = PandoraCompiler()

        with patch.object(compiler, "_support_scan", return_value={"unsupported_operations": [], "supported_qiskit_gates": ["cx", "h", "x"]}):
            with patch.object(compiler, "_database_is_available", return_value=False):
                with patch(
                    "backend.services.compilers.pandora_compiler.subprocess.run",
                    return_value=SimpleNamespace(stdout=json.dumps({"translation_only": True}), stderr=""),
                ):
                    result = compiler.compile(SMALL_QASM, target_config=TARGET_CONFIG)

        topology = result.artifacts["target_topology"]
        self.assertIn("architecture_id", topology)
        self.assertIn("number_of_qubits", topology)
        self.assertIn("allowed_coupling_edges", topology)
        self.assertIn("native_gate_set", topology)
        self.assertIn("qubit_to_node_mapping", topology)
        self.assertIn("local_edges", topology)
        self.assertIn("remote_inter_node_edges", topology)
        self.assertIn("directed_edge_policy", topology)
        self.assertIn("architecture_limitations", topology)

    def test_pandora_output_with_illegal_two_qubit_edges_is_rejected(self) -> None:
        compiler = PandoraCompiler()
        illegal_qasm = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
cx q[0],q[3];
"""

        with patch.object(compiler, "_support_scan", return_value={"unsupported_operations": [], "supported_qiskit_gates": ["cx", "swap", "h", "x"]}):
            with patch.object(compiler, "_database_is_available", return_value=False):
                with patch(
                    "backend.services.compilers.pandora_compiler.subprocess.run",
                    return_value=SimpleNamespace(stdout=json.dumps({"optimized_qasm": illegal_qasm}), stderr=""),
                ):
                    with self.assertRaises(CompilerError) as ctx:
                        compiler.compile(SMALL_QASM, target_config=LINEAR_TARGET_CONFIG)

        self.assertIn("illegal two-qubit edges", str(ctx.exception))

    def test_pandora_legalizes_circuit_against_target_topology_before_runner(self) -> None:
        compiler = PandoraCompiler()
        submitted_payload: dict[str, object] = {}

        def fake_run(cmd, input, capture_output, check, env, text, timeout):
            del cmd, capture_output, check, env, text, timeout
            submitted_payload.update(json.loads(input))
            return SimpleNamespace(stdout=json.dumps({"translation_only": True}), stderr="")

        with patch.object(compiler, "_support_scan", return_value={"unsupported_operations": [], "supported_qiskit_gates": ["cx", "swap", "h"]}):
            with patch.object(compiler, "_database_is_available", return_value=False):
                with patch("backend.services.compilers.pandora_compiler.subprocess.run", side_effect=fake_run):
                    result = compiler.compile(REMOTE_CX_QASM, target_config=LINEAR_TARGET_CONFIG)

        target = build_target(LINEAR_TARGET_CONFIG)
        compiled = result.compiled_circuit
        self.assertEqual(submitted_payload["mode"], "translate")
        self.assertTrue(result.artifacts["topology_aware"])
        self.assertEqual(result.artifacts["target_topology"]["topology_type"], "tiled_k_nearest")
        self.assertGreater(compiled.size(), circuit_from_qasm(REMOTE_CX_QASM).size())
        self.assertEqual(result.artifacts["topology_lowering"]["status"], "completed")
        self.assertEqual(result.artifacts["topology_lowering"]["legalization_backend"], "pandora_native_router")
        self.assertTrue(result.artifacts["topology_validation"]["validated"])
        for instruction in compiled.data:
            if len(instruction.qubits) != 2:
                continue
            q0 = compiled.find_bit(instruction.qubits[0]).index
            q1 = compiled.find_bit(instruction.qubits[1]).index
            self.assertIn((q0, q1), set(target.cmap.get_edges()))

    def test_pandora_rejects_unsupported_topology_types(self) -> None:
        compiler = PandoraCompiler()

        with self.assertRaises(CompilerError) as ctx:
            compiler.compile(SMALL_QASM, target_config=CUSTOM_TARGET_CONFIG)

        self.assertIn("currently supports", str(ctx.exception))
        self.assertIn("custom_coupling_map", str(ctx.exception))

    def test_pandora_accepts_existing_heavy_hex_topology(self) -> None:
        compiler = PandoraCompiler()

        with patch.object(compiler, "_support_scan", return_value={"unsupported_operations": [], "supported_qiskit_gates": ["cx", "h", "x"]}):
            with patch.object(compiler, "_database_is_available", return_value=False):
                with patch(
                    "backend.services.compilers.pandora_compiler.subprocess.run",
                    return_value=SimpleNamespace(stdout=json.dumps({"translation_only": True}), stderr=""),
                ):
                    result = compiler.compile(SMALL_QASM, target_config=HEAVY_HEX_TARGET_CONFIG)

        self.assertEqual(result.artifacts["target_topology"]["topology_type"], "heavy_hex")
        self.assertTrue(result.artifacts["topology_aware"])

    def test_heavy_square_and_custom_coupling_maps_are_validated(self) -> None:
        heavy_square_target = build_target(HEAVY_SQUARE_TARGET_CONFIG)
        heavy_square_topology = export_target_topology(heavy_square_target)
        custom_target = build_target(CUSTOM_TARGET_CONFIG)
        custom_topology = export_target_topology(custom_target)

        legal_square = QuantumCircuit(heavy_square_target.total_qubits)
        edge = next(iter(heavy_square_target.cmap.get_edges()))
        legal_square.cx(edge[0], edge[1])
        self.assertTrue(validate_compiled_circuit_against_architecture(legal_square, heavy_square_topology)["validated"])

        legal_custom = QuantumCircuit(custom_target.total_qubits)
        legal_custom.cx(0, 1)
        self.assertTrue(validate_compiled_circuit_against_architecture(legal_custom, custom_topology)["validated"])

        illegal_custom = QuantumCircuit(custom_target.total_qubits)
        illegal_custom.cx(0, 2)
        with self.assertRaises(CompilerError):
            validate_compiled_circuit_against_architecture(illegal_custom, custom_topology)

    def test_architecture_comparison_mode_rejects_topology_ignorant_pandora_results(self) -> None:
        with self.assertRaises(CompilerError) as ctx:
            validate_pandora_comparison_ready({"topology_aware": False})

        self.assertIn("topology-ignorant Pandora results", str(ctx.exception))

    def test_logical_ir_after_pandora_reflects_architecture_respecting_circuit(self) -> None:
        compiler = PandoraCompiler()
        estimator = _StubEstimator()

        with patch.object(compiler, "_support_scan", return_value={"unsupported_operations": [], "supported_qiskit_gates": ["cx", "swap", "h", "x"]}):
            with patch.object(compiler, "_database_is_available", return_value=False):
                with patch(
                    "backend.services.compilers.pandora_compiler.subprocess.run",
                    return_value=SimpleNamespace(stdout=json.dumps({"translation_only": True}), stderr=""),
                ):
                    with patch("backend.services.transpilation_service.get_compiler_backend", return_value=compiler):
                        with patch("backend.services.transpilation_service.get_resource_estimator", return_value=estimator):
                            result = compile_qasm(
                                REMOTE_CX_QASM,
                                target_config=LINEAR_TARGET_CONFIG,
                                compiler_backend="pandora",
                                resource_estimator="native_qre",
                            )

        logical_ir = result["artifacts"]["logical_ir"]
        self.assertEqual(logical_ir["metadata"]["compiler_metadata"]["topology_validation"]["validated"], True)
        self.assertEqual(logical_ir["remote_operation_count"], 0)
        for operation in logical_ir["operations"]:
            self.assertNotEqual(operation["op_kind"], "two_qubit_remote")

    def test_architecture_comparison_readiness_export_rejects_topology_ignorant_pandora(self) -> None:
        circuit = circuit_from_qasm(SMALL_QASM)
        compilation = CompilationResult(
            compiler="pandora",
            original_circuit=circuit,
            compiled_circuit=circuit,
            target=build_target(TARGET_CONFIG),
            artifacts={"topology_aware": False},
            logical_ir=build_logical_ir(circuit, build_target(TARGET_CONFIG), "pandora", artifacts={"topology_aware": False}),
        )
        export = build_reproducible_run_export(
            qasm=SMALL_QASM,
            target_config=TARGET_CONFIG,
            requested_compiler_backend="pandora",
            requested_resource_estimator="native_qre",
            estimation_profiles=None,
            compilation=compilation,
            resource_estimator_key="stub_estimator",
            metrics={"native_qre_trace": {"mapped_operations": [], "skipped_operations": [], "source_operations": []}, "qre_assumptions": {}},
            routing_artifacts={},
        )

        self.assertFalse(export["compilation"]["architecture_comparison"]["accepted"])


if __name__ == "__main__":
    unittest.main()
