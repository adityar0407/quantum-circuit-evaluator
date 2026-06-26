from __future__ import annotations

from typing import Any


def qre_v3_lattice_surgery_status() -> dict[str, Any]:
    try:
        import qdk.qre as qre
        from qdk.qre.application import OpenQASMApplication
        from qdk.qre.models.qec import SurfaceCode
        from qdk.qre.models.qubits import GateBased
    except Exception as exc:
        return {
            "available": False,
            "status": "unavailable",
            "reason": f"qdk.qre import failed: {exc}",
        }

    return {
        "available": True,
        "status": "adapter_pending",
        "reason": (
            "qdk.qre v3 lattice-surgery APIs are installed, but this repository still needs a validated "
            "QecIR-to-QRE Application/Trace/ISA adapter before native QRE pricing can replace local QecIR pricing."
        ),
        "detected_symbols": {
            "estimate": hasattr(qre, "estimate"),
            "LatticeSurgery": hasattr(qre, "LatticeSurgery"),
            "OpenQASMApplication": OpenQASMApplication.__name__,
            "SurfaceCode": SurfaceCode.__name__,
            "GateBased": GateBased.__name__,
        },
        "current_native_flow": None,
        "target_native_flow": "LogicalIR -> QecIR -> QRE Trace/ISA -> QRE estimate",
    }
