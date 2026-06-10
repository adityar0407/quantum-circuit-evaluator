import type { TargetConfig } from "../api/types";

export const defaultQasm = `OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];`;

export type ModalityKey = "ft_logical" | "superconducting" | "neutral_atom" | "trapped_ion";
export type ModalitySettings = Record<string, number>;

type ModalityField = {
  key: string;
  label: string;
  step: number;
  min?: number;
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
    description: "Abstract logical gates with explicit network-link assumptions.",
    fields: [
      { key: "clifford_error", label: "Clifford error", step: 0.000001, min: 0 },
      { key: "t_error", label: "T gate error", step: 0.000001, min: 0 },
      { key: "cx_error", label: "Logical CX error", step: 0.000001, min: 0 },
      { key: "clifford_duration", label: "Clifford duration", step: 0.000001, min: 0 },
      { key: "t_duration", label: "T gate duration", step: 0.000001, min: 0 },
      { key: "cx_duration", label: "Logical CX duration", step: 0.000001, min: 0 },
      { key: "network_error", label: "Network link error", step: 0.0001, min: 0 },
      { key: "network_duration", label: "Network link duration", step: 0.000001, min: 0 },
    ],
    defaults: {
      clifford_error: 0.0001,
      t_error: 0.0002,
      cx_error: 0.001,
      clifford_duration: 0.00001,
      t_duration: 0.00002,
      cx_duration: 0.000001,
      network_error: 0.05,
      network_duration: 0.00001,
    },
  },
  superconducting: {
    label: "Superconducting",
    description: "IBM-style basis gates with fast local operations and slower inter-module links.",
    fields: [
      { key: "rz_error", label: "RZ error", step: 0.000001, min: 0 },
      { key: "sx_x_error", label: "SX/X error", step: 0.000001, min: 0 },
      { key: "oneq_duration", label: "1Q duration", step: 0.00000001, min: 0 },
      { key: "cx_error", label: "CX error", step: 0.0001, min: 0 },
      { key: "cx_duration", label: "CX duration", step: 0.00000001, min: 0 },
      { key: "module_link_error", label: "Module link error", step: 0.0001, min: 0 },
      { key: "module_link_duration", label: "Module link duration", step: 0.000001, min: 0 },
    ],
    defaults: {
      rz_error: 0.00001,
      sx_x_error: 0.0001,
      oneq_duration: 0.00000005,
      cx_error: 0.002,
      cx_duration: 0.00000025,
      module_link_error: 0.05,
      module_link_duration: 0.00005,
    },
  },
  neutral_atom: {
    label: "Neutral Atom",
    description: "Rydberg/CZ-style profile with blockade-radius-inspired local connectivity assumptions.",
    fields: [
      { key: "rotation_error", label: "Rotation error", step: 0.000001, min: 0 },
      { key: "rotation_duration", label: "Rotation duration", step: 0.0000001, min: 0 },
      { key: "cz_error", label: "CZ error", step: 0.0001, min: 0 },
      { key: "cz_duration", label: "CZ duration", step: 0.0000001, min: 0 },
      { key: "blockade_radius", label: "Blockade radius", step: 1, min: 1 },
      { key: "shuttle_error", label: "Transport/link error", step: 0.0001, min: 0 },
      { key: "shuttle_duration", label: "Transport/link duration", step: 0.000001, min: 0 },
    ],
    defaults: {
      rotation_error: 0.00001,
      rotation_duration: 0.000001,
      cz_error: 0.0007,
      cz_duration: 0.000002,
      blockade_radius: 2,
      shuttle_error: 0.05,
      shuttle_duration: 0.00005,
    },
  },
  trapped_ion: {
    label: "Trapped Ion",
    description: "Long-range ion-chain gates with slower entangling operations.",
    fields: [
      { key: "rotation_error", label: "Rotation error", step: 0.000001, min: 0 },
      { key: "rotation_duration", label: "Rotation duration", step: 0.000001, min: 0 },
      { key: "rxx_error", label: "RXX error", step: 0.0001, min: 0 },
      { key: "rxx_duration", label: "RXX duration", step: 0.000001, min: 0 },
      { key: "chain_mode_penalty", label: "Chain mode penalty", step: 0.1, min: 1 },
      { key: "link_error", label: "Module link error", step: 0.0001, min: 0 },
      { key: "link_duration", label: "Module link duration", step: 0.000001, min: 0 },
    ],
    defaults: {
      rotation_error: 0.00001,
      rotation_duration: 0.00001,
      rxx_error: 0.0005,
      rxx_duration: 0.0001,
      chain_mode_penalty: 1,
      link_error: 0.05,
      link_duration: 0.00005,
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
        RZGate: { error: settings.rz_error, duration: settings.oneq_duration },
        SXGate: { error: settings.sx_x_error, duration: settings.oneq_duration },
        XGate: { error: settings.sx_x_error, duration: settings.oneq_duration },
      },
      two_q_gates: {
        CXGate: { local_error: settings.cx_error, local_duration: settings.cx_duration },
      },
      inter_device_gates: {
        SwapGate: { inter_error: settings.module_link_error, inter_duration: settings.module_link_duration },
      },
    };
  }

  if (modality === "neutral_atom") {
    return {
      sq_gates: {
        RXGate: { error: settings.rotation_error, duration: settings.rotation_duration },
        RYGate: { error: settings.rotation_error, duration: settings.rotation_duration },
        RZGate: { error: settings.rotation_error, duration: settings.rotation_duration },
      },
      two_q_gates: {
        CZGate: { local_error: settings.cz_error, local_duration: settings.cz_duration },
      },
      inter_device_gates: {
        SwapGate: { inter_error: settings.shuttle_error, inter_duration: settings.shuttle_duration },
      },
    };
  }

  if (modality === "trapped_ion") {
    return {
      sq_gates: {
        RXGate: { error: settings.rotation_error, duration: settings.rotation_duration },
        RYGate: { error: settings.rotation_error, duration: settings.rotation_duration },
        RZGate: { error: settings.rotation_error, duration: settings.rotation_duration },
      },
      two_q_gates: {
        RXXGate: {
          local_error: settings.rxx_error * settings.chain_mode_penalty,
          local_duration: settings.rxx_duration,
        },
      },
      inter_device_gates: {
        SwapGate: { inter_error: settings.link_error, inter_duration: settings.link_duration },
      },
    };
  }

  return {
    sq_gates: {
      HGate: { error: settings.clifford_error, duration: settings.clifford_duration },
      TGate: { error: settings.t_error, duration: settings.t_duration },
    },
    two_q_gates: {
      CXGate: { local_error: settings.cx_error, local_duration: settings.cx_duration },
    },
    inter_device_gates: {
      SwapGate: { inter_error: settings.network_error, inter_duration: settings.network_duration },
    },
  };
}

export const defaultTargetConfig: TargetConfig = {
  topology: {
    type: "tiled_k_nearest",
    n_blocks_row: 2,
    n_blocks_col: 2,
    n: 3,
    m: 3,
    k_intra: 1,
    k_inter: 1,
    connector_local: 1,
  },
  profile: buildProfile(defaultModality, cloneModalitySettings(defaultModality)),
};
