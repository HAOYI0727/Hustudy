import { useId, useState, type ReactNode } from "react";
import { Icon } from "./Icon";

/** Keep library state mounted when a narrow-screen reader/editor needs the space. */
export function CompactLibrary({ className, label, children }: { className: string; label: string; children: ReactNode }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  return <aside className={`${className} compact-library`}>
    <button type="button" className="compact-library-toggle" aria-expanded={expanded} aria-controls={id} onClick={() => setExpanded(value => !value)}><Icon name="folder"/><strong>{label}</strong><span>{expanded ? "收起" : "展开"}</span><Icon name={expanded ? "collapse" : "expand"} size={16}/></button>
    <div id={id} className={`library-content ${expanded ? "library-expanded" : ""}`}>{children}</div>
  </aside>;
}
