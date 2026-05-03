def count_gates_from_qasm(qasm_str: str):
    counts = {}
    for line in qasm_str.splitlines():
        line = line.strip()
        if not line or line.startswith("OPENQASM") or line.startswith("qreg"):
            continue

        gate = line.split()[0]
        gate = gate.split("(")[0]  # remove parameters if present

        counts[gate] = counts.get(gate, 0) + 1

    return counts