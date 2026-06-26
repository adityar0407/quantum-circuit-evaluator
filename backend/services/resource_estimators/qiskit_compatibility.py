from __future__ import annotations

import warnings
import importlib.metadata as importlib_metadata
from typing import Any

from qdk.estimator import EstimatorError
from qiskit import QuantumCircuit

from backend.IR.qiskit_adapter import LogicalIrToQiskitError
from backend.IR.qiskit_adapter import logical_ir_to_qiskit_circuit
from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.base import ResourceEstimatorError
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
                from qdk.qiskit import estimate as qre_estimate

                warnings.simplefilter("ignore", category=DeprecationWarning)
                result = qre_estimate(estimation_circuit, params=params)
        except EstimatorError as exc:
            raise ResourceEstimatorError(f"Azure QRE estimation failed: {exc}") from exc
        except Exception as exc:
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
