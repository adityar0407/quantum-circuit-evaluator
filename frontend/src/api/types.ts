export type CircuitSummary = {
  num_qubits: number;
  num_clbits: number;
  depth: number;
  gate_count: number;
  operation_counts: Record<string, number>;
};

export type TargetConfig = {
  topology: Record<string, unknown>;
  profile: Record<string, unknown>;
};

export type EstimationProfiles = {
  physical_hardware: Record<string, unknown>;
  qec: Record<string, unknown>;
  network?: Record<string, unknown>;
};

export type ResourceCapabilities = {
  physical_hardware: {
    profile_modes: string[];
    verified_builtin_models: Array<{
      key: string;
      label: string;
      class: string;
      description: string;
      defaults: Record<string, unknown>;
      supported_qec_models: string[];
    }>;
    unsupported_models: Array<Record<string, unknown>>;
    custom_profile_fields: Array<{
      key: string;
      type: string;
      unit: string | null;
      default: unknown;
    }>;
    mapping_notes: string[];
  };
  qec_models: string[];
  native_operations: string[];
};

export type TargetPreview = {
  topology_type: string;
  total_qubits: number;
  total_edges: number;
  n_block: number;
  operation_names: string[];
  nodes: Array<{ id: number; block: number; x: number | null; y: number | null }>;
  edges: Array<{ source: number; target: number; local: boolean }>;
};

export type CompilerBackend = "auto" | "qiskit_ftarget" | "pandora";
export type ResourceEstimator = "native_qre" | "qiskit_compatibility";

export type TranspileResponse = {
  compiler: CompilerBackend | string;
  resource_estimator: ResourceEstimator | string;
  original: CircuitSummary;
  transpiled: CircuitSummary;
  compiled?: CircuitSummary;
  metrics: Record<string, unknown>;
  artifacts: Record<string, unknown>;
  warnings: string[];
};
