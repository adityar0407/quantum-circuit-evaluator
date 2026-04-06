## need to import QiskitRuntime on your own device and get a token from IBM Quantum Experience to run this code. 
# The code will download the coupling map of the specified backend and save it as a CSV file. 

from qiskit_ibm_runtime import QiskitRuntimeService
import pandas as pd
name = "ibm_miami"
# Load account
service = QiskitRuntimeService()
backend = service.backend(name) # Example device

# Get coupling map
coupling_map = backend.configuration().coupling_map
df = pd.DataFrame(coupling_map, columns=["Qubit_1", "Qubit_2"])
export_name = f"{name}_connectivity.csv"
# Export to CSV
df.to_csv(export_name, index=False)
