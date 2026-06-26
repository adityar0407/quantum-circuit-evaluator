#!/usr/bin/env python3

from __future__ import annotations

import shutil
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


def ensure_exists(path: Path, description: str) -> None:
    if not path.exists():
        raise SystemExit(f"{description} not found: {path}")


def ensure_port_free(port: int, label: str) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"{label} port {port} is already in use. Stop the existing process and rerun `npm run dev`.")


def pump_output(stream, prefix: str) -> None:
    try:
        for line in iter(stream.readline, ""):
            sys.stdout.write(f"[{prefix}] {line}")
    finally:
        stream.close()


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    ensure_exists(VENV_PYTHON, "Virtualenv Python")
    if shutil.which("npm") is None:
        raise SystemExit("npm is not available on PATH.")

    ensure_port_free(8000, "Backend")
    ensure_port_free(4173, "Frontend")

    backend = subprocess.Popen(
        [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "backend.api.app:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    frontend = subprocess.Popen(
        [
            "npm",
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            "4173",
            "--strictPort",
        ],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    threads = [
        threading.Thread(target=pump_output, args=(backend.stdout, "backend"), daemon=True),
        threading.Thread(target=pump_output, args=(frontend.stdout, "frontend"), daemon=True),
    ]
    for thread in threads:
        thread.start()

    processes = [backend, frontend]

    def shutdown(*_args) -> None:
        for process in processes:
            terminate_process(process)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        for process, name in ((backend, "Backend"), (frontend, "Frontend")):
            code = process.poll()
            if code is not None:
                other = frontend if process is backend else backend
                terminate_process(other)
                return code if code != 0 else 1
        try:
            backend.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            continue


if __name__ == "__main__":
    raise SystemExit(main())
