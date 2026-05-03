# fault_tolerant_target.py
from backend.target_creation.target import FTarget

class FTTarget(FTarget):
    """
    User-Facing inherited Target Object for constructing and displaying a Fault Tolerant network
    Requires two dictionaries with keys profile (ISA of the computer) and target
    """

    def __init__(self, profile_dict: dict):
        # Call the initialization logic of the parent FTarget class
        super().__init__(profile_dict)
        
        # extra initialization specific to the user-facing version
        self._is_initialized = True

    def summary(self):
        """human-readable summary of the generated topology."""
        print("=" * 40)
        print(" FAULT TOLERANT TARGET SUMMARY")
        print("=" * 40)
        print(f"Topology Type:    {self.type}")
        print(f"Total Qubits:     {self.total_qubits}")
        
        if hasattr(self, 'n_blocks_row'):
            blocks = self.n_blocks_row * getattr(self, 'n_blocks_col', 1)
            print(f"Total Blocks:     {blocks}")
            
        print(f"Total Edges:      {len(self.cmap.get_edges())}")
        print("=" * 40)

    def __str__(self):
        """
        Overrides the default print() behavior. 
        If a user types `print(my_target)`, this is what they will see.
        """
        return f"<FaultTolerantTarget: {self.type} topology with {self.total_qubits} qubits>"