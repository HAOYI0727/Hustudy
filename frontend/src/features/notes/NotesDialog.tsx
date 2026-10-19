import {useEffect, useId, useRef, useState, type ReactNode} from 'react';

/** Keep completed imports and retry identities alive when a tool is closed. */
export function NotesDialog({open, title, onClose, busy = false, className = '', children}: {
  open: boolean; title: string; onClose: () => void; busy?: boolean; className?: string; children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLElement | null>(null);
  const [visited, setVisited] = useState(open);
  const heading = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open) {
      setVisited(true);
      trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      if (!dialog.open) dialog.showModal();
      const overflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {document.body.style.overflow = overflow;};
    }
    if (dialog.open) dialog.close();
  }, [open]);
  return <dialog ref={ref} className={'notes-dialog ' + className} aria-labelledby={heading}
    onCancel={event => {event.preventDefault(); if (!busy) onClose();}}
    onClose={() => {if (trigger.current?.isConnected) trigger.current.focus({preventScroll: true});}}>
    <header className="notes-dialog-header"><h2 id={heading}>{title}</h2><button className="secondary" aria-label={`关闭${title}`} disabled={busy} onClick={onClose}>关闭 ×</button></header>
    <div className="notes-dialog-body">{visited && children}</div>
    {busy && <p className="hint notes-dialog-progress" role="status">正在处理，请稍候…</p>}
  </dialog>;
}
