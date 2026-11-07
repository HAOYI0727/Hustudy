import { Icon, type IconName } from "./Icon";
import { useEffect, useState } from "react";

function ModuleIllustration({ kind }: { kind: string }) {
  return <svg className="module-illustration" viewBox="0 0 200 140" aria-hidden="true" focusable="false">
    <circle cx="106" cy="71" r="58" fill="currentColor" opacity=".07"/>
    <circle cx="175" cy="25" r="6" fill="currentColor" opacity=".2"/>
    <path d="M25 28h12m-6-6v12M166 107h14m-7-7v14" stroke="currentColor" strokeWidth="2" opacity=".45"/>
    {kind === "materials" ? <g stroke="currentColor" strokeWidth="3" fill="white"><rect x="68" y="22" width="76" height="95" rx="10" transform="rotate(12 106 70)" opacity=".4"/><rect x="55" y="22" width="76" height="95" rx="10"/><path d="M71 45h41M71 60h41M71 75h25"/><path d="M103 91l9 8 18-20" fill="none"/></g>
    : kind === "notes" ? <g stroke="currentColor" strokeWidth="3" fill="white"><path d="M61 54l70-19-12 68-58-49M61 54l-22 50 80-1" fill="none" opacity=".5"/><rect x="43" y="35" width="37" height="38" rx="10"/><rect x="112" y="16" width="37" height="38" rx="10"/><rect x="101" y="84" width="37" height="38" rx="10"/><circle cx="39" cy="104" r="10"/><path d="M53 48h17M53 58h10M122 30h17M111 100h17"/></g>
    : kind === "ai" ? <g stroke="currentColor" strokeWidth="3" fill="white"><path d="M45 33q0-10 10-10h90q10 0 10 10v57q0 10-10 10H88l-25 18V100H55q-10 0-10-10z"/><path d="M101 39l6 16 17 6-17 6-6 16-6-16-17-6 17-6z" fill="currentColor" opacity=".7"/></g>
    : kind === "exam" ? <g stroke="currentColor" strokeWidth="3" fill="white"><rect x="58" y="22" width="83" height="101" rx="10"/><rect x="82" y="14" width="35" height="16" rx="5"/><path d="M73 51l5 5 8-10M94 52h29M73 75l5 5 8-10M94 76h29M73 101h50"/></g>
    : kind === "backup" ? <g stroke="currentColor" strokeWidth="3" fill="white"><rect x="48" y="28" width="100" height="28" rx="9"/><rect x="48" y="62" width="100" height="28" rx="9"/><path d="M62 42h40M62 76h40"/><circle cx="128" cy="102" r="24"/><path d="m116 102 8 8 16-18" fill="none"/></g>
    : <g stroke="currentColor" strokeWidth="3" fill="white"><circle cx="102" cy="72" r="39"/><path d="M82 72l14 14 29-31" fill="none"/><path d="M48 69a55 55 0 0 1 93-37M150 73a53 53 0 0 1-90 40" fill="none" opacity=".5"/><path d="M138 19l5 15-17 1M62 125l-5-15 16-1" fill="none"/></g>}
  </svg>;
}

export function PageTitle({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  const kind = eyebrow.startsWith("MATERIAL") ? "materials" : eyebrow.startsWith("NOTE") ? "notes" : eyebrow.startsWith("AI") ? "ai" : eyebrow.startsWith("EXAM") ? "exam" : eyebrow.startsWith("ACCOUNT") ? "backup" : "review";
  return <div className={`page-title theme-${kind}`}><div className="module-title-copy"><p className="eyebrow">{eyebrow}</p><h2>{title}</h2><p>{text}</p></div><ModuleIllustration kind={kind}/></div>;
}
export function Status({ value }: { value: string }) { const label: Record<string, string> = { PENDING: "待处理", SAVED: "已保存", IN_PROGRESS: "作答中", SUBMITTED: "已提交", COMPLETED: "已完成", NEEDS_SELF_REVIEW: "待自评", TEXT_ONLY: "原格式可读", CANCELLED: "已取消", SUCCEEDED: "已完成", RUNNING: "处理中", QUEUED: "排队中", FAILED: "失败", DRAFT: "草稿", READY: "可作答", SCORED: "已评分", CONFIRMED: "已确认", grounded: "有来源", insufficient_evidence: "证据不足", provider_error: "AI处理异常" }; return <span className={`status status-${value.toLowerCase()}`}>{label[value] || value}</span>; }
export function EmptyInline({ text }: { text: string }) { return <div className="empty-inline"><Icon name="info" size={16}/>{text}</div>; }
export function EmptyState({ title, text, action, onAction, icon = "folder" }: { title: string; text: string; action?: string; onAction?: () => void; icon?: IconName }) { return <div className="empty-state"><div className="empty-icon"><Icon name={icon} size={26}/></div><h3>{title}</h3><p>{text}</p>{action && <button className="secondary" onClick={onAction}>{action}<Icon name="arrow" size={16}/></button>}</div>; }


export function ModuleStats({ items }: { items: { label: string; value: string | number; hint: string }[] }) {
  return <div className="module-stats">{items.map((item) => <article key={item.label}><span>{item.label}</span><strong>{item.value}</strong><small>{item.hint}</small></article>)}</div>;
}

export function ScrollToTop() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const update = () => setVisible(window.scrollY > 550);
    update(); window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return visible ? <button className="floating-top" aria-label="返回页面顶部" title="返回顶部" onClick={() => {
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    document.getElementById("workspace-content")?.focus({ preventScroll: true });
  }}><Icon name="up" size={20}/></button> : null;
}
