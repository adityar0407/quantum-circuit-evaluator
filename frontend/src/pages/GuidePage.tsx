import { ArrowRight, BarChart3, Cpu, PanelsTopLeft, Shield, TerminalSquare } from "lucide-react";
import { SectionLabel } from "../components/tool/ToolPrimitives";

type StageCard = {
  eyebrow: string;
  title: string;
  summary: string;
  variant: "intake" | "mapping" | "estimation";
  active?: boolean;
  icon: typeof PanelsTopLeft;
};

const stageCards: StageCard[] = [
  {
    eyebrow: "Stage one",
    title: "Circuit Intake",
    summary: "Import the circuit, inspect the instruction mix, and establish a clean baseline before hardware mapping begins.",
    variant: "intake",
    icon: PanelsTopLeft,
  },
  {
    eyebrow: "Current focus",
    title: "Architecture Mapping",
    summary: "Map the circuit onto the selected hardware topology and compiler path while enforcing connectivity, routing, and modality constraints.",
    variant: "mapping",
    active: true,
    icon: Cpu,
  },
  {
    eyebrow: "Stage three",
    title: "Resource Estimation",
    summary: "Translate the compiled result into fault-tolerant overhead, logical-qubit counts, runtime, and QEC-driven cost signals.",
    variant: "estimation",
    icon: BarChart3,
  },
];

export function GuidePage() {
  return (
    <main className="guide-shell">
      <section className="guide-overview-header">
        <SectionLabel>Onboarding guide</SectionLabel>
        <h1>How the evaluator moves from circuit input to hardware-aware cost.</h1>
        <p>
          Understand the three-stage workflow before configuring architectures, compilers, and estimation profiles for a comparative run.
        </p>
      </section>

      <section className="guide-stage-grid">
        {stageCards.map((card) => {
          const Icon = card.icon;
          return (
            <article
              key={card.title}
              className={`guide-stage-card ${card.active ? "is-active" : ""}`}
            >
              <div className="guide-stage-card-header">
                <div className={`guide-stage-icon ${card.active ? "is-active" : ""}`}>
                  <Icon aria-hidden="true" />
                </div>
                <span>{card.eyebrow}</span>
              </div>
              <h2>{card.title}</h2>
              <p>{card.summary}</p>
              <div className={`guide-stage-diagram ${card.variant}`}>
                {card.variant === "intake" ? (
                  <div className="guide-diagram-lines" aria-hidden="true">
                    <div><span /><i /></div>
                    <div><span /><i className="is-bright" /></div>
                    <div><span /><i /></div>
                  </div>
                ) : null}
                {card.variant === "mapping" ? (
                  <div className="guide-diagram-nodes" aria-hidden="true">
                    <div className="node small"><span /></div>
                    <i />
                    <div className="node large"><span /></div>
                    <i />
                    <div className="node small muted"><span /></div>
                  </div>
                ) : null}
                {card.variant === "estimation" ? (
                  <div className="guide-diagram-bars" aria-hidden="true">
                    <span />
                    <span />
                    <span className="highlight" />
                    <span />
                    <span />
                  </div>
                ) : null}
              </div>
            </article>
          );
        })}
      </section>

      <section className="guide-cta-card">
        <div>
          <h2>Ready to begin your analysis?</h2>
          <p>Open the tool workflow and move through circuit setup, architecture mapping, and estimation one stage at a time.</p>
        </div>
        <div className="guide-cta-actions">
          <button type="button" className="secondary" onClick={() => (window.location.hash = "credits")}>
            View documentation
          </button>
          <button type="button" onClick={() => (window.location.hash = "tool")}>
            Initialize pipeline
            <ArrowRight aria-hidden="true" />
          </button>
        </div>
      </section>

      <section className="guide-signal-row">
        <article className="guide-signal-card">
          <TerminalSquare aria-hidden="true" />
          <div>
            <h3>CLI integration</h3>
            <p>Use the same staged evaluator flow in local automation and reproducible research runs.</p>
          </div>
        </article>
        <article className="guide-signal-card">
          <Shield aria-hidden="true" />
          <div>
            <h3>Separated run artifacts</h3>
            <p>Compiled artifacts and estimation payloads stay distinct from the presentation layer so runs remain traceable.</p>
          </div>
        </article>
      </section>
    </main>
  );
}
