from __future__ import annotations

from typing import Any

from backend.models.estimation_profiles import EstimationContext
from backend.models.estimation_profiles import LogicalArchitecture
from backend.models.estimation_profiles import NetworkProfile
from backend.models.estimation_profiles import PhysicalHardwareProfile
from backend.models.estimation_profiles import QecProfile


def build_estimation_context(target: Any, profile_overrides: dict[str, Any] | None = None) -> EstimationContext:
    overrides = profile_overrides or {}

    physical_hardware = _build_physical_hardware_profile(overrides.get("physical_hardware"))
    qec = _build_qec_profile(overrides.get("qec"))
    network = _build_network_profile(overrides.get("network"))

    return EstimationContext(
        logical_architecture=_build_logical_architecture(target),
        physical_hardware=physical_hardware,
        qec=qec,
        network=network,
    )


def _build_logical_architecture(target: Any) -> LogicalArchitecture:
    logical_gate_set = sorted(getattr(target, "operation_names", []))
    topology = str(getattr(target, "type", "unknown"))
    node_count = _node_count(target)
    logical_qubits_per_node = int(getattr(target, "n_block", getattr(target, "total_qubits", 0)))
    local_connectivity = _local_connectivity_label(target)
    inter_node_connectivity = _inter_node_connectivity_label(target)
    remote_operation_model = _remote_operation_model(target)
    communication_capacity = _communication_capacity(target)

    return LogicalArchitecture(
        topology=topology,
        logical_qubits_per_node=logical_qubits_per_node,
        node_count=node_count,
        logical_gate_set=logical_gate_set,
        local_connectivity=local_connectivity,
        inter_node_connectivity=inter_node_connectivity,
        remote_operation_model=remote_operation_model,
        communication_capacity=communication_capacity,
    )


def _build_physical_hardware_profile(raw: Any) -> PhysicalHardwareProfile:
    payload = _as_dict(raw)
    mode = str(payload.get("physical_profile_mode", PhysicalHardwareProfile.physical_profile_mode))
    if mode == "custom":
        required = (
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
        for field in required:
            if field not in payload or payload.get(field) in {None, ""}:
                raise ValueError(f"Missing custom physical hardware field: physical_hardware.{field}")

    return PhysicalHardwareProfile(
        physical_profile_mode=mode,
        qdk_hardware_model=str(payload.get("qdk_hardware_model", PhysicalHardwareProfile.qdk_hardware_model)),
        one_qubit_gate_error_rate=float(payload.get("one_qubit_gate_error_rate", PhysicalHardwareProfile.one_qubit_gate_error_rate)),
        two_qubit_gate_error_rate=float(payload.get("two_qubit_gate_error_rate", PhysicalHardwareProfile.two_qubit_gate_error_rate)),
        measurement_error_rate=float(payload.get("measurement_error_rate", PhysicalHardwareProfile.measurement_error_rate)),
        idle_error_rate=float(payload.get("idle_error_rate", PhysicalHardwareProfile.idle_error_rate)),
        one_qubit_gate_time=float(payload.get("one_qubit_gate_time", PhysicalHardwareProfile.one_qubit_gate_time)),
        two_qubit_gate_time=float(payload.get("two_qubit_gate_time", PhysicalHardwareProfile.two_qubit_gate_time)),
        measurement_time=float(payload.get("measurement_time", PhysicalHardwareProfile.measurement_time)),
        cycle_time=float(payload.get("cycle_time", PhysicalHardwareProfile.cycle_time)),
        physical_modality=str(payload.get("physical_modality", PhysicalHardwareProfile.physical_modality)),
    )


def _build_qec_profile(raw: Any) -> QecProfile:
    payload = _as_dict(raw)
    qec_model_name = str(payload.get("qec_model_name", payload.get("qec_scheme", QecProfile.qec_model_name)))
    return QecProfile(
        qec_scheme=str(payload.get("qec_scheme", qec_model_name)),
        error_budget=float(payload.get("error_budget", QecProfile.error_budget)),
        qec_model_source=str(payload.get("qec_model_source", QecProfile.qec_model_source)),
        qec_model_name=qec_model_name,
        qec_model_parameters=_as_dict(payload.get("qec_model_parameters")),
    )


def _build_network_profile(raw: Any) -> NetworkProfile | None:
    payload = _as_dict(raw)
    if not payload:
        return None

    return NetworkProfile(
        topology=str(payload.get("topology", NetworkProfile.topology)),
        epr_generation_time=_optional_float(payload.get("epr_generation_time")),
        epr_generation_error=_optional_float(payload.get("epr_generation_error")),
        remote_gate_time=_optional_float(payload.get("remote_gate_time")),
        remote_gate_error=_optional_float(payload.get("remote_gate_error")),
        communication_qubits_per_link=_optional_int(payload.get("communication_qubits_per_link")),
        link_capacity=_optional_int(payload.get("link_capacity")),
        classical_feedforward_time=_optional_float(payload.get("classical_feedforward_time")),
    )


def _node_count(target: Any) -> int:
    if hasattr(target, "n_blocks_row") and hasattr(target, "n_blocks_col"):
        return int(target.n_blocks_row * target.n_blocks_col)
    return 1


def _local_connectivity_label(target: Any) -> str:
    if getattr(target, "type", "") == "tiled_k_nearest":
        return f"k_intra={getattr(target, 'k_intra', 'unknown')}"
    return str(getattr(target, "type", "custom"))


def _inter_node_connectivity_label(target: Any) -> str:
    inter_gate_dict = getattr(target, "inter_device_gate_dict", {})
    if not inter_gate_dict:
        return "none"
    if getattr(target, "type", "") == "tiled_k_nearest":
        return f"k_inter={getattr(target, 'k_inter', 'unknown')}"
    return "configured"


def _remote_operation_model(target: Any) -> str:
    inter_gate_dict = getattr(target, "inter_device_gate_dict", {})
    if not inter_gate_dict:
        return "none"
    return ",".join(sorted(inter_gate_dict.keys()))


def _communication_capacity(target: Any) -> int | None:
    if hasattr(target, "connector_local"):
        return int(target.connector_local)
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
