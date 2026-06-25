
# FTTarget - a Fault Tolerant Target generator
### Physics-765-final-project

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📌 Problem Statement

A fundamental constraint in Qauntum Computing is the scale of implementation for a given quantum cirucit. Current NISQ hardware is too limited in number of qubits and the error rate to provide a meaningful computational advantage beyond toy examples. As we advance towards the FTQC era, one must consider the actual implementation of a circuit for a hardware that would utilize an Error Correcting Gadget intrinsicly.

FTarget inherits the Qiskit Target object for just this purpose, allowing one to construct an abstracted fault-tolerant device defined by it's logical qubit's error rate, gate duration, and intrinsic connectivity. FTarget takes a dictionary argument of parameters to construct the connectivity alongside single and two qubit gates that define a computers ISA, allowing one to save various configurations via JSON files for later usage. Once created, a user can utilize the target to transpile a circuit within the predefined parameters of each gate on a logical qubit. 

A viable strategy to better scale computation is via networking of multiple fault tolerant devices together as opposed to controlling a single large device. The FTarget also supports this networking by abstracting to edge-qubit connections of the k-nearest devices, which allow one to transpile a circuit with network error in consideration and benchmark their circuit based on this.

Once a circuit has been transpiled with these fault tolerant considerations in mind, the mapping of logical gate execution to physical gate implementation depends on the error correcting code one is implementing. The current IBM platform is exploring implementation of heavy square and heavy hexagon surface codes, which utilize data, flag and ancilla qubits to measure Z and X pairity. As such, FTarget also supports the creation of a tiled heavy hexagon and heavy square lattice, with intent to create a compiler for logical gate instructions to be translated directly onto the code. This would give an accurate and true gate execution and success probability based on any abstract circuit implementation.

FTarget is a reusable tool to allow one to explore transpilation onto their own Fault Tolerant arcitecture by abstracting the overlying assumptions on intra and inter device connectivity, and the fidelity/exectution time of gates within it to better understand metrics of a circuit transpiled under Fault Tolerant conditions. Whether one wants to understand if their optimizer/router/scheduler performs differently under a fault tolerant regime, or if they want to understand how their circuit performs in a networked setting compared to 


## Installation

To install and run this project locally, we recommend using a Python virtual environment.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/](https://github.com/)[TODO-INSERT USERNAME]/[your-repo-name].git
   cd [your-repo-name]
    ```
2. **Create venv**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    pip install -e .
    ```


## Quick Start

Checkout the Demo in examples/01_Target_creation.ipynb to learn how to make your own target and compile it with a circuit! You can use the blueprint.json file to fill in your own gates and test your own circuit as well
