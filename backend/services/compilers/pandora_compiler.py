from __future__ import annotations

import json
import os
import socket
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import RemoveBarriers

from backend.IR.qasm import export_circuit_to_qasm
from backend.services.circuit_service import circuit_from_qasm
from backend.services.compilers.base import CompilationResult, CompilerBackendUnavailable, CompilerError
from backend.services.compilers.pandora_router import route_circuit_with_target
from backend.services.compilers.pandora_topology import validate_compiled_circuit_against_architecture
from backend.services.target_service import build_target, export_target_topology


class PandoraCompiler:
    key = "pandora"
    supported_topologies = {"tiled_k_nearest", "heavy_hex", "heavy_square"}

    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.python_path = self.repo_root / ".venv" / "bin" / "python"
        self.runner_path = Path(__file__).resolve().with_name("pandora_runner.py")
        self.db_config = {
            "host": "localhost",
            "port": 55432,
            "user": None,
            "database": "pandora",
        }

    def compile(self, qasm: str, target_config: dict[str, Any]) -> CompilationResult:
        if not self.python_path.exists():
            raise CompilerBackendUnavailable(
                "Pandora environment was not found. Expected .venv/bin/python in the repo root."
            )

        circuit = circuit_from_qasm(qasm)
        target = build_target(target_config)
        topology = export_target_topology(target)
        self._ensure_supported_topology(topology)

        normalized_circuit, normalization_artifacts = _normalize_for_pandora_routing(circuit, topology)
        legalized = route_circuit_with_target(normalized_circuit, target, topology)
        legalized_circuit = legalized.circuit
        legalization_artifacts = legalized.artifacts
        legalized_qasm = export_circuit_to_qasm(legalized_circuit)

        support_scan = self._support_scan(legalized_qasm)
        unsupported_operations = support_scan.get("unsupported_operations", [])
        if unsupported_operations:
            supported = ", ".join(support_scan.get("supported_qiskit_gates", []))
            unsupported = ", ".join(unsupported_operations)
            raise CompilerError(
                "Pandora support preflight failed. "
                f"Unsupported operations after topology legalization: {unsupported}. "
                f"Supported Pandora operations: {supported}"
            )

        try:
            use_database = self._database_is_available() and _database_mode_supported_for_circuit(legalized_circuit)
            completed = subprocess.run(
                [str(self.python_path), str(self.runner_path)],
                input=json.dumps(
                    {
                        "qasm": legalized_qasm,
                        "mode": "translate",
                        "use_database": use_database,
                        "db_config": self.db_config,
                    }
                ),
                capture_output=True,
                check=True,
                env=self._subprocess_env(),
                text=True,
                timeout=60,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            raise CompilerError(f"Pandora translation failed: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CompilerError("Pandora translation timed out after 60 seconds.") from exc

        try:
            artifacts = self._load_runner_json(completed.stdout)
        except json.JSONDecodeError as exc:
            raise CompilerError(f"Pandora returned invalid JSON: {completed.stdout}") from exc

        compiled_circuit = legalized_circuit
        if artifacts.get("optimized_qasm"):
            compiled_circuit = circuit_from_qasm(artifacts["optimized_qasm"])
        topology_validation = validate_compiled_circuit_against_architecture(compiled_circuit, topology)
        artifacts.setdefault("database_mode", bool(artifacts.get("database_enabled")))
        artifacts.setdefault("rewrite_passes", artifacts.get("optimization_passes", []))
        artifacts.setdefault("unsupported_operations", [])
        if not use_database and "database_error" not in artifacts:
            artifacts.setdefault("database_skipped_reason", _database_skip_reason(legalized_circuit))
        artifacts["target_topology"] = topology
        artifacts["topology_aware"] = True
        artifacts["basis_normalization"] = normalization_artifacts
        artifacts["topology_lowering"] = legalization_artifacts
        artifacts["topology_validation"] = topology_validation
        artifacts["support_scan"] = support_scan
        artifacts["removed_operations"] = _removed_operations(circuit, compiled_circuit)

        return CompilationResult(
            compiler=self.key,
            original_circuit=circuit,
            compiled_circuit=compiled_circuit,
            target=target,
            artifacts=artifacts,
            warnings=self._warnings_for_artifacts(artifacts),
        )

    def _ensure_supported_topology(self, topology: dict[str, Any]) -> None:
        topology_type = str(topology.get("topology_type", "unknown"))
        if topology_type not in self.supported_topologies:
            supported = ", ".join(sorted(self.supported_topologies))
            raise CompilerError(
                f"Pandora topology-aware compilation currently supports {supported}. "
                f"Received topology type: {topology_type}"
            )

    def _support_scan(self, qasm: str) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                [str(self.python_path), str(self.runner_path)],
                input=json.dumps(
                    {
                        "qasm": qasm,
                        "mode": "support_scan",
                    }
                ),
                capture_output=True,
                check=True,
                env=self._subprocess_env(),
                text=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            raise CompilerError(f"Pandora support preflight failed: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CompilerError("Pandora support preflight timed out after 30 seconds.") from exc

        try:
            return self._load_runner_json(completed.stdout)
        except json.JSONDecodeError as exc:
            raise CompilerError(f"Pandora support preflight returned invalid JSON: {completed.stdout}") from exc

    def _database_is_available(self) -> bool:
        try:
            with socket.create_connection((self.db_config["host"], self.db_config["port"]), timeout=0.5):
                return True
        except OSError:
            return False

    @staticmethod
    def _load_runner_json(stdout: str) -> dict[str, Any]:
        start = stdout.find("{")
        if start == -1:
            raise json.JSONDecodeError("No JSON object found", stdout, 0)

        return json.loads(stdout[start:])

    @staticmethod
    def _warnings_for_artifacts(artifacts: dict[str, Any]) -> list[str]:
        if artifacts.get("database_enabled"):
            return [
                "Pandora legalized the circuit against the selected FTarget topology, loaded it into PostgreSQL, "
                "and ran conservative cancellation rewrites before reconstructing Qiskit output."
            ]

        if artifacts.get("database_error"):
            return [
                "Pandora legalized the circuit against the selected FTarget topology and completed support checks, "
                f"but database-backed rewrites were skipped because Pandora database mode failed: {artifacts['database_error']}."
            ]

        if artifacts.get("database_skipped_reason"):
            return [
                "Pandora legalized the circuit against the selected FTarget topology and completed support checks, "
                f"but database-backed rewrites were skipped: {artifacts['database_skipped_reason']}."
            ]

        return [
            "Pandora legalized the circuit against the selected FTarget topology and completed support checks, "
            "but PostgreSQL was not reachable so database-backed rewrite passes were skipped."
        ]

    def _subprocess_env(self) -> dict[str, str]:
        runtime_dir = self.repo_root / ".tmp" / "pandora-runtime"
        mpl_dir = runtime_dir / "matplotlib"
        cache_dir = runtime_dir / "cache"
        mpl_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.setdefault("MPLBACKEND", "Agg")
        env["MPLCONFIGDIR"] = str(mpl_dir)
        env["XDG_CACHE_HOME"] = str(cache_dir)
        return env


def _removed_operations(original_circuit, compiled_circuit) -> dict[str, int]:
    original_counts = Counter({name: int(count) for name, count in original_circuit.count_ops().items()})
    compiled_counts = Counter({name: int(count) for name, count in compiled_circuit.count_ops().items()})
    removed = original_counts - compiled_counts
    return dict(removed)


def _normalize_for_pandora_routing(circuit: QuantumCircuit, topology: dict[str, Any]) -> tuple[QuantumCircuit, dict[str, Any]]:
    basis_gates = sorted(
        {
            str(name).lower()
            for name in topology.get("native_gate_set", [])
            if str(name).lower() not in {"barrier"}
        }
        | {"measure"}
    )
    before_counts = dict(circuit.count_ops())
    try:
        translated = transpile(
            circuit,
            basis_gates=basis_gates,
            optimization_level=1,
            seed_transpiler=1738,
        )
        normalized = PassManager([RemoveBarriers()]).run(translated)
    except Exception as exc:
        raise CompilerError(
            "Pandora basis normalization failed before topology routing. "
            f"Target basis: {', '.join(basis_gates)}. {exc}"
        ) from exc

    after_counts = dict(normalized.count_ops())
    return normalized, {
        "status": "completed",
        "basis_gates": basis_gates,
        "before_operation_counts": before_counts,
        "after_operation_counts": after_counts,
        "removed_barriers": int(before_counts.get("barrier", 0)),
        "decomposed_operations": sorted(set(before_counts) - set(after_counts) - {"barrier"}),
    }


def _database_mode_supported_for_circuit(circuit: QuantumCircuit) -> bool:
    return int(circuit.count_ops().get("measure", 0)) == 0


def _database_skip_reason(circuit: QuantumCircuit) -> str:
    if int(circuit.count_ops().get("measure", 0)) > 0:
        return "Pandora database reconstruction cannot map measurement gate code 14 back to Qiskit in the installed Pandora package."
    return "Pandora database was not reachable."
