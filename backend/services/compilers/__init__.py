from __future__ import annotations

from backend.services.compilers.base import CompilerBackend, CompilerError
from backend.services.compilers.pandora_compiler import PandoraCompiler
from backend.services.compilers.qiskit_ftarget import QiskitFTargetCompiler


def get_compiler_backend(key: str) -> CompilerBackend:
    compilers: dict[str, CompilerBackend] = {
        QiskitFTargetCompiler.key: QiskitFTargetCompiler(),
        PandoraCompiler.key: PandoraCompiler(),
    }

    try:
        return compilers[key]
    except KeyError as exc:
        supported = ", ".join(sorted(compilers))
        raise CompilerError(f"Unsupported compiler backend '{key}'. Supported backends: {supported}") from exc
