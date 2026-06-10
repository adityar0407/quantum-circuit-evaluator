import type {
  CircuitSummary,
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
    try {
      const parsed = JSON.parse(detail) as { detail?: string };
      throw new Error(parsed.detail || `Request failed with status ${response.status}`);
    } catch {
      throw new Error(detail || `Request failed with status ${response.status}`);
    }
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
): Promise<TranspileResponse> {
  return postJson<TranspileResponse>("/runs/transpile", {
    qasm,
    target_config: targetConfig,
  });
}
