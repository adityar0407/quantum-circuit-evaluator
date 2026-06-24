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
export type ResourceEstimator = "simple_logical" | "azure_qre";

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
