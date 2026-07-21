from __future__ import annotations

import json
import sys
import traceback
from collections import Counter
from contextlib import suppress

from qiskit import QuantumCircuit
from qiskit import qasm2

from pandora.db.core import PandoraDB
from pandora.db.repository import GateRepository
from pandora.db.service import PandoraService
from pandora.optimisation.optimiser import PandoraOptimiser
from pandora.translation.qiskit_translator import QiskitToPandoraTranslator
from pandora.translation.translator import PandoraGateTranslator, QISKIT_TO_PANDORA
from pandora.util.circuit_util import remove_io_gates


def circuit_summary(circuit: QuantumCircuit) -> dict:
    return {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "depth": circuit.depth(),
        "gate_count": circuit.size(),
        "operation_counts": dict(circuit.count_ops()),
    }


async def run_database_mode(payload: dict) -> dict:
    circuit = QuantumCircuit.from_qasm_str(payload["qasm"])
    db_config = payload["db_config"]
    db = PandoraDB(db_config, min_size=1, max_size=payload.get("max_pool_size", 4))
    await db.connect()

    try:
        repo = GateRepository(db)
        service = PandoraService(
            db,
            repo,
            decomposition_window_size=payload.get("window_size", 10_000),
        )
        await service.build_circuit(circuit)

        before = await repo.fetch_all()
        optimiser = PandoraOptimiser(
            db,
            timeout=payload.get("rewrite_timeout", 10),
            pass_count=payload.get("rewrite_pass_count", 1),
            max_concurrency=payload.get("max_concurrency", 1),
        )
        optimiser.cancel_single_qubit_gates(
            (PandoraGateTranslator.HPowGate, PandoraGateTranslator.HPowGate),
            dedicated_nproc=1,
        )
        optimiser.cancel_two_qubit_gates(
            (PandoraGateTranslator.CXPowGate, PandoraGateTranslator.CXPowGate),
            dedicated_nproc=1,
        )
        await optimiser.start()

        after = await repo.fetch_all()
        optimized_circuit = await service.load_circuit("qiskit")
        optimized_circuit = remove_io_gates(optimized_circuit, type="qiskit")

        return {
            "database_enabled": True,
            "database_config": {
                "host": db_config.get("host", "localhost"),
                "port": db_config.get("port", 5432),
                "database": db_config.get("database", "postgres"),
                "user": db_config.get("user"),
            },
            "db_gate_rows_before": len(before),
            "db_gate_rows_after": len(after),
            "db_gate_type_counts_before": dict(Counter(str(gate.type) for gate in before)),
            "db_gate_type_counts_after": dict(Counter(str(gate.type) for gate in after)),
            "optimized_summary": circuit_summary(optimized_circuit),
            "optimized_qasm": qasm2.dumps(optimized_circuit),
            "optimization_passes": [
                "cancel_adjacent_h_pairs",
                "cancel_adjacent_cx_pairs",
            ],
        }
    finally:
        with suppress(Exception):
            await db.close()


def run_translation_mode(payload: dict) -> dict:
    circuit = QuantumCircuit.from_qasm_str(payload["qasm"])
    translator = QiskitToPandoraTranslator()
    pandora_gate_codes = []
    unsupported_operations = sorted(
        {
            instruction.operation.name
            for instruction in circuit.data
            if instruction.operation.name not in QISKIT_TO_PANDORA
        }
    )

    for instruction in circuit.data:
        pandora_gate = translator.translate(instruction)
        pandora_gate_codes.append(pandora_gate.type)

    return {
        "summary": circuit_summary(circuit),
        "supported_qiskit_gates": sorted(QISKIT_TO_PANDORA.keys()),
        "unsupported_operations": unsupported_operations,
        "pandora_gate_code_counts": dict(Counter(pandora_gate_codes)),
        "translation_only": not payload.get("use_database", False),
    }


def run_support_scan_mode(payload: dict) -> dict:
    circuit = QuantumCircuit.from_qasm_str(payload["qasm"])
    operations = sorted({instruction.operation.name for instruction in circuit.data})
    unsupported_operations = sorted(
        operation_name
        for operation_name in operations
        if operation_name not in QISKIT_TO_PANDORA
    )

    return {
        "operations": operations,
        "supported_qiskit_gates": sorted(QISKIT_TO_PANDORA.keys()),
        "unsupported_operations": unsupported_operations,
    }


def main() -> int:
    import asyncio

    payload = json.load(sys.stdin)
    mode = payload.get("mode", "translate")
    if mode == "support_scan":
        result = run_support_scan_mode(payload)
    else:
        result = run_translation_mode(payload)
    if mode == "translate" and payload.get("use_database"):
        try:
            result.update(asyncio.run(run_database_mode(payload)))
        except Exception as exc:
            result.update(
                {
                    "database_enabled": False,
                    "database_mode": False,
                    "database_error": f"{type(exc).__name__}: {exc}",
                    "database_traceback": traceback.format_exc(),
                    "translation_only": True,
                    "optimization_passes": [],
                }
            )

    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
