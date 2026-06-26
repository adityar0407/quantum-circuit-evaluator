from __future__ import annotations

import unittest
from unittest.mock import patch

from qiskit import QuantumCircuit

from backend.IR.logical_ir import build_logical_ir
from backend.models.estimation_profiles import PhysicalHardwareProfile
from backend.services.compilers.base import CompilationResult
from backend.services.estimation_context import build_estimation_context
from backend.services.resource_estimators.base import ResourceEstimatorError
from backend.services.resource_estimators.native_qre import NativeQreEstimator
from backend.services.resource_estimators.physical_qdk_adapter import physical_profile_to_qdk_model
from backend.services.target_service import build_target
from backend.services.transpilation_service import _select_resource_estimator, compile_qasm


H_MEASURE_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];
"""

H_CX_MEASURE_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""

T_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
t q[0];
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


class TestNativeQreEstimator(unittest.TestCase):
    def test_native_qre_is_default_estimator(self) -> None:
        self.assertEqual(_select_resource_estimator("auto"), "native_qre")
        self.assertEqual(_select_resource_estimator(""), "native_qre")
        self.assertEqual(_select_resource_estimator("native_qre"), "native_qre")
        self.assertEqual(_select_resource_estimator("qiskit_compatibility"), "qiskit_compatibility")

    def test_h_measure_works(self) -> None:
        result = compile_qasm(H_MEASURE_QASM, TARGET_CONFIG, compiler_backend="qiskit_ftarget")

        self.assertEqual(result["resource_estimator"], "native_qre")
        self.assertEqual(result["metrics"]["qre_mode"], "native_qre")
        self.assertEqual(result["metrics"]["qre_input_source"], "native_trace")
        self.assertGreater(result["metrics"]["physical_qubits"], 0)
        self.assertGreater(result["metrics"]["runtime"], 0)
        self.assertIn("qdk_version", result["metrics"])

    def test_h_cx_measure_works_without_qiskit_qre_or_qiskit_reconstruction(self) -> None:
        with patch("qdk.qiskit.estimate", side_effect=AssertionError("qdk.qiskit.estimate must not be called")):
            with patch(
                "backend.IR.qiskit_adapter.logical_ir_to_qiskit_circuit",
                side_effect=AssertionError("LogicalIR must not be reconstructed as Qiskit in native mode"),
            ):
                result = compile_qasm(H_CX_MEASURE_QASM, TARGET_CONFIG, compiler_backend="qiskit_ftarget")

        self.assertEqual(result["resource_estimator"], "native_qre")
        self.assertEqual(result["metrics"]["native_qre_trace"]["mapped_operation_count"], 4)

    def test_custom_qdk_qec_model_parameters_are_used(self) -> None:
        result = compile_qasm(
            H_MEASURE_QASM,
            TARGET_CONFIG,
            compiler_backend="qiskit_ftarget",
            estimation_profiles={
                "qec": {
                    "error_budget": 1e-2,
                    "qec_model_source": "custom",
                    "qec_model_name": "surface_code",
                    "qec_model_parameters": {
                        "distance": 5,
                        "crossing_prefactor": 0.04,
                    },
                }
            },
        )

        qec_model = result["metrics"]["qre_assumptions"]["qec_model"]
        self.assertEqual(qec_model["source"], "custom")
        self.assertEqual(qec_model["name"], "surface_code")
        self.assertEqual(qec_model["parameters"]["distance"], 5)
        self.assertEqual(qec_model["attributes"]["distance"], 5)

    def test_verified_builtin_physical_models_work(self) -> None:
        for model_name in ("gate_based", "neutral_atom"):
            with self.subTest(model_name=model_name):
                result = compile_qasm(
                    H_MEASURE_QASM,
                    TARGET_CONFIG,
                    compiler_backend="qiskit_ftarget",
                    estimation_profiles={
                        "physical_hardware": {
                            "physical_profile_mode": "built_in",
                            "qdk_hardware_model": model_name,
                        }
                    },
                )
                physical = result["metrics"]["qre_assumptions"]["physical_hardware"]
                self.assertEqual(physical["selected_qdk_hardware_model"], model_name)
                self.assertGreater(result["metrics"]["physical_qubits"], 0)

    def test_valid_custom_gate_based_profile_reports_full_mapping(self) -> None:
        result = compile_qasm(
            H_MEASURE_QASM,
            TARGET_CONFIG,
            compiler_backend="qiskit_ftarget",
            estimation_profiles={
                "physical_hardware": {
                    "physical_profile_mode": "custom",
                    "qdk_hardware_model": "gate_based",
                    "physical_modality": "gate_based",
                    "one_qubit_gate_error_rate": 1e-4,
                    "two_qubit_gate_error_rate": 1e-3,
                    "measurement_error_rate": 2e-4,
                    "idle_error_rate": 1e-5,
                    "one_qubit_gate_time": 50e-9,
                    "two_qubit_gate_time": 400e-9,
                    "measurement_time": 900e-9,
                    "cycle_time": 1e-6,
                }
            },
        )

        physical = result["metrics"]["qre_assumptions"]["physical_hardware"]
        self.assertEqual(physical["physical_profile_mode"], "custom")
        self.assertEqual(physical["selected_qdk_hardware_model"], "gate_based")
        self.assertEqual(physical["normalized_qdk_parameters"]["error_rate"], 1e-3)
        self.assertIn("idle_error_rate", physical["ignored_fields"])
        self.assertIn("cycle_time", physical["ignored_fields"])
        self.assertEqual(physical["defaulted_fields"], [])

    def test_invalid_physical_error_rate_fails_clearly(self) -> None:
        with self.assertRaisesRegex(Exception, "physical_hardware.two_qubit_gate_error_rate"):
            compile_qasm(
                H_MEASURE_QASM,
                TARGET_CONFIG,
                compiler_backend="qiskit_ftarget",
                estimation_profiles={
                    "physical_hardware": {
                        "physical_profile_mode": "custom",
                        "qdk_hardware_model": "gate_based",
                        "physical_modality": "gate_based",
                        "one_qubit_gate_error_rate": 1e-4,
                        "two_qubit_gate_error_rate": 1.2,
                        "measurement_error_rate": 2e-4,
                        "idle_error_rate": 1e-5,
                        "one_qubit_gate_time": 50e-9,
                        "two_qubit_gate_time": 300e-9,
                        "measurement_time": 800e-9,
                        "cycle_time": 1e-6,
                    }
                },
            )

    def test_invalid_physical_time_fails_clearly(self) -> None:
        with self.assertRaisesRegex(Exception, "physical_hardware.measurement_time"):
            compile_qasm(
                H_MEASURE_QASM,
                TARGET_CONFIG,
                compiler_backend="qiskit_ftarget",
                estimation_profiles={
                    "physical_hardware": {
                        "physical_profile_mode": "custom",
                        "qdk_hardware_model": "gate_based",
                        "physical_modality": "gate_based",
                        "one_qubit_gate_error_rate": 1e-4,
                        "two_qubit_gate_error_rate": 1e-3,
                        "measurement_error_rate": 2e-4,
                        "idle_error_rate": 1e-5,
                        "one_qubit_gate_time": 50e-9,
                        "two_qubit_gate_time": 300e-9,
                        "measurement_time": 0,
                        "cycle_time": 1e-6,
                    }
                },
            )

    def test_incomplete_custom_physical_profile_fails_clearly(self) -> None:
        with self.assertRaisesRegex(Exception, "Missing custom physical hardware field: physical_hardware.measurement_time"):
            compile_qasm(
                H_MEASURE_QASM,
                TARGET_CONFIG,
                compiler_backend="qiskit_ftarget",
                estimation_profiles={
                    "physical_hardware": {
                        "physical_profile_mode": "custom",
                        "qdk_hardware_model": "gate_based",
                        "physical_modality": "gate_based",
                        "one_qubit_gate_error_rate": 1e-4,
                        "two_qubit_gate_error_rate": 1e-3,
                        "measurement_error_rate": 2e-4,
                        "idle_error_rate": 1e-5,
                        "one_qubit_gate_time": 50e-9,
                        "two_qubit_gate_time": 300e-9,
                        "cycle_time": 1e-6,
                    }
                },
            )

    def test_unsupported_physical_model_fails_clearly(self) -> None:
        with self.assertRaisesRegex(Exception, "Unsupported physical hardware model"):
            compile_qasm(
                H_MEASURE_QASM,
                TARGET_CONFIG,
                compiler_backend="qiskit_ftarget",
                estimation_profiles={
                    "physical_hardware": {
                        "physical_profile_mode": "built_in",
                        "qdk_hardware_model": "majorana",
                    }
                },
            )

    def test_physical_parameter_changes_are_reflected_in_qdk_model(self) -> None:
        low_params = physical_profile_to_qdk_model(
            PhysicalHardwareProfile(
                physical_profile_mode="custom",
                qdk_hardware_model="gate_based",
                two_qubit_gate_error_rate=1e-3,
                two_qubit_gate_time=300e-9,
            )
        ).metadata["normalized_qdk_parameters"]
        high_params = physical_profile_to_qdk_model(
            PhysicalHardwareProfile(
                physical_profile_mode="custom",
                qdk_hardware_model="gate_based",
                two_qubit_gate_error_rate=5e-3,
                two_qubit_gate_time=600e-9,
            )
        ).metadata["normalized_qdk_parameters"]
        self.assertNotEqual(low_params["error_rate"], high_params["error_rate"])
        self.assertNotEqual(low_params["two_qubit_gate_time"], high_params["two_qubit_gate_time"])

    def test_invalid_qdk_qec_model_fails_clearly(self) -> None:
        with self.assertRaisesRegex(Exception, "does not support QEC model"):
            compile_qasm(
                H_MEASURE_QASM,
                TARGET_CONFIG,
                compiler_backend="qiskit_ftarget",
                estimation_profiles={
                    "qec": {
                        "qec_model_source": "azure_builtin",
                        "qec_model_name": "not_a_qec_model",
                    }
                },
            )

    def test_barriers_are_skipped_explicitly(self) -> None:
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.barrier(0)
        circuit.measure(0, 0)
        target = build_target(TARGET_CONFIG)
        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")
        compilation = CompilationResult(
            compiler="qiskit_ftarget",
            original_circuit=circuit,
            compiled_circuit=circuit,
            target=target,
            estimation_context=build_estimation_context(target),
            logical_ir=logical_ir,
        )

        metrics = NativeQreEstimator().estimate(compilation)

        self.assertEqual(metrics["native_qre_trace"]["skipped_operation_count"], 1)
        self.assertEqual(metrics["native_qre_trace"]["skipped_operations"][0]["operation"], "BARRIER")

    def test_unsupported_t_fails_clearly(self) -> None:
        with self.assertRaisesRegex(Exception, "Native QRE does not support operation T"):
            compile_qasm(T_QASM, TARGET_CONFIG, compiler_backend="qiskit_ftarget", resource_estimator="native_qre")

    def test_remote_gate_fails_clearly(self) -> None:
        target = build_target(TARGET_CONFIG)
        circuit = QuantumCircuit(8)
        circuit.cx(0, 4)
        logical_ir = build_logical_ir(circuit, target, compiler="qiskit_ftarget")
        compilation = CompilationResult(
            compiler="qiskit_ftarget",
            original_circuit=circuit,
            compiled_circuit=circuit,
            target=target,
            estimation_context=build_estimation_context(target),
            logical_ir=logical_ir,
        )

        with self.assertRaisesRegex(ResourceEstimatorError, "does not support remote operation"):
            NativeQreEstimator().estimate(compilation)


if __name__ == "__main__":
    unittest.main()
