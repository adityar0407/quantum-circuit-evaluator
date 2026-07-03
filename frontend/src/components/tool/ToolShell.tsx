import type { ReactNode } from "react";

type ToolStage = {
  id: string;
  label: string;
  title: string;
};

export function ToolShell({
  stages,
  activeStage,
  runAction,
  secondaryAction,
  children,
}: {
  stages: ToolStage[];
  activeStage: string;
  runAction: ReactNode;
  secondaryAction?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="tool-shell">
      <aside className="tool-sidebar">
        <div className="tool-sidebar-brand">
          <p>Workflow</p>
          <strong>Analysis stages</strong>
        </div>
        <nav className="tool-stage-nav" aria-label="Tool workflow">
          {stages.map((stage, index) => (
            <a key={stage.id} href={`#${stage.id}`} className={activeStage === stage.id ? "active" : undefined}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <small>{stage.label}</small>
                <strong>{stage.title}</strong>
              </div>
            </a>
          ))}
        </nav>
        {runAction || secondaryAction ? (
          <div className="tool-sidebar-actions">
            {runAction}
            {secondaryAction}
          </div>
        ) : null}
      </aside>

      <section className="tool-main">
        {children}
      </section>
    </main>
  );
}
