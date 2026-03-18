def is_native_gate(gate_name, native_gate_list):
    assert isinstance(native_gate_list, list), "native_gate_list should be a list"
    
    return gate_name in native_gate_list