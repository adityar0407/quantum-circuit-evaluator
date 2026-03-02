def export_qasm_stub():
    return """OPENQASM 2.0;
qreg q[3];
cx q[0],q[1];
rx(0.5) q[2];
measure q[0] -> c[0];
"""