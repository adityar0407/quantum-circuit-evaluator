from hardware.connectivity import generate_modular_ft_lattice, k_nearest_tiled_coupling_map
import json
import matplotlib.pyplot as plt
from qiskit.transpiler import Target, InstructionProperties
import qiskit.circuit.library as qlib
import networkx as nx
from qiskit.transpiler import CouplingMap



class FTarget(Target):
    """
    A Qiskit Target fully defined by a configuration dictionary or JSON.
    It validates the gate set architecture upon creation.
    """
    def __init__(self, config: dict = None, **kwargs):
        # 1. Merge the provided config with any explicit kwargs
        self.config = config or {}
        self.config.update(kwargs)
        



        self.topology = self.config.get("topology")

        # 2. Extract topology parameters
        self.type = self.topology.get("type", "tiled_k_nearest")
        # topology will be a dict containing the necessary parameters to build the coupling map

        if self.type == "tiled_k_nearest":
            self.n_blocks_row = self.topology.get("n_blocks_row", 2)
            self.n_blocks_col = self.topology.get("n_blocks_col", 2)
            self.n = self.topology.get("n", 10)
            self.m = self.topology.get("m", 10)
            self.k_intra = self.topology.get("k_intra", self.n * self.m) # Default to fully connected locally
            self.k_inter = self.topology.get("k_inter", 1)
            self.connector_local = self.topology.get("connector_local", 1)

            # 2.1. Build the underlying geometry for the target using the provided topology parameters
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
        

        ## todo test implementation of a custom coupling map directly 
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
            self.d = self.topology.get("d", 5)  # Number of data qubits per side in the base block
            self.cmap, self.total_qubits, self.n_block, self.pos = generate_modular_ft_lattice(
                architecture=self.type,
                d=self.topology.get("d", 5),
                n_blocks_row=self.n_blocks_row,
                n_blocks_col=self.n_blocks_col,
                k_inter=self.k_inter  # Pass your connection distribution density here!
            )
            self._is_local_edge = lambda q1, q2: (q1 // self.n_block) == (q2 // self.n_block)
            
            

            # need to extract the n and m per block to identify the block structure for error assignment
        else:
            raise ValueError(f"Unsupported topology type: {self.type}. Supported types are 'tiled_k_nearest', 'custom_coupling_map', 'heavy_hex', and 'heavy_square'.")

        # 3. UNIVERSAL LOGIC FOR LOCAL VS NETWORK EDGES
        self._is_local_edge = lambda q1, q2: (q1 // self.n_block) == (q2 // self.n_block)

        # 4. Validate and parse the profile from the configuration
        self._validate_and_parse_profile()

        # 5. Initialize parent Qiskit Target
        super().__init__()
        
        # 6. Populate Target with the dynamically loaded gates
        self._populate_instructions()



    def _validate_and_parse_profile(self):
        """Validates the input profile and converts string names to Qiskit gates."""
        profile = self.config.get("profile")
        if not profile:
            raise ValueError("Configuration must contain a 'profile' dictionary defining the architecture.")

        # -- Checks: Architecture Completeness --
        
        # 1. Single Qubit Gates
        sq_gate_names = profile.get("sq_gates", [])
        print(f"Debug: sq_gate_names from profile: {sq_gate_names}")
        if not sq_gate_names or not isinstance(sq_gate_names, list):
            raise ValueError("Profile must include a valid list of 'sq_gates' as a list of strings (e.g., ['HGate', 'TGate']).")
        
        if len(sq_gate_names) < 2:
            print("Warning: Profile has fewer than 2 single-qubit gates. This may not form a universal gate set.")

        # 2. Two Qubit Gates
        two_q_gate_names = profile.get("two_q_gates", [])
        if not two_q_gate_names or not isinstance(two_q_gate_names, list):
            raise ValueError("Profile must specify minimum one 'two_q_gates' as a list of strings (e.g., 'CXGate').")

        # 3. Required Metrics
        required_metrics = ['sq_err', 'sq_dur', 'intra_err', 'intra_dur']
        for metric in required_metrics:
            if metric not in profile:
                raise ValueError(f"Profile is missing required performance property: '{metric}'.")

        # Save metrics to instance
        try:
            self.sq_err = float(profile['sq_err'])
            self.sq_dur = float(profile['sq_dur'])
            self.intra_err = float(profile['intra_err'])
            self.intra_dur = float(profile['intra_dur'])
            
           
            self.inter_err = float(profile.get("inter_err", 0.05))
            self.inter_dur = float(profile.get("inter_dur", 1e-6))
            
        except (ValueError, TypeError):
            raise TypeError("All error rates and durations must be numeric values (int or float).")
        

        # -- String to Qiskit Object Conversion --
        self.sq_gates = [self._instantiate_gate(name) for name in sq_gate_names]
        self.two_q_gates = [self._instantiate_gate(name) for name in two_q_gate_names]

    def _instantiate_gate(self, gate_name: str):
        """Dynamically fetches a gate class from qiskit.circuit.library and instantiates it."""
        if not hasattr(qlib, gate_name):
            raise ValueError(f"Gate '{gate_name}' is not recognized in qiskit.circuit.library.")
        
        gate_class = getattr(qlib, gate_name)
        

        # Qiskit basis gates for Targets only need a dummy instance.
        # Try standard instantiation, and fallback to providing dummy angles (0) 
        # for parameterized gates like RZGate, U2Gate, or U3Gate.
        try:
            return gate_class()
        except TypeError:
            try:
                return gate_class(0)
            except TypeError:
                try:
                    return gate_class(0, 0)
                except TypeError:
                    return gate_class(0, 0, 0)

    def _populate_instructions(self):
        """Internal method to add gates and error rates to the Target."""
        sq_props = {
            (q,): InstructionProperties(error=self.sq_err, duration=self.sq_dur) 
            for q in range(self.total_qubits)
        }
        for gate in self.sq_gates:
            self.add_instruction(gate, sq_props)

        two_q_props = {}
        for q1, q2 in self.cmap.get_edges():
            # call the local vs network edge logic to assign appropriate error/duration
            if self._is_local_edge(q1, q2):
                two_q_props[(q1, q2)] = InstructionProperties(error=self.intra_err, duration=self.intra_dur)
            else:
                two_q_props[(q1, q2)] = InstructionProperties(error=self.inter_err, duration=self.inter_dur)
        for gate in self.two_q_gates:
            self.add_instruction(gate, two_q_props)

    def to_json(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.config, f, indent=4)
        print(f"Target configuration saved to {filepath}")

    @classmethod
    def from_json(cls, filepath: str):
        with open(filepath, 'r') as f:
            config = json.load(f)
        return cls(config)
    

    def plot(self, filename: str = None, gap: int = 3):
        """Plots the coupling map using the structured grid layout."""
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
            pos = self.pos  # Grab the pre-calculated positions from __init__
            
        else:
            # Fallback for custom maps
            G_temp = nx.Graph(self.cmap.get_edges())
            pos = nx.spring_layout(G_temp)

        # 2. Create NetworkX graph
        G = nx.DiGraph()
        G.add_nodes_from(range(self.total_qubits))
        G.add_edges_from(self.cmap.get_edges())

        # 3. Determine edge colors dynamically
        edge_colors = [
            "#A0A0A0" if self._is_local_edge(u, v) else "#E74C3C" 
            for u, v in G.edges()
        ]

        # 4. Draw
        if self.type == "tiled_k_nearest":
            aspect_ratio = (self.n_blocks_col * (self.m + gap)) / max(1, (self.n_blocks_row * (self.n + gap)))
            plt.figure(figsize=(10 * aspect_ratio, 10))
        else:
            plt.figure(figsize=(12, 12))

        nx.draw(
            G,
            pos=pos,
            node_size=100,
            with_labels=False,
            edge_color=edge_colors,
            node_color="#3498DB",
            arrows=False
        )
        
        if filename is not None:
            plt.savefig(filename, dpi=300, bbox_inches="tight")
            print(f"Plot saved to {filename}")
        else:
            plt.show()