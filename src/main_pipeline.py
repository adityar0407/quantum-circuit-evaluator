from configs.load_config import load_config
from IR.export_qasm import export_qasm_stub
from metrics.qasm_counter import count_gates_from_qasm
from hardware.connectivity import is_connected


def main():
    config = load_config("src/configs/test.yaml")
    qasm = export_qasm_stub()
    counts = count_gates_from_qasm(qasm)

    print("Gate counts:", counts)




if __name__ == "__main__":
    main()