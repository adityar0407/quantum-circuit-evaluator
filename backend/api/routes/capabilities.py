from __future__ import annotations

from fastapi import APIRouter

from backend.hardware.architecture_presets import list_architecture_presets

router = APIRouter()

_FALLBACK_QEC_MODELS = [
    "one_dimensional_yoked_surface_code",
    "surface_code",
    "surface_code_low_move",
    "three_aux",
    "two_dimensional_yoked_surface_code",
]

_FALLBACK_PHYSICAL_HARDWARE = {
    "profile_modes": ["built_in", "custom"],
    "verified_builtin_models": [
        {
            "key": "gate_based",
            "label": "GateBased",
            "class": "GateBased",
            "description": "QDK gate-based physical qubit model verified with native QRE lattice-surgery traces.",
            "defaults": {
                "physical_profile_mode": "built_in",
                "qdk_hardware_model": "gate_based",
                "one_qubit_gate_error_rate": 1e-4,
                "sx_gate_error_rate": None,
                "two_qubit_gate_error_rate": 1e-3,
                "measurement_error_rate": 2e-4,
                "idle_error_rate": 1e-5,
                "one_qubit_gate_time": 50e-9,
                "sx_gate_time": None,
                "two_qubit_gate_time": 300e-9,
                "measurement_time": 800e-9,
                "cycle_time": 1e-6,
                "physical_modality": "gate_based",
            },
            "supported_qec_models": ["surface_code"],
        },
        {
            "key": "neutral_atom",
            "label": "NeutralAtom",
            "class": "NeutralAtom",
            "description": "QDK neutral-atom physical qubit model verified with native QRE lattice-surgery traces.",
            "defaults": {
                "physical_profile_mode": "built_in",
                "qdk_hardware_model": "neutral_atom",
                "physical_modality": "neutral_atom",
                "one_qubit_gate_error_rate": 1e-4,
                "sx_gate_error_rate": None,
                "two_qubit_gate_error_rate": 1e-3,
                "measurement_error_rate": 1e-4,
                "idle_error_rate": 1e-5,
                "one_qubit_gate_time": 1000e-9,
                "sx_gate_time": None,
                "two_qubit_gate_time": 500e-9,
                "measurement_time": 10000e-9,
                "cycle_time": 1e-6,
            },
            "supported_qec_models": ["surface_code"],
        },
    ],
    "unsupported_models": [
        {
            "key": "majorana",
            "label": "Majorana",
            "class": "Majorana",
            "reason": "Majorana instantiates, but the current lattice-surgery trace estimate fails with an unsupported QDK instruction.",
        }
    ],
    "custom_profile_fields": [
        {"key": "physical_modality", "type": "string", "unit": None, "default": "gate_based"},
        {"key": "one_qubit_gate_error_rate", "type": "probability", "unit": None, "default": 1e-4},
        {"key": "sx_gate_error_rate", "type": "probability", "unit": None, "default": None},
        {"key": "two_qubit_gate_error_rate", "type": "probability", "unit": None, "default": 1e-3},
        {"key": "measurement_error_rate", "type": "probability", "unit": None, "default": 2e-4},
        {"key": "idle_error_rate", "type": "probability", "unit": None, "default": 1e-5},
        {"key": "one_qubit_gate_time", "type": "duration", "unit": "seconds", "default": 50e-9},
        {"key": "sx_gate_time", "type": "duration", "unit": "seconds", "default": None},
        {"key": "two_qubit_gate_time", "type": "duration", "unit": "seconds", "default": 300e-9},
        {"key": "measurement_time", "type": "duration", "unit": "seconds", "default": 800e-9},
        {"key": "cycle_time", "type": "duration", "unit": "seconds", "default": 1e-6},
    ],
    "mapping_notes": [
        "Capability metadata is still available when QDK is unavailable locally; estimation itself requires the QDK runtime.",
        "GateBased requires a single QDK error_rate, so the adapter uses max(1Q error, SX error, 2Q error, measurement error).",
        "NeutralAtom accepts separate one-qubit, two-qubit/Rydberg, and measurement error/time values.",
        "idle_error_rate and cycle_time are retained for traceability but are currently ignored by both verified QDK hardware models.",
    ],
}


@router.get("/resource-estimation")
def resource_estimation_capabilities() -> dict:
    physical_hardware, qec_models, native_operations = _load_qre_capabilities()
    return {
        "physical_hardware": physical_hardware,
        "qec_models": qec_models,
        "native_operations": native_operations,
    }


@router.get("/architectures")
def architecture_capabilities() -> dict:
    return {
        "architectures": list_architecture_presets(),
    }


def _load_qre_capabilities() -> tuple[dict, list[str], list[str]]:
    try:
        from backend.services.resource_estimators.native_qre import QDK_QEC_MODELS
        from backend.services.resource_estimators.native_qre import SUPPORTED_NATIVE_OPERATIONS
        from backend.services.resource_estimators.physical_qdk_adapter import physical_profile_capabilities
    except ModuleNotFoundError:
        return _FALLBACK_PHYSICAL_HARDWARE, _FALLBACK_QEC_MODELS, [
            "BARRIER",
            "CX",
            "H",
            "MEASURE",
            "RESET",
            "RX",
            "RY",
            "RZ",
            "S",
            "SDG",
            "SWAP",
            "SX",
            "T",
            "TDG",
            "X",
            "Z",
        ]

    return physical_profile_capabilities(), sorted(QDK_QEC_MODELS), sorted(SUPPORTED_NATIVE_OPERATIONS)
