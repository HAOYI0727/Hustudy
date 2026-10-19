import { Icon } from "../../components/Icon";
import { CompactLibrary } from "../../components/CompactLibrary";
import { lazy, Suspense, useEffect, useRef, useState, type DragEvent } from "react";
import { api, ApiError, Note, Asset, type NoteFolder } from "../../api/client";
import { EmptyInline } from "../../components/workspace";
import { addNoteTag, filterNotes } from "./tags";
import { NoteExports } from "./NoteExports";
import { markdownFilename } from "./exportNames";
import {uploadImages, imageLabel, MAX_IMAGE_BATCH, type ImageFailure, type ImageProgress} from "../materials/uploadImages";
import {ImageUploadStatus} from "../materials/ImageUploadStatus";
import {NoteCitations} from "./NoteCitations";
import {FolderLibrary} from "./FolderLibrary";
import {NoteOrganizer} from "./NoteOrganizer";
import {MarkdownImport} from "./MarkdownImport";
import {NoteCapture} from "./NoteCapture";
import {SpeechInput} from "./SpeechInput";
import {MarkdownEditor} from "./MarkdownEditor";
import {folderOptions, folderPath, insideFolder} from "./organization";
import {NotesDialog} from './NotesDialog';
import {NoteManager} from './NoteManager';
import {NoteTrash} from './NoteTrash';
import {NOTE_DRAG_TYPE, canDropNotes, type NoteDrag} from './noteDragging';
import "./notes.css";

const AssetLibrary = lazy(() => import("../materials/AssetLibrary").then(module => ({default: module.AssetLibrary})));

type Props = { onSource: (versionId: string, chunkId: string) => void; initialNoteId?: string; token: string; courseId: string; onNotice: (s: string) => void; onError: (e: unknown) => void };
type Draft = { title: string; content: string; tags: string[]; folder_id?: string | null };
type Conflict = Draft & { revision: number };
const templates = [
  { name: "概念学习", content: "## 学习目标\n\n## 概念与原理\n\n## 例子\n\n## 常见误区\n\n## 自测问题\n" },
  { name: "错题复盘", content: "## 原题与来源\n\n## 我的思路\n\n## 出错原因\n\n## 正确解法\n\n## 下次如何识别\n" },
  { name: "课前预习", content: "## 已知内容\n\n## 不理解的问题\n\n## 课堂核实\n\n## 课后总结\n" },
];

export function Notes({ token, courseId, onNotice, onError: reportError, initialNoteId, onSource }: Props) {
  const [opening, setOpening] = useState(!!initialNoteId);
  const [notes, setNotes] = useState<Note[]>([]);
  const [folders, setFolders] = useState<NoteFolder[]>([]);
  const [folderFilter, setFolderFilter] = useState("*");
  const [selectedNotes, setSelectedNotes] = useState<string[]>([]);
  const [workspaceView, setWorkspaceView] = useState<'manage' | 'edit'>(initialNoteId ? 'edit' : 'manage');
  const [tool, setTool] = useState<'import' | 'export' | 'batch' | 'tags' | 'recommend' | 'metadata' | 'insert' | 'images' | 'context' | 'templates' | 'trash' | 'capture' | 'speech' | null>(null);
  const [exportSelection, setExportSelection] = useState({ids: [] as string[], version: 0});
  const [organizationError, setOrganizationError] = useState('');
  const [exportBusy, setExportBusy] = useState(false);
  const [captureBusy, setCaptureBusy] = useState(false);
  const [recognitionError, setRecognitionError] = useState('');
  const recognitionTarget = useRef<{session: number; content: string; start: number; end: number} | null>(null);
  const onError = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401) {setTool(null); window.dispatchEvent(new Event('hustudy:notes-session-expired'));}
    else setOrganizationError(error instanceof Error ? error.message : '操作未完成，请重试。');
    reportError(error);
  };
  const [moveNotice, setMoveNotice] = useState('');
  const [drag, setDrag] = useState<NoteDrag | null>(null);
  const dragRef = useRef<NoteDrag | null>(null);
  const [focusedEditor, setFocusedEditor] = useState(false);
  const [editorSession, setEditorSession] = useState(0);
  const [editing, setEditing] = useState<Note | null>(null);
  const [draft, setDraft] = useState<Draft>({ title: "", content: "", tags: [] });
  const [tagInput, setTagInput] = useState("");
  const [tagError, setTagError] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [search, setSearch] = useState("");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetRevision, setAssetRevision] = useState(0);
  const [preview, setPreview] = useState(false);
  const [foreground, setForeground] = useState(document.visibilityState === "visible");
  const [backlinks, setBacklinks] = useState<Note[]>([]);
  const [busy, setBusy] = useState(false);
  const [organizing, setOrganizing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadFailures, setUploadFailures] = useState<ImageFailure[]>([]);
  const [uploadProgress, setUploadProgress] = useState<ImageProgress | null>(null);
  const [uploadSummary, setUploadSummary] = useState("");
  const [status, setStatus] = useState("开始记录你的理解");
  const [paused, setPaused] = useState(false);
  const [networkRetry, setNetworkRetry] = useState(false);
  const pendingCreate = useRef<(Draft & {course_id: string; request_id: string}) | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const lock = useRef(false);
  const loadedInitial = useRef<string | undefined>(undefined);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const imageInput = useRef<HTMLInputElement>(null);
  const dirty = draft.title !== (editing?.title || "") || draft.content !== (editing?.content || "") || JSON.stringify(draft.tags) !== JSON.stringify(editing?.tags ?? []) || (!!editing && (draft.folder_id ?? null) !== (editing.folder_id ?? null)) || !!tagInput.trim();
  const organizationDisabled = dirty || busy || !!conflict;
  const refreshFolders = async () => setFolders(await api.noteFolders(token, courseId));
  useEffect(() => {
    let live = true; setFolders([]); setFolderFilter("*"); setSelectedNotes([]);
    void api.noteFolders(token, courseId).then(rows => {if (live) setFolders(rows);}).catch(error => {if (live) onError(error);});
    return () => {live = false;};
  }, [token, courseId]);
  const mergeNotes = (changed: Note[]) => {
    setNotes(rows => [...changed, ...rows.filter(row => !changed.some(item => item.id === row.id))]);
    const current = changed.find(row => row.id === editing?.id);
    if (current) {setEditing(current); setDraft({title: current.title, content: current.content, tags: current.tags, folder_id: current.folder_id ?? null});}
  };
  const performOrganization = async (action: () => Promise<void>) => {
    if (lock.current || organizationDisabled) return;
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable: true}))) return;
    lock.current = true; setBusy(true); setOrganizing(true); setOrganizationError('');
    try {await action();} catch (error) {setOrganizationError(error instanceof Error ? error.message : '操作未完成，请重试。'); onError(error);} finally {lock.current = false; setBusy(false); setOrganizing(false);}
  };
  const showTool = (next: typeof tool) => {
    setOrganizationError('');
    if (next === 'export') setExportSelection(value => ({ids: [...selectedNotes], version: value.version + 1}));
    if (next === 'capture' || next === 'speech') {
      if (workspaceView !== 'edit' || busy || conflict) return;
      const start = textarea.current?.selectionStart ?? draft.content.length;
      recognitionTarget.current = {session: editorSession, content: draft.content, start, end: textarea.current?.selectionEnd ?? start};
      setRecognitionError(''); setPreview(false);
    }
    setTool(next);
  };
  const endDrag = () => {dragRef.current = null; setDrag(null);};
  const startDrag = (event: DragEvent, value: NoteDrag) => {
    if (organizationDisabled || (value.kind === 'notes' && value.notes.length > 200)) {event.preventDefault(); return;}
    dragRef.current = value; setDrag(value);
    event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData(NOTE_DRAG_TYPE, 'internal');
  };
  const dragNote = (event: DragEvent, note: Note) => startDrag(event, {kind: 'notes', notes: (selectedNotes.includes(note.id) ? notes.filter(n => n.course_id === courseId && selectedNotes.includes(n.id)) : [note]).map(n => ({id: n.id, revision: n.revision, folder_id: n.folder_id}))});
  const drop = (target: string | null) => {
    const value = dragRef.current; endDrag();
    if (organizationDisabled || !canDropNotes(value, target, folders) || !value) return;
    void performOrganization(async () => {
      if (value.kind === 'folder') {
        const updated = await api.updateNoteFolder(token, value.folder.id, {parent_id: target, revision: value.folder.revision});
        setFolders(rows => rows.map(row => row.id === updated.id ? updated : row));
        setMoveNotice(`已将“${updated.name}”移到${target ? folderPath(folders, target) : '根目录'}。`);
      } else {
        const updated = await api.batchNotes(token, value.notes.map(n => ({id: n.id, revision: n.revision})), {folder_id: target});
        mergeNotes(updated); setSelectedNotes([]); setMoveNotice(`已将 ${updated.length} 篇笔记移到${folderPath(folders, target)}。`);
      }
    });
  };
  const imageCourse = editing?.course_id || courseId;
  useEffect(() => {
    let active = true; setAssets([]);
    void api.assets(token,imageCourse).then(rows => { if (active) setAssets(rows); }).catch(onError);
    return () => { active = false; };
  }, [token,imageCourse,assetRevision]);
  useEffect(() => {
    let active = true;
    void api.notes(token).then(async rows => {
      if (!active) return;
      setNotes(rows);
      if (!initialNoteId || loadedInitial.current === initialNoteId) return;
      if (!rows.some(row => row.id === initialNoteId && row.course_id === courseId)) throw new Error("这篇笔记已删除或不在当前课程");
      const note = await api.note(token, initialNoteId);
      if (active) { loadedInitial.current = initialNoteId; setEditing(note); setDraft({ title: note.title, content: note.content, tags: note.tags ?? [], folder_id: note.folder_id ?? null }); setEditorSession(value => value + 1); setStatus("已载入保存版本"); }
    }).catch(error => { if (active) onError(error); }).finally(() => { if (active) setOpening(false); });
    return () => { active = false; };
  }, [courseId, token, initialNoteId]);
  useEffect(() => {
    let active = true;
    setBacklinks([]);
    if (editing) void api.backlinks(token, editing.id).then((rows) => { if (active) setBacklinks(rows); }).catch(onError);
    return () => { active = false; };
  }, [editing?.id, token]);
  useEffect(() => {
    const changed = () => setForeground(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", changed);
    return () => document.removeEventListener("visibilitychange", changed);
  }, []);
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
    if (lock.current || !draft.title.trim() || !dirty || conflict || tagInput.trim()) return;
    lock.current = true; setBusy(true); setNetworkRetry(false); setStatus("正在保存…");
    const snapshot = { ...draft };
    if (!editing) pendingCreate.current ??= {...snapshot, course_id: courseId, request_id: crypto.randomUUID()};
    try {
      const saved = editing
        ? await api.updateNote(token, editing.id, { ...snapshot, revision: editing.revision })
        : await api.createNote(token, pendingCreate.current!);
      pendingCreate.current = null;
      setEditing(saved); setPaused(false); setStatus("已保存到本地服务");
      setNotes((rows) => [saved, ...rows.filter((row) => row.id !== saved.id)]);
    } catch (error) {
      setPaused(true); setStatus("未保存 · 请处理后重试");
      setNetworkRetry(error instanceof ApiError && error.status === 0);
      if (error instanceof ApiError && error.status === 422) pendingCreate.current = null;
      if (error instanceof ApiError && error.status === 409 && error.details) {
        if (!editing && error.details.server_id === pendingCreate.current?.request_id) {
          setEditing({id: String(error.details.server_id), course_id: courseId, title: String(error.details.server_title || ""), content: String(error.details.server_content || ""), tags: Array.isArray(error.details.server_tags) ? error.details.server_tags as string[] : [], folder_id: error.details.server_folder_id as string | null ?? null, revision: Number(error.details.server_revision), updated_at: ""});
          pendingCreate.current = null;
        }
        setConflict({ title: String(error.details.server_title || ""), content: String(error.details.server_content || ""), tags: Array.isArray(error.details.server_tags) ? error.details.server_tags as string[] : [], folder_id: error.details.server_folder_id as string | null ?? null, revision: Number(error.details.server_revision) });
      } else onError(error);
    } finally { lock.current = false; setBusy(false); }
  };
  useEffect(() => {
    const recover = () => {
      if (networkRetry && navigator.onLine && document.visibilityState === "visible") {
        setPaused(false); setNetworkRetry(false); setStatus("连接已恢复 · 等待保存");
      }
    };
    window.addEventListener("online", recover);
    document.addEventListener("visibilitychange", recover);
    const timer = networkRetry ? window.setTimeout(recover, 15000) : undefined;
    return () => { window.clearTimeout(timer); window.removeEventListener("online", recover); document.removeEventListener("visibilitychange", recover); };
  }, [networkRetry]);
  useEffect(() => {
    if (!foreground || !dirty || busy || paused || conflict || !draft.title.trim() || tagInput.trim()) return;
    const timer = window.setTimeout(() => { if (document.visibilityState === "visible") void save(); }, 2000);
    return () => window.clearTimeout(timer);
  }, [draft, editing, busy, paused, conflict, tagInput, foreground]);

  const open = async (note?: Note) => {
    if (lock.current) return;
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable: true}))) return;
    if (dirty && !window.confirm("当前有未保存内容。确认放弃这些修改并切换？")) return;
    lock.current = true; setBusy(true);
    try {
      const fresh = note ? await api.note(token, note.id) : null;
      if (fresh) setNotes(rows => [fresh, ...rows.filter(row => row.id !== fresh.id)]);
      setEditing(fresh); setDraft({ title: fresh?.title || "", content: fresh?.content || "", tags: fresh?.tags ?? [], folder_id: fresh ? fresh.folder_id ?? null : folders.some(f => f.id === folderFilter) ? folderFilter : null });
      setEditorSession(value => value + 1); setWorkspaceView('edit');
      setTagInput(""); setTagError(""); setUploadError("");
      setUploadFailures([]); setUploadSummary("");
      pendingCreate.current = null; setNetworkRetry(false);
      setConflict(null); setPaused(false); setStatus(fresh ? "已载入保存版本" : "新笔记 · 填写标题后自动保存");
    } catch (error) { onError(error); } finally { lock.current = false; setBusy(false); }
  };
  const remove = async () => {
    if (!editing || lock.current) return;
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable: true}))) return;
    if (!window.confirm(`确认删除“${editing.title}”并移入回收站？${dirty ? "未保存修改也会放弃。" : ""}可在回收站恢复；其他笔记中的双链暂时不可用。`)) return;
    lock.current = true; setBusy(true);
    try {
      await api.deleteNote(token, editing.id, editing.revision);
      setNotes(rows => rows.filter(row => row.id !== editing.id));
      setSelectedNotes(ids => ids.filter(id => id !== editing.id));
      setEditing(null); setDraft({title: "", content: "", tags: []}); setTagInput(""); setTagError("");
      setEditorSession(value => value + 1);
      setUploadFailures([]); setUploadSummary(""); setUploadError("");
      setConflict(null); setPaused(false); setNetworkRetry(false); pendingCreate.current = null;
      setStatus("笔记已删除，已移入回收站"); onNotice("笔记已删除，可在回收站恢复"); setWorkspaceView('manage');
    } catch (error) {
      setPaused(true); setNetworkRetry(false); setStatus("删除未完成 · 本地内容保留");
      if (error instanceof ApiError && error.status === 409 && error.details) {
        setConflict({title: String(error.details.server_title || ""), content: String(error.details.server_content || ""), tags: Array.isArray(error.details.server_tags) ? error.details.server_tags as string[] : [], folder_id: error.details.server_folder_id as string | null ?? null, revision: Number(error.details.server_revision)});
      } else onError(error);
    } finally { lock.current = false; setBusy(false); }
  };
  const removeSelected = () => {
    if (organizationDisabled || !selectedNotes.length || selectedNotes.length > 200) return;
    const rows = notes.filter(note => selectedNotes.includes(note.id));
    if (!window.confirm(`将所选 ${rows.length} 篇笔记移入回收站？包含：${rows.slice(0, 3).map(n => n.title).join('、')}${rows.length > 3 ? '等' : ''}。可以在回收站恢复。`)) return;
    void performOrganization(async () => {
      await api.trashNotes(token, 'trash', rows.map(n => ({id: n.id, revision: n.revision})));
      const ids = new Set(rows.map(n => n.id));
      setNotes(items => items.filter(n => !ids.has(n.id))); setSelectedNotes([]);
      setBacklinks(items => items.filter(n => !ids.has(n.id)));
      if (editing && ids.has(editing.id)) {
        setEditing(null); setDraft({title: '', content: '', tags: []}); setTagInput(''); setTagError('');
        setEditorSession(value => value + 1); setUploadFailures([]); setUploadSummary(''); setUploadError('');
        setConflict(null); setPaused(false); setNetworkRetry(false); pendingCreate.current = null;
      }
      setMoveNotice(`已将 ${rows.length} 篇笔记移入回收站，可恢复。`);
    });
  };
  const insert = (text: string) => {
    const start = textarea.current?.selectionStart ?? draft.content.length;
    const end = textarea.current?.selectionEnd ?? start;
    setDraft((value) => ({ ...value, content: value.content.slice(0, start) + text + value.content.slice(end) }));
    setTool(null);
    window.requestAnimationFrame(() => {textarea.current?.focus(); textarea.current?.setSelectionRange(start + text.length, start + text.length);});
  };
  const insertRecognition = (text: string) => {
    const target = recognitionTarget.current;
    if (lock.current || busy || conflict || workspaceView !== 'edit') {
      setRecognitionError('当前笔记正在保存或存在冲突，请处理后重新打开识别窗口。识别文字已保留。'); return false;
    }
    if (!target || target.session !== editorSession || target.content !== draft.content) {
      setRecognitionError('笔记正文或编辑目标已变化，请关闭窗口、重新选择插入位置后再打开。识别文字已保留。'); return false;
    }
    const {start, end} = target;
    setDraft(value => ({...value, content: value.content.slice(0, start) + text + value.content.slice(end)}));
    recognitionTarget.current = null; setTool(null); setStatus('识别文字已插入 · 待保存');
    window.requestAnimationFrame(() => {textarea.current?.focus(); textarea.current?.setSelectionRange(start + text.length, start + text.length);});
    return true;
  };
  const uploadImage = async (files: File[]) => {
    if (lock.current) { setUploadError("笔记正在保存，请稍后重新选择图片。"); return; }
    if (!files.length) return;
    if (files.length > MAX_IMAGE_BATCH) { setUploadError(`每批最多选择 ${MAX_IMAGE_BATCH} 张图片，请分批上传。`); return; }
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable: true}))) return;
    setUploadError("");
    setUploadFailures([]); setUploadSummary("");
    const contentBefore = draft.content;
    const start = textarea.current?.selectionStart ?? contentBefore.length;
    const end = textarea.current?.selectionEnd ?? start;
    lock.current = true; setBusy(true); setUploading(true);
    try {
      const result = await uploadImages(files, file => api.uploadAsset(token, imageCourse, file, imageLabel(file)), setUploadProgress);
      setUploadFailures(result.failures);
      const summary = `已上传并插入 ${result.assets.length} 张图片${result.failures.length ? `，${result.failures.length} 张未完成` : ""}。`;
      setUploadSummary(summary);
      if (result.assets.length) {
        setAssets(rows => [...result.assets, ...rows.filter(row => !result.assets.some(asset => asset.id === row.id))]);
        setAssetRevision(value => value + 1);
        const embedded = "\n" + result.assets.map(asset => `![[asset:${asset.id}|${(asset.alt || asset.name || asset.original_filename).replace(/[\]\r\n]/g, " ")}]]`).join("\n") + "\n";
        setDraft(value => ({...value, content: value.content === contentBefore
          ? value.content.slice(0, start) + embedded + value.content.slice(end)
          : value.content + embedded}));
        setStatus("图片已插入 · 待保存");
        onNotice(summary);
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "图片上传失败，请重试。");
      onError(error);
    } finally { lock.current = false; setBusy(false); setUploading(false); setUploadProgress(null); }
  };
  const download = async () => {
    if (!editing || dirty) return;
    try {
      const content = await api.exportNote(token, editing.id);
      const url = URL.createObjectURL(new Blob([content], { type: "text/markdown;charset=utf-8" }));
      const link = document.createElement("a"); link.href = url; link.download = markdownFilename(editing.title); link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000); onNotice("已按笔记标题导出 Markdown；需要离线图片时，请在“选择笔记导出”中下载 ZIP，自动附带引用图片。");
    } catch (error) { onError(error); }
  };
  const courseNotes = notes.filter(note => note.course_id === courseId);
  const filtered = filterNotes(courseNotes, search, tagFilter).filter(note => folderFilter === "*" || (folderFilter === "" ? !note.folder_id : insideFolder(folders, note.folder_id, folderFilter)));
  const availableTags = [...new Set(courseNotes.flatMap(note => note.tags ?? []))].sort((a, b) => a.localeCompare(b, "zh-CN"));
  const addTag = () => {
    try {
      const tags = addNoteTag(draft.tags, tagInput);
      setDraft(value => ({ ...value, tags })); setTagInput(""); setTagError("");
    } catch (error) { setTagError((error as Error).message); }
  };
  const outgoing = [...draft.content.matchAll(/\[\[note:([0-9a-fA-F-]{36})(?:\|([^\]]+))?\]\]/g)];
  if (opening) return <div className="panel" role="status">正在打开指定笔记…</div>;
  return <div className="page notes-workspace">
    <header className="notes-workspace-heading"><div><span className="eyebrow">PERSONAL KNOWLEDGE</span><h1>我的笔记 <small>{courseNotes.length}</small></h1></div><div className="notes-workspace-tools"><button className="secondary" onClick={() => showTool('trash')}>回收站</button><button className="secondary" onClick={() => showTool('import')}>导入 Markdown</button><button className="secondary" onClick={() => showTool('export')}>选择笔记导出</button><button className="secondary" onClick={() => showTool('tags')}>标签管理</button><button className="secondary" onClick={() => showTool('recommend')}>推荐归类</button><button className="primary" disabled={busy} onClick={() => void open()}><Icon name="plus" size={16}/>新建笔记</button></div></header>
    {moveNotice && <p className="note-operation-notice" role="status">{moveNotice}</p>}
    <div className="knowledge-layout">
      <CompactLibrary className="panel knowledge-library" label="笔记列表与新建">
        <div className="panel-title"><h3>课程笔记</h3><span className="count-pill">{courseNotes.length}</span></div>
        <FolderLibrary token={token} courseId={courseId} folders={folders} notes={courseNotes} selected={folderFilter} onSelect={setFolderFilter} disabled={organizationDisabled} perform={performOrganization} refresh={refreshFolders} drag={drag} startDrag={startDrag} endDrag={endDrag} drop={drop} error={organizationError}/>
        <p className="hint note-nav-caption">快速打开 · {filtered.length} 篇</p>
        <div className="list">{filtered.map((note) => <button key={note.id} title={note.title} draggable={!organizationDisabled} onDragStart={e => dragNote(e, note)} onDragEnd={endDrag} disabled={busy} className={`knowledge-item ${note.id === editing?.id ? "selected" : ""}`} onClick={() => void open(note)}><Icon name="notes" size={15}/><strong>{note.title}</strong></button>)}</div>
        {!filtered.length && <EmptyInline text={search || tagFilter ? "未找到匹配笔记，试试其他关键词或标签" : "从一个概念开始记录"} />}
      </CompactLibrary>
      <div className="notes-main"><nav className="notes-view-tabs" aria-label="笔记工作区视图"><button aria-pressed={workspaceView === 'manage'} onClick={() => setWorkspaceView('manage')}>笔记管理</button><button aria-label={editing ? '编辑笔记' : '编辑草稿'} aria-description={dirty ? '有未保存修改' : undefined} aria-pressed={workspaceView === 'edit'} onClick={() => setWorkspaceView('edit')}>{editing ? '编辑笔记' : '编辑草稿'}{dirty && <span className="draft-dot" aria-hidden="true"/>}</button></nav>
      <div hidden={workspaceView !== 'manage'}><NoteManager notes={filtered} folders={folders} selected={selectedNotes} setSelected={setSelectedNotes} disabled={organizationDisabled} search={search} setSearch={setSearch} tag={tagFilter} setTag={setTagFilter} tags={availableTags} path={folderFilter === '*' ? '全部笔记' : folderPath(folders, folderFilter)} onOpen={note => void open(note)} onTool={showTool} onRefresh={() => void performOrganization(async () => {const rows = await api.notes(token); setNotes(rows); const current = rows.find(row => row.id === editing?.id); if (current) mergeNotes([current]);})} onDrag={dragNote} onDragEnd={endDrag} onDelete={removeSelected}/>{organizationDisabled && <p className="hint">请先保存或处理编辑区的草稿，再批量整理或拖动笔记。</p>}</div>
      <section hidden={workspaceView !== 'edit'} className={`panel knowledge-editor ${focusedEditor ? "is-focused" : ""}`} inert={organizing} aria-busy={organizing}>
        {editing && editing.course_id !== courseId && <p className="hint" role="status">当前打开的是{editing.course_id ? "其他课程" : "未分类"}的关联笔记；保存会保留其原有归属。</p>}
        <div className="panel-title"><h3>{editing ? "编辑笔记" : "新建笔记"}</h3><span className={`save-indicator ${dirty ? "unsaved" : ""}`} role="status"><Icon name={busy ? "refresh" : paused || conflict ? "info" : dirty ? "edit" : editing ? "check" : "notes"} size={13} className={busy ? "is-spinning" : ""}/>{uploading ? "正在上传图片…" : busy ? "保存中…" : dirty && !paused ? "有修改待保存" : status}</span></div>
        <input className="title-input" aria-label="笔记标题" maxLength={240} placeholder="为这份理解起一个名字" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
        <button className="text-button note-preview-toggle" aria-pressed={preview} onClick={() => setPreview(!preview)}>{preview ? '继续编辑' : 'Markdown 预览'}</button>
        <div className="note-editor-tools"><button className="primary" disabled={busy || !!conflict} onClick={() => showTool('speech')}>语音输入</button><button className="secondary" onClick={() => showTool('capture')}>文字识别</button><button className="secondary" onClick={() => showTool('metadata')}>文件夹与标签{draft.tags.length ? ` · ${draft.tags.length}` : ''}</button><button className="secondary" onClick={() => showTool('images')}>管理图片</button><button className="secondary" onClick={() => showTool('context')}>引用与关联 · {outgoing.length + backlinks.length}</button><button className="secondary" onClick={() => showTool('templates')}>学习模板</button><span className="hint">{folderPath(folders, draft.folder_id)}</span></div>
        <NotesDialog open={tool === 'metadata'} title="文件夹与标签" onClose={() => setTool(null)} busy={busy}>
        {conflict ? <p role="alert">检测到另一处修改，本地标签和草稿已保留。关闭窗口后在编辑区处理冲突。</p> : organizationError ? <p role="alert">{organizationError}</p> : <p className="hint" role="status">{dirty ? '修改会随笔记自动保存。' : status}</p>}
        <label className="note-filter">所在文件夹<select aria-label="笔记所在文件夹" value={draft.folder_id || ""} disabled={busy || !!conflict || (!!editing && editing.course_id !== courseId)} onChange={e => setDraft(value => ({...value, folder_id: e.target.value || null}))}><option value="">未归档</option>{folderOptions(folders).map(f => <option key={f.id} value={f.id}>{f.path}</option>)}{draft.folder_id && !folders.some(f => f.id === draft.folder_id) && <option value={draft.folder_id}>保留原文件夹归属</option>}</select></label>
        <section className="note-tag-editor" aria-label="笔记标签">
          <div className="note-tag-heading"><strong>标签</strong><span className="hint">{draft.tags.length} / 12</span></div>
          <div className="note-tags">{draft.tags.map(tag => <span className="note-tag" key={tag}><span>#{tag}</span><button type="button" className="text-button" aria-label={`移除标签 ${tag}`} onClick={() => { setDraft(value => ({ ...value, tags: value.tags.filter(item => item !== tag) })); setTagError(""); }}>×</button></span>)}</div>
          <div className="note-tag-input"><input aria-label="新标签" aria-describedby="note-tag-help" value={tagInput} placeholder="例如：期末重点" onChange={e => { setTagInput(e.target.value); setTagError(""); }} onKeyDown={e => { if (e.key === "Enter" && !e.nativeEvent.isComposing) { e.preventDefault(); addTag(); } }} /><button type="button" className="secondary" disabled={!tagInput.trim()} onClick={addTag}>添加标签</button></div>
          <p id="note-tag-help" className="hint">输入后按 Enter 或点击添加，每项最多 32 字；{tagInput.trim() ? "请先添加或清空输入，再保存笔记。" : "标签随笔记自动保存。"}</p>
          {tagError && <p role="alert">{tagError}</p>}
        </section>
        </NotesDialog>
        <div className="writing-toolbar note-quick-insert" aria-label="笔记图片上传">
          <input ref={imageInput} type="file" multiple disabled={busy || !!conflict} hidden accept="image/png,image/jpeg,image/webp" aria-label="选择上传的笔记图片" onChange={event => { const files = Array.from(event.target.files ?? []); event.target.value = ""; void uploadImage(files); }}/>
          <button className="secondary" disabled={busy || !!conflict} onClick={() => imageInput.current?.click()}>{uploading ? "正在上传…" : "上传图片并插入"}</button>
        </div>
        {uploadError && <p role="alert" className="note-upload-error">{uploadError}</p>}
        <ImageUploadStatus progress={uploadProgress} failures={uploadFailures} summary={uploadSummary} busy={busy || !!conflict} retry={() => void uploadImage(uploadFailures.map(item => item.file))} clear={() => {setUploadFailures([]); setUploadSummary("");}}/>
        <NotesDialog open={tool === 'insert'} title="插入图片与双链" onClose={() => setTool(null)} busy={busy}>
        <div className="writing-toolbar" aria-label="笔记编辑工具">
          <select aria-label="插入课程图片" disabled={busy || !assets.length} value="" onChange={e=>{const asset=assets.find(a=>a.id===e.target.value);if(asset)insert(`\n![[asset:${asset.id}|${(asset.alt || asset.name || asset.original_filename).replace(/[\]\n]/g," ")}]]\n`);}}><option value="">{assets.length ? "插入已有课程图片…" : "暂无课程图片，请先上传"}</option>{assets.map(a=><option key={a.id} value={a.id}>{a.name || a.alt || a.original_filename}</option>)}</select>
          <select aria-label="插入笔记双链" value="" onChange={(e) => { const note = notes.find((row) => row.id === e.target.value); if (note) insert(`[[note:${note.id}|${note.title.replace(/[\]\n]/g, " ")}]]`); }}><option value="">插入笔记双链…</option>{notes.filter((row) => row.id !== editing?.id).map((row) => <option key={row.id} value={row.id}>{row.title}{row.course_id !== courseId ? " · 其他课程/未分类" : ""}</option>)}</select>
        </div>
        <p className="hint">可多选 PNG、JPG、WebP 图片，每批最多 20 张，每张最大 10 MiB；成功的图片按选择顺序插入正文。</p>
        </NotesDialog>
        <NotesDialog open={tool === 'images'} title="管理图片" onClose={() => {if (window.dispatchEvent(new Event('hustudy:before-material-change', {cancelable: true}))) setTool(null);}}>{organizationError && <p role="alert">{organizationError}</p>}<Suspense fallback={<p role="status">正在打开图片管理…</p>}><AssetLibrary key={imageCourse} token={token} courseId={imageCourse} refreshKey={assetRevision} onError={error => {setOrganizationError(error instanceof Error ? error.message : '图片操作失败'); onError(error);}} onNotice={onNotice} onChanged={() => setAssetRevision(value => value + 1)} onNote={id => { const target = notes.find(note => note.id === id); if (target) {setTool(null); void open(target);} }}/></Suspense></NotesDialog>
        <MarkdownEditor key={editorSession} value={draft.content} onChange={content => setDraft(value => ({...value, content}))} textarea={textarea} preview={preview} setPreview={setPreview} token={token} notes={notes} onNote={note => void open(note)} onSave={() => {setPaused(false); void save();}} assetRevision={assetRevision} focused={focusedEditor} setFocused={setFocusedEditor} onImage={() => showTool('insert')}/>
        <div className="editor-footer"><span className="hint">{Array.from(draft.content).length} 字符 · Markdown</span><button className="secondary" disabled={!editing || dirty || busy} onClick={() => void download()}><Icon name="download" size={15}/>导出 .md</button><button className="primary" disabled={busy || !dirty || !draft.title.trim() || !!conflict || !!tagInput.trim()} onClick={() => { setPaused(false); void save(); }}><Icon name="check" size={15}/>立即保存</button></div>
        {editing && <button className="text-button note-delete" disabled={busy || !!conflict} onClick={() => void remove()}>删除这篇笔记</button>}
        {paused && !conflict && <p role="alert">{networkRetry ? "网络连接失败，本地内容仍在；联网或返回页面后自动重试，也可点击“立即保存”。" : "自动保存已暂停，本地内容仍在。检查连接后点击“立即保存”重试。"}</p>}
        {conflict && <section className="conflict-panel" role="alert"><h3>检测到另一处修改</h3><p>上方保留你的本地草稿和标签。请先复制需要保留的内容，再选择载入服务端版本；不会自动覆盖任一版本。</p><strong>{conflict.title} · 版本 {conflict.revision}</strong><p>服务端标签：{conflict.tags.join("、") || "无标签"}</p><p>服务端文件夹：{folderPath(folders, conflict.folder_id)}</p><pre>{conflict.content}</pre><button className="secondary" onClick={() => { if (editing && window.confirm("确认载入服务端版本？上方本地草稿将被替换。")) { setEditing({ ...editing, ...conflict }); setDraft({ title: conflict.title, content: conflict.content, tags: conflict.tags, folder_id: conflict.folder_id ?? null }); setTagInput(""); setTagError(""); setConflict(null); setPaused(false); setStatus("已载入服务端版本"); } }}>载入服务端版本</button></section>}
      </section>
      </div>
      <NotesDialog open={tool === 'context'} title="引用与关联" onClose={() => {if (window.dispatchEvent(new Event('hustudy:before-material-change', {cancelable: true}))) setTool(null);}} busy={busy}>
        {organizationError && <p role="alert">{organizationError}</p>}
        <NoteCitations key={editing?.id || "new"} noteId={editing?.id} token={token} disabled={busy} onSource={onSource} onError={onError} onNotice={onNotice}/>
        <section className="panel"><h3>关联笔记</h3>{outgoing.map((match, index) => { const target = notes.find((note) => note.id === match[1]); return <button className="relation-link" disabled={!target || busy} key={`${match[1]}-${index}`} onClick={() => {if (target) {setTool(null); void open(target);}}}>↗ {target?.title || "目标笔记已删除或不可用"}</button>; })}{!outgoing.length && <EmptyInline text="插入双链，连接相关概念" />}<h4>被这些笔记引用</h4>{backlinks.map((note) => <button className="relation-link" key={note.id} disabled={busy} onClick={() => {setTool(null); void open(note);}}>↙ {note.title}</button>)}{!backlinks.length && <EmptyInline text="暂无反向链接" />}</section>
      </NotesDialog>
    </div>
    <NotesDialog open={tool === 'templates'} title="学习模板" onClose={() => setTool(null)}><p className="hint">追加到正文，保留已有内容。</p>{templates.map(template => <button key={template.name} className="template-card" onClick={() => {setDraft(value => ({...value, title: value.title || template.name, content: value.content + '\n' + template.content})); setTool(null);}}><Icon name="notes" size={16}/><span>{template.name}</span><Icon name="plus" size={15}/></button>)}</NotesDialog>
    <NotesDialog open={tool === 'speech'} title="语音输入" onClose={() => setTool(null)}>{recognitionError && <p role="alert">{recognitionError}</p>}<SpeechInput open={tool === 'speech'} disabled={busy || !!conflict} onInsert={insertRecognition}/></NotesDialog>
    <NotesDialog open={tool === 'capture'} title="文字识别" onClose={() => setTool(null)} busy={captureBusy}>{recognitionError && <p role="alert">{recognitionError}</p>}<NoteCapture token={token} courseId={imageCourse} isOpen={tool === 'capture'} disabled={busy || !!conflict} onInsert={insertRecognition} onError={onError} onBusy={setCaptureBusy}/></NotesDialog>
    <NotesDialog open={tool === 'import'} title="导入 Markdown" onClose={() => setTool(null)} busy={busy}>{organizationError && <p role="alert">{organizationError}</p>}<MarkdownImport token={token} courseId={courseId} folders={folders} disabled={organizationDisabled} perform={performOrganization} onImported={mergeNotes}/></NotesDialog>
    <NotesDialog open={tool === 'export'} title="导出笔记" onClose={() => setTool(null)} busy={exportBusy}>{organizationError && <p role="alert">{organizationError}</p>}<NoteExports token={token} notes={notes} courseId={courseId} unsaved={organizationDisabled} onError={onError} selection={exportSelection} onBusyChange={setExportBusy} isOpen={tool === 'export'}/></NotesDialog>
    {(['batch', 'tags', 'recommend'] as const).map(mode => <NotesDialog key={mode} open={tool === mode} title={{batch: '批量整理', tags: '标签管理', recommend: '推荐归类'}[mode]} onClose={() => setTool(null)} busy={busy}>{organizationError && <p role="alert">{organizationError}</p>}<NoteOrganizer mode={mode} token={token} notes={courseNotes} folders={folders} selected={selectedNotes} setSelected={setSelectedNotes} disabled={organizationDisabled} perform={performOrganization} onChanged={mergeNotes} suggestedFolder={folderFilter}/></NotesDialog>)}
    <NotesDialog open={tool === 'trash'} title="笔记回收站" onClose={() => setTool(null)} busy={busy}>
      <NoteTrash token={token} courseId={courseId} open={tool === 'trash'} disabled={organizationDisabled} perform={performOrganization} onChanged={async () => {setNotes(await api.notes(token)); setSelectedNotes([]); if (editing) setBacklinks(await api.backlinks(token, editing.id));}} onError={onError} onNotice={onNotice}/>
    </NotesDialog>
  </div>;
}
