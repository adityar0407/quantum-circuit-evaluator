import type { TargetConfig } from "../api/types";

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
  profile: {
    sq_gates: {
      HGate: { error: 0.0001, duration: 0.00001 },
      TGate: { error: 0.0002, duration: 0.00002 },
    },
    two_q_gates: {
      CXGate: { local_error: 0.001, local_duration: 0.000001 },
    },
    inter_device_gates: {
      SwapGate: { inter_error: 0.05, inter_duration: 0.00001 },
    },
  },
};

