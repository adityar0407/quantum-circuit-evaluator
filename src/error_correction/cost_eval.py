from typing import Dict, Callable
from qiskit.circuit import QuantumCircuit

def create_gate_cost_evaluator(
    gate_weights: Dict[str, float], 
    depth_weight: float = 0.0,
    unmapped_gate_penalty: float = 0.0
) -> Callable[[QuantumCircuit], float]:
    """
    Creates a customized cost evaluator function for dynamic transpilation.
    
    Args:
        gate_weights: Dictionary mapping gate names (e.g., 't', 'cx') to their numeric cost.
        depth_weight: Cost multiplier for the overall circuit depth.
        unmapped_gate_penalty: Default cost applied to any gate found in the circuit 
                               that isn't explicitly listed in gate_weights.
                               
    Returns:
        A function that evaluates a QuantumCircuit and returns a total cost.
    """
    
    def evaluator(circuit: QuantumCircuit) -> float:
        
        gate_counts = circuit.count_ops()
        
        total_cost = 0.0
        
        # Calculate the cost contribution from gates
        for gate_name, count in gate_counts.items():
            # Look up the weight for the gate; if not found, use the default penalty
            weight = gate_weights.get(gate_name, unmapped_gate_penalty)
            total_cost += weight * count
            
        # Calculate the cost contribution from overall circuit depth
        if depth_weight > 0.0:
            total_cost += depth_weight * circuit.depth()
            
        return total_cost
        
    return evaluator