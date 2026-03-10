from IR.circuit_loader import  input_test_circuit
from IR.export_qasm import export_to_qasm

circuit = input_test_circuit()

qasm = export_to_qasm(circuit)
print(qasm)


# Validation for QASM to prevent errors from popping up downstream
# from IR.validate_qasm import validate_qasm

# is_valid, result = validate_qasm(qasm)

# print("Valid QASM:", is_valid)
# print(result)



# Only for file ingestion input 
# from IR.qasm_ingestor import ingest_qasm_string

# raw_qasm = export_to_qasm(circuit)
# qasm = ingest_qasm_string(raw_qasm)

# print(qasm)

# Call the IR creation function and print the IR format result 
from IR.qasm_to_ir import qasm_to_ir

ir_circuit = qasm_to_ir(qasm)
print(ir_circuit)

from IR.IR_metadata_schema import extract_metadata

meta = extract_metadata(ir_circuit)
print(meta)


