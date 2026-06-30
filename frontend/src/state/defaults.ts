import type { EstimationProfiles, TargetConfig } from "../api/types";

export const defaultQasm = `OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];`;

export type ModalityKey = "ft_logical" | "superconducting" | "neutral_atom" | "trapped_ion";
export type ModalitySettings = Record<string, number>;
export type QecModelKey =
  | "surface_code"
  | "surface_code_low_move"
  | "three_aux"
  | "one_dimensional_yoked_surface_code"
  | "two_dimensional_yoked_surface_code";

type ModalityField = {
  key: string;
  label: string;
  step: number;
  min?: number;
};

export type QecParameterField = {
  key: string;
  label: string;
  type: "number" | "boolean";
  step?: string;
  min?: string;
};

export const qecModelOptions: Array<{ key: QecModelKey; label: string; description: string }> = [
  {
    key: "surface_code",
    label: "SurfaceCode",
    description: "Default QDK surface-code model.",
  },
  {
    key: "surface_code_low_move",
    label: "SurfaceCodeLowMove",
    description: "QDK surface-code variant with lower movement overhead.",
  },
  {
    key: "three_aux",
    label: "ThreeAux",
    description: "QDK three-auxiliary-qubit model.",
  },
  {
    key: "one_dimensional_yoked_surface_code",
    label: "OneDimensionalYokedSurfaceCode",
    description: "QDK one-dimensional yoked surface-code model.",
  },
  {
    key: "two_dimensional_yoked_surface_code",
    label: "TwoDimensionalYokedSurfaceCode",
    description: "QDK two-dimensional yoked surface-code model.",
  },
];

export const qecModelParameterFields: Record<QecModelKey, QecParameterField[]> = {
  surface_code: [
    { key: "distance", label: "Distance", type: "number", step: "2", min: "1" },
    { key: "crossing_prefactor", label: "Crossing prefactor", type: "number", step: "any", min: "0" },
    { key: "error_correction_threshold", label: "EC threshold", type: "number", step: "any", min: "0" },
    { key: "one_qubit_gate_depth", label: "1Q gate depth", type: "number", step: "1", min: "0" },
    { key: "two_qubit_gate_depth", label: "2Q gate depth", type: "number", step: "1", min: "0" },
    { key: "code_cycle_override", label: "Cycle override", type: "number", step: "1", min: "0" },
    { key: "code_cycle_offset", label: "Cycle offset", type: "number", step: "1", min: "0" },
  ],
  surface_code_low_move: [
    { key: "distance", label: "Distance", type: "number", step: "2", min: "1" },
    { key: "crossing_prefactor", label: "Crossing prefactor", type: "number", step: "any", min: "0" },
    { key: "error_correction_threshold", label: "EC threshold", type: "number", step: "any", min: "0" },
    { key: "code_cycle_override", label: "Cycle override", type: "number", step: "1", min: "0" },
    { key: "code_cycle_offset", label: "Cycle offset", type: "number", step: "1", min: "0" },
  ],
  three_aux: [
    { key: "distance", label: "Distance", type: "number", step: "2", min: "1" },
    { key: "single_rail", label: "Single rail", type: "boolean" },
  ],
  one_dimensional_yoked_surface_code: [
    { key: "crossing_prefactor", label: "Crossing prefactor", type: "number", step: "any", min: "0" },
    { key: "error_correction_threshold", label: "EC threshold", type: "number", step: "any", min: "0" },
  ],
  two_dimensional_yoked_surface_code: [
    { key: "crossing_prefactor", label: "Crossing prefactor", type: "number", step: "any", min: "0" },
    { key: "error_correction_threshold", label: "EC threshold", type: "number", step: "any", min: "0" },
  ],
};

export const qecModelDefaultParameters: Record<QecModelKey, Record<string, string | number | boolean | null>> = {
  surface_code: {
    distance: 3,
    crossing_prefactor: 0.03,
    error_correction_threshold: 0.01,
    one_qubit_gate_depth: 1,
    two_qubit_gate_depth: 4,
    code_cycle_override: null,
    code_cycle_offset: 0,
  },
  surface_code_low_move: {
    distance: 3,
    crossing_prefactor: 0.03,
    error_correction_threshold: 0.01,
    code_cycle_override: null,
    code_cycle_offset: 0,
  },
  three_aux: {
    distance: 3,
    single_rail: false,
  },
  one_dimensional_yoked_surface_code: {
    crossing_prefactor: 0.5333333333333333,
    error_correction_threshold: 6.4,
  },
  two_dimensional_yoked_surface_code: {
    crossing_prefactor: 0.008333333333333333,
    error_correction_threshold: 250,
  },
};

export const modalityPresets: Record<
  ModalityKey,
  {
    label: string;
    description: string;
    fields: ModalityField[];
    defaults: ModalitySettings;
  }
> = {
  ft_logical: {
    label: "Logical Clifford+T",
    description: "A hardware-agnostic logical gate basis for abstract fault-tolerant studies.",
    fields: [
      { key: "clifford_weight", label: "Clifford weight", step: 0.1, min: 0 },
      { key: "t_weight", label: "T gate weight", step: 0.1, min: 0 },
      { key: "cx_weight", label: "Logical CX weight", step: 0.1, min: 0 },
      { key: "clifford_preference", label: "Clifford preference", step: 0.1, min: 0 },
      { key: "t_preference", label: "T gate preference", step: 0.1, min: 0 },
      { key: "cx_preference", label: "Logical CX preference", step: 0.1, min: 0 },
      { key: "network_weight", label: "Network link weight", step: 0.1, min: 0 },
      { key: "network_preference", label: "Network link preference", step: 0.1, min: 0 },
    ],
    defaults: {
      clifford_weight: 1,
      t_weight: 2,
      cx_weight: 3,
      clifford_preference: 1,
      t_preference: 1.5,
      cx_preference: 2,
      network_weight: 5,
      network_preference: 3,
    },
  },
  superconducting: {
    label: "Superconducting",
    description: "A superconducting-style gate basis with local CX interactions and optional inter-module moves.",
    fields: [
      { key: "rz_weight", label: "RZ weight", step: 0.1, min: 0 },
      { key: "sx_x_weight", label: "SX/X weight", step: 0.1, min: 0 },
      { key: "oneq_preference", label: "1Q preference", step: 0.1, min: 0 },
      { key: "cx_weight", label: "CX weight", step: 0.1, min: 0 },
      { key: "cx_preference", label: "CX preference", step: 0.1, min: 0 },
      { key: "module_link_weight", label: "Module link weight", step: 0.1, min: 0 },
      { key: "module_link_preference", label: "Module link preference", step: 0.1, min: 0 },
    ],
    defaults: {
      rz_weight: 0.5,
      sx_x_weight: 1,
      oneq_preference: 1,
      cx_weight: 3,
      cx_preference: 2,
      module_link_weight: 5,
      module_link_preference: 3,
    },
  },
  neutral_atom: {
    label: "Neutral Atom",
    description: "A neutral-atom style gate basis with CZ interactions and optional atom movement between regions.",
    fields: [
      { key: "rotation_weight", label: "Rotation weight", step: 0.1, min: 0 },
      { key: "rotation_preference", label: "Rotation preference", step: 0.1, min: 0 },
      { key: "cz_weight", label: "CZ weight", step: 0.1, min: 0 },
      { key: "cz_preference", label: "CZ preference", step: 0.1, min: 0 },
      { key: "blockade_radius", label: "Blockade radius", step: 1, min: 1 },
      { key: "shuttle_weight", label: "Transport/link weight", step: 0.1, min: 0 },
      { key: "shuttle_preference", label: "Transport/link preference", step: 0.1, min: 0 },
    ],
    defaults: {
      rotation_weight: 1,
      rotation_preference: 1,
      cz_weight: 3,
      cz_preference: 2,
      blockade_radius: 2,
      shuttle_weight: 5,
      shuttle_preference: 3,
    },
  },
  trapped_ion: {
    label: "Trapped Ion",
    description: "An ion-style gate basis for long-range interactions and optional inter-zone or inter-module moves.",
    fields: [
      { key: "rotation_weight", label: "Rotation weight", step: 0.1, min: 0 },
      { key: "rotation_preference", label: "Rotation preference", step: 0.1, min: 0 },
      { key: "rxx_weight", label: "RXX weight", step: 0.1, min: 0 },
      { key: "rxx_preference", label: "RXX preference", step: 0.1, min: 0 },
      { key: "chain_mode_penalty", label: "Chain mode penalty", step: 0.1, min: 1 },
      { key: "link_weight", label: "Module link weight", step: 0.1, min: 0 },
      { key: "link_preference", label: "Module link preference", step: 0.1, min: 0 },
    ],
    defaults: {
      rotation_weight: 1,
      rotation_preference: 1,
      rxx_weight: 3,
      rxx_preference: 2,
      chain_mode_penalty: 1,
      link_weight: 5,
      link_preference: 3,
    },
  },
};

export const defaultModality: ModalityKey = "ft_logical";

export function cloneModalitySettings(modality: ModalityKey): ModalitySettings {
  return { ...modalityPresets[modality].defaults };
}

export function buildProfile(modality: ModalityKey, settings: ModalitySettings): TargetConfig["profile"] {
  if (modality === "superconducting") {
    return {
      sq_gates: {
        RZGate: { logical_weight: settings.rz_weight, logical_preference: settings.oneq_preference },
        SXGate: { logical_weight: settings.sx_x_weight, logical_preference: settings.oneq_preference },
        XGate: { logical_weight: settings.sx_x_weight, logical_preference: settings.oneq_preference },
      },
      two_q_gates: {
        CXGate: { logical_weight: settings.cx_weight, routing_preference: settings.cx_preference },
      },
      inter_device_gates: {
        SwapGate: { logical_weight: settings.module_link_weight, routing_preference: settings.module_link_preference },
      },
    };
  }

  if (modality === "neutral_atom") {
    return {
      sq_gates: {
        RXGate: { logical_weight: settings.rotation_weight, logical_preference: settings.rotation_preference },
        RYGate: { logical_weight: settings.rotation_weight, logical_preference: settings.rotation_preference },
        RZGate: { logical_weight: settings.rotation_weight, logical_preference: settings.rotation_preference },
      },
      two_q_gates: {
        CZGate: { logical_weight: settings.cz_weight, routing_preference: settings.cz_preference },
      },
      inter_device_gates: {
        SwapGate: { logical_weight: settings.shuttle_weight, routing_preference: settings.shuttle_preference },
      },
    };
  }

  if (modality === "trapped_ion") {
    return {
      sq_gates: {
        RXGate: { logical_weight: settings.rotation_weight, logical_preference: settings.rotation_preference },
        RYGate: { logical_weight: settings.rotation_weight, logical_preference: settings.rotation_preference },
        RZGate: { logical_weight: settings.rotation_weight, logical_preference: settings.rotation_preference },
      },
      two_q_gates: {
        RXXGate: {
          logical_weight: settings.rxx_weight * settings.chain_mode_penalty,
          routing_preference: settings.rxx_preference,
        },
      },
      inter_device_gates: {
        SwapGate: { logical_weight: settings.link_weight, routing_preference: settings.link_preference },
      },
    };
  }

  return {
    sq_gates: {
      HGate: { logical_weight: settings.clifford_weight, logical_preference: settings.clifford_preference },
      TGate: { logical_weight: settings.t_weight, logical_preference: settings.t_preference },
    },
    two_q_gates: {
      CXGate: { logical_weight: settings.cx_weight, routing_preference: settings.cx_preference },
    },
    inter_device_gates: {
      SwapGate: { logical_weight: settings.network_weight, routing_preference: settings.network_preference },
    },
  };
}

export const defaultTargetConfig: TargetConfig = {
  architecture_preset: "square_grid_surface_code",
  topology: {
    type: "tiled_k_nearest",
    n_blocks_row: 1,
    n_blocks_col: 1,
    n: 7,
    m: 7,
    k_intra: 1,
    k_inter: 1,
    connector_local: 1,
  },
  profile: buildProfile(defaultModality, cloneModalitySettings(defaultModality)),
};

export const defaultEstimationProfiles: EstimationProfiles = {
  physical_hardware: {
    physical_profile_mode: "built_in",
    qdk_hardware_model: "gate_based",
    one_qubit_gate_error_rate: 1e-4,
    two_qubit_gate_error_rate: 1e-3,
    measurement_error_rate: 2e-4,
    idle_error_rate: 1e-5,
    one_qubit_gate_time: 50e-9,
    two_qubit_gate_time: 300e-9,
    measurement_time: 800e-9,
    cycle_time: 1e-6,
    physical_modality: "gate_based",
  },
  qec: {
    qec_scheme: "surface_code",
    error_budget: 1e-2,
    qec_model_source: "azure_builtin",
    qec_model_name: "surface_code",
    qec_model_parameters: {},
  },
  network: {
    topology: "none",
    remote_gate_time: "",
    remote_gate_error: "",
    epr_generation_time: "",
    epr_generation_error: "",
    communication_qubits_per_link: "",
    link_capacity: "",
    classical_feedforward_time: "",
  },
};

export function cloneEstimationProfiles(): EstimationProfiles {
  return JSON.parse(JSON.stringify(defaultEstimationProfiles)) as EstimationProfiles;
}
