from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class LogicalArchitecture:
    topology: str
    logical_qubits_per_node: int
    node_count: int
    logical_gate_set: list[str]
    local_connectivity: str
    inter_node_connectivity: str
    remote_operation_model: str
    communication_capacity: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PhysicalHardwareProfile:
    physical_profile_mode: str = "built_in"
    qdk_hardware_model: str = "gate_based"
    one_qubit_gate_error_rate: float = 1e-4
    sx_gate_error_rate: float | None = None
    two_qubit_gate_error_rate: float = 1e-3
    measurement_error_rate: float = 2e-4
    idle_error_rate: float = 1e-5
    one_qubit_gate_time: float = 50e-9
    sx_gate_time: float | None = None
    two_qubit_gate_time: float = 300e-9
    measurement_time: float = 800e-9
    cycle_time: float = 1e-6
    physical_modality: str = "gate_based"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QecProfile:
    qec_scheme: str = "surface_code"
    error_budget: float = 1e-2
    qec_model_source: str = "azure_builtin"
    qec_model_name: str = "surface_code"
    qec_model_parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NetworkProfile:
    topology: str = "none"
    epr_generation_time: float | None = None
    epr_generation_error: float | None = None
    remote_gate_time: float | None = None
    remote_gate_error: float | None = None
    communication_qubits_per_link: int | None = None
    link_capacity: int | None = None
    classical_feedforward_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EstimationContext:
    logical_architecture: LogicalArchitecture
    physical_hardware: PhysicalHardwareProfile
    qec: QecProfile
    network: NetworkProfile | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "logical_architecture": self.logical_architecture.to_dict(),
            "physical_hardware": self.physical_hardware.to_dict(),
            "qec": self.qec.to_dict(),
        }
        if self.network is not None:
            payload["network"] = self.network.to_dict()
        return payload
