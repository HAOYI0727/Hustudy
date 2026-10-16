import { CompactLibrary } from "../../components/CompactLibrary";
import { PreviewStatus } from "./PreviewStatus";
import { FormEvent, lazy, Suspense, useEffect, useRef, useState } from "react";
import { api, ApiError, Chunk, DocumentItem, Job, MaterialReference, Note, Version } from "../../api/client";
import { AssetLibrary } from "./AssetLibrary";
import { Icon } from "../../components/Icon";
import { Transcripts } from "./Transcripts";
import { MaterialExports } from "./MaterialExports";
import { PageTitle, Status, EmptyInline, EmptyState, ModuleStats } from "../../components/workspace";

const OfficeReader = lazy(() => import("./OfficeReader"));
const PdfReader = lazy(() => import("./PdfReader"));
type Target = { documentId: string; versionId: string; chunkId: string; previewPage?: number };
type Props = { initialTarget?: Target; token: string; courseId: string; onNote: (id: string) => void; onNotice: (s: string) => void; onError: (e: unknown) => void };
const sizeLabel = (bytes: number) => bytes < 1024 * 1024 ? Math.max(1, Math.round(bytes / 1024)) + " KB" : (bytes / 1024 / 1024).toFixed(1) + " MB";
const timeLabel = (value: string) => new Date(value).toLocaleDateString("zh-CN", { month: "short", day: "numeric" });

function Highlight({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const lower = text.toLocaleLowerCase(), key = query.trim().toLocaleLowerCase();
  const parts = []; let cursor = 0, position = lower.indexOf(key);
  while (position >= 0) {
    parts.push(text.slice(cursor, position), <mark key={position}>{text.slice(position, position + key.length)}</mark>);
    cursor = position + key.length; position = lower.indexOf(key, cursor);
  }
  parts.push(text.slice(cursor)); return <>{parts}</>;
}
export function Materials({ token, courseId, onNote, onNotice, onError, initialTarget }: Props) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [file, setFile] = useState<File>();
  const [filter, setFilter] = useState("");
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [sort, setSort] = useState("recent");
  const [docOffset, setDocOffset] = useState(0), [jobOffset, setJobOffset] = useState(0);
  const [docInfo, setDocInfo] = useState({total:0, stats:{} as Record<string, number>, categories:[] as string[], tags:[] as string[]});
  const [jobInfo, setJobInfo] = useState({total:0, pending_count:0});
  const [selected, setSelected] = useState<Chunk[]>([]);
  const [active, setActive] = useState<DocumentItem | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [versionId, setVersionId] = useState("");
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [fontSize, setFontSize] = useState(16);
  const [previewOpenFailed,setPreviewOpenFailed] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [assetRefresh, setAssetRefresh] = useState(0);
  const [previewPage, setPreviewPage] = useState(1);
  const [transcriptRequest,setTranscriptRequest] = useState<{page:number;serial:number}>();
  const [view, setView] = useState("text");
  const [targetNote, setTargetNote] = useState("");
  const [uploadMode, setUploadMode] = useState("new");
  const [dragging, setDragging] = useState(false);
  const [focused, setFocused] = useState(false);
  const [readerQuery, setReaderQuery] = useState("");
  const [references, setReferences] = useState<MaterialReference[]>([]);
  const [referencesFailed, setReferencesFailed] = useState(false);
  const [referencesLoading, setReferencesLoading] = useState(false);
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftCategory, setDraftCategory] = useState("");
  const [draftTags, setDraftTags] = useState("");
  const [jobFilter, setJobFilter] = useState("all");
  const sequence = useRef(0), listSequence = useRef(0), refSequence = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const alive = useRef(true);
  const openedInitial = useRef(false);
  const rebuildRequest = useRef<{version: string; id: string} | null>(null);
  const currentVersion = versions.find(row => row.id === versionId);
  const officeKind = currentVersion?.original_filename.toLowerCase().endsWith(".pptx") ? "pptx" : currentVersion?.original_filename.toLowerCase().endsWith(".docx") ? "docx" : undefined;
  const nativePdf = currentVersion?.original_filename.toLowerCase().endsWith(".pdf");
  const categories = docInfo.categories;
  const tags = docInfo.tags;
  const listKey = JSON.stringify([filter,category,tag,stateFilter,sort,docOffset,jobOffset,jobFilter]);
  const lastListKey = useRef(listKey);
  const currentListKey = useRef(listKey); currentListKey.current = listKey;
  const parsedTags = Array.from(new Set(draftTags.split(/[,，]/).map(s => s.trim()).filter(Boolean)));
  const metadataDirty = !!active && (draftName !== active.name || draftCategory !== active.category || draftTags !== active.tags.join("，"));
  const canLeave = () => !metadataDirty || window.confirm("资料整理尚未保存，确定放弃这次改名或标签修改吗？");

  const load = async () => {
    const generation = ++listSequence.current;
    const requestedKey = listKey;
    try {
      const [page, queue, notebook] = await Promise.all([api.documentPage(token, courseId, {q:filter,category,tag,state:stateFilter,sort,offset:docOffset,limit:12}), api.jobPage(token, courseId, jobFilter, jobOffset), api.notes(token, courseId)]);
      if (alive.current && generation === listSequence.current && requestedKey === currentListKey.current) {
        setDocuments(page.items); setJobs(queue.items); setDocInfo(page); setJobInfo(queue); setNotes(notebook); setLoadFailed(false);
        if (docOffset > 0 && !page.items.length) setDocOffset(page.total ? Math.floor((page.total-1)/12)*12 : 0);
        if (jobOffset > 0 && !queue.items.length) setJobOffset(queue.total ? Math.floor((queue.total-1)/10)*10 : 0);
      }
      return page.items;
    } catch (error) { if (alive.current && generation === listSequence.current && requestedKey === currentListKey.current) setLoadFailed(true); throw error; }
    finally { if (alive.current && generation === listSequence.current && requestedKey === currentListKey.current) setLoading(false); }
  };
  const openDocument = async (doc: DocumentItem, target?: Target, bypassGuard = false) => {
    if (!bypassGuard && !window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable:true}))) return;
    if (!bypassGuard && !canLeave()) return;
    const current = ++sequence.current;
    setPreviewOpenFailed(false);
    setActive(doc); setSelected([]); setPreviewUrl(""); setView("text"); setReading(true); setVersions([]); setVersionId(""); setReaderQuery("");
    setDraftName(doc.name); setDraftCategory(doc.category); setDraftTags(doc.tags.join("，")); setMetadataOpen(false);
    setPreviewPage(target?.previewPage || 1);
    try {
      const list = await api.versions(token, doc.id);
      const chosen = target?.versionId || list[0]?.id;
      const rows = chosen ? await api.chunks(token, chosen) : [];
      if (current === sequence.current && alive.current) {
        setVersions(list); setVersionId(chosen || ""); setSelected(rows);
        if (target?.previewPage && chosen) {
          const blob = await api.preview(token, chosen);
          if (current === sequence.current && alive.current) { setPreviewUrl(URL.createObjectURL(blob)); setView("pdf"); }
        }
      }
    } catch (reason) { if (current === sequence.current && alive.current) onError(reason); }
    finally { if (current === sequence.current && alive.current) setReading(false); }
  };
  const loadReferences = async (id: string) => {
    const current = ++refSequence.current;
    setReferencesLoading(true); setReferencesFailed(false); setReferences([]);
    try { const rows = await api.materialReferences(token, id); if (alive.current && current === refSequence.current) setReferences(rows); }
    catch { if (alive.current && current === refSequence.current) setReferencesFailed(true); }
    finally { if (alive.current && current === refSequence.current) setReferencesLoading(false); }
  };
  useEffect(() => {
    alive.current = true;
    void load().then(async () => {
      if (!alive.current || !initialTarget || openedInitial.current) return;
      const doc = await api.document(token, initialTarget.documentId);
      if (alive.current && !openedInitial.current) { openedInitial.current = true; void openDocument(doc, initialTarget, true); }
    }).catch(onError);
    return () => { alive.current = false; sequence.current++; listSequence.current++; refSequence.current++; };
  }, [courseId, token]);
  useEffect(() => {
    if (lastListKey.current === listKey) return;
    lastListKey.current = listKey;
    setLoading(true);
    const timer = window.setTimeout(() => { void load().catch(onError); }, 180);
    return () => window.clearTimeout(timer);
  }, [listKey]);
  useEffect(() => {
    if (!jobInfo.pending_count) return;
    const timer = window.setTimeout(() => { void load().catch(onError); }, 2000);
    return () => window.clearTimeout(timer);
  }, [jobs, jobInfo.pending_count, listKey]);
  useEffect(() => {
    if (!active) return;
    const current = sequence.current;
    void api.versions(token, active.id).then(list => {
      if (alive.current && current === sequence.current) {
        setVersions(list);
        if (list.find(v => v.id === versionId)?.parse_status === "SUCCEEDED" && !selected.length && !reading) {
          // Background completion must not reset the user's native/PDF reading mode.
          void api.chunks(token,versionId).then(rows => {
            if(alive.current && current===sequence.current)setSelected(rows);
          }).catch(onError);
        }
      }
    }).catch(onError);
  }, [jobs]);
  useEffect(() => { if (versionId) void loadReferences(versionId); else { refSequence.current++; setReferences([]); setReferencesFailed(false); setReferencesLoading(false); } }, [versionId]);
  useEffect(() => {
    const navigate = (event: Event) => { if (!canLeave()) event.preventDefault(); };
    const unload = (event: BeforeUnloadEvent) => { if (metadataDirty) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("hustudy:before-navigate", navigate);
    window.addEventListener("beforeunload", unload);
    return () => { window.removeEventListener("hustudy:before-navigate", navigate); window.removeEventListener("beforeunload", unload); };
  }, [metadataDirty]);
  useEffect(() => {
    if (initialTarget && selected.some(chunk => chunk.id === initialTarget.chunkId)) scrollToChunk(initialTarget.chunkId);
  }, [selected, reading]);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  const scrollToChunk = (id: string) => document.getElementById("chunk-" + id)?.scrollIntoView({ block: "center", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  const choose = (picked?: File) => {
    setDragging(false); if (!picked || busy) return;
    if (!/\.(pptx|pdf|docx|md|markdown|txt)$/i.test(picked.name) || !picked.size || picked.size > 20 * 1024 * 1024) {
      setFile(undefined); if (input.current) input.current.value = "";
      onError(new Error("请选择非空、≤20 MiB 的 PPTX/PDF/DOCX/Markdown/TXT 文件")); return;
    }
    setFile(picked);
  };
  const upload = async (event: FormEvent) => {
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable:true}))) { event.preventDefault(); return; }
    event.preventDefault(); if (!file || busy || !canLeave()) return; setBusy(true);
    try {
      const job = uploadMode === "version" && active ? await api.uploadVersion(token, active.id, file) : await api.uploadDocument(token, courseId, file);
      setFile(undefined); if (input.current) input.current.value = "";
      await load(); const version = await api.version(token, job.resource_id);
      const document = await api.document(token, version.document_id);
      if (document && alive.current) await openDocument(document, { documentId: document.id, versionId: version.id, chunkId: "" }, true);
      onNotice(job.status === "SUCCEEDED" ? "内容已存在，已打开原有版本" : "资料已保存，正在等待解析；状态会自动更新");
    } catch (reason) { onError(reason); } finally { if (alive.current) setBusy(false); }
  };
  const readVersion = async (id: string) => {
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable:true}))) return;
    setPreviewPage(1);
    const current = ++sequence.current; setVersionId(id); setSelected([]); setPreviewUrl(""); setView("text"); setReading(true); setReaderQuery("");
    try { const rows = await api.chunks(token, id); if (current === sequence.current && alive.current) setSelected(rows); }
    catch (reason) { if (current === sequence.current && alive.current) onError(reason); }
    finally { if (current === sequence.current && alive.current) setReading(false); }
  };
  const saveMetadata = async (event: FormEvent) => {
    event.preventDefault(); if (!active || busy) return;
    if (!draftName.trim() || parsedTags.length > 12 || parsedTags.some(t => t.length > 32)) { onError(new Error("请填写资料名称；标签最多 12 个，每个不超过 32 字")); return; }
    const payload: {name?: string; category?: string; tags?: string[]} = {};
    if (draftName !== active.name) payload.name = draftName.trim();
    if (draftCategory !== active.category) payload.category = draftCategory.trim() || "未分类";
    if (draftTags !== active.tags.join("，")) payload.tags = parsedTags;
    setBusy(true);
    try {
      const updated = await api.updateDocument(token, active.id, payload);
      if (alive.current) { setActive(updated); setDraftName(updated.name); setDraftCategory(updated.category); setDraftTags(updated.tags.join("，")); }
      await load(); onNotice("资料整理已保存，原有版本与引用保持有效");
    } catch (reason) { onError(reason); } finally { if (alive.current) setBusy(false); }
  };
  const showPreview = async () => {
    const current = sequence.current; setBusy(true); setPreviewOpenFailed(false);
    try { const blob = await api.preview(token, versionId); if (current === sequence.current && alive.current) { setPreviewUrl(URL.createObjectURL(blob)); setView("pdf"); } }
    catch (reason) { if (current === sequence.current && alive.current) {setPreviewOpenFailed(true);onError(reason);} }
    finally { if (alive.current) setBusy(false); }
  };
  const previewAt = async (page:number) => { setPreviewPage(page); await showPreview(); };
  const refreshTranscripts = async () => {
    setAssetRefresh(value => value + 1);
    const version = versionId, current = sequence.current;
    const rows = await api.chunks(token, version);
    if (alive.current && current === sequence.current) setSelected(rows);
    await load(); await loadReferences(version);
  };
  const download = async () => {
    try { const blob = await api.original(token, versionId); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = currentVersion?.original_filename || "document"; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); }
    catch (reason) { onError(reason); }
  };
  const remove = async () => {
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable:true}))) return;
    if (!active || !canLeave() || !window.confirm("删除这份资料及其全部版本？已有引用将显示不可用，原文和文件将无法读取。")) return;
    setBusy(true);
    try { await api.deleteDocument(token, active.id); sequence.current++; setActive(null); setVersions([]); setVersionId(""); setSelected([]); setPreviewUrl(""); setUploadMode("new"); setFocused(false); setAssetRefresh(s => s + 1); await load(); onNotice("资料已删除，引用已标记不可用"); }
    catch (reason) { onError(reason); } finally { if (alive.current) setBusy(false); }
  };
  const cite = async (chunk: Chunk) => {
    if (!targetNote || busy) return; setBusy(true);
    const highlighted = window.getSelection()?.toString().trim();
    const quote = highlighted && chunk.text.includes(highlighted) ? highlighted : chunk.text.slice(0, 500);
    try { await api.citation(token, targetNote, { version_id: chunk.version_id, chunk_id: chunk.id, quote }); await loadReferences(chunk.version_id); onNotice("原文引用已添加到笔记，关联列表已更新"); }
    catch (reason) { onError(reason); } finally { if (alive.current) setBusy(false); }
  };
  const retry = async (job: Job) => {
    setBusy(true);
    try { const result = await api.retryJob(token, job.id); await load(); onNotice(result.status === "RUNNING" ? "任务已经在处理中" : "任务已重新入队"); }
    catch (reason) { onError(reason); } finally { if (alive.current) setBusy(false); }
  };
  const cancel = async (job: Job) => {
    if (busy || !window.confirm("取消这项处理？已保存资料和引用保留。后台处理可能稍后结束，取消后的结果不会写入；可在尝试上限内恢复。")) return;
    setBusy(true);
    try { await api.cancelJob(token, job.id); await load(); onNotice("任务已取消，资料与引用保留"); }
    catch (reason) {onError(reason);} finally {if (alive.current) setBusy(false);}
  };
  const rebuild = async () => {
    if (!versionId || busy || !window.confirm("重建当前版本的关键词索引？原文与引用不变；重建期间原提取正文暂不参与检索，已确认人工文字仍可查找。")) return;
    if (rebuildRequest.current?.version !== versionId) rebuildRequest.current = {version: versionId, id: crypto.randomUUID()};
    setBusy(true);
    try { const result = await api.reindexVersion(token, versionId, rebuildRequest.current.id); rebuildRequest.current = null; await load(); onNotice(result.status === "SUCCEEDED" ? "索引重建已完成" : ["FAILED", "CANCELLED"].includes(result.status) ? "重建记录已失败或取消，请在处理记录中查看并恢复" : "索引重建已入队，可在处理记录中查看"); }
    catch (reason) {if (reason instanceof ApiError && reason.status > 0 && reason.status < 500) rebuildRequest.current = null; onError(reason);}
    finally {if (alive.current) setBusy(false);}
  };
  const clearFilters = () => { setDocOffset(0); setFilter(""); setCategory(""); setTag(""); setStateFilter("all"); };
  const visible = documents;
  const shownChunks = selected.filter(chunk => (chunk.text + " " + chunk.locator_value).toLocaleLowerCase().includes(readerQuery.trim().toLocaleLowerCase()));
  const shownJobs = jobs;
  const linkedNotes = new Set(references.map(ref => ref.note_id));
  const pending = jobInfo.pending_count;

  return <div className={"page materials-page" + (focused ? " reading-focused" : "")}>
    <PageTitle eyebrow="MATERIAL HUB / READ & DISCOVER" title="每一份资料，都是理解的起点" text="整理章节与标签，读懂原文，再把资料连到自己的知识笔记。"/>
    <ModuleStats items={[{ label: "课程资料", value: docInfo.stats.total || 0, hint: "在当前课程积累" }, { label: "可检索", value: docInfo.stats.ready || 0, hint: "原文索引或已确认人工补录" }, { label: "处理中", value: pending, hint: pending ? "全部页面任务 · 后台更新" : "可以开始阅读与整理" }]}/>
    <div className="reading-layout">
      <CompactLibrary className="panel material-library" label="资料库与上传">
        <div className="panel-title"><h3><Icon name="folder"/>资料库</h3><button className="icon-button secondary" title="刷新资料与处理状态" aria-label="刷新资料与处理状态" disabled={loading || busy} onClick={() => void load().catch(onError)}><Icon name="refresh"/></button></div>
        <form className={"upload-zone compact-upload material-upload" + (dragging ? " is-dragging" : "")} onSubmit={upload} onDragOver={e => { e.preventDefault(); if (!busy) setDragging(true); }} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false); }} onDrop={e => { e.preventDefault(); choose(e.dataTransfer.files[0]); }}>
          <select aria-label="上传方式" value={uploadMode} disabled={busy} onChange={e => setUploadMode(e.target.value)}><option value="new">导入新资料</option><option value="version" disabled={!active}>为选中资料添加新版本</option></select>
          <span className="material-upload-symbol"><Icon name={file ? "file" : "upload"} size={26}/></span>
          <strong>{file?.name || "把课件放进知识库"}</strong>
          <small>{file ? sizeLabel(file.size) + " · 已准备上传" : "拖放文件，或点击下方按钮选择"}</small>
          <input ref={input} className="sr-only" aria-label="选择课程文件" type="file" accept=".pptx,.pdf,.docx,.md,.markdown,.txt" disabled={busy} onChange={e => choose(e.target.files?.[0])}/>
          <div className="upload-actions"><button type="button" className="secondary" disabled={busy} onClick={() => input.current?.click()}><Icon name="folder" size={16}/>{file ? "换一份" : "选择文件"}</button>{file && <button type="button" className="icon-button secondary" aria-label="取消所选文件" disabled={busy} onClick={() => { setFile(undefined); if (input.current) input.current.value = ""; }}><Icon name="close" size={16}/></button>}</div>
          <button className="primary" disabled={!file || busy || (uploadMode === "version" && !active)}><Icon name={busy ? "refresh" : "upload"} className={busy ? "is-spinning" : ""}/>{busy ? "正在处理…" : uploadMode === "version" ? "保存为新版本" : "上传并开始整理"}</button>
          <small>PPTX / PDF / DOCX / MD / TXT · ≤20 MiB</small>
        </form>
        <div className="material-list-filters">
          <div className="input-with-icon"><Icon name="search" size={16}/><input aria-label="筛选资料名称或标签" placeholder="查找名称、文件或标签…" value={filter} onChange={e => { setDocOffset(0); setFilter(e.target.value); }}/>{filter && <button className="icon-button" aria-label="清空名称筛选" onClick={() => { setDocOffset(0); setFilter(""); }}><Icon name="close" size={14}/></button>}</div>
          <div className="filter-pair"><select aria-label="按资料分类筛选" value={category} onChange={e => { setDocOffset(0); setCategory(e.target.value); }}><option value="">全部分类</option>{categories.map(value => <option key={value}>{value}</option>)}</select><select aria-label="按资料标签筛选" value={tag} onChange={e => { setDocOffset(0); setTag(e.target.value); }}><option value="">全部标签</option>{tags.map(value => <option key={value}>{value}</option>)}</select></div>
          <div className="filter-pair"><select aria-label="按处理状态筛选" value={stateFilter} onChange={e => { setDocOffset(0); setStateFilter(e.target.value); }}><option value="all">全部状态</option><option value="ready">可检索</option><option value="processing">处理中</option><option value="failed">需要处理</option></select><select aria-label="资料排序" value={sort} onChange={e => { setDocOffset(0); setSort(e.target.value); }}><option value="recent">最近更新</option><option value="name">名称顺序</option><option value="size">文件大小</option></select></div>
        </div>
        <div className="library-result-label"><span>匹配 {docInfo.total} / {docInfo.stats.total || 0} 份资料</span>{(filter || category || tag || stateFilter !== "all") && <button className="text-button" onClick={clearFilters}>清除筛选</button>}</div>
        {loading ? <div className="material-loading" role="status"><Icon name="refresh" className="is-spinning"/>正在加载课程资料…</div> : loadFailed ? <div className="inline-retry" role="alert">资料加载未完成<button className="secondary" onClick={() => void load().catch(onError)}>重新加载</button></div> : <div className="list material-document-list">{visible.map(doc => {
          const type = doc.original_filename.split(".").pop()?.toLowerCase() || "file";
          return <button className={"document-row material-document " + (active?.id === doc.id ? "selected-document" : "")} aria-pressed={active?.id === doc.id} key={doc.id} disabled={busy} onClick={() => void openDocument(doc)}>
            <span className={"file-icon file-type-" + type}><Icon name="file" size={22}/><small>{type.toUpperCase()}</small></span>
            <span className="row-main"><strong>{doc.name}</strong><small>{doc.category} · v{doc.latest_version_no || 1} · {sizeLabel(doc.size_bytes)}</small><span className="document-tags">{doc.tags.slice(0, 3).map(value => <span key={value}>{value}</span>)}{doc.tags.length > 3 && <span>＋{doc.tags.length - 3}</span>}</span><span className="document-bottom"><Status value={doc.parse_status || "QUEUED"}/>{!!doc.confirmed_transcript_count && <span className="manual-count">补录 {doc.confirmed_transcript_count} 页</span>}<time dateTime={doc.updated_at}>{timeLabel(doc.updated_at)}</time></span></span>
          </button>;
        })}</div>}
        <nav className="catalogue-pages" aria-label="资料分页"><button className="secondary" disabled={loading || docOffset===0} onClick={() => setDocOffset(Math.max(0,docOffset-12))}>上一页</button><span role="status">{Math.floor(docOffset/12)+1} / {Math.max(1,Math.ceil(docInfo.total/12))} 页</span><button className="secondary" disabled={loading || docOffset+12>=docInfo.total} onClick={() => setDocOffset(docOffset+12)}>下一页</button></nav>
        {!loading && !loadFailed && !visible.length && <EmptyInline text={documents.length ? "没有匹配资料，试试清除筛选" : "从第一份课件开始积累"}/>}
      </CompactLibrary>
      <section className="panel reader-workspace">
        <div className="panel-title reader-title"><div><p className="eyebrow">READING DESK</p><h3>{active?.name || "留一张桌子，给新的理解"}</h3></div><div className="reading-tools"><button title="减小字号" aria-label="减小阅读字号" className="icon-button secondary" disabled={fontSize <= 14} onClick={() => setFontSize(s => s - 1)}>A−</button><span className="reader-font-size">{fontSize}</span><button title="增大字号" aria-label="增大阅读字号" className="icon-button secondary" disabled={fontSize >= 24} onClick={() => setFontSize(s => s + 1)}>A＋</button><button title={focused ? "返回完整工作台" : "展开专注阅读"} aria-label={focused ? "返回完整工作台" : "展开专注阅读"} aria-pressed={focused} className="icon-button secondary" onClick={() => setFocused(s => !s)}><Icon name={focused ? "collapse" : "expand"}/></button></div></div>
        {active && <>
          <div className="material-toolbar reader-primary-actions"><select aria-label="资料版本" value={versionId} disabled={busy || reading} onChange={e => void readVersion(e.target.value)}>{versions.map(v => <option value={v.id} key={v.id}>v{v.version_no} · {v.original_filename}</option>)}</select><button className="secondary" disabled={!versionId || busy} onClick={() => void download()}><Icon name="download" size={16}/>原件</button>{officeKind && <button className={"secondary "+(view==="native"?"button-selected":"")} disabled={busy} onClick={() => setView("native")} title="直接读取原文件，无需等待PDF转换"><Icon name="preview" size={16}/>{officeKind==="pptx"?"PPT 预览":"Word 预览"}</button>}{(officeKind || nativePdf) && <button className="secondary" disabled={currentVersion?.preview_status !== "SUCCEEDED" || busy} onClick={() => void showPreview()} title={currentVersion?.preview_status !== "SUCCEEDED" ? "兼容预览处理后可打开；可先使用原格式或文本阅读" : "打开按页预览"}><Icon name="preview" size={16}/>{officeKind?"兼容预览（PDF）":"PDF 预览"}</button>}<button className="secondary" disabled={!versionId || busy || reading || currentVersion?.index_status === "QUEUED" || currentVersion?.index_status === "RUNNING" || !selected.length} onClick={() => void rebuild()} title="重建当前版本关键词索引，不修改原文或引用"><Icon name="refresh" size={16}/>重建索引</button><button className={"secondary " + (metadataOpen ? "button-selected" : "")} aria-expanded={metadataOpen} onClick={() => setMetadataOpen(s => !s)}><Icon name="edit" size={16}/>整理</button></div>
          <div className="material-statuses"><span>解析 <Status value={currentVersion?.parse_status || "QUEUED"}/></span><span>索引 <Status value={currentVersion?.index_status || "PENDING"}/></span><span>{officeKind?"兼容 PDF":"预览"} <Status value={currentVersion?.preview_status || "PENDING"}/></span></div>
          {metadataOpen && <form className="material-metadata" onSubmit={saveMetadata}><div className="metadata-heading"><h4><Icon name="tag"/>整理这份资料</h4><span className={metadataDirty ? "unsaved-indicator" : "hint"}>{metadataDirty ? "有未保存的修改" : "已保存"}</span></div><label>资料名称<input required maxLength={240} value={draftName} onChange={e => setDraftName(e.target.value)} disabled={busy}/></label><div className="metadata-fields"><label>分类<input list="material-categories" maxLength={40} placeholder="例如：核心章节" value={draftCategory} onChange={e => setDraftCategory(e.target.value)} disabled={busy}/><datalist id="material-categories">{categories.map(value => <option value={value} key={value}/>)}</datalist></label><label>标签<input value={draftTags} onChange={e => setDraftTags(e.target.value)} placeholder="进程，期末，重点" disabled={busy}/></label></div><p className="hint">逗号分隔，最多 12 个标签；改名不会改变原文版本和引用。</p><div className="metadata-actions"><button className="primary" disabled={!metadataDirty || busy || !draftName.trim()}><Icon name="check" size={16}/>保存整理</button><button type="button" className="secondary" disabled={!metadataDirty || busy} onClick={() => { setDraftName(active.name); setDraftCategory(active.category); setDraftTags(active.tags.join("，")); }}>撤销修改</button><button type="button" className="text-button danger" disabled={busy} onClick={() => void remove()}><Icon name="trash" size={15}/>删除资料</button></div></form>}
          {currentVersion?.parse_error && <p className="dashboard-warning" role="alert"><Icon name="info" size={16}/>{currentVersion.parse_error}</p>}{currentVersion && (officeKind ? <details className="native-compatibility-status"><summary><Icon name="info" size={14}/>兼容 PDF 状态与修复</summary><PreviewStatus key={currentVersion.id} token={token} version={currentVersion} openFailed={previewOpenFailed} onQueued={load} onError={onError} onNotice={onNotice}/></details> : <PreviewStatus key={currentVersion.id} token={token} version={currentVersion} openFailed={previewOpenFailed} onQueued={load} onError={onError} onNotice={onNotice}/>)}
          {currentVersion && <div className="version-caption"><Icon name="clock" size={14}/><span>导入于 {timeLabel(currentVersion.created_at)} · {sizeLabel(currentVersion.size_bytes)} · {versions.length} 个版本</span><span className="metadata-chips"><span>{active.category}</span>{active.tags.map(t => <span key={t}>{t}</span>)}</span></div>}
          <div className="citation-toolbar"><Icon name="link" size={17}/><select aria-label="引用到笔记" value={targetNote} onChange={e => setTargetNote(e.target.value)}><option value="">选择接收引用的笔记…</option>{notes.map(n => <option key={n.id} value={n.id}>{n.title}</option>)}</select><small>{notes.length ? "选中原文后引用，或保存片段前 500 字" : "先在知识笔记创建一篇笔记，再回到这里引用"}</small></div>
        </>}
        {view === "native" && officeKind ? <><button className="secondary" onClick={() => setView("text")}><Icon name="list" size={16}/>返回文本与引用</button><Suspense fallback={<p className="material-loading" role="status">正在打开原格式阅读器…</p>}><OfficeReader key={versionId} token={token} versionId={versionId} kind={officeKind} name={active?.name || "课程资料"} initialPage={officeKind==="pptx"?previewPage:1} compatibilityReady={currentVersion?.preview_status==="SUCCEEDED"} onCompatibility={() => void showPreview()} onDownload={() => void download()}/></Suspense></> : view === "pdf" && previewUrl ? <><button className="secondary" onClick={() => setView("text")}><Icon name="list" size={16}/>返回文本与引用</button><Suspense fallback={<p className="material-loading" role="status">正在打开按页阅读器…</p>}><PdfReader key={versionId} url={previewUrl} initialPage={previewPage} name={active?.name || "课程资料"} sourceType={currentVersion?.original_filename.toLowerCase().endsWith(".pptx") ? "slide" : currentVersion?.original_filename.toLowerCase().endsWith(".docx") ? "preview_page" : "page"} onDownload={() => void download()} onTranscribe={currentVersion?.original_filename.toLowerCase().endsWith(".pdf") ? page => setTranscriptRequest({page,serial:Date.now()}) : undefined} onCapture={async (file, page) => {
          await api.uploadAsset(token, courseId, file, `${active?.name || "课程资料"} · 第 ${page} 页`, {versionId, page});
          if (alive.current) { setAssetRefresh(s => s + 1); onNotice("当前页图片已保存，来源版本与页号已记录"); }
        }}/></Suspense></> : reading ? <div className="material-loading" role="status"><Icon name="refresh" className="is-spinning"/>正在读取这个版本…</div> : selected.length ? <>
          <div className="reader-searchbar"><div className="input-with-icon"><Icon name="search" size={16}/><input aria-label="在当前版本原文中查找" value={readerQuery} onChange={e => setReaderQuery(e.target.value)} placeholder="在这份原文中查找…"/>{readerQuery && <button className="icon-button" aria-label="清空原文查找" onClick={() => setReaderQuery("")}><Icon name="close" size={14}/></button>}</div><small role="status">{shownChunks.length} / {selected.length} 个片段</small></div>
          <details className="reader-directory" open><summary><Icon name="list" size={16}/>原文目录<span>{shownChunks.length}</span></summary><div className="reader-outline" aria-label="资料目录">{shownChunks.map((chunk, index) => <button className="secondary" key={chunk.id} onClick={() => scrollToChunk(chunk.id)}>{index + 1}. {chunk.locator_value}</button>)}</div></details>
          <div className="reading-paper" style={{ fontSize }}>{shownChunks.map(chunk => <article id={"chunk-" + chunk.id} className={"chunk " + (chunk.id === initialTarget?.chunkId ? "chunk-highlight" : "")} key={chunk.id}><div className="chunk-heading"><span className="locator">{({slide:"幻灯片",page:"页",heading:"标题",docx_block:"正文块"} as Record<string,string>)[chunk.locator_type] || chunk.locator_type} · {chunk.locator_value}</span><span className="chunk-source-label">{chunk.source_kind === "manual_transcript" ? chunk.transcript_status === "SUPERSEDED" ? "人工补录 · 历史确认" : "人工补录 · 已确认" : "文件提取"}</span><span className="chunk-reference-count">{references.filter(r => r.chunk_id === chunk.id).length > 0 ? references.filter(r => r.chunk_id === chunk.id).length + " 条笔记引用" : ""}</span></div><p><Highlight text={chunk.text} query={readerQuery}/></p><button className="secondary citation-action" disabled={!targetNote || busy} onClick={() => void cite(chunk)}><Icon name="link" size={15}/>引用到所选笔记<Icon name="arrow" size={14}/></button></article>)}</div>
          {!shownChunks.length && <EmptyInline text="当前版本没有匹配片段，试试更短的关键词"/>}<p className="hint reader-footnote">结构化文本保留原文定位；阅读原始版式请打开 PDF 预览。</p>
        </> : <EmptyState title={active ? "这个版本暂时没有可读文本" : "从一份资料，开启一段学习"} text={active ? "处理完成后将自动显示正文；扫描 PDF 可预览原页，并在下方人工补录文字。" : "在左侧上传或选择资料。整理、查找、引用，都从这里开始。"}/>}
        {versionId && currentVersion?.original_filename.toLowerCase().endsWith(".pdf") && <Transcripts key={versionId} token={token} versionId={versionId} request={transcriptRequest} onPreview={page => void previewAt(page)} onChanged={refreshTranscripts} onError={onError}/>}
        {versionId && <section className="material-references"><div className="panel-title"><h4><Icon name="notes" size={18}/>引用这份原文的笔记 <span className="count-pill">{linkedNotes.size}</span></h4><button className="icon-button secondary" aria-label="刷新原文引用笔记" disabled={referencesLoading} onClick={() => void loadReferences(versionId)}><Icon name="refresh" size={16}/></button></div>{referencesLoading ? <p className="hint" role="status">正在查找关联笔记…</p> : referencesFailed ? <div className="inline-retry">关联笔记暂未加载<button className="secondary" onClick={() => void loadReferences(versionId)}>重试</button></div> : references.length ? <div className="material-reference-grid">{references.map(ref => <button key={ref.citation_id} className="source-note-card" onClick={() => onNote(ref.note_id)}><span><Icon name="notes" size={17}/><strong>{ref.note_title}</strong><Icon name="arrow" size={15}/></span><p>{ref.quote.slice(0, 130)}</p><small>{ref.locator_value} · 打开笔记</small></button>)}</div> : <p className="hint">还没有笔记引用这个版本。选择一篇笔记，将理解和原文连起来。</p>}</section>}
      </section>
    </div>
    {!focused && <MaterialExports refreshKey={assetRefresh} key={courseId} token={token} courseId={courseId} onError={onError} onNotice={onNotice}/>}
    {!focused && <AssetLibrary onChanged={() => setAssetRefresh(value => value + 1)} onNote={onNote} refreshKey={assetRefresh} onSource={target => {
      void api.document(token, target.documentId).then(doc => { if (alive.current) void openDocument(doc, target); }).catch(onError);
    }} token={token} courseId={courseId} onError={onError} onNotice={onNotice}/>}
    {!focused && <details className="panel material-jobs"><summary className="jobs-summary"><span><Icon name="clock"/>处理记录</span><span className="hint">{pending ? pending + " 个任务正在排队或处理" : jobInfo.total + " 条匹配任务记录"}<Icon name="arrow" size={16}/></span></summary><div className="panel-title jobs-filter"><span className="hint">解析、索引与预览独立记录 · 全部历史可翻页 · 取消保留原件和引用</span><select aria-label="筛选处理记录" value={jobFilter} onChange={e => { setJobOffset(0); setJobFilter(e.target.value); }}><option value="all">全部任务</option><option value="pending">正在处理</option><option value="failed">失败任务</option><option value="cancelled">已取消</option></select></div>{shownJobs.map(job => <div className="job-row material-job" key={job.id}><div className="job-identity"><strong>{job.document_name || "课程资料"}{job.version_no ? " · v" + job.version_no : ""}</strong><small>{({PARSE:"原文解析", INDEX:"关键词索引", PREVIEW:"预览转换"} as Record<string,string>)[job.type] || job.type} · 第 {job.attempt_count}/{job.max_attempts} 次尝试</small></div><Status value={job.status}/><div className="job-progress"><progress aria-label={(job.document_name || "资料") + " " + job.type + "处理进度"} value={job.progress} max={100}/><span>{job.error || (job.status === "QUEUED" ? "等待后台处理" : job.status === "SUCCEEDED" ? "处理完成" : job.status === "CANCELLED" ? "已取消，结果不会写入" : "处理中")}</span></div>{["QUEUED", "RUNNING"].includes(job.status) && <button className="secondary" disabled={busy} onClick={() => void cancel(job)}><Icon name="close" size={15}/>取消</button>}{["FAILED", "CANCELLED"].includes(job.status) && <button className="secondary" disabled={job.attempt_count >= job.max_attempts || busy} onClick={() => void retry(job)}><Icon name="refresh" size={15}/>{job.status === "CANCELLED" ? "恢复" : "重试"}</button>}</div>)}<nav className="catalogue-pages" aria-label="任务分页"><button className="secondary" disabled={loading || jobOffset===0} onClick={() => setJobOffset(Math.max(0,jobOffset-10))}>上一页</button><span role="status">{Math.floor(jobOffset/10)+1} / {Math.max(1,Math.ceil(jobInfo.total/10))} 页 · {jobInfo.total} 条</span><button className="secondary" disabled={loading || jobOffset+10>=jobInfo.total} onClick={() => setJobOffset(jobOffset+10)}>下一页</button></nav>{!shownJobs.length && <EmptyInline text={jobs.length ? "没有符合条件的任务" : "上传后可在这里查看处理状态"}/>}</details>}
  </div>;
}
