import { ArrowRight } from "lucide-react";
import type { ResourceCapabilities } from "../../api/types";
import type { QecModelKey } from "../../state/defaults";
import { qecModelDefaultParameters, qecModelOptions, qecModelParameterFields } from "../../state/defaults";
import { PanelCard, SectionLabel } from "./ToolPrimitives";

function AssumptionField({
  label,
  help,
  value,
  step = "any",
  min,
  onChange,
}: {
  label: string;
  help?: string;
  value: unknown;
  step?: string;
  min?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" min={min} step={step} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)} />
      {help ? <small className="field-hint">{help}</small> : null}
    </label>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  if (typeof value !== "number") {
    return String(value);
  }
  if (value === 0) {
    return "0";
  }
  if (Math.abs(value) < 0.001 || Math.abs(value) >= 10000) {
    return value.toExponential(3);
  }
  return value.toLocaleString(undefined, { maximumSignificantDigits: 6 });
}

function friendlyHardwareModel(key: string): string {
  return key === "neutral_atom" ? "Neutral-atom hardware" : "Standard quantum hardware";
}

function friendlyPhysicalFieldLabel(key: string): string {
  const labels: Record<string, string> = {
    physical_modality: "Physical hardware type",
    qdk_hardware_model: "Hardware calculation method",
    error_rate: "Combined operation error rate",
    one_qubit_gate_error_rate: "Single-qubit error",
    two_qubit_gate_error_rate: "Two-qubit error",
    measurement_error_rate: "Measurement error",
    idle_error_rate: "Idle error rate",
    one_qubit_gate_time: "Single-qubit operation",
    two_qubit_gate_time: "Two-qubit operation",
    measurement_time: "Measurement time",
    cycle_time: "Surface-code cycle time",
  };
  return labels[key] ?? key.replace(/_/g, " ");
}

const visibleHardwareValueKeys = [
  "error_rate",
  "one_qubit_gate_error_rate",
  "two_qubit_gate_error_rate",
  "measurement_error_rate",
  "one_qubit_gate_time",
  "two_qubit_gate_time",
  "measurement_time",
  "cycle_time",
];

function formatHardwareValue(key: string, value: unknown): string {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "";
  }
  if (key.includes("error_rate")) {
    return `${(number * 100).toLocaleString(undefined, { maximumSignificantDigits: 4 })}%`;
  }
  if (key.endsWith("_time")) {
    if (number < 0.000001) {
      return `${(number * 1_000_000_000).toLocaleString(undefined, { maximumSignificantDigits: 4 })} ns`;
    }
    if (number < 0.001) {
      return `${(number * 1_000_000).toLocaleString(undefined, { maximumSignificantDigits: 4 })} µs`;
    }
    return `${number.toLocaleString(undefined, { maximumSignificantDigits: 4 })} s`;
  }
  return formatNumber(number);
}

function physicalFieldHelp(key: string): string | undefined {
  const help: Record<string, string> = {
    error_rate: "One combined error rate used when separate gate error rates are unavailable.",
    idle_error_rate: "Recorded in exported results, but not included in the current calculation.",
    cycle_time: "Time required for one round of error correction.",
  };
  return help[key];
}

export function EstimationStage({
  resourceCapabilities,
  estimationProfiles,
  status,
  onUpdateProfileSection,
  onUpdateQecModelSource,
  onUpdateQecModelName,
  onUpdateQecModelParameter,
  onUpdatePhysicalProfileMode,
  onUpdateHardwareModel,
  onRun,
  onProceed,
}: {
  resourceCapabilities?: ResourceCapabilities;
  estimationProfiles: { physical_hardware: Record<string, unknown>; qec: Record<string, unknown>; network?: Record<string, unknown> };
  status: "idle" | "loading" | "ready" | "error";
  onUpdateProfileSection: (section: "physical_hardware" | "qec" | "network", key: string, value: unknown) => void;
  onUpdateQecModelSource: (value: string) => void;
  onUpdateQecModelName: (value: QecModelKey) => void;
  onUpdateQecModelParameter: (key: string, value: unknown) => void;
  onUpdatePhysicalProfileMode: (value: string) => void;
  onUpdateHardwareModel: (value: string) => void;
  onRun: () => void;
  onProceed: () => void;
}) {
  const physicalProfile = estimationProfiles.physical_hardware;
  const qecProfile = estimationProfiles.qec;
  const networkProfile = estimationProfiles.network ?? {};
  const physicalProfileMode = String(physicalProfile.physical_profile_mode ?? "built_in");
  const selectedHardwareModel = String(physicalProfile.qdk_hardware_model ?? "gate_based");
  const verifiedHardwareModels = resourceCapabilities?.physical_hardware.verified_builtin_models ?? [];
  const selectedHardwareCapability = verifiedHardwareModels.find((model) => model.key === selectedHardwareModel);
  const customPhysicalFields = resourceCapabilities?.physical_hardware.custom_profile_fields ?? [];
  const qecModelSource = String(qecProfile.qec_model_source ?? "azure_builtin");
  const selectedQecModel = String(qecProfile.qec_model_name ?? "surface_code") as QecModelKey;
  const qecModelParameters = asRecord(qecProfile.qec_model_parameters);
  const selectedQecParameterFields = qecModelParameterFields[selectedQecModel] ?? qecModelParameterFields.surface_code;
  const selectedQecDefaultParameters = qecModelDefaultParameters[selectedQecModel] ?? qecModelDefaultParameters.surface_code;
  const selectedQecModelDescription =
    qecModelOptions.find((model) => model.key === selectedQecModel)?.description ?? "Uses the selected error-correction model.";
  const recommendedHardwareValues = Object.entries(selectedHardwareCapability?.defaults ?? physicalProfile)
    .filter(([key, value]) => visibleHardwareValueKeys.includes(key) && Number.isFinite(Number(value)))
    .sort(([left], [right]) => visibleHardwareValueKeys.indexOf(left) - visibleHardwareValueKeys.indexOf(right));

  return (
    <section id="estimation" className="workspace-section">
      <div className="section-header">
        <div>
          <SectionLabel>Stage 3</SectionLabel>
          <h2>Resource estimation profile</h2>
          <p className="section-copy">Choose the physical error, timing, and error-correction assumptions that turn the compiled circuit into resource numbers.</p>
        </div>
        <div className="section-actions">
          <button type="button" onClick={onProceed}>
            Proceed to Results <ArrowRight aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="tool-grid tool-grid-estimation">
        <div className="stack-column">
          <PanelCard label="Physical hardware" title="Hardware numbers used by the estimator" className="estimation-primary-card">
            <div className="form-grid">
              <label className="field">
                <span>Hardware values</span>
                <select value={physicalProfileMode} onChange={(event) => onUpdatePhysicalProfileMode(event.target.value)}>
                  <option value="built_in">Recommended values</option>
                  <option value="custom">Enter my own values</option>
                </select>
                <small className="field-hint">Choose recommended values for a quick estimate, or enter measured and experimental values.</small>
              </label>
              <label className="field">
                <span>Hardware type</span>
                <select value={selectedHardwareModel} onChange={(event) => onUpdateHardwareModel(event.target.value)}>
                  {verifiedHardwareModels.map((model) => (
                    <option key={model.key} value={model.key}>
                      {friendlyHardwareModel(model.key)}
                    </option>
                  ))}
                </select>
                <small className="field-hint">Choose whether the calculation should include neutral-atom movement costs.</small>
              </label>
            </div>

            {physicalProfileMode === "custom" ? (
              <div className="form-grid">
                {customPhysicalFields.map((field) =>
                  field.key === "physical_modality" ? (
                    <label className="field" key={field.key}>
                      <span>{friendlyPhysicalFieldLabel(field.key)}</span>
                      <select
                        value={String(physicalProfile.physical_modality ?? "gate_based")}
                        onChange={(event) => onUpdateProfileSection("physical_hardware", "physical_modality", event.target.value)}
                      >
                        <option value="gate_based">General gate-based hardware</option>
                        <option value="neutral_atom">Neutral-atom hardware</option>
                        <option value="superconducting">Superconducting hardware</option>
                        <option value="trapped_ion">Trapped-ion hardware</option>
                      </select>
                      <small className="field-hint">This identifies the hardware represented by your custom values.</small>
                    </label>
                  ) : (
                    <AssumptionField
                      key={field.key}
                      label={`${friendlyPhysicalFieldLabel(field.key)}${field.unit ? ` (${field.unit})` : ""}`}
                      help={physicalFieldHelp(field.key)}
                      value={physicalProfile[field.key] ?? field.default}
                      min={field.type === "probability" || field.type === "duration" ? "0" : undefined}
                      onChange={(value) => onUpdateProfileSection("physical_hardware", field.key, value)}
                    />
                  ),
                )}
              </div>
            ) : (
              <div className="subsection-block">
                <h4>Values included in this estimate</h4>
                <div className="qec-parameter-grid">
                  {recommendedHardwareValues.map(([key, value]) => (
                    <div className="qec-parameter" key={key}>
                      <span>{friendlyPhysicalFieldLabel(key)}</span>
                      <strong>{formatHardwareValue(key, value)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </PanelCard>

          <PanelCard label="Error correction" title="Error-correction assumptions" className="estimation-primary-card">
            <div className="form-grid">
              <AssumptionField
                label="Target failure probability"
                help="The maximum logical failure probability you want the estimated run to target."
                value={qecProfile.error_budget}
                min="0"
                onChange={(value) => onUpdateProfileSection("qec", "error_budget", value)}
              />
              <label className="field">
                <span>Error-correction values</span>
                <select value={qecModelSource} onChange={(event) => onUpdateQecModelSource(event.target.value)}>
                  <option value="azure_builtin">Recommended values</option>
                  <option value="custom">Enter advanced values</option>
                </select>
                <small className="field-hint">Advanced values change how error-correction overhead is calculated.</small>
              </label>
              <label className="field">
                <span>Error-correction model</span>
                <select value={selectedQecModel} onChange={(event) => onUpdateQecModelName(event.target.value as QecModelKey)}>
                  {qecModelOptions.map((model) => (
                    <option key={model.key} value={model.key}>
                      {model.label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="field static-field">
                <span>What this model assumes</span>
                <strong>{selectedQecModelDescription}</strong>
              </div>
            </div>

            {qecModelSource === "custom" ? (
              <div className="form-grid">
                {selectedQecParameterFields.map((field) =>
                  field.type === "boolean" ? (
                    <label className="field" key={field.key}>
                      <span>{field.label}</span>
                      <select
                        value={String(qecModelParameters[field.key] ?? false)}
                        onChange={(event) => onUpdateQecModelParameter(field.key, event.target.value === "true")}
                      >
                        <option value="false">No</option>
                        <option value="true">Yes</option>
                      </select>
                      {field.help ? <small className="field-hint">{field.help}</small> : null}
                    </label>
                  ) : (
                    <AssumptionField
                      key={field.key}
                      label={field.label}
                      help={field.help}
                      value={qecModelParameters[field.key] ?? ""}
                      min={field.min}
                      step={field.step}
                      onChange={(value) => onUpdateQecModelParameter(field.key, value)}
                    />
                  ),
                )}
              </div>
            ) : (
              <div className="qec-parameter-grid">
                {selectedQecParameterFields.map((field) => (
                  <div className="qec-parameter" key={field.key}>
                    <span>{field.label}</span>
                    <strong>{formatNumber(selectedQecDefaultParameters[field.key])}</strong>
                    {field.help ? <small>{field.help}</small> : null}
                  </div>
                ))}
              </div>
            )}
          </PanelCard>
        </div>

        <div className="stack-column estimation-sidebar-stack">
          <PanelCard label="Advanced settings" title="Remote-link assumptions" className="estimation-sidebar-card">
            <div className="form-grid">
              <label className="field">
                <span>System organization</span>
                <select value={String(networkProfile.topology ?? "none")} onChange={(event) => onUpdateProfileSection("network", "topology", event.target.value)}>
                  <option value="none">Single device</option>
                  <option value="distributed">Distributed devices</option>
                  <option value="modular">Modular device</option>
                </select>
                <small className="field-hint">Use single device unless you want to include remote or inter-module operation assumptions.</small>
              </label>
              <AssumptionField label="Remote operation time (seconds)" help="Time assigned to an operation that crosses devices or modules." value={networkProfile.remote_gate_time} min="0" onChange={(value) => onUpdateProfileSection("network", "remote_gate_time", value)} />
              <AssumptionField label="Remote operation error rate" help="Error probability assigned to an operation that crosses devices or modules." value={networkProfile.remote_gate_error} min="0" onChange={(value) => onUpdateProfileSection("network", "remote_gate_error", value)} />
              <AssumptionField label="Remote link capacity" help="How many remote links can be active at the same time." value={networkProfile.link_capacity} min="0" step="1" onChange={(value) => onUpdateProfileSection("network", "link_capacity", value)} />
            </div>
          </PanelCard>
        </div>
      </div>
    </section>
  );
}
