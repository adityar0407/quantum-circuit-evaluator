from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from qiskit.transpiler import CouplingMap

from hardware.connectivity import (
    build_ft_style_coupling_map,
    load_ibm_fez_coupling_map,
    load_ibm_torino_coupling_map,
)


@dataclass(frozen=True)
class ArchitectureProfile:
    """
    Benchmark architecture profile.

    Weight fields are model assumptions for the current compiler score only.
    They are not calibrated hardware runtime or fidelity predictions.
    """

    name: str
    profile: str
    coupling_map: CouplingMap
    backend_name: str | None
    fallback_basis_gates: Sequence[str]
    gate_weights: Mapping[str, float]
    depth_weight: float
    unmapped_gate_penalty: float
    cost_model_source: str


SUPERCONDUCTING_PLACEHOLDER_WEIGHTS = {
    "rz": 0.0,
    "sx": 1.0,
    "x": 1.0,
    "cx": 10.0,
    "swap": 30.0,
}

FT_STYLE_LOGICAL_PLACEHOLDER_WEIGHTS = {
    "h": 1.0,
    "s": 1.0,
    "sdg": 1.0,
    "cx": 2.0,
    "swap": 6.0,
    "t": 50.0,
    "tdg": 50.0,
}

IBM_HEAVY_HEX_FALLBACK_BASIS = ("rz", "sx", "x", "cx", "id", "swap")
FT_STYLE_LOGICAL_BASIS = ("h", "s", "sdg", "cx", "t", "tdg", "swap")

PLACEHOLDER_COST_MODEL_SOURCE = "placeholder compiler score model"


def get_benchmark_architecture_profiles() -> list[ArchitectureProfile]:
    """
    Return the architecture profiles used by the main benchmark.

    IBM profiles currently use frozen CSV connectivity maps plus placeholder
    score weights. Backend-derived targets/properties should replace those
    placeholders when IBM Runtime access is configured.
    """
    return [
        ArchitectureProfile(
            name="IBM Fez heavy-hex",
            profile="ibm_heavy_hex",
            coupling_map=load_ibm_fez_coupling_map(),
            backend_name="ibm_fez",
            fallback_basis_gates=IBM_HEAVY_HEX_FALLBACK_BASIS,
            gate_weights=SUPERCONDUCTING_PLACEHOLDER_WEIGHTS,
            depth_weight=0.1,
            unmapped_gate_penalty=100.0,
            cost_model_source=PLACEHOLDER_COST_MODEL_SOURCE,
        ),
        ArchitectureProfile(
            name="IBM Torino heavy-hex",
            profile="ibm_heavy_hex",
            coupling_map=load_ibm_torino_coupling_map(),
            backend_name="ibm_torino",
            fallback_basis_gates=IBM_HEAVY_HEX_FALLBACK_BASIS,
            gate_weights=SUPERCONDUCTING_PLACEHOLDER_WEIGHTS,
            depth_weight=0.1,
            unmapped_gate_penalty=100.0,
            cost_model_source=PLACEHOLDER_COST_MODEL_SOURCE,
        ),
        ArchitectureProfile(
            name="Custom FT-style tiled k-nearest",
            profile="ft_style_logical",
            coupling_map=build_ft_style_coupling_map(k_intra=2, k_inter=1),
            backend_name=None,
            fallback_basis_gates=FT_STYLE_LOGICAL_BASIS,
            gate_weights=FT_STYLE_LOGICAL_PLACEHOLDER_WEIGHTS,
            depth_weight=0.1,
            unmapped_gate_penalty=100.0,
            cost_model_source=PLACEHOLDER_COST_MODEL_SOURCE,
        ),
    ]
