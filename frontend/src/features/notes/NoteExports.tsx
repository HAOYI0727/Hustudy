import { useEffect, useRef, useState } from "react";
import { api, Course, NoteSummary, NoteExport } from "../../api/client";

const labels: Record<string, string> = {QUEUED: "排队中", RUNNING: "正在打包", SUCCEEDED: "已完成", FAILED: "失败", CANCELLED: "已取消"};
export function NoteExports({token, notes, courseId, unsaved, onError, selection, onBusyChange, isOpen = true}: {token: string; notes: NoteSummary[]; courseId: string; unsaved: boolean; onError: (error: unknown) => void; selection?: {ids: string[]; version: number}; onBusyChange?: (busy: boolean) => void; isOpen?: boolean}) {
  const [rows, setRows] = useState<NoteExport[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {onBusyChange?.(busy);}, [busy, onBusyChange]);
  const expanded = isOpen;
  const [loaded, setLoaded] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  useEffect(() => {if (selection) setSelected(selection.ids);}, [selection]);
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("current");
  const [courses, setCourses] = useState<Course[]>([]);
  const requestId = useRef<{id: string; key: string} | null>(null);
  const lock = useRef(false);
  const active = rows.some(row => ["QUEUED", "RUNNING"].includes(row.job.status));
  const chosen = selected.filter(id => notes.some(note => note.id === id));
  const visible = notes.filter(note => (scope === "all" || (scope === "unclassified" ? !note.course_id : note.course_id === courseId)) && note.title.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  useEffect(() => {
    if (!expanded) return;
    let live = true;
    void api.courses(token).then(result => { if (live) setCourses(result); }).catch(error => { if (live) onError(error); });
    return () => { live = false; };
  }, [token, expanded]);
  useEffect(() => {
    if (!expanded) return;
    let live = true; let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await api.noteExports(token);
        if (!live) return;
        setRows(next); setLoaded(true);
        if (next.some(row => ["QUEUED", "RUNNING"].includes(row.job.status))) timer = window.setTimeout(poll, 2000);
      } catch (error) { if (live) onError(error); }
    };
    void poll();
    return () => { live = false; window.clearTimeout(timer); };
  }, [token, expanded, active, busy]);
  const perform = async (action: () => Promise<unknown>) => {
    if (lock.current) return;
    lock.current = true; setBusy(true);
    try { await action(); setRows(await api.noteExports(token)); setLoaded(true); }
    catch (error) { onError(error); }
    finally { lock.current = false; setBusy(false); }
  };
  const create = () => perform(async () => {
    const ids = [...chosen].sort();
    const key = JSON.stringify(ids);
    if (requestId.current?.key !== key) requestId.current = {id: crypto.randomUUID(), key};
    await api.createNoteExport(token, requestId.current.id, ids, true);
    requestId.current = null;
  });
  const download = (row: NoteExport) => perform(async () => {
    const blob = await api.downloadNoteExport(token, row.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = row.filename || `Hustudy-笔记知识库-${row.created_at.replace(/[:.]/g, "-")}.zip`; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  return <section className="panel note-export-panel" aria-label="知识库导出">
    <p className="hint">选择需要的笔记，按标题保存为 Markdown 文件。</p>
    {expanded && <>
      <div className="note-export-filters">
        <label>查找笔记<input aria-label="查找待导出笔记" value={query} onChange={event => setQuery(event.target.value)} placeholder="按标题查找…"/></label>
        <label>显示范围<select aria-label="导出列表范围" value={scope} onChange={event => setScope(event.target.value)}><option value="current">当前课程</option><option value="all">全部课程</option><option value="unclassified">未分类</option></select></label>
      </div>
      <div className="note-export-selection-actions"><button className="secondary" disabled={busy || !visible.length} onClick={() => setSelected(ids => [...new Set([...ids, ...visible.map(note => note.id)])])}>全选当前列表</button><button className="text-button" disabled={busy || !chosen.length} onClick={() => setSelected([])}>清空选择</button><strong aria-live="polite">已选择 {chosen.length} 篇</strong></div>
      <div className="note-export-picker" aria-label="待导出笔记">{visible.map(note => <label key={note.id} className="note-export-choice"><input type="checkbox" disabled={busy} checked={chosen.includes(note.id)} onChange={event => setSelected(ids => event.target.checked ? [...new Set([...ids, note.id])] : ids.filter(id => id !== note.id))}/><span><strong>{note.title}</strong><small>{courses.find(course => course.id === note.course_id)?.name || (note.course_id ? "课程笔记" : "未分类")}</small></span></label>)}{!visible.length && <p className="hint">没有匹配的已保存笔记。</p>}</div>
      <p className="hint">仅包含所选笔记和引用图片，保留笔记文件夹层级，未归档笔记放在根目录。图片集中保存在 images，跨目录链接自动转换，共用图片只存一份，同名自动加序号。请完整解压后阅读并保持目录结构。未选中的链接目标只保留文字说明。</p>
      {unsaved && <p role="status">请先保存或处理当前草稿，再生成包含最新内容的笔记包。</p>}
      <button className="primary" disabled={busy || active || unsaved || !loaded || !chosen.length || chosen.length > 2000} onClick={() => void create()}>导出所选笔记（{chosen.length}）</button>
      {chosen.length > 2000 && <p role="alert">每次最多导出2000篇，请分批选择。</p>}
      <button className="text-button" disabled={busy} onClick={() => void perform(async () => {})}>刷新导出记录</button>
      {active && <p role="status">正在准备笔记压缩包，可稍后回来下载。</p>}
      {!loaded && <p role="status">正在读取导出记录…</p>}
      {loaded && !rows.length && <p className="hint">尚无导出记录。</p>}
      <div className="note-export-list">{rows.map(row => <article className="note-export-item" key={row.id}>
        <div><strong>{labels[row.job.status] || row.job.status}</strong><span className="hint"> · {new Date(row.created_at).toLocaleString()}</span>
          {row.filename && <p className="note-export-filename">{row.filename}</p>}
          {row.layout !== "simple" && <p className="hint">旧版导出：可能使用编号或包含来源清单。请重新勾选导出，获取简洁的标题命名文件。</p>}
          {row.job.status === "SUCCEEDED" && <p>{row.counts.notes} 篇笔记 · {row.counts.assets} 张图片 · {(row.size_bytes / 1024).toFixed(1)} KB</p>}
          {row.job.error && <p role="alert">{row.job.error}</p>}
          {row.availability === "unavailable" && <p>包内来源或文件已不可用，请重新导出。</p>}
        </div>
        <div className="note-export-actions">
          {row.availability === "active" && <button className="secondary" disabled={busy} onClick={() => void download(row)}>下载 ZIP</button>}
          {row.job.status === "FAILED" && row.job.attempt_count < row.job.max_attempts && <button className="secondary" disabled={busy || active} onClick={() => void perform(() => api.retryNoteExport(token, row.id))}>重试导出</button>}
          <button className="text-button" disabled={busy} onClick={() => { if (window.confirm("移除此导出记录？正在处理的任务会取消，笔记和图片会保留。")) void perform(() => api.removeNoteExport(token, row.id)); }}>移除记录</button>
        </div>
      </article>)}</div>
    </>}
  </section>;
}
