from qiskit.transpiler.passes import (
    CommutativeCancellation, 
    RemoveResetInZeroState,
    Depth,
    Size
)


from qiskit.transpiler import PassManager



# TODO: find other optimization passes...
def get_optimization_pm() -> PassManager:
    """
    Phase 5: Optimization
    Iteratively shrinks the circuit by removing redundancies. 
    This is the core of the dynamic transpiler loop.
    """
    
    
    return PassManager([
        CommutativeCancellation(),
        RemoveResetInZeroState(),
        # You can add passes like Collect2qBlocks and ConsolidateBlocks here later
        # to resynthesize complex 2-qubit interactions.
    ])