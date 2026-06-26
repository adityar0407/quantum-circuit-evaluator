# Backend Function Glossary

This glossary lists custom Python functions and methods defined under `backend/`. It excludes frontend code, scripts, examples, third-party libraries, virtual environments, and the archived `Custom QEC compiler [future feature]` folder.

Generated from source definitions. Descriptions use docstrings where available and concise name-based summaries otherwise.

## Production backend

### `backend/FaultTolerantTarget.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `FTTarget.__init__` (`L10`) | `(self, profile_dict: dict)` | Initializes the object with its stored configuration. |
| `FTTarget.summary` (`L17`) | `(self)` | human-readable summary of the generated topology. |
| `FTTarget.__str__` (`L32`) | `(self)` | Overrides the default print() behavior. |

### `backend/IR/analysis.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `analyze_logical_ir` (`L12`) | `(logical_ir: LogicalIR) -> dict[str, Any]` | Implements backend logic for analyze logical ir. |
| `_critical_path` (`L91`) | `(logical_ir: LogicalIR, successor_map: dict[str, list[str]], depth_by_id: dict[str, int]) -> list[str]` | Implements backend logic for critical path. |
| `_t_family_demand` (`L108`) | `(gate_counts: dict[str, int]) -> dict[str, int]` | Implements backend logic for t family demand. |

### `backend/IR/logical_ir.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `build_logical_ir` (`L18`) | `(circuit: QuantumCircuit, target: Any \| None, compiler: str, artifacts: dict[str, Any] \| None=None, original_circuit: QuantumCircuit \| None=None) -> LogicalIR` | Builds logical ir from the provided inputs. |
| `validate_logical_ir` (`L136`) | `(logical_ir: LogicalIR) -> None` | Validates logical ir and returns/raises status. |
| `serialize_logical_ir` (`L167`) | `(logical_ir: LogicalIR) -> dict[str, Any]` | Implements backend logic for serialize logical ir. |
| `_build_placement` (`L171`) | `(qubit_index: int, target: Any \| None) -> LogicalPlacement` | Builds placement from internal inputs. |
| `_classify_operation` (`L179`) | `(base_operation: str, qargs: list[int], cargs: list[int], target: Any \| None) -> str` | Implements backend logic for classify operation. |
| `_is_remote_operation` (`L198`) | `(qargs: list[int], target: Any \| None) -> bool` | Implements backend logic for is remote operation. |
| `_node_for_qubit` (`L206`) | `(qubit_index: int, target: Any \| None) -> int \| None` | Implements backend logic for node for qubit. |
| `_serialize_parameter` (`L212`) | `(value: Any) -> float \| str` | Implements backend logic for serialize parameter. |
| `_build_compiler_metadata` (`L218`) | `(compiler: str, artifacts: dict[str, Any], target: Any \| None, circuit: QuantumCircuit, original_circuit: QuantumCircuit \| None) -> dict[str, Any]` | Builds compiler metadata from internal inputs. |

### `backend/IR/models/logical_ir.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `UnmodeledCost.to_dict` (`L30`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |
| `LogicalInstruction.to_dict` (`L48`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |
| `LogicalPlacement.to_dict` (`L61`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |
| `LogicalIR.to_dict` (`L78`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |

### `backend/IR/qasm.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `ingest_qasm_string` (`L9`) | `(qasm_string: str) -> str` | Implements backend logic for ingest qasm string. |
| `ingest_qasm_file` (`L13`) | `(file_path: str \| Path) -> str` | Implements backend logic for ingest qasm file. |
| `load_qasm_circuit` (`L17`) | `(qasm_string: str) -> QuantumCircuit` | Loads qasm circuit from input data. |
| `validate_qasm` (`L21`) | `(qasm_string: str) -> tuple[bool, QuantumCircuit \| str]` | Validates qasm and returns/raises status. |
| `export_circuit_to_qasm` (`L28`) | `(circuit: QuantumCircuit) -> str` | Exports circuit to qasm to an external representation. |

### `backend/IR/qiskit_adapter.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `logical_ir_to_qiskit_circuit` (`L16`) | `(logical_ir: LogicalIR) -> tuple[QuantumCircuit, dict[str, Any]]` | Implements backend logic for logical ir to qiskit circuit. |
| `_apply_operation` (`L47`) | `(circuit: QuantumCircuit, operation: LogicalInstruction) -> None` | Implements backend logic for apply operation. |
| `_param` (`L103`) | `(params: list[float \| str], index: int) -> float` | Implements backend logic for param. |

### `backend/api/app.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `health_check` (`L24`) | `() -> dict[str, str]` | Implements backend logic for health check. |

### `backend/api/routes/circuits.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `validate_circuit` (`L10`) | `(payload: CircuitQasmRequest) -> CircuitSummaryResponse` | Validates circuit and returns/raises status. |

### `backend/api/routes/runs.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `run_compilation` (`L11`) | `(payload: TranspileRequest) -> TranspileResponse` | Implements backend logic for run compilation. |
| `compile_run` (`L27`) | `(payload: TranspileRequest) -> TranspileResponse` | Implements backend logic for compile run. |
| `transpile` (`L32`) | `(payload: TranspileRequest) -> TranspileResponse` | Implements backend logic for transpile. |

### `backend/api/routes/targets.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `preview` (`L10`) | `(payload: TargetPreviewRequest) -> TargetPreviewResponse` | Implements backend logic for preview. |

### `backend/configs/load_config.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `load_config` (`L5`) | `(path: str)` | Loads config from input data. |

### `backend/hardware/connectivity.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `load_coupling_map_from_csv` (`L11`) | `(csv_path: str \| Path) -> CouplingMap` | Load a Qiskit CouplingMap from a CSV edge list. |
| `load_ibm_fez_coupling_map` (`L25`) | `() -> CouplingMap` | Load the IBM Fez heavy-hex coupling map from CSV. |
| `load_ibm_torino_coupling_map` (`L32`) | `() -> CouplingMap` | Load the IBM Torino heavy-hex coupling map from CSV. |
| `_block_edges` (`L49`) | `(n, m, k)` | Build undirected edges inside one n x m block. |
| `k_nearest_tiled_coupling_map` (`L79`) | `(n_blocks_row: int, n_blocks_col: int, n: int, m: int, k_intra: int, k_inter: int=1, connector_local: int=1) -> tuple[CouplingMap, int]` | Build a CouplingMap for a tiled block layout. |
| `block_id` (`L117`) | `(br, bc)` | Implements backend logic for block id. |
| `block_offset` (`L120`) | `(br, bc)` | Implements backend logic for block offset. |
| `get_centered_edge_indices` (`L123`) | `(length: int, step: int) -> range` | Returns a range of indices stepping by `step`, |
| `orient_by_triangle` (`L236`) | `(pos, corner_list)` | Identifies the pivot corner of the 3-point triangle, calculates its angle, |
| `sq_dist` (`L245`) | `(pa, pb)` | Implements backend logic for sq dist. |
| `re_center` (`L281`) | `(pos, total)` | Implements backend logic for re center. |
| `get_perimeter_data_qubits` (`L293`) | `(d)` | Utilizes indexing math to safely identify the boundary qubits by the |
| `generate_modular_layout` (`L345`) | `(architecture='heavy_hex', d=3, rows=2, cols=2, interconnect=1)` | Implements backend logic for generate modular layout. |

### `backend/metrics/metrics_evaluator.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `count_network_operations` (`L10`) | `(qc: QuantumCircuit, n: int, m: int) -> dict` | Scans a transpiled physical circuit to count total 2-qubit gates |
| `calculate_circuit_success_chance` (`L39`) | `(transpiled_qc: QuantumCircuit, target) -> float` | Calculate overall circuit fidelity based on the specific mapped edges. |
| `get_total_duration` (`L64`) | `(qc: QuantumCircuit) -> float` | Safely retrieves duration from a scheduled circuit. |
| `evaluate_circuit_metrics` (`L92`) | `(circuit: QuantumCircuit, target: Target) -> CircuitMetrics` | Evaluate first-order target-dependent metrics for a mapped circuit. |

### `backend/metrics/qasm_counter.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `count_gates_from_qasm` (`L1`) | `(qasm_str: str)` | Implements backend logic for count gates from qasm. |

### `backend/models/estimation_profiles.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `LogicalArchitecture.to_dict` (`L20`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |
| `PhysicalHardwareProfile.to_dict` (`L36`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |
| `QecProfile.to_dict` (`L48`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |
| `NetworkProfile.to_dict` (`L63`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |
| `EstimationContext.to_dict` (`L74`) | `(self) -> dict[str, Any]` | Serializes the object to a dictionary payload. |

### `backend/pass_managers/cost_eval.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `create_gate_cost_evaluator` (`L4`) | `(gate_weights: Dict[str, float], depth_weight: float=0.0, unmapped_gate_penalty: float=0.0) -> Callable[[QuantumCircuit], float]` | Creates a customized cost evaluator function for dynamic transpilation. |
| `evaluator` (`L22`) | `(circuit: QuantumCircuit) -> float` | Implements backend logic for evaluator. |

### `backend/pass_managers/initializer.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `get_init_pm` (`L7`) | `(basis_gates: list[str] \| None=None) -> PassManager` | Phase 1: Initialization |

### `backend/pass_managers/layout_n_routing.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `get_layout_pm` (`L9`) | `(coupling_map: CouplingMap, use_sabre: bool=True, seed_transpiler: int \| None=12345, sabre_layout_trials: int=8, sabre_swap_trials: int=8) -> PassManager` | Phase 2: Layout |
| `get_routing_pm` (`L33`) | `(coupling_map: CouplingMap, use_sabre: bool=True, seed_transpiler: int \| None=12345, sabre_trials: int=8) -> PassManager` | Phase 3: Routing |
| `get_layout_routing_pm` (`L55`) | `(coupling_map: CouplingMap, use_sabre: bool=True, seed_transpiler: int \| None=12345, sabre_layout_trials: int=8, sabre_layout_swap_trials: int=8, sabre_swap_trials: int=8) -> PassManager` | Phases 2 & 3: Layout and Routing |

### `backend/pass_managers/optimizer.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `get_optimization_pm` (`L14`) | `() -> PassManager` | Phase 5: Optimization |

### `backend/pass_managers/scheduling.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `get_scheduling_pm` (`L4`) | `(target: Target) -> PassManager` | Phase 6: Scheduling |

### `backend/pass_managers/translator.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `get_basis_gates` (`L16`) | `(architecture: str) -> list[str]` | Return the native basis gates for a supported architecture profile. |
| `get_translation_pm` (`L27`) | `(architecture: str='superconducting', basis_gates: list[str] \| None=None) -> PassManager` | Phase 4: Translation |

### `backend/services/circuit_service.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `circuit_summary` (`L10`) | `(circuit: QuantumCircuit) -> dict` | Implements backend logic for circuit summary. |
| `circuit_from_qasm` (`L20`) | `(qasm: str) -> QuantumCircuit` | Implements backend logic for circuit from qasm. |
| `summarize_qasm` (`L27`) | `(qasm: str) -> dict` | Implements backend logic for summarize qasm. |

### `backend/services/compilers/__init__.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `get_compiler_backend` (`L8`) | `(key: str) -> CompilerBackend` | Returns compiler backend for callers. |

### `backend/services/compilers/base.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `CompilerBackend.compile` (`L35`) | `(self, qasm: str, target_config: dict[str, Any]) -> CompilationResult` | Compiles an input circuit using this backend. |

### `backend/services/compilers/pandora_compiler.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `PandoraCompiler.__init__` (`L19`) | `(self) -> None` | Initializes the object with its stored configuration. |
| `PandoraCompiler.compile` (`L30`) | `(self, qasm: str, target_config: dict[str, Any]) -> CompilationResult` | Compiles an input circuit using this backend. |
| `PandoraCompiler._support_scan` (`L96`) | `(self, qasm: str) -> dict[str, Any]` | Implements backend logic for support scan. |
| `PandoraCompiler._database_is_available` (`L123`) | `(self) -> bool` | Implements backend logic for database is available. |
| `PandoraCompiler._load_runner_json` (`L131`) | `(stdout: str) -> dict[str, Any]` | Implements backend logic for load runner json. |
| `PandoraCompiler._warnings_for_artifacts` (`L139`) | `(artifacts: dict[str, Any]) -> list[str]` | Implements backend logic for warnings for artifacts. |
| `PandoraCompiler._subprocess_env` (`L150`) | `(self) -> dict[str, str]` | Implements backend logic for subprocess env. |
| `_removed_operations` (`L164`) | `(original_circuit, compiled_circuit) -> dict[str, int]` | Implements backend logic for removed operations. |

### `backend/services/compilers/pandora_runner.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `circuit_summary` (`L20`) | `(circuit: QuantumCircuit) -> dict` | Implements backend logic for circuit summary. |
| `run_database_mode` (`L30`) | `(payload: dict) -> dict` | Implements backend logic for run database mode. |
| `run_translation_mode` (`L90`) | `(payload: dict) -> dict` | Implements backend logic for run translation mode. |
| `run_support_scan_mode` (`L115`) | `(payload: dict) -> dict` | Implements backend logic for run support scan mode. |
| `main` (`L131`) | `() -> int` | Entry point for direct execution. |

### `backend/services/compilers/qiskit_ftarget.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `QiskitFTargetCompiler.compile` (`L15`) | `(self, qasm: str, target_config: dict[str, Any]) -> CompilationResult` | Compiles an input circuit using this backend. |
| `_serialize_layout` (`L53`) | `(layout: Any) -> dict[str, int] \| None` | Implements backend logic for serialize layout. |

### `backend/services/estimation_context.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `build_estimation_context` (`L12`) | `(target: Any, profile_overrides: dict[str, Any] \| None=None) -> EstimationContext` | Builds estimation context from the provided inputs. |
| `_build_logical_architecture` (`L27`) | `(target: Any) -> LogicalArchitecture` | Builds logical architecture from internal inputs. |
| `_build_physical_hardware_profile` (`L49`) | `(raw: Any) -> PhysicalHardwareProfile` | Builds physical hardware profile from internal inputs. |
| `_build_qec_profile` (`L64`) | `(raw: Any) -> QecProfile` | Builds qec profile from internal inputs. |
| `_build_network_profile` (`L76`) | `(raw: Any) -> NetworkProfile \| None` | Builds network profile from internal inputs. |
| `_node_count` (`L93`) | `(target: Any) -> int` | Implements backend logic for node count. |
| `_local_connectivity_label` (`L99`) | `(target: Any) -> str` | Implements backend logic for local connectivity label. |
| `_inter_node_connectivity_label` (`L105`) | `(target: Any) -> str` | Implements backend logic for inter node connectivity label. |
| `_remote_operation_model` (`L114`) | `(target: Any) -> str` | Implements backend logic for remote operation model. |
| `_communication_capacity` (`L121`) | `(target: Any) -> int \| None` | Implements backend logic for communication capacity. |
| `_as_dict` (`L127`) | `(value: Any) -> dict[str, Any]` | Implements backend logic for as dict. |
| `_optional_float` (`L131`) | `(value: Any) -> float \| None` | Parses an optional float value. |
| `_optional_int` (`L137`) | `(value: Any) -> int \| None` | Parses an optional int value. |

### `backend/services/resource_estimators/__init__.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `get_resource_estimator` (`L8`) | `(key: str) -> ResourceEstimator` | Returns resource estimator for callers. |

### `backend/services/resource_estimators/base.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `ResourceEstimator.estimate` (`L19`) | `(self, compilation: CompilationResult) -> dict[str, Any]` | Runs this resource-estimation backend for a compilation result. |

### `backend/services/resource_estimators/native_qre.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `NativeQreEstimator.estimate` (`L61`) | `(self, compilation: CompilationResult) -> dict[str, Any]` | Runs this resource-estimation backend for a compilation result. |
| `logical_ir_to_native_qre_trace` (`L132`) | `(logical_ir: LogicalIR) -> tuple[Trace, dict[str, Any]]` | Implements backend logic for logical ir to native qre trace. |
| `_build_qec_model` (`L177`) | `(model_name: str, source: str, raw_parameters: dict[str, Any]) -> tuple[Any, dict[str, Any]]` | Builds qec model from internal inputs. |
| `_coerce_qec_parameters` (`L206`) | `(model_name: str, raw_parameters: dict[str, Any]) -> dict[str, Any]` | Coerces qec parameters into the backend representation. |
| `_coerce_parameter_value` (`L219`) | `(key: str, value: Any, parameter_type: type) -> Any` | Coerces parameter value into the backend representation. |
| `_qec_model_attributes` (`L236`) | `(model: Any) -> dict[str, Any]` | Implements backend logic for qec model attributes. |
| `_seconds_to_ns_int` (`L253`) | `(value: float) -> int` | Converts seconds into the target time representation. |
| `_qdk_version` (`L257`) | `() -> str` | Returns QDK-related metadata for reporting. |

### `backend/services/resource_estimators/qiskit_compatibility.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `QiskitCompatibilityQreEstimator.estimate` (`L20`) | `(self, compilation: CompilationResult) -> dict[str, Any]` | Runs this resource-estimation backend for a compilation result. |
| `QiskitCompatibilityQreEstimator._prepare_estimation_circuit` (`L68`) | `(circuit: QuantumCircuit) -> QuantumCircuit` | Implements backend logic for prepare estimation circuit. |
| `_qdk_version` (`L77`) | `() -> str` | Returns QDK-related metadata for reporting. |

### `backend/services/resource_estimators/qre_params.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `build_qre_params` (`L13`) | `(context: EstimationContext, logical_ir: LogicalIR \| None=None) -> tuple[EstimatorParams, dict[str, Any]]` | Builds qre params from the provided inputs. |
| `_seconds_to_time_string` (`L71`) | `(value: float) -> str` | Converts seconds into the target time representation. |
| `_qdk_version` (`L81`) | `() -> str` | Returns QDK-related metadata for reporting. |

### `backend/services/target_service.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `build_target` (`L12`) | `(config: dict[str, Any]) -> FTarget` | Builds target from the provided inputs. |
| `_node_positions` (`L19`) | `(target: FTarget) -> dict[int, tuple[float, float]]` | Implements backend logic for node positions. |
| `preview_target` (`L44`) | `(config: dict[str, Any]) -> dict` | Implements backend logic for preview target. |

### `backend/services/transpilation_service.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `select_compiler_backend` (`L25`) | `(qasm: str, requested_backend: str) -> tuple[str, dict[str, Any]]` | Selects compiler backend according to request/configuration. |
| `compile_qasm` (`L49`) | `(qasm: str, target_config: dict[str, Any], compiler_backend: str='auto', resource_estimator: str=DEFAULT_RESOURCE_ESTIMATOR, estimation_profiles: dict[str, Any] \| None=None) -> dict[str, Any]` | Implements backend logic for compile qasm. |
| `transpile_qasm` (`L92`) | `(qasm: str, target_config: dict[str, Any]) -> dict[str, Any]` | Implements backend logic for transpile qasm. |
| `_select_resource_estimator` (`L96`) | `(requested_estimator: str) -> str` | Selects resource estimator according to request/configuration. |

### `backend/target_creation/target.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `FTarget.__init__` (`L23`) | `(self, config: dict=None, **kwargs)` | Initializes the object with its stored configuration. |
| `FTarget._validate_and_parse_profile` (`L126`) | `(self)` | Validates the input profile and converts string names to Qiskit gates. |
| `FTarget._instantiate_gate` (`L187`) | `(self, gate_name: str)` | Dynamically fetches a gate class from qiskit.circuit.library and instantiates it. |
| `FTarget._populate_instructions_network` (`L206`) | `(self)` | Internal method to add logical gate availability and connectivity to the Target. |
| `FTarget._populate_instructions_hex` (`L255`) | `()` | Implements backend logic for populate instructions hex. |
| `FTarget.to_json` (`L262`) | `(self, filepath: str)` | Implements backend logic for to json. |
| `FTarget.from_json` (`L269`) | `(cls, filepath: str)` | Implements backend logic for from json. |
| `FTarget.plot` (`L277`) | `(self, filename: str=None, gap: int=3)` | Plots the coupling map using the structured grid layout |

## Backend tests and debug helpers

### `backend/tests/test_all_targets.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `TestFTarget.setUpClass` (`L12`) | `(cls)` | Set up a base valid profile to reuse across multiple tests. |
| `TestFTarget.test_tiled_k_nearest_instantiation_and_plot` (`L32`) | `(self)` | Tests standard tiled grid networking and plot generation. |
| `TestFTarget.test_heavy_hex_instantiation_and_plot` (`L57`) | `(self)` | Tests heavy-hex fault-tolerant networking and plot generation. |
| `TestFTarget.test_heavy_square_instantiation_and_plot` (`L80`) | `(self)` | Tests heavy-square fault-tolerant networking and plot generation. |
| `TestFTarget.test_custom_coupling_map` (`L99`) | `(self)` | Tests fallback manual coupling map from a list of edges. |
| `TestFTarget.test_invalid_topology_type` (`L117`) | `(self)` | Asserts the class raises a ValueError if given an unsupported topology. |
| `TestFTarget.test_missing_profile` (`L126`) | `(self)` | Asserts the class catches missing profile configurations. |
| `TestFTarget.test_missing_legacy_physical_metric_is_accepted` (`L135`) | `(self)` | FTarget should accept legacy timing/error keys without depending on them. |
| `TestFTarget.test_invalid_gate_name` (`L149`) | `(self)` | Asserts the class catches a gate name that doesn't exist in Qiskit. |
| `TestFTarget.test_is_local_edge_logic` (`L164`) | `(self)` | Directly tests the mathematical logic distinguishing local vs network edges. |

### `backend/tests/test_ir_analysis.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `TestIrAnalysis.test_analysis_reports_dag_layers_and_remote_ops` (`L39`) | `(self) -> None` | Test case covering analysis reports dag layers and remote ops. |

### `backend/tests/test_ir_qasm.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `TestIrQasm.test_ingest_qasm_string_strips_outer_whitespace` (`L25`) | `(self) -> None` | Test case covering ingest qasm string strips outer whitespace. |
| `TestIrQasm.test_ingest_qasm_file_reads_contents` (`L28`) | `(self) -> None` | Test case covering ingest qasm file reads contents. |
| `TestIrQasm.test_validate_and_load_qasm` (`L34`) | `(self) -> None` | Test case covering validate and load qasm. |
| `TestIrQasm.test_export_round_trips_qasm` (`L41`) | `(self) -> None` | Test case covering export round trips qasm. |

### `backend/tests/test_ir_qiskit_adapter.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `TestLogicalIrToQiskitAdapter.test_remote_cx_lowers_to_base_cx_with_metadata` (`L39`) | `(self) -> None` | Test case covering remote cx lowers to base cx with metadata. |

### `backend/tests/test_logical_ir.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `TestLogicalIr.test_cross_node_two_qubit_gate_is_tagged_remote` (`L39`) | `(self) -> None` | Test case covering cross node two qubit gate is tagged remote. |
| `TestLogicalIr.test_dependencies_follow_qubit_access_order` (`L69`) | `(self) -> None` | Test case covering dependencies follow qubit access order. |

### `backend/tests/test_native_qre.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `TestNativeQreEstimator.test_native_qre_is_default_estimator` (`L68`) | `(self) -> None` | Test case covering native QRE is default estimator. |
| `TestNativeQreEstimator.test_h_measure_works` (`L74`) | `(self) -> None` | Test case covering h measure works. |
| `TestNativeQreEstimator.test_h_cx_measure_works_without_qiskit_qre_or_qiskit_reconstruction` (`L84`) | `(self) -> None` | Test case covering h cx measure works without qiskit QRE or qiskit reconstruction. |
| `TestNativeQreEstimator.test_custom_qdk_qec_model_parameters_are_used` (`L95`) | `(self) -> None` | Test case covering custom qdk qec model parameters are used. |
| `TestNativeQreEstimator.test_invalid_qdk_qec_model_fails_clearly` (`L119`) | `(self) -> None` | Test case covering invalid qdk qec model fails clearly. |
| `TestNativeQreEstimator.test_barriers_are_skipped_explicitly` (`L133`) | `(self) -> None` | Test case covering barriers are skipped explicitly. |
| `TestNativeQreEstimator.test_unsupported_t_fails_clearly` (`L154`) | `(self) -> None` | Test case covering unsupported t fails clearly. |
| `TestNativeQreEstimator.test_remote_gate_fails_clearly` (`L158`) | `(self) -> None` | Test case covering remote gate fails clearly. |

### `backend/tests/test_pandora_routing.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `large_gate_qasm` (`L55`) | `() -> str` | Implements backend logic for large gate qasm. |
| `large_qubit_qasm` (`L64`) | `() -> str` | Implements backend logic for large qubit qasm. |
| `_StubCompiler.__init__` (`L73`) | `(self, key: str) -> None` | Initializes the object with its stored configuration. |
| `_StubCompiler.compile` (`L76`) | `(self, qasm: str, target_config: dict) -> CompilationResult` | Compiles an input circuit using this backend. |
| `_StubEstimator.estimate` (`L89`) | `(self, compilation: CompilationResult) -> dict` | Runs this resource-estimation backend for a compilation result. |
| `TestPandoraRouting.test_small_circuit_defaults_to_qiskit` (`L94`) | `(self) -> None` | Test case covering small circuit defaults to qiskit. |
| `TestPandoraRouting.test_large_gate_count_defaults_to_pandora` (`L100`) | `(self) -> None` | Test case covering large gate count defaults to pandora. |
| `TestPandoraRouting.test_large_qubit_count_defaults_to_pandora` (`L107`) | `(self) -> None` | Test case covering large qubit count defaults to pandora. |
| `TestPandoraRouting.test_manual_backend_bypasses_auto_router` (`L114`) | `(self) -> None` | Test case covering manual backend bypasses auto router. |
| `TestPandoraRouting.test_compile_qasm_uses_pandora_for_large_circuits` (`L120`) | `(self) -> None` | Test case covering compile qasm uses pandora for large circuits. |
| `TestPandoraRouting.test_pandora_support_preflight_reports_unsupported_ops_cleanly` (`L139`) | `(self) -> None` | Test case covering pandora support preflight reports unsupported ops cleanly. |

### `backend/tests/test_production_architecture.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `test_production_backend_does_not_reference_custom_qec_compiler` (`L19`) | `() -> None` | Test case covering production backend does not reference custom qec compiler. |

### `backend/tests/test_qiskit_compatibility_qre.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `TestQiskitCompatibilityQreEstimator.test_explicit_qiskit_compatibility_mode_returns_qre_metrics` (`L42`) | `(self) -> None` | Test case covering explicit qiskit compatibility mode returns QRE metrics. |

### `backend/tests/transpilation_debug.py`
| Function / method | Signature | Purpose |
|---|---|---|
| `transpilation_tracker` (`L4`) | `(pass_, dag, time, property_set, count)` | Implements backend logic for transpilation tracker. |
