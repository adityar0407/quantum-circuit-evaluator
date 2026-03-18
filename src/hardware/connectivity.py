import pandas as pd

def is_connected(q1, q2, connectivity):
    df = None
    if q1 == q2:
        raise ValueError("Cannot check connectivity between the same qubits.")
    if connectivity.endswith('.csv'):
        df = pd.read_csv(connectivity)
        connectivity = df.values.tolist()
    
    return [q1, q2] in df or [q2, q1] in df