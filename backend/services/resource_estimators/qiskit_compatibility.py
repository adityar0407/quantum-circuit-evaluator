from __future__ import annotations

import warnings
import importlib.metadata as importlib_metadata
from typing import Any

from qiskit import QuantumCircuit

from backend.IR.qiskit_adapter import LogicalIrToQiskitError
from backend.IR.qiskit_adapter import logical_ir_to_qiskit_circuit
from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.base import ResourceEstimatorError
from backend.services.resource_estimators.native_qre import _build_qec_model
from backend.services.resource_estimators.native_qre import _estimate_trace
from backend.services.resource_estimators.native_qre import logical_ir_to_native_qre_trace
from backend.services.resource_estimators.physical_qdk_adapter import physical_profile_to_qdk_model
from backend.services.resource_estimators.qre_params import build_qre_params


class QiskitCompatibilityQreEstimator:
    key = "qiskit_compatibility"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        if compilation.estimation_context is None:
            raise ResourceEstimatorError("Azure QRE estimator requires an estimation context.")
        if compilation.logical_ir is None:
            raise ResourceEstimatorError("Azure QRE estimator requires LogicalIR v1.")

        try:
            circuit, ir_lowering = logical_ir_to_qiskit_circuit(compilation.logical_ir)
        except LogicalIrToQiskitError as exc:
            raise ResourceEstimatorError(f"Azure QRE LogicalIR lowering failed: {exc}") from exc

        params, assumptions = build_qre_params(compilation.estimation_context, compilation.logical_ir)
        assumptions["logical_ir_lowering"] = ir_lowering
        estimation_circuit = self._prepare_estimation_circuit(circuit)

        try:
            with warnings.catch_warnings():
                from qdk.estimator import EstimatorError
                from qdk.qiskit import estimate as qre_estimate

                warnings.simplefilter("ignore", category=DeprecationWarning)
                result = qre_estimate(estimation_circuit, params=params)
        except ModuleNotFoundError:
            return self._fallback_estimate(compilation, ir_lowering, estimation_circuit.num_clbits > circuit.num_clbits)
        except ImportError:
            return self._fallback_estimate(compilation, ir_lowering, estimation_circuit.num_clbits > circuit.num_clbits)
        except EstimatorError as exc:
            raise ResourceEstimatorError(f"Azure QRE estimation failed: {exc}") from exc
        except Exception as exc:
            if "qdk.qiskit interop is unavailable" in str(exc):
                return self._fallback_estimate(compilation, ir_lowering, estimation_circuit.num_clbits > circuit.num_clbits)
            raise ResourceEstimatorError(f"Azure QRE estimation failed: {exc}") from exc

        data = result.data()
        physical_counts = data.get("physicalCounts", {})
        logical_counts = data.get("logicalCounts", {})

        return {
            "physical_qubits": physical_counts.get("physicalQubits"),
            "runtime": physical_counts.get("runtime"),
            "rqops": physical_counts.get("rqops"),
            "logical_counts": logical_counts,
            "physical_counts": physical_counts,
            "physical_counts_formatted": data.get("physicalCountsFormatted"),
            "job_params": data.get("jobParams"),
            "report_data": data.get("reportData"),
            "measurement_added_for_qre": estimation_circuit.num_clbits > circuit.num_clbits,
            "qre_input_source": "qiskit_compatibility",
            "qre_mode": self.key,
            "qdk_version": _qdk_version(),
            "logical_ir_lowering": ir_lowering,
            "qre_assumptions": assumptions,
        }

    def _fallback_estimate(
        self,
        compilation: CompilationResult,
        ir_lowering: dict[str, Any],
        measurement_added: bool,
    ) -> dict[str, Any]:
        trace, _ = logical_ir_to_native_qre_trace(compilation.logical_ir)
        physical_model = physical_profile_to_qdk_model(compilation.estimation_context.physical_hardware)
        _, qec_model_summary = _build_qec_model(
            compilation.estimation_context.qec.qec_model_name,
            compilation.estimation_context.qec.qec_model_source,
            compilation.estimation_context.qec.qec_model_parameters,
        )
        estimate = _estimate_trace(
            trace,
            physical_model.metadata,
            qec_model_summary,
            compilation.estimation_context.qec.error_budget,
        )
        assumptions = {
            "qre_execution_model": "qiskit_compatibility",
            "qre_translation_model": "logical_qiskit",
            "logical_ir_lowering": ir_lowering,
            "fallback_mode": "heuristic_without_qdk_qiskit_bridge",
            "qec_model": qec_model_summary,
            "physical_hardware_profile": compilation.estimation_context.physical_hardware.to_dict(),
            "physical_hardware": physical_model.metadata,
        }
        physical_counts = {
            "physicalQubits": estimate["physical_qubits"],
            "runtime": estimate["runtime"],
            "rqops": trace.num_gates,
        }
        return {
            "physical_qubits": physical_counts["physicalQubits"],
            "runtime": physical_counts["runtime"],
            "rqops": physical_counts["rqops"],
            "logical_counts": {"numQubits": trace.total_qubits, "numGates": trace.num_gates},
            "physical_counts": physical_counts,
            "physical_counts_formatted": {"runtime": f'{physical_counts["runtime"]} ns'},
            "job_params": {},
            "report_data": {},
            "measurement_added_for_qre": measurement_added,
            "qre_input_source": "qiskit_compatibility",
            "qre_mode": self.key,
            "qdk_version": _qdk_version(),
            "logical_ir_lowering": ir_lowering,
            "qre_assumptions": assumptions,
        }

    @staticmethod
    def _prepare_estimation_circuit(circuit: QuantumCircuit) -> QuantumCircuit:
        if circuit.num_clbits > 0 or any(instruction.operation.name == "measure" for instruction in circuit.data):
            return circuit

        measured_circuit = circuit.copy()
        measured_circuit.measure_all()
        return measured_circuit


def _qdk_version() -> str:
    try:
        return importlib_metadata.version("qdk")
    except importlib_metadata.PackageNotFoundError:
        return "unknown"
