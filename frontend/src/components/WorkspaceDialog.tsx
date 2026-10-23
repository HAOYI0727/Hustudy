import "./workspace-dialog.css";
import {useEffect, useId, useRef, useState, type ReactNode} from 'react';

/** Keep completed imports and retry identities alive when a tool is closed. */
export function WorkspaceDialog({open, title, onClose, restoreFocus, busy = false, className = '', children}: {
  open: boolean; title: string; onClose: () => void; restoreFocus?:()=>boolean; busy?: boolean; className?: string; children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLElement | null>(null);
  const pointerTrigger = useRef<HTMLElement | null>(null);
  const [visited, setVisited] = useState(open);
  const heading = useId();
  useEffect(() => {
    // Safari does not focus a clicked button; remember the actual activator.
    const pointer = (event: PointerEvent) => {pointerTrigger.current = event.target instanceof Element ? event.target.closest<HTMLElement>('button, [role="button"]') : null;};
    const keyboard = () => {pointerTrigger.current = null;};
    document.addEventListener('pointerdown', pointer, true);
    document.addEventListener('keydown', keyboard, true);
    return () => {document.removeEventListener('pointerdown', pointer, true); document.removeEventListener('keydown', keyboard, true);};
  }, []);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open) {
      setVisited(true);
      const candidate = pointerTrigger.current;
      trigger.current = candidate?.isConnected && !dialog.contains(candidate) ? candidate : document.activeElement instanceof HTMLElement ? document.activeElement : null;
      pointerTrigger.current = null;
      if (!dialog.open) dialog.showModal();
      const overflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {document.body.style.overflow = overflow;};
    }
    if (dialog.open) dialog.close();
  }, [open]);
  return <dialog ref={ref} className={'notes-dialog ' + className} aria-labelledby={heading}
    onKeyDown={event => {
      if (event.key !== 'Tab') return;
      const targets = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button, input:not([type="hidden"]), select, textarea, summary, a[href], [tabindex]')).filter(element => element.tabIndex >= 0 && !element.matches(':disabled') && element.getClientRects().length);
      if (!targets.length) return;
      event.preventDefault();
      const index = targets.indexOf(document.activeElement as HTMLElement);
      targets[index < 0 ? event.shiftKey ? targets.length - 1 : 0 : (index + (event.shiftKey ? -1 : 1) + targets.length) % targets.length].focus({preventScroll: true});
    }}
    onCancel={event => {event.preventDefault(); if (!busy) onClose();}}
    onClose={() => {if(restoreFocus?.())return;if (trigger.current?.isConnected) trigger.current.focus({preventScroll: true});}}>
    <header className="notes-dialog-header"><h2 id={heading}>{title}</h2><button className="secondary" aria-label={`关闭${title}`} disabled={busy} onClick={onClose}>关闭 ×</button></header>
    <div className="notes-dialog-body">{visited && children}</div>
    {busy && <p className="hint notes-dialog-progress" role="status">正在处理，请稍候…</p>}
  </dialog>;
}
