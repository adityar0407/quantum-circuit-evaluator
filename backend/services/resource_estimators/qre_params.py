from __future__ import annotations

from statistics import fmean
from typing import Any
import warnings

from qdk.estimator import EstimatorParams


DEFAULT_ERROR_BUDGET = 0.001
DEFAULT_QEC_SCHEME = "surface_code"


def build_qre_params(target: Any) -> tuple[EstimatorParams, dict[str, Any]]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        params = EstimatorParams()

    one_q_error, one_q_duration = _summarize_single_qubit_profile(target)
    two_q_error, two_q_duration = _summarize_two_qubit_profile(target)
    measurement_error, measurement_duration = _measurement_assumptions(
        one_q_error=one_q_error,
        one_q_duration=one_q_duration,
    )
    t_error, t_duration, used_t_defaults = _t_gate_profile(
        target=target,
        fallback_error=one_q_error,
        fallback_duration=one_q_duration,
    )

    qubit_params = params.qubit_params
    qubit_params.instruction_set = "gate-based"
    qubit_params.one_qubit_measurement_time = _seconds_to_time_string(measurement_duration)
    qubit_params.one_qubit_measurement_error_rate = measurement_error
    qubit_params.one_qubit_gate_time = _seconds_to_time_string(one_q_duration)
    qubit_params.one_qubit_gate_error_rate = one_q_error
    qubit_params.two_qubit_gate_time = _seconds_to_time_string(two_q_duration)
    qubit_params.two_qubit_gate_error_rate = two_q_error
    qubit_params.t_gate_time = _seconds_to_time_string(t_duration)
    qubit_params.t_gate_error_rate = t_error
    qubit_params.idle_error_rate = measurement_error

    params.qec_scheme.name = DEFAULT_QEC_SCHEME
    params.error_budget = DEFAULT_ERROR_BUDGET

    topology_type = getattr(target, "type", "unknown")
    sq_gate_names = sorted(getattr(target, "sq_gate_dict", {}).keys())
    two_q_gate_names = sorted(getattr(target, "two_q_gate_dict", {}).keys())
    inter_gate_names = sorted(getattr(target, "inter_device_gate_dict", {}).keys())
    modality = _infer_ftarget_modality(sq_gate_names, two_q_gate_names)

    assumptions = {
        "ftarget_topology_type": topology_type,
        "ftarget_modality": modality,
        "ftarget_single_qubit_gates": sq_gate_names,
        "ftarget_two_qubit_gates": two_q_gate_names,
        "ftarget_inter_device_gates": inter_gate_names,
        "qre_error_budget": DEFAULT_ERROR_BUDGET,
        "qre_qec_scheme": DEFAULT_QEC_SCHEME,
        "qre_translation_model": "ftarget_logical_profile_to_gate_based_qre",
        "measurement_error_assumption": measurement_error,
        "measurement_duration_assumption_seconds": measurement_duration,
        "t_gate_profile_source": "native_t_gate" if not used_t_defaults else "single_qubit_fallback",
        "translation_notes": [
            "FTarget is currently treated as a logical-level architecture profile.",
            "QRE still requires a QEC scheme, so the backend injects a default surface-code model for physical estimation.",
            "Single- and two-qubit gate timings/error rates are averaged from the FTarget profile and mapped into QRE gate-based qubit parameters.",
            "Inter-device topology affects QRE indirectly through the compiled circuit, not through a native QRE network-topology model.",
        ],
    }

    return params, assumptions


def _summarize_single_qubit_profile(target: Any) -> tuple[float, float]:
    entries = [
        gate_props
        for gate_props in getattr(target, "sq_gate_dict", {}).values()
        if isinstance(gate_props, dict)
    ]
    return _average_props(entries, "error", "duration", fallback_error=1e-3, fallback_duration=1e-8)


def _summarize_two_qubit_profile(target: Any) -> tuple[float, float]:
    entries = [
        gate_props
        for gate_props in getattr(target, "two_q_gate_dict", {}).values()
        if isinstance(gate_props, dict)
    ]
    return _average_props(
        entries,
        "local_error",
        "local_duration",
        fallback_error=1e-2,
        fallback_duration=1e-7,
    )


def _t_gate_profile(target: Any, fallback_error: float, fallback_duration: float) -> tuple[float, float, bool]:
    t_props = getattr(target, "sq_gate_dict", {}).get("TGate")
    if isinstance(t_props, dict):
        return float(t_props["error"]), float(t_props["duration"]), False

    return fallback_error, fallback_duration, True


def _measurement_assumptions(*, one_q_error: float, one_q_duration: float) -> tuple[float, float]:
    return max(one_q_error, 1e-6), max(one_q_duration * 2, 1e-9)


def _average_props(
    entries: list[dict[str, Any]],
    error_key: str,
    duration_key: str,
    *,
    fallback_error: float,
    fallback_duration: float,
) -> tuple[float, float]:
    errors = [float(entry[error_key]) for entry in entries if error_key in entry]
    durations = [float(entry[duration_key]) for entry in entries if duration_key in entry]

    error = fmean(errors) if errors else fallback_error
    duration = fmean(durations) if durations else fallback_duration
    return error, duration


def _seconds_to_time_string(value: float) -> str:
    if value >= 1:
        return f"{value:g} s"
    if value >= 1e-3:
        return f"{value * 1e3:g} ms"
    if value >= 1e-6:
        return f"{value * 1e6:g} us"
    return f"{value * 1e9:g} ns"


def _infer_ftarget_modality(sq_gate_names: list[str], two_q_gate_names: list[str]) -> str:
    if "TGate" in sq_gate_names:
        return "logical_clifford_t"
    if "CZGate" in two_q_gate_names:
        return "neutral_atom_like"
    if "RXXGate" in two_q_gate_names:
        return "trapped_ion_like"
    if "CXGate" in two_q_gate_names:
        return "gate_based"
    return "custom_gate_profile"
