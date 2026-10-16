import { useEffect, useRef, useState } from "react";
import { Icon, type IconName } from "./Icon";
import type { Section } from "../features/platform/routing";

export const navigationItems: { id: Section; label: string; icon: IconName }[] = [
  { id: "overview", label: "课程总览", icon: "home" },
  { id: "materials", label: "资料阅读", icon: "file" },
  { id: "notes", label: "知识笔记", icon: "notes" },
  { id: "ai", label: "AI 学习", icon: "ai" },
  { id: "exam", label: "真题与模拟卷", icon: "exam" },
  { id: "review", label: "错题复习", icon: "review" },
  { id: "search", label: "课程查找", icon: "search" },
  { id: "backup", label: "备份与恢复", icon: "download" },
];
type Props = { section: Section; username: string; locationKey: string; expired: boolean; onNavigate: (section: Section) => void; onSignOut: () => void };

function Contents({ section, username, onNavigate, onSignOut }: Pick<Props, "section" | "username" | "onNavigate" | "onSignOut">) {
  return <>
    <div className="brand"><span className="brand-mark">H</span><span>Hustudy</span></div>
    <p className="sidebar-caption">课程学习工作台</p>
    <nav aria-label="主导航">{navigationItems.map(item => <button key={item.id} aria-current={section === item.id ? "page" : undefined} className={`nav-item ${section === item.id ? "active" : ""}`} onClick={() => onNavigate(item.id)}><Icon name={item.icon}/>{item.label}</button>)}</nav>
    <div className="sidebar-bottom">
      <button className={`nav-item ${section === "help" ? "active" : ""}`} aria-current={section === "help" ? "page" : undefined} onClick={() => onNavigate("help")}><Icon name="help"/>使用指南</button>
      <div className="model-badge"><span className="dot"/>AI · 按次选择</div>
      <div className="workspace-account"><span className="account-avatar" aria-hidden="true">{Array.from(username)[0]?.toUpperCase() || "H"}</span><div><strong title={username}>{username}</strong><small>个人学习空间</small></div></div>
      <button className="text-button" onClick={onSignOut}><Icon name="logout" size={16}/>退出登录</button>
    </div>
  </>;
}

export function WorkspaceNavigation(props: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const close = () => { dialog.current?.close(); setOpen(false); };
  // A cancelled route transition leaves the menu and the editor draft intact.
  useEffect(close, [props.locationKey, props.expired]);
  useEffect(() => {
    const wide = window.matchMedia("(min-width: 1101px)");
    const resize = () => { if (wide.matches) close(); };
    wide.addEventListener("change", resize);
    return () => wide.removeEventListener("change", resize);
  }, []);
  return <>
    <aside className="sidebar"><Contents {...props}/></aside>
    <button ref={trigger} type="button" className="mobile-navigation-toggle" aria-label="打开导航菜单" aria-haspopup="dialog" aria-expanded={open} aria-controls="workspace-navigation" onClick={() => { dialog.current?.showModal(); setOpen(true); }}><Icon name="list" size={20}/><span>Hustudy</span><span className="mobile-section-name">{navigationItems.find(item => item.id === props.section)?.label || "使用指南"}</span></button>
    <dialog ref={dialog} id="workspace-navigation" className="navigation-drawer" aria-label="导航菜单" onClose={() => { setOpen(false); trigger.current?.focus({preventScroll:true}); }} onKeyDown={event => {
      if (event.key !== "Tab") return;
      const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")).filter(button => button.getClientRects().length);
      const first = buttons[0], last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }} onClick={event => { if (event.target === dialog.current) { const r = dialog.current.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) close(); } }}>
      <button type="button" className="icon-button drawer-close" aria-label="关闭导航菜单" autoFocus onClick={close}><Icon name="close"/></button>
      <Contents {...props} onNavigate={section => { props.onNavigate(section); if (section === props.section) close(); }}/>
    </dialog>
  </>;
}
