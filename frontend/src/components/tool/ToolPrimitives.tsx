import type { ReactNode } from "react";

export function SectionLabel({ children }: { children: ReactNode }) {
  return <p className="section-label">{children}</p>;
}

export function SurfaceMetric({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  tone?: "default" | "emphasis" | "signal";
}) {
  return (
    <article className={`surface-metric tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export function PanelCard({
  label,
  title,
  description,
  actions,
  className,
  children,
}: {
  label?: string;
  title?: string;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <article className={`surface-card ${className ?? ""}`.trim()}>
      {(label || title || description || actions) && (
        <header className="panel-card-header">
          <div>
            {label ? <SectionLabel>{label}</SectionLabel> : null}
            {title ? <h3 className="panel-card-title">{title}</h3> : null}
            {description ? <p className="body-copy">{description}</p> : null}
          </div>
          {actions ? <div className="panel-card-actions">{actions}</div> : null}
        </header>
      )}
      {children}
    </article>
  );
}
