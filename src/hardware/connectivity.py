# import pandas as pd

# def is_connected(q1, q2, connectivity):
#     df = None
#     if q1 == q2:
#         raise ValueError("Cannot check connectivity between the same qubits.")
#     if connectivity.endswith('.csv'):
#         df = pd.read_csv(connectivity)
#         connectivity = df.values.tolist()
    
#     return [q1, q2] in df or [q2, q1] in df

from qiskit.transpiler import CouplingMap


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
    connector_local: int = 0,
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

    if not (0 <= connector_local < n_block):
        raise ValueError(
            f"connector_local must be between 0 and {n_block - 1}, got {connector_local}."
        )

    edge_set = set()

    def block_id(br, bc):
        return br * n_blocks_col + bc

    def block_offset(br, bc):
        return block_id(br, bc) * n_block

    # Add all intra-block edges.
    local_edges = _block_edges(n, m, k_intra)

    for br in range(n_blocks_row):
        for bc in range(n_blocks_col):
            offset = block_offset(br, bc)
            for u, v in local_edges:
                edge_set.add((u + offset, v + offset))

    # Connect blocks using the chosen connector qubit.
    for br in range(n_blocks_row):
        for bc in range(n_blocks_col):
            for br2 in range(n_blocks_row):
                for bc2 in range(n_blocks_col):
                    # Skip the same block.
                    if br == br2 and bc == bc2:
                        continue

                    block_dist = abs(br2 - br) + abs(bc2 - bc)

                    # k_inter=1 means only adjacent blocks in the tile grid.
                    if 1 <= block_dist <= k_inter:
                        q1 = block_offset(br, bc) + connector_local
                        q2 = block_offset(br2, bc2) + connector_local
                        edge_set.add(tuple(sorted((q1, q2))))

    # Add both directions since CouplingMap is directed.
    coupling_list = [[u, v] for u, v in edge_set] + [[v, u] for u, v in edge_set]

    cmap = CouplingMap(couplinglist=coupling_list)

    # Quick check that the total qubit count matches what we expect.
    if cmap.size() != n_total:
        raise RuntimeError(
            f"CouplingMap size mismatch: expected {n_total}, got {cmap.size()}."
        )

    return cmap


def build_pipeline_coupling_map(
    n_blocks_row: int,
    n_blocks_col: int,
    n: int,
    m: int,
    k_intra: int,
    k_inter: int = 1,
    connector_local: int = 0,
) -> CouplingMap:
    """Build the coupling map used by the main pipeline."""
    return k_nearest_tiled_coupling_map(
        n_blocks_row=n_blocks_row,
        n_blocks_col=n_blocks_col,
        n=n,
        m=m,
        k_intra=k_intra,
        k_inter=k_inter,
        connector_local=connector_local,
    )

# Example 
if __name__ == "__main__":
    cmap = build_pipeline_coupling_map(
        n_blocks_row=2,
        n_blocks_col=2,
        n=3,
        m=3,
        k_intra=1,
        k_inter=1,
        connector_local=0,
    )

    print("Total qubits :", cmap.size())
    print("Total edges  :", len(cmap.get_edges()))
    print("Is connected :", cmap.is_connected())

    img = cmap.draw()
    img.show()