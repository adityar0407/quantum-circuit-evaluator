from __future__ import annotations

import unittest

from qiskit import QuantumCircuit

from backend.IR.logical_ir import build_logical_ir
from backend.IR.qiskit_adapter import logical_ir_to_qiskit_circuit
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


class TestLogicalIrToQiskitAdapter(unittest.TestCase):
    def test_remote_cx_lowers_to_base_cx_with_metadata(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.h(0)
        circuit.cx(0, 4)
        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")

        qre_circuit, metadata = logical_ir_to_qiskit_circuit(logical_ir)

        self.assertEqual(qre_circuit.count_ops().get("h"), 1)
        self.assertEqual(qre_circuit.count_ops().get("cx"), 1)
        self.assertEqual(metadata["source"], "logical_ir_v1")
        self.assertEqual(metadata["remote_ops_lowered_as_base_gate"], 1)


if __name__ == "__main__":
    unittest.main()
