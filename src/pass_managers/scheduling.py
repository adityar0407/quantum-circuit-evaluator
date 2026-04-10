from qiskit.transpiler import Target, PassManager
from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDelay

def get_scheduling_pm(target: Target) -> PassManager:
    """
    Phase 6: Scheduling
    Calculates execution time based on gate durations and pads idle time with delays.
    Essential for checking time-based cutoffs.
    """
    return PassManager([
        # ALAP (As Late As Possible) is the standard for quantum scheduling to minimize decoherence
        ALAPScheduleAnalysis(target.durations()),
        # Optionally insert explicit delay instructions for idling qubits
        PadDelay()
    ])