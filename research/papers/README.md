# Architecture Reference Archive

This folder stores the paper set used to ground the current architecture presets and topology roadmap.

## Implemented or approximated now

### `square_grid_surface_code`
- Papers:
  - `square_grid_surface_code/quantum_error_correction_below_surface_code_threshold_2408.13687.pdf`
  - `square_grid_surface_code/suppressing_quantum_errors_by_scaling_surface_code_2207.06431.pdf`
- Mapping:
  - Implemented as `tiled_k_nearest` with `k_intra = 1` on a single square block.
  - Rationale: both papers use surface-code style nearest-neighbor superconducting layouts, which are well represented by the existing 2D Manhattan grid generator.

### `superconducting_topology_suite`
- Paper:
  - `superconducting_topology_comparison/comparison_of_superconducting_nisq_architectures_2409.02063.pdf`
- Mapping:
  - Added as a paper-backed comparison baseline over `tiled_k_nearest`.
  - Rationale: the paper compares several superconducting coupling graphs; this repo now exposes a buildable baseline architecture and leaves room to add more named presets from the comparison family.

### `heavy_hex`
- Papers:
  - `heavy_hex_sparse_superconducting/creating_entangled_logical_qubits_heavy_hex_2404.15989.pdf`
  - `heavy_hex_sparse_superconducting/linear_depth_qft_ibm_heavy_hex_2402.09705.pdf`
- Mapping:
  - Uses the existing `heavy_hex` generator.
  - Rationale: the heavy-hex graph is already a first-class topology in the repo.

### `modular_superconducting`
- Papers:
  - `modular_superconducting/codesigned_superconducting_architecture_lattice_surgery_2312.01246.pdf`
  - `modular_superconducting/modular_superconducting_qubit_architecture_multichip_tunable_coupler_2308.09240.pdf`
- Mapping:
  - Implemented as a tiled modular graph using `tiled_k_nearest`.
  - Rationale: the current block/grid model can express multiple superconducting tiles linked by a limited number of inter-module connections.

### `modular_distributed_surface_code`
- Papers:
  - `modular_distributed_surface_code/modular_architectures_and_entanglement_schemes_2408.02837.pdf`
  - `modular_distributed_surface_code/large_scale_modular_quantum_computer_architecture_1208.0391.pdf`
- Mapping:
  - Implemented as `tiled_k_nearest` with multiple modules and explicit inter-device links.
  - Rationale: the existing modular graph layer can represent distributed modules, while entanglement-generation performance remains a higher-level limitation outside topology.

### `neutral_atom_reconfigurable`
- Papers:
  - `neutral_atom_reconfigurable/atomique_quantum_compiler_reconfigurable_neutral_atom_arrays_2311.15123.pdf`
  - `neutral_atom_reconfigurable/compiling_quantum_circuits_dynamic_field_programmable_neutral_atoms_2306.03487.pdf`
  - `neutral_atom_reconfigurable/logical_quantum_processor_reconfigurable_atom_arrays_2312.03982.pdf`
- Mapping:
  - Implemented as an approximate dense tiled neutral-atom preset using `tiled_k_nearest`.
  - Rationale: these papers depend on reconfiguration and movement; this repo currently captures the connectivity envelope but not atom transport as a first-class operation.

### `trapped_ion_qccd`
- Papers:
  - `trapped_ion_qccd/backend_compiler_phases_trapped_ion_2206.00544.pdf`
  - `trapped_ion_qccd/scaling_and_assigning_resources_ion_trap_qccd_2408.00225.pdf`
  - `trapped_ion_qccd/orchestrating_multi_zone_shuttling_2505.07928.pdf`
- Mapping:
  - Implemented as an approximate modular line of traps via `tiled_k_nearest`.
  - Rationale: the current topology layer can represent zones and movement links, but not full trap-capacity and shuttling orchestration semantics.

### `cavity_mediated_any_to_any`
- Paper:
  - `cavity_mediated_any_to_any/any_to_any_connected_cavity_mediated_architecture_2109.11551.pdf`
- Mapping:
  - Implemented as an approximate all-to-all preset over `tiled_k_nearest`.
  - Rationale: this architecture’s essential topological claim is any-to-any connectivity.

## Future / unsupported now

### `photonic_fusion_future`
- Papers:
  - `photonic_fusion_future/tailoring_fusion_based_photonic_qc_2410.06784.pdf`
  - `photonic_fusion_future/end_to_end_switchless_photonic_architecture_2412.12680.pdf`
  - `photonic_fusion_future/photonic_fusion_resource_states_quantum_emitter_2312.09070.pdf`
- Mapping:
  - Explicitly documented as unsupported.
  - Rationale: fusion-based photonic architectures do not map cleanly onto the repo’s present gate-connectivity target model.
