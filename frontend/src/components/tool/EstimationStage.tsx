import { ArrowRight } from "lucide-react";
import type { ResourceCapabilities } from "../../api/types";
import type { QecModelKey } from "../../state/defaults";
import { qecModelDefaultParameters, qecModelOptions, qecModelParameterFields } from "../../state/defaults";
import { PanelCard, SectionLabel } from "./ToolPrimitives";

function AssumptionField({
  label,
  value,
  step = "any",
  min,
  onChange,
}: {
  label: string;
  value: unknown;
  step?: string;
  min?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" min={min} step={step} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)} />
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
  return key === "neutral_atom" ? "Neutral-atom hardware model" : "Gate-based hardware model";
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
    qecModelOptions.find((model) => model.key === selectedQecModel)?.description ?? "Uses the selected QDK QEC model.";
  const hardwareModelExplanation =
    selectedHardwareModel === "neutral_atom"
      ? "Uses timing and error assumptions shaped for neutral-atom style gates."
      : "Uses gate-based timing and error assumptions for superconducting and ion-style studies.";

  return (
    <section id="estimation" className="workspace-section">
      <div className="section-header">
        <div>
          <SectionLabel>Stage 3</SectionLabel>
          <h2>Resource estimation profile</h2>
          <p className="section-copy">Configure physical hardware parameters and quantum error-correction assumptions before running the estimate.</p>
        </div>
        <div className="section-actions">
          <button type="button" onClick={onProceed}>
            Proceed to Results <ArrowRight aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="tool-grid tool-grid-estimation">
        <div className="stack-column">
          <PanelCard label="Physical hardware" title="Hardware assumptions" className="estimation-primary-card">
            <div className="form-grid">
              <label className="field">
                <span>Numbers source</span>
                <select value={physicalProfileMode} onChange={(event) => onUpdatePhysicalProfileMode(event.target.value)}>
                  <option value="built_in">Recommended defaults</option>
                  <option value="custom">Enter my own numbers</option>
                </select>
              </label>
              <label className="field">
                <span>Estimator hardware family</span>
                <select value={selectedHardwareModel} onChange={(event) => onUpdateHardwareModel(event.target.value)}>
                  {verifiedHardwareModels.map((model) => (
                    <option key={model.key} value={model.key}>
                      {friendlyHardwareModel(model.key)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="subsection-block">
              <h4>Meaning</h4>
              <p className="body-copy">{hardwareModelExplanation}</p>
            </div>

            {physicalProfileMode === "custom" ? (
              <div className="form-grid">
                {customPhysicalFields.map((field) =>
                  field.key === "physical_modality" ? (
                    <label className="field" key={field.key}>
                      <span>Physical modality</span>
                      <select
                        value={String(physicalProfile.physical_modality ?? "gate_based")}
                        onChange={(event) => onUpdateProfileSection("physical_hardware", "physical_modality", event.target.value)}
                      >
                        <option value="gate_based">Gate-based</option>
                        <option value="neutral_atom">Neutral atom</option>
                        <option value="superconducting">Superconducting</option>
                        <option value="trapped_ion">Trapped ion</option>
                      </select>
                    </label>
                  ) : (
                    <AssumptionField
                      key={field.key}
                      label={`${field.key.replace(/_/g, " ")}${field.unit ? ` (${field.unit})` : ""}`}
                      value={physicalProfile[field.key] ?? field.default}
                      min={field.type === "probability" || field.type === "duration" ? "0" : undefined}
                      onChange={(value) => onUpdateProfileSection("physical_hardware", field.key, value)}
                    />
                  ),
                )}
              </div>
            ) : (
              <div className="qec-parameter-grid">
                {Object.entries(selectedHardwareCapability?.defaults ?? physicalProfile).map(([key, value]) => (
                  <div className="qec-parameter" key={key}>
                    <span>{key.replace(/_/g, " ")}</span>
                    <strong>{formatNumber(value)}</strong>
                  </div>
                ))}
              </div>
            )}
          </PanelCard>

          <PanelCard label="QEC model" title="Error-correction assumptions" className="estimation-primary-card">
            <div className="form-grid">
              <AssumptionField
                label="Target logical failure budget"
                value={qecProfile.error_budget}
                min="0"
                onChange={(value) => onUpdateProfileSection("qec", "error_budget", value)}
              />
              <label className="field">
                <span>QEC parameter mode</span>
                <select value={qecModelSource} onChange={(event) => onUpdateQecModelSource(event.target.value)}>
                  <option value="azure_builtin">Use recommended defaults</option>
                  <option value="custom">Edit advanced QEC parameters</option>
                </select>
              </label>
              <label className="field">
                <span>QEC model</span>
                <select value={selectedQecModel} onChange={(event) => onUpdateQecModelName(event.target.value as QecModelKey)}>
                  {qecModelOptions.map((model) => (
                    <option key={model.key} value={model.key}>
                      {model.label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="field static-field">
                <span>Profile description</span>
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
                        <option value="false">False</option>
                        <option value="true">True</option>
                      </select>
                    </label>
                  ) : (
                    <AssumptionField
                      key={field.key}
                      label={field.label}
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
                  </div>
                ))}
              </div>
            )}
          </PanelCard>
        </div>

        <div className="stack-column estimation-sidebar-stack">
          <PanelCard label="Error budget" title="Logical failure target" className="estimation-sidebar-card">
            <AssumptionField
              label="Logical failure probability"
              value={qecProfile.error_budget}
              min="0"
              onChange={(value) => onUpdateProfileSection("qec", "error_budget", value)}
            />
          </PanelCard>

          <PanelCard label="Advanced settings" title="Remote-link assumptions" className="estimation-sidebar-card">
            <div className="form-grid">
              <label className="field">
                <span>System organization</span>
                <select value={String(networkProfile.topology ?? "none")} onChange={(event) => onUpdateProfileSection("network", "topology", event.target.value)}>
                  <option value="none">None</option>
                  <option value="distributed">Distributed</option>
                  <option value="modular">Modular</option>
                </select>
              </label>
              <AssumptionField label="Remote gate time seconds" value={networkProfile.remote_gate_time} min="0" onChange={(value) => onUpdateProfileSection("network", "remote_gate_time", value)} />
              <AssumptionField label="Remote gate error" value={networkProfile.remote_gate_error} min="0" onChange={(value) => onUpdateProfileSection("network", "remote_gate_error", value)} />
              <AssumptionField label="Link capacity" value={networkProfile.link_capacity} min="0" step="1" onChange={(value) => onUpdateProfileSection("network", "link_capacity", value)} />
            </div>
          </PanelCard>
        </div>
      </div>
    </section>
  );
}
