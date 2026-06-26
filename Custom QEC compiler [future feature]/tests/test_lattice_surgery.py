from __future__ import annotations

import unittest

from qiskit import QuantumCircuit

from backend.IR.logical_ir import build_logical_ir
from backend.IR.qec_lowering import LatticeSurgeryLowerer
from backend.services.compilers.base import CompilationResult
from backend.services.estimation_context import build_estimation_context
from backend.services.resource_estimators.lattice_surgery import LatticeSurgeryEstimator
from backend.services.target_service import build_target
from backend.services.transpilation_service import compile_qasm


QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
t q[1];
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


class TestLatticeSurgery(unittest.TestCase):
    def test_local_cx_is_expanded_into_lattice_surgery_steps(self) -> None:
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        logical_ir = build_logical_ir(circuit, None, compiler="qiskit_ftarget")

        qec_ir = LatticeSurgeryLowerer().lower(logical_ir)

        self.assertEqual(qec_ir.code_family, "surface_code_lattice_surgery")
        self.assertNotIn("LOGICAL_CX", qec_ir.operation_counts)
        self.assertEqual(qec_ir.operation_counts["LS_PREPARE_ANCILLA"], 1)
        self.assertEqual(qec_ir.operation_counts["JOINT_ZZ"], 1)
        self.assertEqual(qec_ir.operation_counts["JOINT_XX"], 1)
        self.assertEqual(qec_ir.operation_counts["CLASSICAL_FEEDFORWARD"], 1)
        self.assertEqual(qec_ir.operation_counts["PATCH_RESET"], 1)

    def test_remote_cx_remains_unlowered(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.cx(0, 4)
        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")

        qec_ir = LatticeSurgeryLowerer().lower(logical_ir)

        self.assertEqual(qec_ir.operation_counts["UNLOWERED_REMOTE_OPERATION"], 1)
        remote = qec_ir.operations[0]
        self.assertEqual(remote.metadata["remote_operation_label"], "UNLOWERED_REMOTE_CX")

    def test_lattice_surgery_estimator_returns_qec_metrics(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")
        compilation = CompilationResult(
            compiler="qiskit_ftarget",
            original_circuit=circuit,
            compiled_circuit=circuit,
            target=target,
            estimation_context=build_estimation_context(target),
            logical_ir=logical_ir,
        )

        metrics = LatticeSurgeryEstimator().estimate(compilation)

        self.assertEqual(metrics["qec_ir_summary"]["code_family"], "surface_code_lattice_surgery")
        self.assertEqual(metrics["qec_operation_counts"]["JOINT_ZZ"], 1)
        self.assertIn("qre_v3_lattice_surgery", metrics)
        self.assertEqual(metrics["lattice_surgery_assumptions"]["estimation_model"], "lattice_surgery_v1_qec_ir")

    def test_compile_qasm_can_select_lattice_surgery_estimator(self) -> None:
        result = compile_qasm(
            QASM,
            TARGET_CONFIG,
            compiler_backend="qiskit_ftarget",
            resource_estimator="lattice_surgery",
        )

        self.assertEqual(result["resource_estimator"], "lattice_surgery")
        self.assertEqual(result["metrics"]["qec_ir_summary"]["code_family"], "surface_code_lattice_surgery")
        self.assertIn("JOINT_ZZ", result["metrics"]["qec_operation_counts"])


if __name__ == "__main__":
    unittest.main()
