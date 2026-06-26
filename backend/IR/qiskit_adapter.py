from __future__ import annotations

from math import pi
from typing import Any

from qiskit import QuantumCircuit

from backend.IR.models.logical_ir import LogicalIR
from backend.IR.models.logical_ir import LogicalInstruction


class LogicalIrToQiskitError(ValueError):
    """Raised when a logical IR operation cannot be represented as a Qiskit circuit."""


def logical_ir_to_qiskit_circuit(logical_ir: LogicalIR) -> tuple[QuantumCircuit, dict[str, Any]]:
    circuit = QuantumCircuit(logical_ir.logical_qubit_count, logical_ir.classical_bit_count)
    remote_ops_lowered_as_base_gate = 0
    unsupported_operations: list[str] = []

    for operation in logical_ir.operations:
        try:
            _apply_operation(circuit, operation)
        except LogicalIrToQiskitError:
            unsupported_operations.append(operation.operation)

        if operation.op_kind == "two_qubit_remote":
            remote_ops_lowered_as_base_gate += 1

    if unsupported_operations:
        unique = sorted(set(unsupported_operations))
        raise LogicalIrToQiskitError(
            f"Unable to lower LogicalIR operations into Qiskit for QRE: {', '.join(unique)}"
        )

    return circuit, {
        "source": "logical_ir_v1",
        "remote_ops_lowered_as_base_gate": remote_ops_lowered_as_base_gate,
        "lowering_notes": [
            "Azure QRE receives a gate-based Qiskit circuit materialized from LogicalIR v1.",
            "REMOTE_* operations are lowered to their base logical gate for QRE submission.",
            "Remote protocol overhead remains unmodeled and is not included in Azure QRE resource counts.",
        ],
    }


def _apply_operation(circuit: QuantumCircuit, operation: LogicalInstruction) -> None:
    gate = operation.base_operation.lower()
    qargs = operation.qargs
    cargs = operation.cargs
    params = operation.parameters

    if gate == "barrier":
        circuit.barrier(*qargs)
    elif gate == "measure":
        if not qargs or not cargs:
            raise LogicalIrToQiskitError("Measurement operation requires qargs and cargs.")
        circuit.measure(qargs, cargs)
    elif gate == "reset":
        for qubit in qargs:
            circuit.reset(qubit)
    elif gate == "h":
        circuit.h(qargs[0])
    elif gate == "x":
        circuit.x(qargs[0])
    elif gate == "y":
        circuit.y(qargs[0])
    elif gate == "z":
        circuit.z(qargs[0])
    elif gate == "sx":
        circuit.sx(qargs[0])
    elif gate == "s":
        circuit.s(qargs[0])
    elif gate == "sdg":
        circuit.sdg(qargs[0])
    elif gate == "t":
        circuit.t(qargs[0])
    elif gate == "tdg":
        circuit.tdg(qargs[0])
    elif gate == "rx":
        circuit.rx(_param(params, 0), qargs[0])
    elif gate == "ry":
        circuit.ry(_param(params, 0), qargs[0])
    elif gate == "rz":
        circuit.rz(_param(params, 0), qargs[0])
    elif gate in {"p", "phase"}:
        circuit.p(_param(params, 0), qargs[0])
    elif gate == "cx":
        circuit.cx(qargs[0], qargs[1])
    elif gate == "cz":
        circuit.cz(qargs[0], qargs[1])
    elif gate == "swap":
        circuit.swap(qargs[0], qargs[1])
    elif gate == "rxx":
        circuit.rxx(_param(params, 0), qargs[0], qargs[1])
    elif gate == "delay":
        # Delays are scheduling artifacts. QRE consumes operation counts, so skip them.
        return
    else:
        raise LogicalIrToQiskitError(f"Unsupported LogicalIR operation: {operation.operation}")


def _param(params: list[float | str], index: int) -> float:
    if len(params) <= index:
        return pi
    value = params[index]
    if isinstance(value, (int, float)):
        return float(value)
    if value == "pi":
        return pi
    try:
        return float(value)
    except ValueError as exc:
        raise LogicalIrToQiskitError(f"Unsupported symbolic parameter: {value}") from exc
