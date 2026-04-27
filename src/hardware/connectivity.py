from __future__ import annotations
from pathlib import Path
import pandas as pd 
from qiskit.transpiler import CouplingMap

CONNECTIVITY_MAP_DIR = Path(__file__).resolve().parents[1] / "connectivity_maps"


def load_coupling_map_from_csv(csv_path: str | Path) -> CouplingMap:
    """
    Load a Qiskit CouplingMap from a CSV edge list.

    Expected CSV columns:
    Qubit_1,Qubit_2
    """
    df = pd.read_csv(csv_path)
    coupling_list = df[["Qubit_1", "Qubit_2"]].astype(int).values.tolist()
    return CouplingMap(couplinglist=coupling_list)



# Build coupling map for IBM Fez 
def load_ibm_fez_coupling_map() -> CouplingMap:
    """Load the IBM Fez heavy-hex coupling map from CSV."""
    return load_coupling_map_from_csv(
        CONNECTIVITY_MAP_DIR / "ibm_fez_connectivity.csv"
    )

# Build coupling map for IBM Torino 
def load_ibm_torino_coupling_map() -> CouplingMap:
    """Load the IBM Torino heavy-hex coupling map from CSV."""
    return load_coupling_map_from_csv(
        CONNECTIVITY_MAP_DIR / "ibm_torino_connectivity.csv"
    )


def _block_edges(n, m, k):
    """Build undirected edges inside one n x m block."""
    edges = set()

    for r in range(n):
        for c in range(m):
            q = r * m + c

            # Check all sites within Manhattan radius k.
            for dr in range(0, k + 1):
                startdc = 1 if dr == 0 else -(k - dr)
                for dc in range(startdc, k - dr + 1):
                    dist = abs(dr) + abs(dc)

                    # Skip itself and anything outside the cutoff.
                    if dist == 0 or dist > k:
                        continue

                    rr, cc = r + dr, c + dc

                    # Ignore coordinates outside the block.
                    if 0 <= rr < n and 0 <= cc < m:
                        q2 = rr * m + cc

                        # Sort so each undirected edge is only stored once.
                        edges.add(tuple(sorted((q, q2))))
    return sorted(edges)


def k_nearest_tiled_coupling_map(
    n_blocks_row: int,
    n_blocks_col: int,
    n: int,
    m: int,
    k_intra: int,
    k_inter: int = 1,
    connector_local: int = 1,
) -> CouplingMap:
    """Build a CouplingMap for a tiled block layout."""
    if n_blocks_row <= 0 or n_blocks_col <= 0:
        raise ValueError("Number of block rows/cols must be positive.")
    if n <= 0 or m <= 0:
        raise ValueError("Block dimensions n and m must be positive.")
    if k_intra < 1:
        raise ValueError("k_intra must be at least 1.")
    if k_inter < 1:
        raise ValueError("k_inter must be at least 1.")

    n_block = n * m
    n_total = n_blocks_row * n_blocks_col * n_block

    if connector_local < 1:
        raise ValueError("connector_local (step size) must be at least 1.")

    edge_set = set()

    def block_id(br, bc):
        return br * n_blocks_col + bc

    def block_offset(br, bc):
        return block_id(br, bc) * n_block

    def get_centered_edge_indices(length: int, step: int) -> range:
        """
        Returns a range of indices stepping by `step`, perfectly 
        centered within the `length` of the edge.
        """
        # Calculate how many full steps fit in the length
        span = ((length - 1) // step) * step
        # Calculate the starting offset to center the span
        offset = (length - 1 - span) // 2
        return range(offset, length, step)

    # Add all intra-block edges.
    local_edges = _block_edges(n, m, k_intra)

    for br in range(n_blocks_row):
        for bc in range(n_blocks_col):
            offset = block_offset(br, bc)
            for u, v in local_edges:
                edge_set.add((u + offset, v + offset))


    
    # add interconnected edges between blocks based on k_inter and connector_local parameters
    for br in range(n_blocks_row):
        for bc in range(n_blocks_col):
            offset_a = block_offset(br, bc)
            
            for br2 in range(n_blocks_row):
                for bc2 in range(n_blocks_col):
                    if br == br2 and bc == bc2: continue
                    
                    # Manhattan distance between blocks
                    block_dist = abs(br2 - br) + abs(bc2 - bc)
                    
                    if 1 <= block_dist <= k_inter:
                        offset_b = block_offset(br2, bc2)
                        
                        # Calculate relative direction
                        dr = br2 - br
                        dc = bc2 - bc
                        
                        # Right Edge
                        if dc > 0 and dr == 0:
                            for r in get_centered_edge_indices(n, connector_local):
                                q_a = offset_a + (r * m + (m - 1))
                                q_b = offset_b + (r * m + 0)
                                edge_set.add(tuple(sorted((q_a, q_b))))
                                
                        # Left Edge
                        elif dc < 0 and dr == 0:
                            for r in get_centered_edge_indices(n, connector_local):
                                q_a = offset_a + (r * m + 0)
                                q_b = offset_b + (r * m + (m - 1))
                                edge_set.add(tuple(sorted((q_a, q_b))))

                        # Bottom Edge
                        elif dr > 0 and dc == 0:
                            for c in get_centered_edge_indices(m, connector_local):
                                q_a = offset_a + ((n - 1) * m + c)
                                q_b = offset_b + (0 * m + c)
                                edge_set.add(tuple(sorted((q_a, q_b))))

                        # Top Edge
                        elif dr < 0 and dc == 0:
                            for c in get_centered_edge_indices(m, connector_local):
                                q_a = offset_a + (0 * m + c)
                                q_b = offset_b + ((n - 1) * m + c)
                                edge_set.add(tuple(sorted((q_a, q_b))))

                        # Diagonals (Lock to the nearest corners to prevent messy crossed wires)
                        elif abs(dr) == 1 and abs(dc) == 1:
                            r_a = n-1 if dr > 0 else 0
                            c_a = m-1 if dc > 0 else 0
                            r_b = 0 if dr > 0 else n-1
                            c_b = 0 if dc > 0 else m-1
                            q_a = offset_a + (r_a * m + c_a)
                            q_b = offset_b + (r_b * m + c_b)
                            edge_set.add(tuple(sorted((q_a, q_b))))
    # Add both directions since CouplingMap is directed.
    coupling_list = [[u, v] for u, v in edge_set] + [[v, u] for u, v in edge_set]

    cmap = CouplingMap(couplinglist=coupling_list)

    # Quick check that the total qubit count matches what we expect.
    if cmap.size() != n_total:
        raise RuntimeError(
            f"CouplingMap size mismatch: expected {n_total}, got {cmap.size()}."
        )

    return cmap


def build_ft_style_coupling_map(
    k_intra: int = 2,
    k_inter: int = 1,
) -> CouplingMap:
    """
    Build the custom multi-block k-nearest connectivity map used as the
    FT-style architecture model.

    This uses the same 2x2 tiled 10x10-block structure from main_pipeline.py.
    It is a structural connectivity model only, not a full surface-code,
    decoder, or noise simulation.
    """
    return k_nearest_tiled_coupling_map(
        n_blocks_row=2,
        n_blocks_col=2,
        n=10,
        m=10,
        k_intra=k_intra,
        k_inter=k_inter,
        connector_local=0,
    )



def get_benchmark_coupling_maps() -> dict[str, CouplingMap]:
    """
    Return all coupling maps used in the main NISQ-vs-FT-style benchmark.
    """
    return {
        "IBM Fez heavy-hex": load_ibm_fez_coupling_map(),
        "IBM Torino heavy-hex": load_ibm_torino_coupling_map(),
        "Custom FT-style 2x2 tiled k-nearest": build_ft_style_coupling_map(
            k_intra=2,
            k_inter=1,
        ),
    }


if __name__ == "__main__":
    maps = get_benchmark_coupling_maps()

    for name, cmap in maps.items():
        print(name)
        print("Total qubits :", cmap.size())
        print("Total edges  :", len(cmap.get_edges()))
        print("Is connected :", cmap.is_connected())
        print()
