import type {
  CircuitSummary,
  CompilerBackend,
  EstimationProfiles,
  ResourceEstimator,
  ResourceCapabilities,
  TargetConfig,
  TargetPreview,
  TranspileResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await response.text();
    let parsedDetail: string | undefined;

    try {
      const parsed = JSON.parse(detail) as { detail?: string };
      parsedDetail = parsed.detail;
    } catch {}

    throw new Error(parsedDetail || detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function validateCircuit(qasm: string): Promise<CircuitSummary> {
  return postJson<CircuitSummary>("/circuits/validate", { qasm });
}

export function previewTarget(config: TargetConfig): Promise<TargetPreview> {
  return postJson<TargetPreview>("/targets/preview", { config });
}

export function transpileCircuit(
  qasm: string,
  targetConfig: TargetConfig,
  compilerBackend: CompilerBackend = "auto",
  resourceEstimator: ResourceEstimator = "native_qre",
  estimationProfiles?: EstimationProfiles,
): Promise<TranspileResponse> {
  return postJson<TranspileResponse>("/runs/compile", {
    qasm,
    target_config: targetConfig,
    compiler_backend: compilerBackend,
    resource_estimator: resourceEstimator,
    estimation_profiles: estimationProfiles,
  });
}

export function fetchResourceCapabilities(): Promise<ResourceCapabilities> {
  return getJson<ResourceCapabilities>("/capabilities/resource-estimation");
}
