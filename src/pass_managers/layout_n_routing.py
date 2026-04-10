from qiskit.transpiler import CouplingMap, PassManager
from qiskit.transpiler.passes import (
    TrivialLayout, SabreLayout, 
    BasicSwap, SabreRouting
)
# TODO: other layout and routing passes to consider
def get_layout_routing_pm(coupling_map: CouplingMap, use_sabre: bool = True) -> PassManager:
    """
    Phases 2 & 3: Layout and Routing
    Maps the circuit to the physical hardware and inserts SWAP gates to satisfy connectivity.
    """
    if use_sabre:
        # Sabre is hardware-aware and highly optimized
        return PassManager([
            SabreLayout(coupling_map),
            SabreRouting(coupling_map)
        ])
    else:
        # Trivial is good for basic, predictable test cases
        return PassManager([
            TrivialLayout(coupling_map),
            BasicSwap(coupling_map)
        ])