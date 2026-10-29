import {useEffect, useRef, useState, type ReactNode} from "react";
import type {NoteSummary} from "../../api/client";
import {NotePreview} from "../../components/knowledge";
import {NotesDialog} from "./NotesDialog";
import {NoteReaderLibrary} from './NoteReaderLibrary';
import "./note-reader.css";

type ReadingSize = "small" | "standard" | "large";
type HeadingEntry = {index: number; level: number; label: string};
const TOC_LIMIT = 200;

function ReaderIcon({kind}: {kind: "book" | "expand" | "edit"}) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {kind === "book" ? <><path d="M12 5v15M3 4h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v15h-5a5 5 0 0 0-4 1 5 5 0 0 0-4-1H3Z"/></> : kind === "expand" ? <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/> : <><path d="m15 5 4 4M4 20l4-1L20 7a2.8 2.8 0 0 0-4-4L4 15Z"/><path d="M12 20h8"/></>}
  </svg>;
}

export function NoteReader({title, content, tags, path, noteId, token, notes, courseId = '', assetRevision = 0, disabled = false, notice, onNote, onEdit, sources}: {
  title: string; content: string; tags: string[]; path: string; noteId?: string;
  token: string; notes: NoteSummary[]; courseId?: string; assetRevision?: number; disabled?: boolean;
  notice?: string; onNote: (note: NoteSummary) => void; onEdit: () => void; sources?: ReactNode;
}) {
  const [size, setSize] = useState<ReadingSize>("standard");
  const [focused, setFocused] = useState(false);
  const [outlineTab,setOutlineTab]=useState<'notes'|'headings'>('notes');
  const [headings, setHeadings] = useState<HeadingEntry[]>([]);
  const [headingCount, setHeadingCount] = useState(0);
  const [activeHeading, setActiveHeading] = useState<number | null>(null);
  const sourceKey = noteId ?? "draft";
  const [sourceState, setSourceState] = useState({key: sourceKey, open: false, visited: false});
  const sourceOpen = sourceState.key === sourceKey && sourceState.open;
  const sourceVisited = sourceState.key === sourceKey && sourceState.visited;
  const [article, setArticle] = useState<HTMLElement | null>(null);
  const headingElements = useRef<HTMLElement[]>([]);
  const focusTrigger = useRef<HTMLButtonElement>(null);
  const titleElement = useRef<HTMLHeadingElement>(null);
  const previousNote = useRef(noteId);

  useEffect(() => {
    if (previousNote.current && previousNote.current !== noteId) {
      titleElement.current?.focus({preventScroll: true});
      titleElement.current?.scrollIntoView({block: 'start', behavior: 'auto'});
    }
    previousNote.current = noteId;
  }, [noteId]);

  useEffect(() => {
    const expire = () => setFocused(false);
    window.addEventListener("hustudy:notes-session-expired", expire);
    return () => window.removeEventListener("hustudy:notes-session-expired", expire);
  }, []);

  useEffect(() => {
    const body = article;
    if (!body) return;
    setActiveHeading(null);
    const collect = () => {
      // Read the rendered Markdown tree: fenced code and escaped hashes are not headings.
      const elements = Array.from(body.querySelectorAll<HTMLElement>("h1,h2,h3,h4,h5,h6"));
      headingElements.current = elements.slice(0, TOC_LIMIT);
      setHeadingCount(elements.length);
      const entries = headingElements.current.map((element, index) => {
        element.tabIndex = -1;
        const copy = element.cloneNode(true) as HTMLElement;
        // KaTeX includes both visual and accessible trees; keep one readable formula label.
        copy.querySelectorAll(".katex").forEach(formula => {
          formula.textContent = formula.querySelector("annotation")?.textContent ?? formula.textContent;
        });
        return {index, level: Number(element.tagName.slice(1)), label: (copy.textContent?.replace(/\s+/g, " ").trim() || "未命名标题").slice(0, 180)};
      });
      setHeadings(previous => previous.length === entries.length && previous.every((entry, index) => entry.level === entries[index].level && entry.label === entries[index].label) ? previous : entries);
    };
    collect();
    // Local math rendering may finish after the first layout. Never observe source/citation panels.
    const observer = new MutationObserver(collect);
    observer.observe(body, {childList: true, subtree: true, characterData: true});
    return () => observer.disconnect();
  }, [article, content, focused, noteId, assetRevision]);

  const jumpTo = (index: number) => {
    const target = headingElements.current[index];
    if (!target?.isConnected) return;
    setActiveHeading(index);
    target.focus({preventScroll: true});
    target.scrollIntoView({block: "start", behavior: "auto"});
  };

  const reader = <section className={`note-reader note-reader-size-${size}`} aria-label="笔记阅读模式">
    <div className="note-reader-toolbar">
      <span className="note-reader-mode"><ReaderIcon kind="book"/>阅读模式</span>
      <div className="note-reader-actions">
        <label className="note-reader-size-control"><span>字号</span><select aria-label="阅读字号" value={size} onChange={event => setSize(event.target.value as ReadingSize)}>
          <option value="small">小</option><option value="standard">标准</option><option value="large">大</option>
        </select></label>
        {focused ? <button type="button" className="secondary" onClick={() => setFocused(false)}><ReaderIcon kind="expand"/>退出专注</button> : <button ref={focusTrigger} type="button" className="secondary" disabled={disabled} onClick={() => setFocused(true)}><ReaderIcon kind="expand"/>专注阅读</button>}
        <button type="button" className="secondary" disabled={disabled} onClick={() => {setFocused(false); onEdit();}}><ReaderIcon kind="edit"/>返回编辑</button>
      </div>
    </div>
    {notice && <p className="note-reader-notice" role="status">{notice}</p>}
    <header className="note-reader-heading">
      <p className="note-reader-path">{path || "未归档"}</p>
      <h2 ref={titleElement} tabIndex={-1}>{title.trim() || "未命名笔记"}</h2>
      {tags.length > 0 && <ul className="note-reader-tags" aria-label="笔记标签">{tags.map((tag, index) => <li key={`${tag}-${index}`}>{tag}</li>)}</ul>}
    </header>
    <div className={`note-reader-layout${headings.length || focused ? " has-outline" : ""}`}>
      {(headings.length > 0 || focused) && <aside className="note-reader-outline">
        {focused&&<><div className="note-reader-directory-tabs" aria-label="阅读目录类型"><button aria-pressed={outlineTab==='notes'} onClick={()=>setOutlineTab('notes')}>全部笔记</button><button aria-pressed={outlineTab==='headings'} onClick={()=>setOutlineTab('headings')}>本篇目录</button></div><div hidden={outlineTab!=='notes'}><NoteReaderLibrary token={token} courseId={courseId} noteId={noteId} notes={notes} disabled={disabled} onNote={onNote}/></div></>}
        <details open hidden={focused&&outlineTab!=='headings'}>
          <summary>目录 <span>{headingCount}</span></summary>
          <nav aria-label="笔记目录"><ol>{headings.map(heading => <li key={heading.index} data-level={heading.level}>
            <button type="button" aria-current={activeHeading === heading.index ? "location" : undefined} onClick={() => jumpTo(heading.index)}>{heading.label}</button>
          </li>)}</ol></nav>
          {headingCount > TOC_LIMIT && <p className="note-reader-toc-limit">目录显示前 {TOC_LIMIT} 个标题，正文完整显示。</p>}
          {!headings.length&&<p className="hint">本篇没有Markdown标题。</p>}
        </details>
      </aside>}
      <div className="note-reader-paper">
        <article ref={setArticle} className="note-reader-content" aria-label="笔记阅读正文">
          {content.trim() ? <NotePreview key={assetRevision} content={content} token={token} notes={notes} onNote={note => {if (!disabled) onNote(note);}}/> : <p className="note-reader-empty">这篇笔记还没有正文，可以返回编辑添加内容。</p>}
        </article>
        {sources && <details className="note-reader-sources" open={sourceOpen} onToggle={event => {
          const open = event.currentTarget.open;
          setSourceState(previous => ({key: sourceKey, open, visited: open || (previous.key === sourceKey && previous.visited)}));
        }}><summary>资料引用</summary>{sourceVisited && sources}</details>}
      </div>
    </div>
  </section>;

  return <>
    {!focused && reader}
    <NotesDialog open={focused} title="专注阅读" onClose={() => setFocused(false)} className="note-reader-dialog" restoreFocus={() => {
      const trigger = focusTrigger.current;
      if (!trigger?.isConnected || trigger.disabled) return false;
      trigger.focus({preventScroll: true});
      return true;
    }}>{focused ? reader : null}</NotesDialog>
  </>;
}
