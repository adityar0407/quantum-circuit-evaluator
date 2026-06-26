from __future__ import annotations

import json
import os
import socket
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from backend.services.circuit_service import circuit_from_qasm
from backend.services.compilers.base import CompilationResult, CompilerBackendUnavailable, CompilerError
from backend.services.target_service import build_target


class PandoraCompiler:
    key = "pandora"

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
        support_scan = self._support_scan(qasm)
        unsupported_operations = support_scan.get("unsupported_operations", [])
        if unsupported_operations:
            supported = ", ".join(support_scan.get("supported_qiskit_gates", []))
            unsupported = ", ".join(unsupported_operations)
            raise CompilerError(
                "Pandora support preflight failed. "
                f"Unsupported operations: {unsupported}. "
                f"Supported Pandora operations: {supported}"
            )

        try:
            use_database = self._database_is_available()
            completed = subprocess.run(
                [str(self.python_path), str(self.runner_path)],
                input=json.dumps(
                    {
                        "qasm": qasm,
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

        compiled_circuit = circuit
        if artifacts.get("optimized_qasm"):
            compiled_circuit = circuit_from_qasm(artifacts["optimized_qasm"])
        artifacts.setdefault("database_mode", bool(artifacts.get("database_enabled")))
        artifacts.setdefault("translation_only_status", not bool(artifacts.get("database_enabled")))
        artifacts.setdefault("rewrite_passes", artifacts.get("optimization_passes", []))
        artifacts.setdefault("unsupported_operations", [])
        artifacts["removed_operations"] = _removed_operations(circuit, compiled_circuit)

        return CompilationResult(
            compiler=self.key,
            original_circuit=circuit,
            compiled_circuit=compiled_circuit,
            target=target,
            artifacts=artifacts,
            warnings=self._warnings_for_artifacts(artifacts),
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
                "Pandora PostgreSQL mode loaded the circuit and ran conservative cancellation rewrites. "
                "The optimized circuit was reconstructed into Qiskit form for downstream metrics."
            ]

        return [
            "Pandora backend performed translation/support checks only because PostgreSQL was not reachable."
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
