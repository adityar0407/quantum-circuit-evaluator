# Quantum Circuit Evaluator

Quantum Circuit Evaluator (QCE) is a local research workspace for evaluating quantum circuits under configurable architecture, compilation, and resource-estimation assumptions.

QCE is designed to make the full evaluation path inspectable:

1. Import an OpenQASM circuit.
2. Configure the target architecture.
3. Compile and route the circuit.
4. Convert the compiled circuit into a logical intermediate representation.
5. Run a selected resource estimator.
6. Inspect results and export the complete run record.

The application uses a React/Vite frontend and a Python/FastAPI backend. Qiskit is the common circuit representation between intake, compiler, target-configuration, Logical IR, and resource-estimation stages.

## Quick Start

Clone the repository:

```bash
git clone https://github.com/adityar0407/quantum-circuit-evaluator.git
cd quantum-circuit-evaluator
```

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies and the local package:

```bash
pip install -r requirements.txt
pip install -e .
```

Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

Launch the local app:

```bash
npm run dev
```

This starts:

- FastAPI backend: `http://127.0.0.1:8000`
- Vite frontend: `http://127.0.0.1:4173`

Open the frontend URL in your browser:

```text
http://127.0.0.1:4173
```

If either port is already in use, the launcher stops and tells you which process to clear first.

## Repository Layout

```text
quantum-circuit-evaluator/
├── backend/
│   ├── api/
│   ├── hardware/
│   ├── models/
│   ├── services/
│   │   ├── compilers/
│   │   └── resource_estimators/
│   └── tests/
├── frontend/
│   └── src/
├── scripts/
├── docs/
├── examples/
├── package.json
└── requirements.txt
```

The frontend is responsible for circuit input, architecture configuration, estimation-profile configuration, results display, and run export.

The backend is responsible for circuit parsing, target construction, compiler selection, placement and routing, Logical IR generation, resource estimation, and reproducible export generation.

## Evaluation Pipeline

```text
Circuit input
    ↓
Circuit parsing
    ↓
FTarget construction
    ↓
Compiler selection
    ↓
Placement and routing
    ↓
Compiled circuit
    ↓
Logical IR
    ↓
Resource estimator
    ↓
Results and reproducible export
```

Each stage records metadata so the final estimate can be traced back to the circuit, target, compiler, topology, estimation profile, and estimator assumptions used to produce it.

## Architecture and FTarget

QCE uses FTarget to describe the architecture presented to the compiler.

An FTarget configuration includes:

- Topology, such as heavy hex, heavy square, tiled nearest-neighbor layouts, or custom coupling maps.
- Single-qubit operations with logical weights and preferences.
- Two-qubit operations with logical weights and routing preferences.
- Optional inter-device operations for modular or networked architectures.

Compiler weights influence compilation decisions. They are not physical gate times or physical error rates. For example, increasing an `SX` compiler weight discourages `SX` during compilation, but estimator support and pricing are controlled separately by the resource-estimation profile.

## Compiler Backends

### Qiskit FTarget

The Qiskit FTarget compiler performs architecture-aware transpilation against the selected target. The target defines supported operations, available qubits, coupling constraints, topology, logical gate weights, and routing preferences.

### Pandora

Pandora is an alternative compiler and routing path. QCE can attempt Pandora first for supported topologies and then fall back to Qiskit if Pandora cannot process the circuit cleanly.

Run exports record:

- Whether Pandora was attempted.
- Why it was selected.
- Why it failed, if it failed.
- Which compiler ultimately produced the compiled circuit.

QCE normalizes Pandora input before routing by translating circuits to the target basis and stripping barriers. If Pandora database-backed rewrites are unavailable or unsafe for a circuit, QCE keeps the topology-legalized translation path rather than discarding the run.

## Logical IR

After compilation, QCE serializes the compiled circuit into a Logical IR.

The Logical IR records:

- Operations and operation parameters.
- Logical and classical operands.
- Dependencies.
- Placement and node assignments.
- Local versus remote operation classification.
- Operation counts.
- DAG and critical-path metadata.
- Compiler artifacts relevant to the run.

The Logical IR preserves the compiler output. Estimator-specific lowering happens later in the estimator layer.

## Resource Estimation

QCE includes a native QRE path that consumes the Logical IR and selected estimation profiles.

The native estimator returns the fields used by the Results page, including:

- `physical_qubits`
- `runtime`
- `rqops`
- `logical_counts`
- `physical_counts`

The estimator can lower compiler operations into an estimator-supported basis. For example, each local `SWAP` is priced as three `CX` operations:

```text
SWAP(a, b)
    ↓
CX(a, b)
CX(b, a)
CX(a, b)
```

`SX` pricing is configurable through:

- `sx_gate_time`
- `sx_gate_error_rate`

If those fields are omitted, QCE falls back to:

- `one_qubit_gate_time`
- `one_qubit_gate_error_rate`

## Estimation Profiles

The estimation context combines physical hardware, QEC, and optional network assumptions.

Physical hardware fields include:

- One-qubit error rate.
- Two-qubit error rate.
- Measurement error rate.
- Idle error rate.
- One-qubit gate time.
- Two-qubit gate time.
- SX gate time.
- SX error rate.
- Measurement time.
- Cycle time.

QEC fields include:

- QEC scheme.
- Logical failure budget.
- QEC model source.
- QEC model name.
- Model-specific parameters.

Network fields can represent modular topology and remote-link assumptions when those are relevant to the selected architecture.

## Reproducible Run Export

Each run can export a JSON record containing:

- Original QASM.
- Requested compiler.
- Selected compiler.
- Compiler version and configuration.
- FTarget configuration.
- Original and compiled circuit summaries.
- Compiled QASM.
- Placement and routing metadata.
- Logical IR.
- Estimation profiles.
- Estimator output.
- Warnings and fallback reasons.

The goal is to provide not just final numbers, but also the assumptions and transformations that produced them.

## Validation

Run the backend test suite:

```bash
python3 -m pytest -q backend/tests
```

Build the frontend:

```bash
cd frontend
npm run build
cd ..
```

Check the backend capability endpoint after launching:

```bash
curl http://127.0.0.1:8000/api/capabilities/resource-estimation
```

## Notes

- QCE is local-first. The frontend calls the local FastAPI backend.
- The backend source of truth is under `backend/`.
- Pandora is treated as a compiler backend; FTarget remains the architecture/topology model.
- Resource-estimation assumptions are explicit and exported with each run.
