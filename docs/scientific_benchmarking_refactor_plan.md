# Scientific Benchmarking Refactor Plan

## Current scientific framing

This project should benchmark how the same logical quantum circuit compiles under
different architecture assumptions. It is not currently a full surface-code,
decoder, or calibrated QEC simulation.

Safe framing:

- PennyLane circuit -> QASM -> Qiskit circuit -> architecture-aware compilation.
- Compare structural and model-based metrics across architecture profiles.
- IBM heavy-hex profiles should use backend-derived target data where available.
- The FT-style profile is an abstract logical connectivity-and-basis model unless
  a cited timing/error model is explicitly added.

## Architecture set to support first

1. IBM Fez heavy-hex.
2. IBM Torino heavy-hex.
3. Custom FT-style 2x2 tiled k-nearest logical connectivity graph.

Trapped-ion and neutral-atom profiles should stay out of the active benchmark
until they are tied to provider-specific or cited models.

## File-by-file change checklist

### `src/main_pipeline.py`

- Keep orchestration only.
- Remove hardcoded basis gates, durations, errors, and weights.
- Build or load architecture profiles from helper modules.
- Use one common pass stack across the sparse-graph benchmark profiles.
- Rename reported metric columns so they do not overclaim:
  - `weighted_cost` -> `model_weighted_score`
  - `expected_success_probability` -> `independent_error_success_proxy`
  - `total_duration_seconds` -> `scheduled_duration_estimate_seconds`

### `src/pass_managers/translator.py`

- Let IBM basis/instruction support come from `backend.target` where possible.
- Keep FT Clifford+T-style basis as a logical abstraction.
- Remove or disable active trapped-ion / neutral-atom basis profiles unless tied
  to provider-specific documentation or cited hardware models.

### `src/pass_managers/layout_n_routing.py`

- Keep SABRE for sparse static graph comparisons.
- Set explicit SABRE trial counts for reproducibility:
  - `SabreLayout(..., layout_trials=..., swap_trials=...)`
  - `SabreSwap(..., trials=...)`
- Keep seed settings explicit.

### `src/pass_managers/initializer.py`

- Keep `HighLevelSynthesis`.
- Use `UnrollCustomDefinitions` only where needed and compatible with the active
  Qiskit version.

### `src/pass_managers/optimizer.py`

- Keep architecture-neutral optimization passes.
- If adding optimizations, apply the same optimizer stack across compared sparse
  architectures unless there is a stated justification.

### `src/pass_managers/cost_eval.py`

- Treat weighted cost as a model-dependent compiler score, not a universal
  runtime or fidelity metric.
- Move architecture-specific weights out of `main_pipeline.py`.
- Source weights from backend target/properties, provider docs, cited FT models,
  or explicitly labeled placeholder models.

### `src/target_creation/target.py`

- For IBM heavy-hex, prefer real backend `target` / backend properties over
  placeholder durations and errors.
- For FT-style logical architecture, default to connectivity + logical basis
  only.
- If FT durations/errors are ever assigned, label them as toy assumptions unless
  tied to a cited model.
- Avoid treating missing duration/error as perfect or instantaneous.

Implementation note: IBM profiles now attempt to load `backend.target` when
`qiskit_ibm_runtime` is installed and configured. If that is unavailable, the
pipeline falls back to a basis/connectivity-only target with undefined
duration/error properties.

### `src/metrics/metrics_evaluator.py`

- Relabel:
  - expected success probability -> first-order independent-error success proxy.
  - runtime -> scheduled duration estimate under the chosen target model.
- Return unavailable/undefined values when error or duration data are not defined.
- State omitted effects clearly: crosstalk, correlated errors, leakage,
  idle/memory errors, decoder failure, controller bottlenecks, drift, and
  non-Markovian effects.

### `src/hardware/connectivity.py`

- Keep IBM Fez/Torino as physical NISQ heavy-hex connectivity maps.
- Keep FT map as an abstract logical connectivity model.
- Do not call the FT tiled map a full surface-code architecture.

### `src/qiskit_transpiler.py`

- Either remove from active use or update it to call the same modular pipeline.
- Avoid multiple competing transpilation paths.

## Recommended implementation order

1. Create a small architecture profile layer that owns assumptions.
2. Move weights and labels out of `main_pipeline.py`.
3. Fix metric naming and missing-data behavior.
4. Make FT target connectivity+basis-only by default.
5. Add explicit SABRE trial counts.
6. Add backend-derived IBM target support, with graceful fallback if
   `qiskit_ibm_runtime` or credentials are unavailable.
7. Update or retire `qiskit_transpiler.py`.

## Report-safe language

- "For IBM heavy-hex architectures, instruction support, durations, and error
  rates were taken from backend target data or backend properties where
  available."
- "For non-IBM architecture profiles, basis sets and timing/error parameters
  were treated as analytical abstractions unless explicitly tied to provider
  documentation or a cited hardware model."
- "The weighted-cost metric reported in this work is a model-dependent compiler
  score rather than a universal predictor of hardware runtime or fidelity."
- "The FT-style architecture considered here is an abstract logical connectivity
  model for compilation benchmarking and is not a full surface-code
  resource-estimation framework."
- "Expected success probability is reported only as a first-order approximation
  under independent gate-error assumptions and does not include correlated
  errors, crosstalk, leakage, or decoder failure."
