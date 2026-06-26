from backend.hardware.connectivity import k_nearest_tiled_coupling_map, generate_modular_layout
import json
from qiskit.transpiler import Target
import qiskit.circuit.library as qlib
import networkx as nx
from qiskit.transpiler import CouplingMap
from qiskit.circuit import Measure, Parameter, Delay
import random



class FTarget(Target):
    """
    A Qiskit Target fully defined by a configuration dictionary or JSON.
    It validates the gate set architecture upon creation. Topology is 
    defined as either a custom target, a k nearest connected network, or 
    a heavy hexagonal / heavy square surface code. 

    FTarget is treated as a logical architecture object. Gate-property payloads
    in the input profile are accepted for backward compatibility, but they are
    not interpreted as physical error rates or physical gate durations here.
    """
    def __init__(self, config: dict = None, **kwargs):


        # Merge the provided config with any explicit kwargs
        self.config = config or {}
        self.config.update(kwargs)
        self.logical_architecture_only = True
        self.legacy_physical_metadata_fields = {
            "sq_gates": ["error", "duration"],
            "two_q_gates": ["local_error", "local_duration"],
            "inter_device_gates": ["inter_error", "inter_duration"],
        }
        

        

        self.topology = self.config.get("topology")
        if not isinstance(self.topology, dict):
            raise ValueError("Configuration must contain a 'topology' dictionary.")

        # Extract topology parameters
        self.type = self.topology.get("type", "tiled_k_nearest")
        # topology will be a dict containing the necessary parameters to build the coupling map

        # Validate the profile before doing expensive topology/layout work.
        self._validate_and_parse_profile()

        if self.type == "tiled_k_nearest":
            # defaults to constructing a 2x2 computer with 100 qubits each. 
            self.n_blocks_row = self.topology.get("n_blocks_row", 2)
            self.n_blocks_col = self.topology.get("n_blocks_col", 2)
            self.n = self.topology.get("n", 10)
            self.m = self.topology.get("m", 10)
            self.k_intra = self.topology.get("k_intra", self.n * self.m) # Default to fully connected locally

            
            self.k_inter = self.topology.get("k_inter", 1) # default to nearest neighbor
            self.connector_local = self.topology.get("connector_local", 1)


            # Build the underlying geometry for the target using the provided topology parameters
            self.cmap, self.total_qubits = k_nearest_tiled_coupling_map(
                n_blocks_row=self.n_blocks_row, 
                n_blocks_col=self.n_blocks_col,
                n=self.n, 
                m=self.m, 
                k_intra=self.k_intra, 
                k_inter=self.k_inter, 
                connector_local=self.connector_local
                )
            
            # number of qubits per block
            self.n_block = self.n * self.m
            


        ## 
        elif self.type == "custom_coupling_map":
            raw_cmap = self.topology.get("coupling_map", [])
            # Fixed the isinstance syntax
            if isinstance(raw_cmap, CouplingMap):
                self.cmap = raw_cmap
            elif isinstance(raw_cmap, list):
                self.cmap = CouplingMap(couplinglist=raw_cmap)
            else:
                raise ValueError("For 'custom_coupling_map', 'coupling_map' must be a CouplingMap or list of edges.")
            
            self.total_qubits = self.cmap.size()
            self.n_block = self.total_qubits  # Default: treat custom maps as one single block

        

        elif self.type in ["heavy_hex", "heavy_square"]:
            self.n_blocks_row = self.topology.get("n_blocks_row", 2)
            self.n_blocks_col = self.topology.get("n_blocks_col", 2)
            self.k_inter = self.topology.get("k_inter", 1)
            self.d = self.topology.get("d", 5)  # The distance of the generated heavy_hex or heavy_square
            self.cmap, self.total_qubits, self.n_block, self.pos = generate_modular_layout(
                architecture=self.type,
                d=self.topology.get("d", 5),
                rows=self.n_blocks_row,
                cols=self.n_blocks_col,
                interconnect=self.k_inter  # Pass your connection distribution density here!
            )

            
            

            # need to extract the n and m per block to identify the block structure for logical block assignment
        else:
            raise ValueError(f"Unsupported topology type: {self.type}. Supported types are 'tiled_k_nearest', 'custom_coupling_map', 'heavy_hex', and 'heavy_square'.")

        # Global logic for determining if an edge is local or global 
        self._is_local_edge = lambda q1, q2: (q1 // self.n_block) == (q2 // self.n_block)

        # Initialize parent Qiskit Target
        super().__init__()
        
        # Populate Target with the dynamically loaded gates
        self._populate_instructions_network()



    def _validate_and_parse_profile(self):
        """Validates the input profile and converts string names to Qiskit gates."""
        profile = self.config.get("profile")
        if not profile:
            raise ValueError("Configuration must contain a 'profile' dictionary defining the architecture.")

        # -- 1. Single Qubit Gates --
        # Default to empty dict instead of list for safety
        self.sq_gate_dict = profile.get("sq_gates", {}) 
        
        if not isinstance(self.sq_gate_dict, dict) or not self.sq_gate_dict:
            raise ValueError("Profile must include a valid dict of 'sq_gates' (e.g., {'HGate': {'logical_weight': 1, 'logical_preference': 1}}).")

        sq_gate_names = list(self.sq_gate_dict.keys())


        # Accept legacy metadata keys for backward compatibility, but do not
        # interpret them as physical hardware properties in FTarget.
        for gate, props in self.sq_gate_dict.items():
            if not isinstance(props, dict):
                raise ValueError(f"Single-qubit gate '{gate}' must map to a metadata dictionary.")

        if len(sq_gate_names) < 2:
            print("Warning: Profile has fewer than 2 single-qubit gates. This may not form a universal gate set.")

        # -- 2. Two Qubit Gates --
        self.two_q_gate_dict = profile.get("two_q_gates", {})
        
        if not isinstance(self.two_q_gate_dict, dict) or not self.two_q_gate_dict:
            raise ValueError("Profile must specify at least one 'two_q_gates' dict.")
            
        two_q_gate_names = list(self.two_q_gate_dict.keys())
        
        for gate, props in self.two_q_gate_dict.items():
            if not isinstance(props, dict):
                raise ValueError(f"Two-qubit gate '{gate}' must map to a metadata dictionary.")


        # -- 3. Inter device Gates -- 
        # if none was provided, default to no networking at all
        self.inter_device_gate_dict = profile.get("inter_device_gates", {})
        if not isinstance(self.inter_device_gate_dict, dict) or not self.inter_device_gate_dict:
            if self.type == "tiled_k_nearest":
                print("Warning: No inter gate dictionary was provided. No gates between computers will be allowed")
            inter_device_gate_names = []
        else:
            inter_device_gate_names = list(self.inter_device_gate_dict.keys())
            for gate, props in self.inter_device_gate_dict.items():
                if not isinstance(props, dict):
                    raise ValueError(f"Inter-device gate '{gate}' must map to a metadata dictionary.")



        # String to Qiskit Object Conversion 
        # Store as dictionaries tying the name to the instantiated object
        self.sq_gates_objs = {name: self._instantiate_gate(name) for name in sq_gate_names}
        self.two_q_gates_objs = {name: self._instantiate_gate(name) for name in two_q_gate_names}
        self.inter_device_objs = {name: self._instantiate_gate(name) for name in inter_device_gate_names}



    def _instantiate_gate(self, gate_name: str):
        """Dynamically fetches a gate class from qiskit.circuit.library and instantiates it."""
        if not hasattr(qlib, gate_name):
            raise ValueError(f"Gate '{gate_name}' is not recognized in qiskit.circuit.library.")
        
        gate_class = getattr(qlib, gate_name)
        
        try:
            return gate_class()
        except TypeError:
            try:
                return gate_class(Parameter('theta'))
            except TypeError:
                try:
                    return gate_class(Parameter('theta'), Parameter('phi'))
                except TypeError:
                    return gate_class(Parameter('theta'), Parameter('phi'), Parameter('lam'))


    def _populate_instructions_network(self):
        """Internal method to add logical gate availability and connectivity to the Target."""
        
        # 1. Populate Single Qubit Gates

        for gate_name, gate_obj in self.sq_gates_objs.items():
            sq_props = {(q,): None for q in range(self.total_qubits)}
            self.add_instruction(gate_obj, sq_props)

        measure_props = {(q,): None for q in range(self.total_qubits)}
        self.add_instruction(Measure(), measure_props)

        # 2. Build Unified Two-Qubit Properties
        unified_two_q_props = {}
        unified_gate_objs = {}
        
        # Initialize dictionaries for local gates
        for gate_name, gate_obj in self.two_q_gates_objs.items():
            unified_two_q_props[gate_name] = {}
            unified_gate_objs[gate_name] = gate_obj
            
        # Initialize dictionaries for inter-device gates (if they aren't already there)
        for gate_name, gate_obj in self.inter_device_objs.items():
            if gate_name not in unified_two_q_props:
                unified_two_q_props[gate_name] = {}
                unified_gate_objs[gate_name] = gate_obj

        # Loop through ALL edges and funnel them into the unified dictionary
        for q1, q2 in self.cmap.get_edges():
            if self._is_local_edge(q1, q2):
                for gate_name in self.two_q_gates_objs.keys():
                    unified_two_q_props[gate_name][(q1, q2)] = None
            elif self.inter_device_objs:
                for inter_gate_name in self.inter_device_objs.keys():
                    unified_two_q_props[inter_gate_name][(q1, q2)] = None

        # 3. Add Instructions 
        for gate_name, gate_obj in unified_gate_objs.items():
            edge_dict = unified_two_q_props[gate_name]
            if len(edge_dict) > 0:
                self.add_instruction(gate_obj, edge_dict)
            else:
                print(f"Notice: '{gate_name}' was provided but skipped because no valid edges exist.")

        




    def _populate_instructions_hex():
        ## TODO implement a logic to accurately populate a heavy_hex and heavy_square
        ## based on the code's themselves
        pass
            
        
    # allows saving a target configurations if one made one dynamically 
    def to_json(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.config, f, indent=4)
        print(f"Target configuration saved to {filepath}")

    # allows opening from json files
    @classmethod
    def from_json(cls, filepath: str):
        with open(filepath, 'r') as f:
            config = json.load(f)
        return cls(config)
    



    def plot(self, filename: str = None, gap: int = 3):
        """Plots the coupling map using the structured grid layout
        Inter-connected devices are made to be the same color, with links 
        between devices being colored for easy identification"""
        import matplotlib.pyplot as plt

        # local dictionary for plotting
        pos = {}

        # 1. Fetch or generate the coordinate positions
        if self.type == "tiled_k_nearest":
            for qubit_id in range(self.total_qubits):
                block_id = qubit_id // self.n_block
                br_idx = block_id // self.n_blocks_col
                bc_idx = block_id % self.n_blocks_col
                local_id = qubit_id % self.n_block
                r = local_id // self.m
                c = local_id % self.m
                
                x = (bc_idx * (self.m + gap)) + c
                y = -((br_idx * (self.n + gap)) + r)
                pos[qubit_id] = [x, y]
                
        elif self.type in ["heavy_hex", "heavy_square"]:
            # saved computation from drawing graph when I was debugging,
            # so it's kept in the logic of implementing the grid layout
            pos = self.pos  
            
        else:
            G_temp = nx.Graph(self.cmap.get_edges())
            pos = nx.spring_layout(G_temp)

        # 2. Create NetworkX graph
        G = nx.DiGraph()
        G.add_nodes_from(range(self.total_qubits))
        G.add_edges_from(self.cmap.get_edges())

        # 3. Group Edges by Distance
        local_edges = []
        inter_edges_by_dist = {}  # Dictionary to group long-range edges by distance
        
        for u, v in G.edges():
            if self._is_local_edge(u, v):
                local_edges.append((u, v))
            else:
                # Reverse-engineer block coordinates for node u
                block_u = u // self.n_block
                br_u = block_u // self.n_blocks_col
                bc_u = block_u % self.n_blocks_col
                
                # Reverse-engineer block coordinates for node v
                block_v = v // self.n_block
                br_v = block_v // self.n_blocks_col
                bc_v = block_v % self.n_blocks_col
                
                # Calculate distance using Chebyshev (max ray) logic
                dist = max(abs(br_u - br_v), abs(bc_u - bc_v))
                
                # Group the edge into the dictionary based on its distance
                if dist not in inter_edges_by_dist:
                    inter_edges_by_dist[dist] = []
                inter_edges_by_dist[dist].append((u, v))

        # 4. Canvas Setup
        if self.type == "tiled_k_nearest":
            aspect_ratio = (self.n_blocks_col * (self.m + gap)) / max(1, (self.n_blocks_row * (self.n + gap)))
            plt.figure(figsize=(10 * aspect_ratio, 10))
        else:
            plt.figure(figsize=(12, 12))

        # 5. Layered Drawing Process
        block_colors = {}
        node_color_list = []
        
        # Use a vibrant continuous colormap to pick random colors from
        node_cmap = plt.get_cmap("rainbow") 

        for node in G.nodes():
            # Safely determine block ID (fallback to 0 if n_block doesn't exist for heavy_hex)
            if hasattr(self, 'n_block') and self.n_block > 0:
                block_id = node // self.n_block
            else:
                block_id = 0 
                
            # If this block doesn't have a color yet, assign it a random one!
            if block_id not in block_colors:
                # random.random() picks a random float between 0.0 and 1.0
                block_colors[block_id] = node_cmap(random.random())
                
            node_color_list.append(block_colors[block_id])

        # Draw Nodes with the generated list of colors
        nx.draw_networkx_nodes(
            G, 
            pos=pos, 
            node_size=100, 
            node_color=node_color_list 
        )
        
        # Draw Local Edges (Straight, Gray)
        nx.draw_networkx_edges(
            G, 
            pos=pos, 
            edgelist=local_edges, 
            edge_color="#A0A0A0", 
            arrows=False
        )
        
        # Draw Inter-block Edges in Batches
        # Grab a discrete categorical colormap 
        cmap = plt.get_cmap("tab10") 
        
        # Sort the dictionary so we draw distance 1, then distance 2, etc.
        for dist, edges in sorted(inter_edges_by_dist.items()):
            
            # Map the distance to a specific color in the colormap
            # (used dist % 10 just in case k_inter > 10, to prevent index errors)
            color = cmap(dist % 10)
            
            # Dynamically calculate curvature! Longer distances get taller arcs.
            # dist 1 = 0.2 rad, dist 2 = 0.3 rad, dist 3 = 0.4 rad, etc.
            if self.type == "tiled_k_nearest":

                dynamic_rad = 0.1 + (dist * 0.1)
            elif self.type == "heavy_hex" or self.type == "heavy_square":
                dynamic_rad = 0
            
            nx.draw_networkx_edges(
                G, 
                pos=pos, 
                edgelist=edges, 
                edge_color=[color] * len(edges), # Apply the specific color to this batch
                arrows=True,             
                arrowstyle="-",          
                connectionstyle=f"arc3,rad={dynamic_rad}" 
            )

        # Cleanup and Save/Show
        plt.axis('off') 
        
        if filename is not None:
            plt.savefig(filename, dpi=300, bbox_inches="tight")
            print(f"Plot saved to {filename}")
        else:
            plt.show()
