from __future__ import annotations

import unittest

from qiskit import QuantumCircuit

from backend.IR.logical_ir import build_logical_ir
from backend.IR.logical_ir import serialize_logical_ir
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


class TestLogicalIr(unittest.TestCase):
    def test_cross_node_two_qubit_gate_is_tagged_remote(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.cx(0, 4)

        logical_ir = build_logical_ir(
            circuit,
            target,
            compiler="qiskit_ftarget",
            artifacts={
                "original_layout": {"q[0]": 0, "q[4]": 4},
                "final_layout": {"q[0]": 0, "q[4]": 4},
                "routing_swaps": 0,
                "optimization_level": 3,
                "target_snapshot": {"topology_type": "tiled_k_nearest"},
            },
        )
        payload = serialize_logical_ir(logical_ir)

        self.assertEqual(logical_ir.remote_operation_count, 1)
        self.assertEqual(logical_ir.operation_counts["REMOTE_CX"], 1)
        self.assertEqual(logical_ir.operations[0].operation, "REMOTE_CX")
        self.assertEqual(logical_ir.operations[0].metadata["source_node"], 0)
        self.assertEqual(logical_ir.operations[0].metadata["target_node"], 1)
        self.assertEqual(logical_ir.operations[0].op_kind, "two_qubit_remote")
        self.assertEqual(logical_ir.operations[0].unmodeled_cost.status, "unmodeled")
        self.assertEqual(payload["operations"][0]["operation"], "REMOTE_CX")
        self.assertEqual(payload["operations"][0]["unmodeled_cost"]["category"], "remote_execution_overhead")
        self.assertEqual(payload["metadata"]["compiler_metadata"]["optimization_level"], 3)

    def test_dependencies_follow_qubit_access_order(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.h(0)
        circuit.cx(0, 4)

        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")

        self.assertEqual(logical_ir.operations[1].dependencies, ["op_00000"])


if __name__ == "__main__":
    unittest.main()
