import unittest
import os

os.environ.setdefault("MPLBACKEND", "Agg")

from qiskit.transpiler import CouplingMap
from backend.target_creation.target import FTarget

class TestFTarget(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up a base valid profile to reuse across multiple tests."""
        cls.valid_profile = {
            "sq_gates": {
                "XGate": {"error": 1e-4, "duration": 5e-8},
                "SXGate": {"error": 1e-4, "duration": 5e-8},
                "RZGate": {"error": 1e-4, "duration": 5e-8}
            },
            "two_q_gates": {
                "CXGate": {"local_error": 1e-3, "local_duration": 2e-7}
            },
            "inter_device_gates": {
                "SwapGate": {"inter_error": 5e-2, "inter_duration": 1e-6}
            }
        }
        
        # Create a directory to hold the plots so they don't clutter the root folder
        cls.plot_dir = "test_plots"
        os.makedirs(cls.plot_dir, exist_ok=True)

    def test_tiled_k_nearest_instantiation_and_plot(self):
        """Tests standard tiled grid networking and plot generation."""
        config = {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 2,
                "n_blocks_col": 2,
                "n": 3,
                "m": 3,
                "k_intra": 9,
                "k_inter": 2,
                "connector_local": 1
            },
            "profile": self.valid_profile,
            
        }
        
        target = FTarget(config)
        self.assertIsNotNone(target.cmap, "Coupling map should be generated.")
        self.assertEqual(target.n_block, 9, "Block size should be exactly n * m.")
        
        plot_path = os.path.join(self.plot_dir, "tiled_k_nearest.png")
        target.plot(filename=plot_path)
        self.assertTrue(os.path.exists(plot_path), "Plot file should be created.")

    def test_heavy_hex_instantiation_and_plot(self):
        """Tests heavy-hex fault-tolerant networking and plot generation."""
        config = {
            "topology": {
                "type": "heavy_hex",
                "n_blocks_row": 2,
                "n_blocks_col": 1,
                "d": 3,  # Small distance for fast testing
                "k_inter": 2
            },
            "profile": self.valid_profile
        }
        
        target = FTarget(config)
        
        # For d=3 Heavy Hex, Qiskit creates 19 base qubits per block.
        # The modular layout adds 3 intermediary connection qubits between two vertical blocks.
        self.assertEqual(target.total_qubits, 41, "Total qubits should include base blocks plus connector qubits.")
        
        plot_path = os.path.join(self.plot_dir, "heavy_hex_network.png")
        target.plot(filename=plot_path)
        self.assertTrue(os.path.exists(plot_path))

    def test_heavy_square_instantiation_and_plot(self):
        """Tests heavy-square fault-tolerant networking and plot generation."""
        config = {
            "topology": {
                "type": "heavy_square",
                "n_blocks_row": 1,
                "n_blocks_col": 2,
                "d": 3,
                "k_inter": 1
            },
            "profile": self.valid_profile
        }
        
        target = FTarget(config)
        
        plot_path = os.path.join(self.plot_dir, "heavy_square_network.png")
        target.plot(filename=plot_path)
        self.assertTrue(os.path.exists(plot_path))

    def test_custom_coupling_map(self):
        """Tests fallback manual coupling map from a list of edges."""
        config = {
            "topology": {
                "type": "custom_coupling_map",
                "coupling_map": [[0, 1], [1, 2], [2, 3]]
            },
            "profile": self.valid_profile
        }
        
        target = FTarget(config)
        self.assertEqual(target.total_qubits, 4, "Custom map should detect 4 qubits.")
        self.assertEqual(target.n_block, 4, "Custom map should default to a single block.")

    # ---------------------------------------------------------
    # EDGE CASES & ERROR HANDLING
    # ---------------------------------------------------------

    def test_invalid_topology_type(self):
        """Asserts the class raises a ValueError if given an unsupported topology."""
        config = {
            "topology": {"type": "triangle_lattice"},
            "profile": self.valid_profile
        }
        with self.assertRaises(ValueError):
            FTarget(config)

    def test_missing_profile(self):
        """Asserts the class catches missing profile configurations."""
        config = {
            "topology": {"type": "tiled_k_nearest"}
            # Missing "profile" entirely
        }
        with self.assertRaises(ValueError):
            FTarget(config)

    def test_missing_error_metric(self):
        """Asserts the class catches missing required physical metrics."""
        bad_profile = self.valid_profile.copy()
        bad_profile["two_q_gates"] = {
            "CXGate": {"local_duration": 2e-7}
        }
        
        config = {
            "topology": {"type": "heavy_hex", "d": 3},
            "profile": bad_profile
        }
        with self.assertRaises(ValueError):
            FTarget(config)

    def test_invalid_gate_name(self):
        """Asserts the class catches a gate name that doesn't exist in Qiskit."""
        bad_profile = self.valid_profile.copy()
        bad_profile["sq_gates"] = {
            "XGate": {"error": 1e-4, "duration": 5e-8},
            "MagicNonExistentGate": {"error": 1e-4, "duration": 5e-8}
        }
        
        config = {
            "topology": {"type": "heavy_hex", "d": 3},
            "profile": bad_profile
        }
        with self.assertRaises(ValueError):
            FTarget(config)

    def test_is_local_edge_logic(self):
        """Directly tests the mathematical logic distinguishing local vs network edges."""
        config = {
            "topology": {
                "type": "tiled_k_nearest",
                "n_blocks_row": 2,
                "n_blocks_col": 1,
                "n": 10,
                "m": 10
            },
            "profile": self.valid_profile
        }
        target = FTarget(config)
        
        # n_block should be 100
        # Qubits 0-99 are Block 0. Qubits 100-199 are Block 1.
        self.assertTrue(target._is_local_edge(5, 99), "Nodes inside block 0 should be local.")
        self.assertTrue(target._is_local_edge(101, 150), "Nodes inside block 1 should be local.")
        self.assertFalse(target._is_local_edge(99, 100), "Edge spanning block 0 to 1 should be network.")

if __name__ == "__main__":
    unittest.main()
