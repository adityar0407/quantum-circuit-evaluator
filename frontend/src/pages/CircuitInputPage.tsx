export function CircuitInputPage() {
  return (
    <section id="circuit" className="panel">
      <header>
        <p>Circuit Input</p>
        <h1>OpenQASM and example circuits</h1>
      </header>
      <textarea
        aria-label="OpenQASM circuit input"
        spellCheck={false}
        defaultValue={`OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];`}
      />
    </section>
  );
}

