from __future__ import annotations

from copy import deepcopy
from typing import Any


def list_architecture_presets() -> list[dict[str, Any]]:
    return [deepcopy(preset) for preset in _ARCHITECTURE_PRESETS]


def get_architecture_preset(preset_id: str) -> dict[str, Any]:
    for preset in _ARCHITECTURE_PRESETS:
        if preset["id"] == preset_id:
            return deepcopy(preset)
    supported = ", ".join(sorted(preset["id"] for preset in _ARCHITECTURE_PRESETS))
    raise KeyError(f"Unknown architecture preset '{preset_id}'. Supported presets: {supported}")


def resolve_architecture_config(
    preset_id: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preset = get_architecture_preset(preset_id)
    config = deepcopy(preset["target_config"])
    metadata = {
        "architecture_preset": preset["id"],
        "display_name": preset["display_name"],
        "category": preset["category"],
        "implemented_as": preset["implemented_as"],
        "references": deepcopy(preset["references"]),
        "limitations": deepcopy(preset["limitations"]),
        "support_status": preset["support_status"],
    }
    config["architecture_metadata"] = metadata

    if overrides:
        _deep_update(config, overrides)
    return config


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = deepcopy(value)


_LOGICAL_SURFACE_PROFILE = {
    "sq_gates": {
        "HGate": {"logical_weight": 1, "logical_preference": 1},
        "TGate": {"logical_weight": 2, "logical_preference": 1.2},
        "XGate": {"logical_weight": 1, "logical_preference": 1},
    },
    "two_q_gates": {
        "CXGate": {"logical_weight": 3, "routing_preference": 2},
        "SwapGate": {"logical_weight": 4, "routing_preference": 2.5},
    },
    "inter_device_gates": {},
}

_SUPERCONDUCTING_PROFILE = {
    "sq_gates": {
        "HGate": {"logical_weight": 1, "logical_preference": 1},
        "XGate": {"logical_weight": 1, "logical_preference": 1},
        "RZGate": {"logical_weight": 0.5, "logical_preference": 0.8},
    },
    "two_q_gates": {
        "CXGate": {"logical_weight": 3, "routing_preference": 2},
        "SwapGate": {"logical_weight": 4, "routing_preference": 2.5},
    },
    "inter_device_gates": {},
}

_NEUTRAL_ATOM_PROFILE = {
    "sq_gates": {
        "RXGate": {"logical_weight": 1, "logical_preference": 1},
        "RYGate": {"logical_weight": 1, "logical_preference": 1},
        "RZGate": {"logical_weight": 0.5, "logical_preference": 0.8},
    },
    "two_q_gates": {
        "CZGate": {"logical_weight": 3, "routing_preference": 2},
        "SwapGate": {"logical_weight": 4, "routing_preference": 2.5},
    },
    "inter_device_gates": {},
}

_TRAPPED_ION_PROFILE = {
    "sq_gates": {
        "RXGate": {"logical_weight": 1, "logical_preference": 1},
        "RYGate": {"logical_weight": 1, "logical_preference": 1},
        "RZGate": {"logical_weight": 0.5, "logical_preference": 0.8},
    },
    "two_q_gates": {
        "CXGate": {"logical_weight": 3, "routing_preference": 2},
        "SwapGate": {"logical_weight": 4, "routing_preference": 2.5},
    },
    "inter_device_gates": {
        "SwapGate": {"logical_weight": 5, "routing_preference": 3},
    },
}


_ARCHITECTURE_PRESETS: list[dict[str, Any]] = [
    {
        "id": "square_grid_surface_code",
        "display_name": "Square Grid Surface Code",
        "category": "superconducting_surface_code",
        "implemented_as": "tiled_k_nearest",
        "support_status": "supported",
        "references": [
            "research/papers/square_grid_surface_code/quantum_error_correction_below_surface_code_threshold_2408.13687.pdf",
            "research/papers/square_grid_surface_code/suppressing_quantum_errors_by_scaling_surface_code_2207.06431.pdf",
        ],
        "limitations": [
            "Uses the existing Manhattan nearest-neighbor tiled generator as a surface-code square lattice model.",
            "Captures connectivity and logical gate assumptions, not calibration-cycle timing or decoder latency.",
        ],
        "target_config": {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 1,
                "n_blocks_col": 1,
                "n": 7,
                "m": 7,
                "k_intra": 1,
                "k_inter": 1,
                "connector_local": 1,
            },
            "profile": deepcopy(_LOGICAL_SURFACE_PROFILE),
        },
    },
    {
        "id": "heavy_hex",
        "display_name": "Heavy Hex",
        "category": "sparse_superconducting",
        "implemented_as": "heavy_hex",
        "support_status": "supported",
        "references": [
            "research/papers/heavy_hex_sparse_superconducting/creating_entangled_logical_qubits_heavy_hex_2404.15989.pdf",
            "research/papers/heavy_hex_sparse_superconducting/linear_depth_qft_ibm_heavy_hex_2402.09705.pdf",
        ],
        "limitations": [
            "Uses the existing heavy_hex topology generator.",
            "Models heavy-hex as a sparse coupling graph rather than a pulse-scheduled device family.",
        ],
        "target_config": {
            "topology": {
                "type": "heavy_hex",
                "d": 3,
                "n_blocks_row": 1,
                "n_blocks_col": 1,
                "k_inter": 1,
            },
            "profile": deepcopy(_SUPERCONDUCTING_PROFILE),
        },
    },
    {
        "id": "superconducting_topology_suite",
        "display_name": "Superconducting Topology Suite",
        "category": "comparison_suite",
        "implemented_as": "tiled_k_nearest",
        "support_status": "supported",
        "references": [
            "research/papers/superconducting_topology_comparison/comparison_of_superconducting_nisq_architectures_2409.02063.pdf",
        ],
        "limitations": [
            "Represents a generic square-like superconducting baseline for architecture comparison.",
            "The paper compares multiple hardware graphs; this preset supplies one baseline buildable topology rather than the entire suite.",
        ],
        "target_config": {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 1,
                "n_blocks_col": 1,
                "n": 5,
                "m": 5,
                "k_intra": 1,
                "k_inter": 1,
                "connector_local": 1,
            },
            "profile": deepcopy(_SUPERCONDUCTING_PROFILE),
        },
    },
    {
        "id": "modular_superconducting",
        "display_name": "Modular Superconducting",
        "category": "modular_superconducting",
        "implemented_as": "tiled_k_nearest",
        "support_status": "supported",
        "references": [
            "research/papers/modular_superconducting/codesigned_superconducting_architecture_lattice_surgery_2312.01246.pdf",
            "research/papers/modular_superconducting/modular_superconducting_qubit_architecture_multichip_tunable_coupler_2308.09240.pdf",
        ],
        "limitations": [
            "Approximates multi-chip modular superconducting systems as a tiled block network with explicit inter-block links.",
            "Does not yet encode coupler-specific bandwidth or control-routing contention.",
        ],
        "target_config": {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 2,
                "n_blocks_col": 2,
                "n": 5,
                "m": 5,
                "k_intra": 1,
                "k_inter": 1,
                "connector_local": 2,
            },
            "profile": deepcopy(_SUPERCONDUCTING_PROFILE),
        },
    },
    {
        "id": "modular_distributed_surface_code",
        "display_name": "Modular Distributed Surface Code",
        "category": "distributed_surface_code",
        "implemented_as": "tiled_k_nearest",
        "support_status": "supported",
        "references": [
            "research/papers/modular_distributed_surface_code/modular_architectures_and_entanglement_schemes_2408.02837.pdf",
            "research/papers/modular_distributed_surface_code/large_scale_modular_quantum_computer_architecture_1208.0391.pdf",
        ],
        "limitations": [
            "Uses tiled modules plus explicit inter-device swap links as a distributed surface-code approximation.",
            "Entanglement generation rates and heralded-photonic link failure are not yet modeled in the connectivity layer.",
        ],
        "target_config": {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 2,
                "n_blocks_col": 3,
                "n": 3,
                "m": 3,
                "k_intra": 1,
                "k_inter": 1,
                "connector_local": 1,
            },
            "profile": {
                "sq_gates": deepcopy(_LOGICAL_SURFACE_PROFILE["sq_gates"]),
                "two_q_gates": deepcopy(_LOGICAL_SURFACE_PROFILE["two_q_gates"]),
                "inter_device_gates": {
                    "SwapGate": {"logical_weight": 6, "routing_preference": 3.5},
                },
            },
        },
    },
    {
        "id": "neutral_atom_reconfigurable",
        "display_name": "Neutral Atom Reconfigurable",
        "category": "neutral_atom",
        "implemented_as": "tiled_k_nearest",
        "support_status": "approximate",
        "references": [
            "research/papers/neutral_atom_reconfigurable/atomique_quantum_compiler_reconfigurable_neutral_atom_arrays_2311.15123.pdf",
            "research/papers/neutral_atom_reconfigurable/compiling_quantum_circuits_dynamic_field_programmable_neutral_atoms_2306.03487.pdf",
            "research/papers/neutral_atom_reconfigurable/logical_quantum_processor_reconfigurable_atom_arrays_2312.03982.pdf",
        ],
        "limitations": [
            "Approximates reconfigurable neutral-atom arrays as a dense 2D tiled graph with CZ-native interactions.",
            "Atom movement, transport, zoning, and dynamic reconfiguration are not yet first-class topology operations.",
        ],
        "target_config": {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 1,
                "n_blocks_col": 1,
                "n": 8,
                "m": 8,
                "k_intra": 2,
                "k_inter": 1,
                "connector_local": 1,
            },
            "profile": deepcopy(_NEUTRAL_ATOM_PROFILE),
        },
    },
    {
        "id": "trapped_ion_qccd",
        "display_name": "Trapped-Ion QCCD",
        "category": "trapped_ion",
        "implemented_as": "tiled_k_nearest",
        "support_status": "approximate",
        "references": [
            "research/papers/trapped_ion_qccd/backend_compiler_phases_trapped_ion_2206.00544.pdf",
            "research/papers/trapped_ion_qccd/scaling_and_assigning_resources_ion_trap_qccd_2408.00225.pdf",
            "research/papers/trapped_ion_qccd/orchestrating_multi_zone_shuttling_2505.07928.pdf",
        ],
        "limitations": [
            "Approximates QCCD as a small-module tiled network with explicit inter-module swap movement.",
            "Zone occupancy, junction shuttling, and trap-capacity scheduling are not yet explicit topology resources.",
        ],
        "target_config": {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 1,
                "n_blocks_col": 4,
                "n": 4,
                "m": 1,
                "k_intra": 4,
                "k_inter": 1,
                "connector_local": 1,
            },
            "profile": deepcopy(_TRAPPED_ION_PROFILE),
        },
    },
    {
        "id": "cavity_mediated_any_to_any",
        "display_name": "Cavity-Mediated Any-to-Any",
        "category": "any_to_any",
        "implemented_as": "tiled_k_nearest",
        "support_status": "approximate",
        "references": [
            "research/papers/cavity_mediated_any_to_any/any_to_any_connected_cavity_mediated_architecture_2109.11551.pdf",
        ],
        "limitations": [
            "Approximates cavity-mediated entanglement as fully connected intra-module connectivity.",
            "Teleportation latency, heralding, and photonic resource contention are not yet modeled.",
        ],
        "target_config": {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 1,
                "n_blocks_col": 1,
                "n": 1,
                "m": 24,
                "k_intra": 24,
                "k_inter": 1,
                "connector_local": 1,
            },
            "profile": deepcopy(_TRAPPED_ION_PROFILE),
        },
    },
    {
        "id": "photonic_fusion_future",
        "display_name": "Photonic Fusion Future Placeholder",
        "category": "future_unsupported",
        "implemented_as": "unsupported",
        "support_status": "unsupported",
        "references": [
            "research/papers/photonic_fusion_future/tailoring_fusion_based_photonic_qc_2410.06784.pdf",
            "research/papers/photonic_fusion_future/end_to_end_switchless_photonic_architecture_2412.12680.pdf",
            "research/papers/photonic_fusion_future/photonic_fusion_resource_states_quantum_emitter_2312.09070.pdf",
        ],
        "limitations": [
            "Fusion-based photonic computation does not fit the current qubit-coupling-map compiler model.",
            "Stored as a documented future architecture only.",
        ],
        "target_config": {
            "topology": {
                "type": "custom_coupling_map",
                "coupling_map": [],
            },
            "profile": deepcopy(_LOGICAL_SURFACE_PROFILE),
        },
    },
]
