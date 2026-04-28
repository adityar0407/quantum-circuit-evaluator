if __name__ == "__main__":
    from .target import DynamicTarget
    from .connectivity import get_benchmark_coupling_maps

    # Load coupling maps for all benchmark targets
    coupling_maps = get_benchmark_coupling_maps()

    # Example configuration for a DynamicTarget (this would normally come from a JSON or dict)
    example_config = {
        "num_qubits": 40,
        "sq_gate_names": ["XGate", "HGate"],
        "two_q_gate_name": "CXGate",
        "profile": {
            "sq_err": 0.001,
            "sq_dur": 50,
            "intra_err": 0.01,
            "intra_dur": 200,
            "inter_err": 0.05,
            "inter_dur": 500,
        },
        # For this test, we'll just use the first coupling map from the benchmark set
        "coupling_map": coupling_maps["Custom FT-style 2x2 tiled k-nearest"],
    }

    # Create a DynamicTarget instance using the example configuration
    target = DynamicTarget(config=example_config)

    # Print out some details about the created Target
    print("Created DynamicTarget with the following properties:")
    print(f"Number of qubits: {target.num_qubits}")
    print(f"Single-qubit gates: {[gate.name for gate in target.sq_gates]}")
    print(f"Two-qubit gate: {target.two_q_gate.name}")
    print(f"Coupling map edges: {target.cmap.get_edges()}")