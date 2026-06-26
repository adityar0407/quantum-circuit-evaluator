from __future__ import annotations

import unittest

from qiskit import QuantumCircuit

from backend.IR.logical_ir import build_logical_ir
from backend.IR.qec_lowering import AnalyticalSurfaceCodeLowerer
from backend.IR.qec_lowering import QecLoweringError
from backend.IR.qec_lowering import validate_qec_ir
from backend.services.target_service import build_target


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


class TestQecIr(unittest.TestCase):
    def test_surface_code_lowering_preserves_logical_provenance(self) -> None:
        circuit = QuantumCircuit(4, 1)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.t(1)
        circuit.measure(1, 0)
        logical_ir = build_logical_ir(circuit, None, compiler="qiskit_ftarget")

        qec_ir = AnalyticalSurfaceCodeLowerer().lower(logical_ir)

        validate_qec_ir(qec_ir)
        self.assertEqual(qec_ir.code_family, "surface_code")
        self.assertEqual(qec_ir.operation_counts["PATCH_H"], 1)
        self.assertEqual(qec_ir.operation_counts["LOGICAL_CX"], 1)
        self.assertEqual(qec_ir.operation_counts["MAGIC_STATE_INJECTION"], 1)
        self.assertEqual(qec_ir.operation_counts["PATCH_MEASURE"], 1)
        self.assertTrue(all(operation.source_logical_op_ids for operation in qec_ir.operations))

    def test_remote_operations_remain_explicit_and_unlowered(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.cx(0, 4)
        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")

        qec_ir = AnalyticalSurfaceCodeLowerer().lower(logical_ir)

        remote_ops = [operation for operation in qec_ir.operations if operation.op_kind == "UNLOWERED_REMOTE_OPERATION"]
        self.assertEqual(len(remote_ops), 1)
        self.assertEqual(remote_ops[0].lowering_status, "unlowered")
        self.assertIn("unmodeled_cost", remote_ops[0].metadata)
        self.assertEqual(remote_ops[0].metadata["remote_operation_label"], "UNLOWERED_REMOTE_CX")
        self.assertIn("remote_limitation", remote_ops[0].metadata)
        self.assertEqual(qec_ir.operation_counts["UNLOWERED_REMOTE_OPERATION"], 1)
        self.assertTrue(any(patch.patch_kind == "routing" for patch in qec_ir.patches))

    def test_validator_rejects_missing_source_provenance(self) -> None:
        circuit = QuantumCircuit(1)
        circuit.h(0)
        logical_ir = build_logical_ir(circuit, None, compiler="qiskit_ftarget")
        qec_ir = AnalyticalSurfaceCodeLowerer().lower(logical_ir)
        broken_operation = qec_ir.operations[0].__class__(
            **{**qec_ir.operations[0].to_dict(), "source_logical_op_ids": ()}
        )
        broken_qec_ir = qec_ir.__class__(
            **{**qec_ir.to_dict(), "patches": qec_ir.patches, "operations": (broken_operation,)}
        )

        with self.assertRaises(QecLoweringError):
            validate_qec_ir(broken_qec_ir)


if __name__ == "__main__":
    unittest.main()
