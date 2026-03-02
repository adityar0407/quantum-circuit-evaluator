# Physics-765-final-project
## Topic of Interest 
PennyLane makes it easy to design quantum circuits, but it doesn’t tell you how expensive those circuits would be on a fault-tolerant machine. We built a tool that inspects PennyLane circuits and estimates their fault-tolerant cost, allowing early stage comparison of circuit designs before running full resource estimators.

By Max Bublik and Adi Ravi

Elevator Pitch:
* The project will be a computational study
* We will compare between NISQ and FTQC era benchmarks
* This would affect the Error Correction and logical quantum processor


## Current Project Structure

| Path | Purpose | What It Does Right Now |
|------|----------|------------------------|
| src/main.py | Entry point | Loads config, generates QASM (stub), counts gates, runs placeholder FT estimate, prints results |
| src/config/load_config.py | Config loader | Reads YAML file and returns Python dictionary |
| src/configs/example.yaml | Configuration file | Defines hardware assumptions and surface code parameters |
| src/ir/export_qasm.py | IR exporter (stub) | Returns a hardcoded OpenQASM string (placeholder for real circuit export) |
| src/metrics/qasm_counter.py | Streaming QASM parser | Counts gates and 2-qubit gates without storing full circuit |
| src/hardware/connectivity.py | Connectivity helper | Checks if two qubits are connected |
| src/hardware/native_gates.py | Native gate checker | Checks if a gate is part of the allowed native gate set |
| src/ec/surface_code.py | Surface code estimator (stub) | Placeholder function for logical qubit estimation |

---

## External Dependencies

| Package | Why It Is Used |
|----------|----------------|
| pyyaml | Load YAML configuration files |
| pathlib (stdlib) | Safe path handling |
