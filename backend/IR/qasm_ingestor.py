# This process is meant to take any form of QASM in the form of a file or string. 
def ingest_qasm_string(qasm_string):
    return qasm_string.strip()

def ingest_qasm_file(file_path):
    with open(file_path, "r") as f:
        qasm_string = f.read().strip()
    return qasm_string