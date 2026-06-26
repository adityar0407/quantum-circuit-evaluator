from __future__ import annotations

import unittest

from qiskit import QuantumCircuit

from backend.IR.analysis import analyze_logical_ir
from backend.IR.logical_ir import build_logical_ir
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


class TestIrAnalysis(unittest.TestCase):
    def test_analysis_reports_dag_layers_and_remote_ops(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.h(0)
        circuit.h(1)
        circuit.cx(0, 4)
        circuit.t(4)

        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")
        analysis = analyze_logical_ir(logical_ir)

        self.assertEqual(analysis["dag"]["node_count"], 4)
        self.assertEqual(analysis["dag"]["critical_path"], ["op_00000", "op_00002", "op_00003"])
        self.assertEqual(analysis["dag"]["parallel_layers"]["0"], ["op_00000", "op_00001"])
        self.assertEqual(analysis["remote_operations"]["count"], 1)
        self.assertTrue(analysis["remote_operations"]["has_unmodeled_cost"])
        self.assertEqual(analysis["operation_summary"]["t_family_demand"]["t_count"], 1)
        self.assertEqual(logical_ir.metadata["analysis"]["dag"]["critical_path_length"], 3)


if __name__ == "__main__":
    unittest.main()
