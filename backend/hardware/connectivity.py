from __future__ import annotations
from pathlib import Path
import pandas as pd 
from qiskit.transpiler import CouplingMap
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

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


######################################################

## CODE FOR K_NEAREST_NEIGHBOR CONNECTIVITY NETWORK ##

######################################################




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
    and connector_local (how many blocks a qubit can connect to).
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

    # helper functions to return a given block ID and calculate the offset
    # for global positioning
    def block_id(br, bc):
        return br * n_blocks_col + bc

    def block_offset(br, bc):
        return block_id(br, bc) * n_block

    def get_centered_edge_indices(length: int, step: int) -> range:
        """
        Returns a range of indices stepping by `step`,  
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
                    if br == br2 and bc == bc2: 
                        continue
                    
                    dr = br2 - br
                    dc = bc2 - bc
                    
                    # Determine if the target block is on a valid horizontal, vertical, or 
                    # exact diagonal ray AND if it is within the k_inter range.
                    is_valid_ray = False
                    if dr == 0 and 0 < abs(dc) <= k_inter:
                        is_valid_ray = True  # Horizontal
                    elif dc == 0 and 0 < abs(dr) <= k_inter:
                        is_valid_ray = True  # Vertical
                    elif abs(dr) == abs(dc) and 0 < abs(dr) <= k_inter:
                        is_valid_ray = True  # Diagonal
                        
                    if is_valid_ray:
                        offset_b = block_offset(br2, bc2)
                        
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
                        elif abs(dr) == abs(dc):
                            # sets the corner indices no matter how far away (k_inter) the block is
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



######################################

## CODE FOR HEAVY HEX AND HEAVY SQUARE

######################################



## helper functions for getting the network of generate_modular_layout

def orient_by_triangle(pos, corner_list):
    """
    Identifies the pivot corner of the 3-point triangle, calculates its angle, 
    and rotates the entire graph so the layout sits perfectly square to the axes.
    """
    c1, c2, c3 = corner_list
    p1, p2, p3 = pos[c1], pos[c2], pos[c3]

    # Fast squared distance helper, useful for trig relation
    def sq_dist(pa, pb):
        return (pa[0] - pb[0])**2 + (pa[1] - pb[1])**2

    # Calculate the lengths of the three sides of the triangle
    d12 = sq_dist(p1, p2)
    d23 = sq_dist(p2, p3)
    d31 = sq_dist(p3, p1)

    # Identify the "Pivot" (the corner opposite the longest side / diagonal)
    if d12 >= d23 and d12 >= d31:
        # Diagonal is c1-c2, therefore c3 is the 90-degree corner
        pivot, edge_pt = c3, c1 
    elif d23 >= d12 and d23 >= d31:
        # Diagonal is c2-c3, therefore c1 is the 90-degree corner
        pivot, edge_pt = c1, c2 
    else:
        # Diagonal is c3-c1, therefore c2 is the 90-degree corner
        pivot, edge_pt = c2, c3 

    # Calculate the angle of the line connecting the Pivot to the Edge Point
    dx = pos[edge_pt][0] - pos[pivot][0]
    dy = pos[edge_pt][1] - pos[pivot][1]
    
    # arctan for angle 
    current_angle = np.arctan2(dy, dx)
    
    # We want this edge to be perfectly horizontal (0 radians)
    # The required rotation is simply the difference: Target (0) - Current
    theta = 0 - current_angle

    # Apply the rotation matrix to all points
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    
    
    return {n : (x * cos_t - y * sin_t, x * sin_t + y * cos_t) for n, (x, y) in pos.items()}

def re_center(pos,total):

    # re-center all points of the network graph
    avg_x = sum(coord[0] for coord in pos.values()) / total
    avg_y = sum(coord[1] for coord in pos.values()) / total
    

    # centering logic
    return {n: (x - avg_x, y - avg_y) for n, (x, y) in pos.items()}
    


def get_perimeter_data_qubits(d):
    """
    Utilizes indexing math to safely identify the boundary qubits by the 
    distance of the code. 
    """

    # there's an indexing skip pattern I can use

    # data qubits are always indexed up to d^2 
    data_qubit_ids = d**2

    one = []
    two = []
    three = []
    
    # the upper and lower are always the firsd d and last d^2-d qubits
    one.extend(list(range(0,d)))
    three.extend(list(range(data_qubit_ids - d, data_qubit_ids)))
    num = d - 1

    #add the first/last edge, always index 0 and d-1
    two.append(0)
    two.append(num)


    # loop the following
    while True:
        # add one higher
        num += 1
        two.append(num)

        # If I've hit the first top qubit or higher, stop
        if num >= (data_qubit_ids - (d+1)):
            break

        # add index d-1 away (skip internal data qubits)
        num += (d-1)
        two.append(num)
    
    #append the final edge index, always the d^2'th one
    two.append((d**2) - 1)
    
    return one, two, three
    


    
            
    



def generate_modular_layout(architecture="heavy_hex", d=3, rows=2, cols=2, interconnect = 1):
    # Generate the base block and layout
    if architecture == "heavy_hex":
        base_cmap = CouplingMap.from_heavy_hex(d)

    elif architecture == "heavy_square":
        base_cmap = CouplingMap.from_heavy_square(d)
        
    else:
        raise KeyError("Need to give heavy_hex or heavy_square")
    
    
    
    # numbr of qubits per blo k
    n_total_per_block = base_cmap.size()

    # need a list of the edges to turn into graph
    edge_list = list(base_cmap.get_edges())

    # Use neato (via networkx) to get the local footprint
    G_base = nx.Graph(edge_list)

    degree_one = [node for node, degree in G_base.degree() if degree == 1]
    
    corners = list()
    if architecture == "heavy_hex":
        corners.append(0)
    elif architecture == "heavy_square":
        corners.append(d-1)

    for ones in degree_one:

        neighbor = next(G_base.neighbors(ones))
        corners.append(neighbor)
        

    # while not necessary for base connectivity, graphing is done here and saved in a 
    # pos variable given complexity of the task
    # could be good to move this elsewhere but was a major challenge to get working
    
    # create the network layout of a single logical qubit
    try:
        local_pos = nx.drawing.nx_agraph.graphviz_layout(G_base, prog='neato')
    except ImportError:
        local_pos = nx.spring_layout(G_base, seed=1738)
    
    # normalize so the center is now located in the middle of the block
    local_pos = re_center(local_pos, n_total_per_block)

    # orient the graph upright for better tiling visibility
    local_pos = orient_by_triangle(local_pos, corners)
    

    # gives lists of upper, lower, and left/right qubits
    # not guarenteed that either x is the top or bottom but 
    # doesn't change the connection logic
    X_one, Y_both, X_two = get_perimeter_data_qubits(d)
    
    # boolean check to find the order 
    # if X_one is on top and if Y_both goes left-right
    if local_pos[X_one[0]][1] < local_pos[X_two[0]][1]:
        top = X_two
        bottom = X_one
    else:
        top = X_one
        bottom = X_two

    if local_pos[Y_both[0]][0] < local_pos[Y_both[1]][0]:
        left_start = 0
    else:
        left_start = 1
    


    # Calculate Width and Height of the block
    xs = [p[0] for p in local_pos.values()]
    ys = [p[1] for p in local_pos.values()]

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    
    # Add a 20% buffer so blocks have breathing room
    pitch_x = width * 1.2
    pitch_y = height * 1.2

    
    # global positioning graph and list of all
    global_pos = {}
    combined_edges = []

    # indexing math to make sure intermediary measurement nodes between data qubits
    # have unique index's. Left to right measurement index starts at 
    # total number of qubits, top to bottom starts at that index times number
    # of measure qubits per left/right and the number of rows / columns that 
    # the left right data will have to fill

    # basically start at total number of qubits then total number of 
    # left/right measurement qubits
    lr_measure_idx = n_total_per_block * rows * cols
    tb_measure_idx = lr_measure_idx + (len(Y_both)//2) * (cols-1) * rows

    # Tile and Shift, go row by row, left to right
    for r in range(rows):
        for c in range(cols):


            # calculate offset index of each qubit inside a block
            offset_idx = (r * cols + c) * n_total_per_block

            # get a position to start at 
            dx, dy = c * pitch_x, -r * pitch_y

            

            # place node in global position by offset
            for node, (lx, ly) in local_pos.items():
                global_pos[node + offset_idx] = (lx + dx, ly + dy)
            
            # get all inter-connected edges of new block
            for q1, q2 in base_cmap.get_edges():
                combined_edges.append((q1 + offset_idx, q2 + offset_idx))
                # follows inter-block connectivity logic of the surface code
                # (i believe needs further testing)

            # ---------------------------------------------------------
            # 1. CONNECT UP (if not first row)
            # ---------------------------------------------------------
            if r != 0:
                # calculate the offset for the block directly above us
                top_block_offset = ((r - 1) * cols + c) * n_total_per_block

                # iterate through your top/bottom boundary lists
                for i in range(len(top)):
                    curr_top_node = top[i] + offset_idx
                    prev_bottom_node = bottom[i] + top_block_offset

                    # find the physical midpoint for the measurement qubit
                    mx = (global_pos[curr_top_node][0] + global_pos[prev_bottom_node][0]) / 2.0
                    my = (global_pos[curr_top_node][1] + global_pos[prev_bottom_node][1]) / 2.0

                    # register the measurement qubit position
                    global_pos[tb_measure_idx] = (mx, my)

                    # connect: Previous Bottom -> Measure Qubit -> Current Top
                    combined_edges.append((prev_bottom_node, tb_measure_idx))
                    combined_edges.append((tb_measure_idx, curr_top_node))

                    # increment the top-bottom measurement index counter
                    tb_measure_idx += 1


            # ---------------------------------------------------------
            # 2. CONNECT LEFT (if not first column)
            # ---------------------------------------------------------
            if c != 0:
                # calculate the offset for the block directly to our left
                left_block_offset = (r * cols + (c - 1)) * n_total_per_block

                # set up the alternating indices based on your boolean
                # if left_start == 0, lefts are even (0, 2, 4) and rights are odd (1, 3, 5)
                # if left_start == 1, lefts are odd (1, 3, 5) and rights are even (0, 2, 4)
                curr_left_start = left_start
                prev_right_start = 1 - left_start # opposite!

                # loop through the pairs in Y_both
                for i in range(0, len(Y_both) // 2):
                    curr_left_node = Y_both[i * 2 + curr_left_start] + offset_idx
                    prev_right_node = Y_both[i * 2 + prev_right_start] + left_block_offset

                    # find the physical midpoint for the measurement qubit
                    mx = (global_pos[curr_left_node][0] + global_pos[prev_right_node][0]) / 2.0
                    my = (global_pos[curr_left_node][1] + global_pos[prev_right_node][1]) / 2.0

                    # register the measurement qubit position
                    global_pos[lr_measure_idx] = (mx, my)

                    # connect: previous right -> measure qubit -> current left
                    combined_edges.append((prev_right_node, lr_measure_idx))
                    combined_edges.append((lr_measure_idx, curr_left_node))

                    # increment the left-right measurement index counter
                    lr_measure_idx += 1

     
    final_map = CouplingMap(combined_edges)


    return final_map, final_map.size(), n_total_per_block, global_pos
