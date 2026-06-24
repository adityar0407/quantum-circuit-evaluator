from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path
from typing import Any

from backend.services.circuit_service import circuit_from_qasm
from backend.services.compilers.base import CompilationResult, CompilerBackendUnavailable, CompilerError
from backend.services.target_service import build_target


class PandoraCompiler:
    key = "pandora"

    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.python_path = self.repo_root / ".venv-pandora" / "bin" / "python"
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
                "Pandora environment was not found. Expected .venv-pandora/bin/python in the repo root."
            )

        circuit = circuit_from_qasm(qasm)
        target = build_target(target_config)

        try:
            use_database = self._database_is_available()
            completed = subprocess.run(
                [str(self.python_path), str(self.runner_path)],
                input=json.dumps(
                    {
                        "qasm": qasm,
                        "use_database": use_database,
                        "db_config": self.db_config,
                    }
                ),
                capture_output=True,
                check=True,
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

        return CompilationResult(
            compiler=self.key,
            original_circuit=circuit,
            compiled_circuit=compiled_circuit,
            target=target,
            artifacts=artifacts,
            warnings=self._warnings_for_artifacts(artifacts),
        )

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
