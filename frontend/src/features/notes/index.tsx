import { Icon } from "../../components/Icon";
import { CompactLibrary } from "../../components/CompactLibrary";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, Note, SourceCitation, Asset } from "../../api/client";
import { NotePreview } from "../../components/knowledge";
import { PageTitle, EmptyInline, ModuleStats } from "../../components/workspace";

type Props = { onSource: (versionId: string, chunkId: string) => void; initialNoteId?: string; token: string; courseId: string; onNotice: (s: string) => void; onError: (e: unknown) => void };
type Draft = { title: string; content: string };
type Conflict = { title: string; content: string; revision: number };
const templates = [
  { name: "概念学习", content: "## 学习目标\n\n## 概念与原理\n\n## 例子\n\n## 常见误区\n\n## 自测问题\n" },
  { name: "错题复盘", content: "## 原题与来源\n\n## 我的思路\n\n## 出错原因\n\n## 正确解法\n\n## 下次如何识别\n" },
  { name: "课前预习", content: "## 已知内容\n\n## 不理解的问题\n\n## 课堂核实\n\n## 课后总结\n" },
];

export function Notes({ token, courseId, onNotice, onError, initialNoteId, onSource }: Props) {
  const [opening, setOpening] = useState(!!initialNoteId);
  const [notes, setNotes] = useState<Note[]>([]);
  const [editing, setEditing] = useState<Note | null>(null);
  const [draft, setDraft] = useState<Draft>({ title: "", content: "" });
  const [search, setSearch] = useState("");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [preview, setPreview] = useState(false);
  const [citations, setCitations] = useState<SourceCitation[]>([]);
  const [backlinks, setBacklinks] = useState<Note[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("开始记录你的理解");
  const [paused, setPaused] = useState(false);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const lock = useRef(false);
  const loadedInitial = useRef<string | undefined>(undefined);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const dirty = draft.title !== (editing?.title || "") || draft.content !== (editing?.content || "");
  useEffect(() => { void api.assets(token,courseId).then(setAssets).catch(onError); }, [token,courseId]);
  const refresh = async () => setNotes(await api.notes(token, courseId));
  useEffect(() => {
    let active = true;
    void api.notes(token, courseId).then(async rows => {
      if (!active) return;
      setNotes(rows);
      if (!initialNoteId || loadedInitial.current === initialNoteId) return;
      if (!rows.some(row => row.id === initialNoteId)) throw new Error("这篇笔记已删除或不在当前课程");
      const note = await api.note(token, initialNoteId);
      if (active) { loadedInitial.current = initialNoteId; setEditing(note); setDraft({ title: note.title, content: note.content }); setStatus("已载入保存版本"); }
    }).catch(error => { if (active) onError(error); }).finally(() => { if (active) setOpening(false); });
    return () => { active = false; };
  }, [courseId, token, initialNoteId]);
  useEffect(() => {
    let active = true;
    setBacklinks([]); setCitations([]);
    if (editing) void api.citations(token, editing.id).then(rows => { if (active) setCitations(rows); }).catch(onError);
    if (editing) void api.backlinks(token, editing.id).then((rows) => { if (active) setBacklinks(rows); }).catch(onError);
    return () => { active = false; };
  }, [editing?.id, token]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty || busy) { event.preventDefault(); event.returnValue = ""; } };
    const navigate = (event: Event) => {
      if (busy || (dirty && !window.confirm("笔记尚未保存，确认放弃本地修改并离开？"))) event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    window.addEventListener("hustudy:before-navigate", navigate);
    return () => { window.removeEventListener("beforeunload", warn); window.removeEventListener("hustudy:before-navigate", navigate); };
  }, [dirty, busy]);

  const save = async () => {
    if (lock.current || !draft.title.trim() || !dirty || conflict) return;
    lock.current = true; setBusy(true); setStatus("正在保存…");
    const snapshot = { ...draft, course_id: courseId };
    try {
      const saved = editing
        ? await api.updateNote(token, editing.id, { ...snapshot, revision: editing.revision })
        : await api.createNote(token, snapshot);
      setEditing(saved); setPaused(false); setStatus("已保存到本地服务");
      setNotes((rows) => [saved, ...rows.filter((row) => row.id !== saved.id)]);
    } catch (error) {
      setPaused(true); setStatus("未保存 · 请处理后重试");
      if (error instanceof ApiError && error.status === 409 && error.details) {
        setConflict({ title: String(error.details.server_title || ""), content: String(error.details.server_content || ""), revision: Number(error.details.server_revision) });
      } else onError(error);
    } finally { lock.current = false; setBusy(false); }
  };
  useEffect(() => {
    if (!dirty || busy || paused || conflict || !draft.title.trim()) return;
    const timer = window.setTimeout(() => { void save(); }, 2000);
    return () => window.clearTimeout(timer);
  }, [draft, editing, busy, paused, conflict]);

  const open = async (note?: Note) => {
    if (lock.current) return;
    if (dirty && !window.confirm("当前有未保存内容。确认放弃这些修改并切换？")) return;
    lock.current = true; setBusy(true);
    try {
      const fresh = note ? await api.note(token, note.id) : null;
      setEditing(fresh); setDraft({ title: fresh?.title || "", content: fresh?.content || "" });
      setConflict(null); setPaused(false); setStatus(fresh ? "已载入保存版本" : "新笔记 · 填写标题后自动保存");
    } catch (error) { onError(error); } finally { lock.current = false; setBusy(false); }
  };
  const insert = (text: string) => {
    const start = textarea.current?.selectionStart ?? draft.content.length;
    const end = textarea.current?.selectionEnd ?? start;
    setDraft((value) => ({ ...value, content: value.content.slice(0, start) + text + value.content.slice(end) }));
    textarea.current?.focus();
  };
  const download = async () => {
    if (!editing || dirty) return;
    try {
      const content = await api.exportNote(token, editing.id);
      const url = URL.createObjectURL(new Blob([content], { type: "text/markdown;charset=utf-8" }));
      const link = document.createElement("a"); link.href = url; link.download = `note-${editing.id}.md`; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000); onNotice("已导出 Markdown；附件与来源清单需完整知识库导出支持");
    } catch (error) { onError(error); }
  };
  const filtered = notes.filter((note) => `${note.title}\n${note.content}`.toLowerCase().includes(search.toLowerCase()));
  const outgoing = [...draft.content.matchAll(/\[\[note:([0-9a-fA-F-]{36})(?:\|([^\]]+))?\]\]/g)];
  if (opening) return <div className="panel" role="status">正在打开指定笔记…</div>;
  return <div className="page">
    <PageTitle eyebrow="NOTE GRAPH / PERSONAL KNOWLEDGE" title="把理解写下来，让知识连接起来" text="使用学习模板整理思路，通过双链连接课程笔记。停止输入约 2 秒后自动保存。" />
    <ModuleStats items={[{label:"课程笔记",value:notes.length,hint:"已保存的知识积累"},{label:"当前出链",value:outgoing.length,hint:"正文中的笔记连接"},{label:"反向引用",value:backlinks.length,hint:"连接到当前笔记"}]} /><div className="knowledge-layout">
      <CompactLibrary className="panel knowledge-library" label="笔记列表与新建">
        <div className="panel-title"><h3>课程笔记</h3><span className="count-pill">{notes.length}</span></div>
        <input aria-label="搜索笔记" placeholder="搜索标题或正文…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button className="primary full" disabled={busy} onClick={() => void open()}><Icon name="plus" size={16}/>新建笔记</button>
        <div className="list">{filtered.map((note) => <button disabled={busy} className={`knowledge-item ${note.id === editing?.id ? "selected" : ""}`} key={note.id} onClick={() => void open(note)}><strong>{note.title}</strong><span>{note.content.slice(0, 70) || "尚未填写正文"}</span><small>保存版本 {note.revision}</small></button>)}</div>
        {!filtered.length && <EmptyInline text={search ? "未找到匹配笔记" : "从一个概念开始记录"} />}
      </CompactLibrary>
      <section className="panel knowledge-editor">
        <div className="panel-title"><h3>{editing ? "编辑笔记" : "新建笔记"}</h3><span className={`save-indicator ${dirty ? "unsaved" : ""}`} role="status"><Icon name={busy ? "refresh" : paused || conflict ? "info" : dirty ? "edit" : editing ? "check" : "notes"} size={13} className={busy ? "is-spinning" : ""}/>{busy ? "保存中…" : dirty && !paused ? "有修改待保存" : status}</span></div>
        <input className="title-input" aria-label="笔记标题" maxLength={240} placeholder="为这份理解起一个名字" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
        <div className="writing-toolbar" aria-label="笔记编辑工具"><button className="secondary" aria-pressed={preview} onClick={()=>setPreview(!preview)}>{preview ? "继续编辑" : "Markdown 预览"}</button><select aria-label="插入课程图片" value="" onChange={e=>{const asset=assets.find(a=>a.id===e.target.value);if(asset)insert(`\n![[asset:${asset.id}|${(asset.alt || asset.name || asset.original_filename).replace(/[\]\n]/g," ")}]]\n`);}}><option value="">插入课程图片…</option>{assets.map(a=><option key={a.id} value={a.id}>{a.name || a.alt || a.original_filename}</option>)}</select>
          <button className="secondary" onClick={() => insert("\n## 小节标题\n")}>H2 标题</button>
          <button className="secondary" onClick={() => insert("**重点**")}>B 重点</button>
          <button className="secondary" onClick={() => insert("\n- 待整理要点\n")}>列表</button>
          <select aria-label="插入笔记双链" value="" onChange={(e) => { const note = notes.find((row) => row.id === e.target.value); if (note) insert(`[[note:${note.id}|${note.title.replace(/[\]\n]/g, " ")}]]`); }}><option value="">插入笔记双链…</option>{notes.filter((row) => row.id !== editing?.id).map((row) => <option key={row.id} value={row.id}>{row.title}</option>)}</select>
        </div>
        {preview ? <NotePreview content={draft.content} token={token} notes={notes} onNote={note=>void open(note)}/> : <textarea ref={textarea} aria-label="Markdown 正文" className="knowledge-text" placeholder="记录概念、例子和未解决的问题…" value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} rows={18} />}
        <div className="editor-footer"><span className="hint">{Array.from(draft.content).length} 字符 · Markdown</span><button className="secondary" disabled={!editing || dirty || busy} onClick={() => void download()}><Icon name="download" size={15}/>导出 .md</button><button className="primary" disabled={busy || !dirty || !draft.title.trim() || !!conflict} onClick={() => { setPaused(false); void save(); }}><Icon name="check" size={15}/>立即保存</button></div>
        {paused && !conflict && <p role="alert">自动保存已暂停，本地内容仍在。检查连接后点击“立即保存”重试。</p>}
        {conflict && <section className="conflict-panel" role="alert"><h3>检测到另一处修改</h3><p>上方保留你的本地草稿。请先复制需要保留的内容，再选择载入服务端版本；不会自动覆盖任一版本。</p><strong>{conflict.title} · 版本 {conflict.revision}</strong><pre>{conflict.content}</pre><button className="secondary" onClick={() => { if (editing && window.confirm("确认载入服务端版本？上方本地草稿将被替换。")) { setEditing({ ...editing, ...conflict }); setDraft({ title: conflict.title, content: conflict.content }); setConflict(null); setPaused(false); setStatus("已载入服务端版本"); } }}>载入服务端版本</button></section>}
      </section>
      <aside className="knowledge-context">
        <section className="panel"><h3>资料来源</h3>{citations.map(c => <div className="citation-card" key={c.id}><span className="locator">{c.source_kind === "manual_transcript" ? "人工补录 · " : ""}{c.locator_type} {c.locator_value}</span><p>{c.quote}</p>{c.availability === "active" ? <button className="secondary" onClick={() => onSource(c.version_id,c.chunk_id)}>回到原文 ↗</button> : <small>来源当前不可用</small>}</div>)}{!citations.length && <EmptyInline text="在资料阅读中选择这篇笔记添加引用"/>}</section>
        <section className="panel"><h3>学习模板</h3><p className="hint">追加到正文，保留已有内容。</p>{templates.map((template) => <button key={template.name} className="template-card" onClick={() => setDraft((value) => ({ title: value.title || template.name, content: value.content + "\n" + template.content }))}><Icon name="notes" size={16}/><span>{template.name}</span><Icon name="plus" size={15}/></button>)}</section>
        <section className="panel"><h3>关联笔记</h3>{outgoing.map((match, index) => { const target = notes.find((note) => note.id === match[1]); return <button className="relation-link" disabled={!target || busy} key={`${match[1]}-${index}`} onClick={() => target && void open(target)}>↗ {target?.title || "目标已删除或不在当前课程"}</button>; })}{!outgoing.length && <EmptyInline text="插入双链，连接相关概念" />}<h4>被这些笔记引用</h4>{backlinks.map((note) => <button className="relation-link" key={note.id} disabled={busy} onClick={() => void open(note)}>↙ {note.title}</button>)}{!backlinks.length && <EmptyInline text="暂无反向链接" />}</section>
      </aside>
    </div>
  </div>;
}
