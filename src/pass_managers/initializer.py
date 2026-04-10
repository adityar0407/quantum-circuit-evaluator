from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import HighLevelSynthesis, UnrollCustomDefinitions

def get_init_pm() -> PassManager:
    """
    Phase 1: Initialization
    Unrolls higher-level mathematical objects and custom gate definitions
    into base quantum instructions.
    """
    return PassManager([
        HighLevelSynthesis(),
        UnrollCustomDefinitions()
    ])