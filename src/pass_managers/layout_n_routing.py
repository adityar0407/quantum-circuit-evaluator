from __future__ import annotations

from qiskit.transpiler import CouplingMap, PassManager
from qiskit.transpiler.passes import (
    TrivialLayout, SabreLayout, 
    BasicSwap, SabreSwap
)
# TODO: other layout and routing passes to consider
def get_layout_pm(
    coupling_map: CouplingMap,
    use_sabre: bool = True,
    seed_transpiler: int | None = 12345,
) -> PassManager:
    """
    Phase 2: Layout
    Assigns logical circuit qubits to physical hardware qubits.
    """
    if use_sabre:
        return PassManager([SabreLayout(coupling_map, seed=seed_transpiler)])

    return PassManager([TrivialLayout(coupling_map)])


def get_routing_pm(
    coupling_map: CouplingMap,
    use_sabre: bool = True,
    seed_transpiler: int | None = 12345,
) -> PassManager:
    """
    Phase 3: Routing
    Inserts SWAP gates until every two-qubit operation satisfies connectivity.
    """
    if use_sabre:
        return PassManager([SabreSwap(coupling_map, seed=seed_transpiler)])

    return PassManager([BasicSwap(coupling_map)])


def get_layout_routing_pm(
    coupling_map: CouplingMap,
    use_sabre: bool = True,
    seed_transpiler: int | None = 12345,
) -> PassManager:
    """
    Phases 2 & 3: Layout and Routing
    Maps the circuit to physical hardware and inserts SWAP gates as needed.
    """
    layout_passes = get_layout_pm(coupling_map, use_sabre, seed_transpiler).passes()
    routing_passes = get_routing_pm(coupling_map, use_sabre, seed_transpiler).passes()

    passes = []
    for pass_group in layout_passes + routing_passes:
        passes.extend(pass_group["passes"])

    return PassManager(passes)
