from __future__ import annotations
from pathlib import Path
import pandas as pd 
from qiskit.transpiler import CouplingMap
import networkx as nx
import matplotlib.pyplot as plt

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

## helper function for building the tiled k-nearest coupling map
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

# helper function for building the hexagonal and square lattice coupling maps
def get_evenly_spaced_ports(port_list: list, k: int) -> list:
    """Returns k evenly spaced elements from a list."""
    if k <= 0 or not port_list:
        return []
    if k >= len(port_list):
        return port_list
    if k == 1:
        # For a single connection, the middle of the edge is the most efficient spot
        return [port_list[len(port_list) // 2]]
    
    # Calculate the exact step size to include both endpoints if possible
    step = (len(port_list) - 1) / (k - 1)
    return [port_list[int(round(i * step))] for i in range(k)]

def k_nearest_tiled_coupling_map(
    n_blocks_row: int,
    n_blocks_col: int,
    n: int,
    m: int,
    k_intra: int,
    k_inter: int = 1,
    connector_local: int = 1,
) -> tuple[CouplingMap, int]:
    """Build a CouplingMap for a tiled block layout.
    each block has n rows and m columns of qubits, with k_intra nearest neighbor connectivity within the block.
    Blocks are arranged in a grid with n_blocks_row rows and n_blocks_col columns.
    Inter-block connectivity is determined by k_inter (which blocks are connected)
    and connector_local (how many qubits on the edge are connected between blocks).
    """


    if n_blocks_row <= 0 or n_blocks_col <= 0:
        raise ValueError("Number of block rows/cols must be positive.")
    if n <= 0 or m <= 0:
        raise ValueError("Block dimensions n and m must be positive.")
    if k_intra < 1:
        raise ValueError("k_intra must be at least 1.")
    if k_inter < 1:
        raise ValueError("k_inter must be at least 1.")


    # total qubits per block and overall
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
                        
                        # Calculate relative direction (up, down, left, right) to determine which edges to connect
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
    _size = cmap.size()
    if _size != n_total:
        raise RuntimeError(
            f"CouplingMap size mismatch: expected {n_total}, got {_size}."
        )

    return (cmap, _size)


# will insert method to construct the coupling map for heavy hex and heavy square arcitectures, given number of qubits per block and number of blocks to consider

#In the heavy-hex architecture, data qubits sit on the vertices and edges of the hexagons. 
# To minimize error cascades and avoid disrupting the inner surface code stabilizers, network interconnects must be attached to boundary 
# data qubits—specifically, qubits on the perimeter of the lattice that have fewer native connections (degree ≤ 2$).

def generate_modular_ft_lattice(
    architecture: str = "heavy_hex", 
    d: int = 5, # number of data qubits per side in the base block (e.g., d=5 for a distance-5 surface code block)
    n_blocks_row: int = 2, 
    n_blocks_col: int = 2,
    k_inter: int = 1  # Number of interconnects between adjacent QPUs
) -> tuple[CouplingMap, int, int, dict]:
    """
    Creates a 2D network of Fault-Tolerant QPUs (Heavy Hex or Heavy Square).
    Automatically identifies boundary data qubits to form the network links.
    """
    # 1. Generate base Logical QPU
    if architecture == "heavy_hex":
        base_cmap = CouplingMap.from_heavy_hex(d)
        max_degree = 3  # Hex lattice max connections
    elif architecture == "heavy_square":
        base_cmap = CouplingMap.from_heavy_square(d)
        max_degree = 4  # Square lattice max connections
    else:
        raise ValueError(f"Unsupported architecture: {architecture}")

    n_block = base_cmap.size()
    G_base = nx.Graph()
    G_base.add_edges_from(base_cmap.get_edges())

    # 2. Auto-discover the 2D geometry to find boundary data qubits
    # kamada_kawai_layout perfectly rebuilds the 2D planar structure based on graph distances
    local_pos = nx.kamada_kawai_layout(G_base)
    
    # 3. Identify Candidate "Data Qubits" on the boundary
    boundary_nodes = [n for n, deg in G_base.degree() if deg < max_degree]
    
    # Find the absolute extreme coordinates of the QPU block
    min_x = min(local_pos[n][0] for n in boundary_nodes)
    max_x = max(local_pos[n][0] for n in boundary_nodes)
    min_y = min(local_pos[n][1] for n in boundary_nodes)
    max_y = max(local_pos[n][1] for n in boundary_nodes)

    # Define a small tolerance (e.g., 20% of the width) to catch all nodes on that edge
    tol_x = 0.2 * (max_x - min_x)
    tol_y = 0.2 * (max_y - min_y)

    # Isolate all qubits that belong to each specific wall
    left_wall = [n for n in boundary_nodes if local_pos[n][0] < min_x + tol_x]
    right_wall = [n for n in boundary_nodes if local_pos[n][0] > max_x - tol_x]
    bottom_wall = [n for n in boundary_nodes if local_pos[n][1] < min_y + tol_y]
    top_wall = [n for n in boundary_nodes if local_pos[n][1] > max_y - tol_y]

    # Sort the walls along their PERIMETER so they are in physical order
    left_wall.sort(key=lambda n: local_pos[n][1])   # Sort Y
    right_wall.sort(key=lambda n: local_pos[n][1])  # Sort Y
    bottom_wall.sort(key=lambda n: local_pos[n][0]) # Sort X
    top_wall.sort(key=lambda n: local_pos[n][0])    # Sort X

    # Sample them evenly using your chosen k_inter!
    left_ports = get_evenly_spaced_ports(left_wall, k_inter)
    right_ports = get_evenly_spaced_ports(right_wall, k_inter)
    bottom_ports = get_evenly_spaced_ports(bottom_wall, k_inter)
    top_ports = get_evenly_spaced_ports(top_wall, k_inter)

    print(f"[{architecture.upper()} d={d}] Block Size: {n_block} physical qubits")
    print(f"Evenly Distributed Ports -> L:{left_ports}, R:{right_ports}, T:{top_ports}, B:{bottom_ports}")

    combined_edges = []
    global_pos = {}  # Store the global coordinates for your plot() function
    
    # Define a visual spacing gap between the QPUs
    gap_x = max(local_pos[n][0] for n in G_base.nodes) - min(local_pos[n][0] for n in G_base.nodes) + 1.5
    gap_y = max(local_pos[n][1] for n in G_base.nodes) - min(local_pos[n][1] for n in G_base.nodes) + 1.5

    # 4. Tile the Blocks and Interconnect Them
    for r in range(n_blocks_row):
        for c in range(n_blocks_col):
            block_idx = r * n_blocks_col + c
            offset = block_idx * n_block
            
            # Shift the local coordinates to global coordinates for plotting
            for n in G_base.nodes:
                global_pos[n + offset] = (local_pos[n][0] + (c * gap_x), local_pos[n][1] - (r * gap_y))
            
            # A. Add Intra-block (Local) edges
            for q1, q2 in base_cmap.get_edges():
                combined_edges.append((q1 + offset, q2 + offset))
                
            # B. Add Inter-block edges (Row connections: Right port to Left port)
            if c < n_blocks_col - 1:
                next_offset = r * n_blocks_col + (c + 1)
                next_offset *= n_block
                
                for port_out, port_in in zip(right_ports, left_ports):
                    combined_edges.append((port_out + offset, port_in + next_offset))
                    combined_edges.append((port_in + next_offset, port_out + offset))
                    
            # C. Add Inter-block edges (Col connections: Bottom port to Top port)
            if r < n_blocks_row - 1:
                down_offset = (r + 1) * n_blocks_col + c
                down_offset *= n_block
                
                for port_out, port_in in zip(bottom_ports, top_ports):
                    combined_edges.append((port_out + offset, port_in + down_offset))
                    combined_edges.append((port_in + down_offset, port_out + offset))

    final_cmap = CouplingMap(combined_edges)
    return final_cmap, final_cmap.size(), n_block, global_pos



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
