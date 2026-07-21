from __future__ import annotations

import sys
import types


def _install_qdk_qiskit_stub() -> None:
    try:
        import qdk  # type: ignore
    except Exception:
        return

    if "qdk.qiskit" in sys.modules:
        return

    try:
        import qdk.qiskit  # type: ignore  # noqa: F401
        return
    except Exception:
        stub = types.ModuleType("qdk.qiskit")

        def estimate(*args, **kwargs):
            raise RuntimeError("qdk.qiskit interop is unavailable in this environment.")

        stub.estimate = estimate  # type: ignore[attr-defined]
        sys.modules["qdk.qiskit"] = stub
        setattr(qdk, "qiskit", stub)


_install_qdk_qiskit_stub()
