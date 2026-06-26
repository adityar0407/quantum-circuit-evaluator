from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdk.qre.models.qubits import GateBased
from qdk.qre.models.qubits import NeutralAtom

from backend.models.estimation_profiles import PhysicalHardwareProfile
from backend.services.resource_estimators.base import ResourceEstimatorError


CUSTOM_PHYSICAL_FIELDS = (
    "physical_modality",
    "one_qubit_gate_error_rate",
    "two_qubit_gate_error_rate",
    "measurement_error_rate",
    "idle_error_rate",
    "one_qubit_gate_time",
    "two_qubit_gate_time",
    "measurement_time",
    "cycle_time",
)

VERIFIED_QDK_HARDWARE_MODELS = {
    "gate_based": {
        "label": "GateBased",
        "class": "GateBased",
        "description": "QDK gate-based physical qubit model verified with native QRE lattice-surgery traces.",
    },
    "neutral_atom": {
        "label": "NeutralAtom",
        "class": "NeutralAtom",
        "description": "QDK neutral-atom physical qubit model verified with native QRE lattice-surgery traces.",
    },
}

UNSUPPORTED_QDK_HARDWARE_MODELS = {
    "majorana": {
        "label": "Majorana",
        "class": "Majorana",
        "reason": "Majorana instantiates, but the current lattice-surgery trace estimate fails with an unsupported QDK instruction.",
    }
}


@dataclass(frozen=True)
class PhysicalQdkModelMapping:
    model: Any
    metadata: dict[str, Any]


def physical_profile_to_qdk_model(profile: PhysicalHardwareProfile) -> PhysicalQdkModelMapping:
    _validate_profile(profile)

    model_name = profile.qdk_hardware_model.strip().lower()
    if model_name == "gate_based":
        return _gate_based_model(profile)
    if model_name == "neutral_atom":
        return _neutral_atom_model(profile)
    if model_name in UNSUPPORTED_QDK_HARDWARE_MODELS:
        reason = UNSUPPORTED_QDK_HARDWARE_MODELS[model_name]["reason"]
        raise ResourceEstimatorError(f"Unsupported physical hardware model physical_hardware.qdk_hardware_model={model_name}: {reason}")

    supported = ", ".join(sorted(VERIFIED_QDK_HARDWARE_MODELS))
    raise ResourceEstimatorError(
        f"Unsupported physical hardware model physical_hardware.qdk_hardware_model={profile.qdk_hardware_model}. "
        f"Verified models: {supported}."
    )


def physical_profile_capabilities() -> dict[str, Any]:
    return {
        "profile_modes": ["built_in", "custom"],
        "verified_builtin_models": [
            {
                "key": key,
                **value,
                "defaults": _default_profile_for_model(key).to_dict(),
                "supported_qec_models": ["surface_code"],
            }
            for key, value in VERIFIED_QDK_HARDWARE_MODELS.items()
        ],
        "unsupported_models": [
            {"key": key, **value}
            for key, value in UNSUPPORTED_QDK_HARDWARE_MODELS.items()
        ],
        "custom_profile_fields": [
            {"key": "physical_modality", "type": "string", "unit": None, "default": "gate_based"},
            {"key": "one_qubit_gate_error_rate", "type": "probability", "unit": None, "default": 1e-4},
            {"key": "two_qubit_gate_error_rate", "type": "probability", "unit": None, "default": 1e-3},
            {"key": "measurement_error_rate", "type": "probability", "unit": None, "default": 2e-4},
            {"key": "idle_error_rate", "type": "probability", "unit": None, "default": 1e-5},
            {"key": "one_qubit_gate_time", "type": "duration", "unit": "seconds", "default": 50e-9},
            {"key": "two_qubit_gate_time", "type": "duration", "unit": "seconds", "default": 300e-9},
            {"key": "measurement_time", "type": "duration", "unit": "seconds", "default": 800e-9},
            {"key": "cycle_time", "type": "duration", "unit": "seconds", "default": 1e-6},
        ],
        "mapping_notes": [
            "GateBased requires a single QDK error_rate, so the adapter uses max(1Q error, 2Q error, measurement error).",
            "NeutralAtom accepts separate one-qubit, two-qubit/Rydberg, and measurement error/time values.",
            "idle_error_rate and cycle_time are retained for traceability but are currently ignored by both verified QDK hardware models.",
        ],
    }


def _gate_based_model(profile: PhysicalHardwareProfile) -> PhysicalQdkModelMapping:
    error_rate = max(
        profile.one_qubit_gate_error_rate,
        profile.two_qubit_gate_error_rate,
        profile.measurement_error_rate,
    )
    parameters = {
        "error_rate": error_rate,
        "gate_time": _seconds_to_ns_int(profile.one_qubit_gate_time),
        "measurement_time": _seconds_to_ns_int(profile.measurement_time),
        "two_qubit_gate_time": _seconds_to_ns_int(profile.two_qubit_gate_time),
    }
    model = GateBased(**parameters)
    return PhysicalQdkModelMapping(
        model=model,
        metadata=_metadata(
            profile,
            model_key="gate_based",
            model_class="GateBased",
            parameters=parameters,
            mapping={
                "error_rate": [
                    "max(one_qubit_gate_error_rate, two_qubit_gate_error_rate, measurement_error_rate)",
                ],
                "gate_time": ["one_qubit_gate_time seconds -> integer ns"],
                "measurement_time": ["measurement_time seconds -> integer ns"],
                "two_qubit_gate_time": ["two_qubit_gate_time seconds -> integer ns"],
            },
            used_fields=[
                "one_qubit_gate_error_rate",
                "two_qubit_gate_error_rate",
                "measurement_error_rate",
                "one_qubit_gate_time",
                "two_qubit_gate_time",
                "measurement_time",
            ],
            ignored_fields=["physical_modality", "idle_error_rate", "cycle_time"],
            warnings=[
                "QDK GateBased exposes one aggregate error_rate; separate 1Q, 2Q, and measurement errors are reduced with max(...).",
            ],
        ),
    )


def _neutral_atom_model(profile: PhysicalHardwareProfile) -> PhysicalQdkModelMapping:
    parameters = {
        "rydberg_time": _seconds_to_ns_int(profile.two_qubit_gate_time),
        "rydberg_error": profile.two_qubit_gate_error_rate,
        "one_qubit_time": _seconds_to_ns_int(profile.one_qubit_gate_time),
        "one_qubit_error": profile.one_qubit_gate_error_rate,
        "measurement_time": _seconds_to_ns_int(profile.measurement_time),
        "measurement_error": profile.measurement_error_rate,
    }
    model = NeutralAtom(**parameters)
    return PhysicalQdkModelMapping(
        model=model,
        metadata=_metadata(
            profile,
            model_key="neutral_atom",
            model_class="NeutralAtom",
            parameters=parameters,
            mapping={
                "rydberg_time": ["two_qubit_gate_time seconds -> integer ns"],
                "rydberg_error": ["two_qubit_gate_error_rate"],
                "one_qubit_time": ["one_qubit_gate_time seconds -> integer ns"],
                "one_qubit_error": ["one_qubit_gate_error_rate"],
                "measurement_time": ["measurement_time seconds -> integer ns"],
                "measurement_error": ["measurement_error_rate"],
            },
            used_fields=[
                "one_qubit_gate_error_rate",
                "two_qubit_gate_error_rate",
                "measurement_error_rate",
                "one_qubit_gate_time",
                "two_qubit_gate_time",
                "measurement_time",
            ],
            ignored_fields=["physical_modality", "idle_error_rate", "cycle_time"],
            warnings=[],
        ),
    )


def _metadata(
    profile: PhysicalHardwareProfile,
    *,
    model_key: str,
    model_class: str,
    parameters: dict[str, Any],
    mapping: dict[str, list[str]],
    used_fields: list[str],
    ignored_fields: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    submitted = profile.to_dict()
    normalized = {
        **submitted,
        "physical_profile_mode": profile.physical_profile_mode,
        "qdk_hardware_model": model_key,
    }
    return {
        "physical_profile_mode": profile.physical_profile_mode,
        "selected_qdk_hardware_model": model_key,
        "qdk_hardware_model_class": model_class,
        "submitted_physical_profile": submitted,
        "normalized_physical_profile": normalized,
        "normalized_qdk_parameters": parameters,
        "profile_to_qdk_mapping": mapping,
        "used_fields": used_fields,
        "ignored_fields": ignored_fields,
        "defaulted_fields": [] if profile.physical_profile_mode == "custom" else CUSTOM_PHYSICAL_FIELDS,
        "validation_warnings": warnings,
    }


def _validate_profile(profile: PhysicalHardwareProfile) -> None:
    if profile.physical_profile_mode not in {"built_in", "custom"}:
        raise ResourceEstimatorError("Invalid physical_hardware.physical_profile_mode: expected built_in or custom.")
    if profile.physical_modality not in {"gate_based", "neutral_atom", "superconducting", "trapped_ion"}:
        raise ResourceEstimatorError(f"Invalid physical_hardware.physical_modality: {profile.physical_modality}.")
    for field in (
        "one_qubit_gate_error_rate",
        "two_qubit_gate_error_rate",
        "measurement_error_rate",
        "idle_error_rate",
    ):
        value = getattr(profile, field)
        if value < 0 or value > 1:
            raise ResourceEstimatorError(f"Invalid physical_hardware.{field}: must be between 0 and 1.")
    for field in (
        "one_qubit_gate_time",
        "two_qubit_gate_time",
        "measurement_time",
        "cycle_time",
    ):
        value = getattr(profile, field)
        if value <= 0:
            raise ResourceEstimatorError(f"Invalid physical_hardware.{field}: must be greater than 0 seconds.")


def _default_profile_for_model(model_key: str) -> PhysicalHardwareProfile:
    if model_key == "neutral_atom":
        return PhysicalHardwareProfile(
            physical_profile_mode="built_in",
            qdk_hardware_model="neutral_atom",
            physical_modality="neutral_atom",
            one_qubit_gate_error_rate=1e-4,
            two_qubit_gate_error_rate=1e-3,
            measurement_error_rate=1e-4,
            one_qubit_gate_time=1000e-9,
            two_qubit_gate_time=500e-9,
            measurement_time=10000e-9,
        )
    return PhysicalHardwareProfile(physical_profile_mode="built_in", qdk_hardware_model="gate_based")


def _seconds_to_ns_int(value: float) -> int:
    return max(1, int(round(value * 1e9)))
