export type CircuitSummary = {
  num_qubits: number;
  num_clbits: number;
  depth: number;
  gate_count: number;
  operation_counts: Record<string, number>;
};

export type CircuitPreview = CircuitSummary & {
  format: "qiskit_text" | string;
  diagram: string;
  warnings: string[];
};

export type TargetConfig = {
  architecture_preset?: string;
  architecture_metadata?: Record<string, unknown>;
  topology: Record<string, unknown>;
  profile: Record<string, unknown>;
};

export type ArchitecturePreset = {
  id: string;
  display_name: string;
  category: string;
  implemented_as: string;
  support_status: "supported" | "approximate" | "unsupported" | string;
  references: string[];
  limitations: string[];
  target_config: TargetConfig;
};

export type ArchitectureCapabilities = {
  architectures: ArchitecturePreset[];
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
  architecture_id?: string;
  topology_type: string;
  total_qubits: number;
  number_of_qubits?: number;
  total_edges: number;
  n_block: number;
  n_blocks_row?: number;
  n_blocks_col?: number;
  operation_names: string[];
  native_gate_set?: string[];
  allowed_coupling_edges?: Array<{ source: number; target: number }>;
  allowed_coupling_edges_undirected?: Array<[number, number]>;
  qubit_to_node_mapping?: Record<string, number> | Record<number, number>;
  local_edges?: Array<{ source: number; target: number }>;
  remote_inter_node_edges?: Array<{ source: number; target: number }>;
  directed_edge_policy?: string;
  architecture_limitations?: string[];
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
  artifacts: Record<string, unknown> & {
    original_circuit_preview?: CircuitPreview;
    compiled_circuit_preview?: CircuitPreview;
  };
  warnings: string[];
};
