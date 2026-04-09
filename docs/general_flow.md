Overall goal of the project:


Under the assumption we are in the FTQC regime, every qubit is now treated as a logical qubit. As such, we can assume that a general algorithm we wish to run on it will need to be transpiled to a fault tolerant arcitecture rather than the modern NISQ setup
We cannot say what the future of FTQC will look like, but we can speculate


APPROACH 1: NAIIVE 
all to all connectivity, any native gate set you want, and the run-time efficiently of your choice

APPROACH 2: K NEAREST TILE
Each qubit can connect to the k-nearest neighbors of itself, creating a tile of logical qubits that all operate within the Fault Tolerant Regime

APPROACH 3: GROUPS OF TILES
From those tiles, we can connect an arbitrairy ammount of qubits between each tiling, representing multiple quantum processors 'talking' like a server


Once inside these fault tolerant regimes, we can optimize each circuit based on the general flow of a transpiler:

initialization:


layout:

routing:

translation:

optimization:

scheduling:
