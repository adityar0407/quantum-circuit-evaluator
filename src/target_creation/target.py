from hardware.connectivity import k_nearest_tiled_coupling_map
import json
import matplotlib.pyplot as plt
from qiskit.transpiler import Target, InstructionProperties
import qiskit.circuit.library as qlib
import networkx as nx

# Ensure your k_nearest_tiled_coupling_map is imported
# from hardware.connectivity import k_nearest_tiled_coupling_map

class DynamicTarget(Target):
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
        self.n_blocks_row = self.topology.get("n_blocks_row", 2)
        self.n_blocks_col = self.topology.get("n_blocks_col", 2)
        self.n = self.topology.get("n", 10)
        self.m = self.topology.get("m", 10)
        self.k_intra = self.topology.get("k_intra", self.n * self.m) # Default to fully connected locally
        self.k_inter = self.topology.get("k_inter", 1)
        self.connector_local = self.topology.get("connector_local", 1)
        

        # 3. Validate and parse the profile from the configuration
        self._validate_and_parse_profile()

        # 4. Build the underlying geometry for the target using the provided topology parameters
        self.cmap, self.total_qubits = k_nearest_tiled_coupling_map(
            n_blocks_row=self.n_blocks_row, 
            n_blocks_col=self.n_blocks_col,
            n=self.n, 
            m=self.m, 
            k_intra=self.k_intra, 
            k_inter=self.k_inter, 
            connector_local=self.connector_local
        )
        
        self.n_block = self.n * self.m
        
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
            raise ValueError("Profile must include a valid list of 'sq_gates' (e.g., ['HGate', 'TGate']).")
        
        if len(sq_gate_names) < 2:
            print("Warning: Profile has fewer than 2 single-qubit gates. This may not form a universal gate set.")

        # 2. Two Qubit Gates
        two_q_gate_name = profile.get("two_q_gate")
        if not two_q_gate_name or not isinstance(two_q_gate_name, str):
            raise ValueError("Profile must specify minimum one 'two_q_gate' as a string (e.g., 'CXGate').")

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
            
            # You can also cast the inter-block properties parsed in the __init__ here
            self.inter_err = float(self.config.get("inter_err", 0.05))
            self.inter_dur = float(self.config.get("inter_dur", 1e-6))
            
        except (ValueError, TypeError):
            raise TypeError("All error rates and durations must be numeric values (int or float).")
        

        # -- String to Qiskit Object Conversion --
        self.sq_gates = [self._instantiate_gate(name) for name in sq_gate_names]
        self.two_q_gate = self._instantiate_gate(two_q_gate_name)

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
            if (q1 // self.n_block) == (q2 // self.n_block):
                # Local Connection
                two_q_props[(q1, q2)] = InstructionProperties(
                    error=self.intra_err, duration=self.intra_dur
                )
            else:
                # Network Connection
                two_q_props[(q1, q2)] = InstructionProperties(
                    error=self.inter_err, duration=self.inter_dur
                )
        self.add_instruction(self.two_q_gate, two_q_props)

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
        for qubit_id in range(self.total_qubits):
            block_id = qubit_id // self.n_block
            br_idx = block_id // self.n_blocks_col
            bc_idx = block_id % self.n_blocks_col
            
            local_id = qubit_id % self.n_block
            r = local_id // self.m
            c = local_id % self.m
            
            # Add the gap multiplier to visually separate the computers
            x = (bc_idx * (self.m + gap)) + c
            y = -((br_idx * (self.n + gap)) + r)
            pos[qubit_id] = [x, y]

        # 1. Create a standard NetworkX graph
        G = nx.DiGraph()
        
        # 2. Add nodes to ensure disconnected qubits still show up
        G.add_nodes_from(range(self.total_qubits))
        
        # 3. Add edges from your coupling map
        G.add_edges_from(self.cmap.get_edges())

        # 4. Draw using NetworkX
        aspect_ratio = (self.n_blocks_col * (self.m + gap)) / (self.n_blocks_row * (self.n + gap))
        plt.figure(figsize=(10 * aspect_ratio, 10))  # Adjust width based on aspect ratio
        nx.draw(
            G,
            pos=pos,
            node_size=100,
            with_labels=False,
            edge_color="#A0A0A0",
            node_color="#3498DB",
            arrows=False  # Set to True if you want to see edge directionality
        )
        
        if filename is not None:
            plt.savefig(filename, dpi=300, bbox_inches="tight")
            print(f"Plot saved to {filename}")
        else:
            plt.show()