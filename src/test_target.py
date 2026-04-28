if __name__ == "__main__":
    from target_creation.target import DynamicTarget


    # Example configuration for a DynamicTarget (this would normally come from a JSON or dict)
    example_config = {
        "profile": {
            "sq_gates": ["XGate", "HGate"],
            "two_q_gate": "CXGate",
            "sq_err": 0.001,
            "sq_dur": 50,
            "intra_err": 0.01,
            "intra_dur": 200,
            "inter_err": 0.05,
            "inter_dur": 500,
        },
        # For this test, we'll just use the first coupling map from the benchmark set
        "topology": {
            "n_blocks_row": 5,
            "n_blocks_col": 12,
            "n": 5,
            "m": 5,
            "k_intra": 2,
            "k_inter": 1,
            "connector_local": 1,
        }
    }

    # Create a DynamicTarget instance using the example configuration
    target = DynamicTarget(config=example_config)
    target.plot()
    # Print out some details about the created Target
    print("Created DynamicTarget with the following properties:")
    print(f"Number of qubits: {target.num_qubits}")
    print(f"Single-qubit gates: {[gate.name for gate in target.sq_gates]}")
    print(f"Two-qubit gate: {target.two_q_gate.name}")
    print(f"Coupling map edges: {target.cmap.get_edges()}")