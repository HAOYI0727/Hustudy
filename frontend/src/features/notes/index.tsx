import { Icon } from "../../components/Icon";
import { CompactLibrary } from "../../components/CompactLibrary";
import { lazy, Suspense, useEffect, useRef, useState, type DragEvent } from "react";
import { api, ApiError, Note, Asset, noteSummary, type NoteSummary, type NoteFolder } from "../../api/client";
import {sessionPartition} from '../../api/query';
import { EmptyInline } from "../../components/workspace";
import {loadNoteCatalog} from "./noteCatalog";
import { addNoteTag } from "./tags";
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
import {NoteReader} from "./NoteReader";
import {NoteAssistant,type AssistantSource,type AssistantApply} from './NoteAssistant';
import {readAutoSavePreference, writeAutoSavePreference} from './notePreferences';
import {folderOptions, folderPath, insideFolder} from "./organization";
import {NotesDialog} from './NotesDialog';
import {NoteManager} from './NoteManager';
import {NoteRecoveryPanel} from "./NoteRecoveryPanel";
import {NoteMergeDialog} from './NoteMergeDialog';
import {downloadDraft} from './draftDownload';
import {recoveryCopies,saveRecovery,removeRecovery,type NoteRecovery,type NoteDraft,type PendingNote,type RecoveryCitation} from "./noteRecovery";
import {NoteTrash} from './NoteTrash';
import {NOTE_DRAG_TYPE, canDropNotes, type NoteDrag} from './noteDragging';
import "./notes.css";

const AssetLibrary = lazy(() => import("../materials/AssetLibrary").then(module => ({default: module.AssetLibrary})));
const NoteGraph = lazy(() => import("./NoteGraph"));
const PackageTransfer = lazy(() => import('../packages/PackageTransfer'));
import type {PackageIntent} from '../packages/PackageTransfer';

type Props = { onCoursesChanged?: () => Promise<void>; onSource: (versionId: string, chunkId: string) => void; initialNoteId?: string; token: string; courseId: string; onNotice: (s: string) => void; onError: (e: unknown) => void };
type Draft = NoteDraft;
type Conflict = Draft & { revision: number; base: Draft | null };
const noteDraft = (note: Draft): Draft => ({title: note.title, content: note.content, tags: [...note.tags], folder_id: note.folder_id ?? null});
const templates = [
  { name: "概念学习", content: "## 学习目标\n\n## 概念与原理\n\n## 例子\n\n## 常见误区\n\n## 自测问题\n" },
  { name: "错题复盘", content: "## 原题与来源\n\n## 我的思路\n\n## 出错原因\n\n## 正确解法\n\n## 下次如何识别\n" },
  { name: "课前预习", content: "## 已知内容\n\n## 不理解的问题\n\n## 课堂核实\n\n## 课后总结\n" },
];

export function Notes({ token, courseId, onNotice, onError: reportError, initialNoteId, onSource, onCoursesChanged }: Props) {
  const [catalogFailed,setCatalogFailed]=useState(false),[catalogLoading,setCatalogLoading]=useState(true);
  const [pageOffset,setPageOffset]=useState(0),[matchIds,setMatchIds]=useState<string[]|null>(null),[matchFailed,setMatchFailed]=useState(false),[matchLoading,setMatchLoading]=useState(false),[matchReload,setMatchReload]=useState(0);
  const [opening, setOpening] = useState(!!initialNoteId);
  const [openingNote, setOpeningNote] = useState(false);
  const [notes, setNotes] = useState<NoteSummary[]>([]);
  const [folders, setFolders] = useState<NoteFolder[]>([]);
  const [folderFilter, setFolderFilter] = useState("*");
  const [selectedNotes, setSelectedNotes] = useState<string[]>([]);
  const [workspaceView, setWorkspaceView] = useState<'manage' | 'edit' | 'read'>(initialNoteId ? 'edit' : 'manage');
  const [tool, setTool] = useState<'import' | 'export' | 'batch' | 'tags' | 'recommend' | 'metadata' | 'insert' | 'images' | 'context' | 'templates' | 'trash' | 'capture' | 'speech' | 'graph' | 'assistant' | null>(null);
  const [assistantSource,setAssistantSource]=useState<AssistantSource|null>(null);
  const [graphFocus, setGraphFocus] = useState<string>();
  const [packageIntent,setPackageIntent]=useState<PackageIntent|null>(null),[packageVisited,setPackageVisited]=useState(false);
  const packageSerial=useRef(0);
  const showPackage=(mode:'import'|'export',folderId?:string)=>{setTool(null);setPackageVisited(true);setPackageIntent({mode,kind:'folder',courseId,folderId,nonce:++packageSerial.current});};
  const [exportSelection, setExportSelection] = useState({ids: [] as string[], version: 0});
  const [organizationError, setOrganizationError] = useState('');
  const [exportBusy, setExportBusy] = useState(false);
  const [captureBusy, setCaptureBusy] = useState(false);
  const [recognitionError, setRecognitionError] = useState('');
  const recognitionTarget = useRef<{session: number; content: string; start: number; end: number} | null>(null);
  const onError = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401) {setTool(null); setMergeSession(null); window.dispatchEvent(new Event('hustudy:notes-session-expired'));}
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
  const [backlinks, setBacklinks] = useState<NoteSummary[]>([]);
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
  const expiredSession = useRef({token, expired: false});
  const pendingCreate = useRef<PendingNote | null>(null);
  const draftCitations=useRef<RecoveryCitation[]>([]);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [mergeSession, setMergeSession] = useState<{noteId: string; local: Draft; server: Conflict; tagInput: string} | null>(null);
  const mergeTrigger = useRef<HTMLButtonElement>(null);
  const closeMerge = () => {setMergeSession(null);requestAnimationFrame(()=>mergeTrigger.current?.focus());};
  // Old recovery records may identify a revision without containing its original body.
  const unavailableBase = useRef<{id: string; revision: number} | null>(null);
  const confirmedBase = (note: Note | null) => note && !(unavailableBase.current?.id === note.id && unavailableBase.current.revision === note.revision) ? noteDraft(note) : null;
  const lock = useRef(false);
  const loadedInitial = useRef<string | undefined>(undefined);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const imageInput = useRef<HTMLInputElement>(null);
  const dirty = draft.title !== (editing?.title || "") || draft.content !== (editing?.content || "") || JSON.stringify(draft.tags) !== JSON.stringify(editing?.tags ?? []) || (!!editing && (draft.folder_id ?? null) !== (editing.folder_id ?? null)) || !!tagInput.trim();
  const organizationDisabled = dirty || busy || !!conflict;
  const [recoveryOwner,setRecoveryOwner]=useState("");
  const [autoSave, setAutoSave] = useState(false);
  const [preferenceNotice, setPreferenceNotice] = useState('');
  useEffect(() => {setAutoSave(readAutoSavePreference(recoveryOwner)); setPreferenceNotice('');}, [recoveryOwner]);
  const chooseAutoSave = (enabled: boolean) => {
    setAutoSave(enabled);
    setPreferenceNotice(writeAutoSavePreference(recoveryOwner, enabled) ? '' : '已应用本次选择；浏览器无法记住设置，下次打开请重新核对。');
  };
  const [copies,setCopies]=useState<NoteRecovery[]>([]),[recoveryError,setRecoveryError]=useState(""),[recoveryMessage,setRecoveryMessage]=useState("");
  const recoveryId=useRef(crypto.randomUUID()), recoveryLatest=useRef({draft,editing,tagInput,dirty,owner:recoveryOwner});
  recoveryLatest.current={draft,editing,tagInput,dirty,owner:recoveryOwner};
  const refreshRecovery=()=>{
    if(!recoveryOwner)return;const result=recoveryCopies(recoveryOwner,courseId);setCopies(result.items.filter(row=>row.id!==recoveryId.current));
    if(!result.available)setRecoveryError("浏览器存储不可用，无法读取本机恢复副本。");
  };
  const persistRecovery=(force=false)=>{
    const current=recoveryLatest.current;
    if(!current.owner)return force?"恢复副本尚未就绪，请先下载草稿或稍后重试。":"";
    if(!current.dirty&&!force)return "";
    return saveRecovery({id:recoveryId.current,userId:current.owner,courseId,noteId:current.editing?.id||null,noteCourseId:current.editing?.course_id||null,baseRevision:current.editing?.revision||null,base:confirmedBase(current.editing),draft:current.draft,tagInput:current.tagInput,pending:pendingCreate.current,citations:current.editing?undefined:draftCitations.current,updatedAt:new Date().toISOString()});
  };
  const retainOriginalDraft=()=>{
    const failure=persistRecovery(true);
    if(failure){setRecoveryError(failure);return failure;}
    recoveryId.current=crypto.randomUUID();
    refreshRecovery();
    return "";
  };
  const applyMerge=(merged:Draft):string=>{
    if(!mergeSession||!editing||busy||editing.id!==mergeSession.noteId||conflict!==mergeSession.server||JSON.stringify(draft)!==JSON.stringify(mergeSession.local)||tagInput!==mergeSession.tagInput)return "草稿或服务端版本已变化，请关闭窗口后重新核对合并。";
    const failure=retainOriginalDraft();if(failure)return failure;
    unavailableBase.current=null;
    setEditing({...editing,...noteDraft(mergeSession.server),revision:mergeSession.server.revision});
    setDraft(merged);setConflict(null);setMergeSession(null);setPaused(true);setNetworkRetry(false);
    const unchanged=JSON.stringify(noteDraft(merged))===JSON.stringify(noteDraft(mergeSession.server));
    setStatus(unchanged?"合并结果与服务端一致 · 无需保存":"合并已应用到草稿 · 请核对后立即保存");
    setRecoveryMessage(unchanged?"合并前的本地草稿已保留为独立恢复副本，当前结果与服务端一致。":"合并前的本地草稿已保留为独立恢复副本。合并结果尚未保存到服务端。");
    requestAnimationFrame(()=>textarea.current?.focus());
    return "";
  };
  useEffect(()=>{
    const expired=()=>setMergeSession(null);
    window.addEventListener('hustudy:notes-session-expired',expired);
    return()=>window.removeEventListener('hustudy:notes-session-expired',expired);
  },[]);
  useEffect(()=>{
    const session = {token, expired: false};
    expiredSession.current = session;
    const expired=(event:Event)=>{
      if((event as CustomEvent).detail!==sessionPartition(token))return;
      session.expired = true;
      setTool(null); setFocusedEditor(false); setPaused(true); setNetworkRetry(false);
      setStatus("登录已过期 · 本地草稿已保留");
      setMergeSession(null);
      window.dispatchEvent(new Event('hustudy:notes-session-expired'));
    };
    window.addEventListener('hustudy:unauthorized',expired);
    return()=>window.removeEventListener('hustudy:unauthorized',expired);
  },[token]);
  useEffect(()=>{
    let live=true;
    void api.me(token).then(user=>{if(!live)return;setRecoveryOwner(user.id);const result=recoveryCopies(user.id,courseId);setCopies(result.items.filter(row=>row.id!==recoveryId.current));if(!result.available)setRecoveryError("浏览器存储不可用，请及时保存正文。");}).catch(error=>{if(live)onError(error);});
    return()=>{live=false;};
  },[token,courseId]);
  useEffect(()=>{
    if(!recoveryOwner)return;
    if(!dirty){removeRecovery({userId:recoveryOwner,courseId,id:recoveryId.current});return;}
    const timer=window.setTimeout(()=>setRecoveryError(persistRecovery()),250);
    return()=>window.clearTimeout(timer);
  },[draft,tagInput,editing,dirty,recoveryOwner]);
  useEffect(()=>{
    const flush=()=>{const error=persistRecovery();if(error)setRecoveryError(error);};
    const hidden=()=>{if(document.visibilityState!=="visible")flush();};
    window.addEventListener("pagehide",flush);window.addEventListener("beforeunload",flush);document.addEventListener("visibilitychange",hidden);
    return()=>{persistRecovery();window.removeEventListener("pagehide",flush);window.removeEventListener("beforeunload",flush);document.removeEventListener("visibilitychange",hidden);};
  },[courseId]);
  const restoreCopy=async(row:NoteRecovery)=>{
    if(lock.current||row.userId!==recoveryOwner||row.courseId!==courseId)return;
    if(dirty&&!window.confirm("当前草稿有修改，先保留恢复副本，再载入这份恢复内容？"))return;
    const failure=persistRecovery();if(failure){setRecoveryError(failure);return;}
    lock.current=true;setBusy(true);setRecoveryMessage("");
    try{
      const fresh=row.noteId?await api.note(token,row.noteId):null;
      if(fresh&&(fresh.course_id||null)!==row.noteCourseId)throw new Error("原笔记课程已变化，暂不能恢复；可展开副本复制正文。");
      recoveryId.current=crypto.randomUUID();
      // A create-409 snapshot can have the current revision without being an ancestor.
      // Missing/explicitly unknown bases stay unknown across reloads, even at equal revisions.
      const base=row.base??null;
      const needsReview=!!fresh&&(fresh.revision!==row.baseRevision||!base);
      unavailableBase.current=fresh&&!base?{id:fresh.id,revision:row.baseRevision||fresh.revision}:null;
      setEditing(fresh?{...fresh,...(base||{}),revision:row.baseRevision||fresh.revision}:null);
      setDraft({...row.draft});setTagInput(row.tagInput);pendingCreate.current=row.pending;draftCitations.current=row.citations||[];
      setConflict(fresh&&needsReview?{...noteDraft(fresh),revision:fresh.revision,base}:null);setMergeSession(null);
      setPaused(true);setNetworkRetry(false);setWorkspaceView('edit');setEditorSession(value=>value+1);
      setRecoveryMessage(needsReview?"已恢复本地草稿；服务端版本变化或共同版本缺失，请在编辑区核对冲突。":"恢复内容尚未写入服务端，请核对后点击立即保存。原恢复副本保留，可手动删除。");
      setStatus("已恢复本机草稿 · 请核对后立即保存");
    }catch(error){setRecoveryMessage("原笔记无法核对，副本已保留；可展开复制正文，不会自动创建笔记。");onError(error);}
    finally{lock.current=false;setBusy(false);}
  };

  const refreshFolders = async () => setFolders(await api.noteFolders(token, courseId));
  useEffect(() => {
    let live = true; setFolders([]); setFolderFilter("*"); setSelectedNotes([]);
    void api.noteFolders(token, courseId).then(rows => {if (live) setFolders(rows);}).catch(error => {if (live) onError(error);});
    return () => {live = false;};
  }, [token, courseId]);
  const mergeNotes = (changed: Note[]) => {
    setNotes(rows => [...changed.map(noteSummary), ...rows.filter(row => !changed.some(item => item.id === row.id))]);
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
    if(next==='assistant'){
      if(busy||conflict||workspaceView!=='edit')return;
      setAssistantSource({session:editorSession,title:draft.title,content:draft.content,start:textarea.current?.selectionStart??0,end:textarea.current?.selectionEnd??0,noteId:editing?.id,revision:editing?.revision,courseId:editing?.course_id||courseId});
    }
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
  const applyAssistant = (text:string,mode:AssistantApply):string => {
    const source=assistantSource;
    if(!source||busy||conflict||source.session!==editorSession||source.content!==draft.content||source.title!==draft.title||source.noteId!==editing?.id||source.revision!==editing?.revision)return '笔记或草稿已变化，请关闭助手后重新预览，当前内容没有改动。';
    const next=mode==='append'?draft.content+'\n\n'+text:mode==='selection'?draft.content.slice(0,source.start)+text+draft.content.slice(source.end):text;
    setDraft(value=>({...value,content:next}));setPreview(false);setTool(null);setStatus('AI建议已采纳到草稿 · 待保存');
    requestAnimationFrame(()=>{textarea.current?.focus();const position=mode==='selection'?source.start+text.length:next.length;textarea.current?.setSelectionRange(position,position);});
    return '';
  };
  const startDrag = (event: DragEvent, value: NoteDrag) => {
    if (organizationDisabled || (value.kind === 'notes' && value.notes.length > 200)) {event.preventDefault(); return;}
    dragRef.current = value; setDrag(value);
    event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData(NOTE_DRAG_TYPE, 'internal');
  };
  const dragNote = (event: DragEvent, note: NoteSummary) => startDrag(event, {kind: 'notes', notes: (selectedNotes.includes(note.id) ? notes.filter(n => n.course_id === courseId && selectedNotes.includes(n.id)) : [note]).map(n => ({id: n.id, revision: n.revision, folder_id: n.folder_id}))});
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
    setCatalogLoading(true);setCatalogFailed(false);
    void loadNoteCatalog(token).then(rows => {if(active)setNotes(rows);}).catch(error=>{if(active){setCatalogFailed(true);onError(error);}}).finally(()=>{if(active)setCatalogLoading(false);});
    return () => { active = false; };
  }, [courseId, token, initialNoteId]);
  useEffect(()=>{
    if(!initialNoteId||loadedInitial.current===initialNoteId){setOpening(false);return;}
    let active=true;setOpening(true);
    void api.note(token,initialNoteId).then(note=>{
      if(!active)return;
      if(note.course_id!==courseId)throw new Error("这篇笔记不在当前课程");
      loadedInitial.current=initialNoteId;setEditing(note);setDraft({title:note.title,content:note.content,tags:note.tags,folder_id:note.folder_id??null});setEditorSession(value=>value+1);setStatus("已载入保存版本");
    }).catch(error=>{if(active)onError(error);}).finally(()=>{if(active)setOpening(false);});
    return()=>{active=false;};
  },[token,courseId,initialNoteId]);
  useEffect(() => {
    let active = true;
    setBacklinks([]);
    if (editing) void api.backlinkOptions(token, editing.id).then((rows) => { if (active) setBacklinks(rows); }).catch(onError);
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
    const session = expiredSession.current;
    if (session.expired || session.token !== token || lock.current || !draft.title.trim() || !dirty || conflict || tagInput.trim()) return;
    lock.current = true; setBusy(true); setNetworkRetry(false); setStatus("正在保存…");
    const snapshot = { ...draft };
    if (!editing) pendingCreate.current ??= {...snapshot, course_id: courseId, request_id: crypto.randomUUID(),citations:draftCitations.current};
    setRecoveryError(persistRecovery());
    try {
      const saved = editing
        ? await api.updateNote(token, editing.id, { ...snapshot, revision: editing.revision })
        : await api.createNote(token, pendingCreate.current!);
      pendingCreate.current = null;draftCitations.current=[];
      removeRecovery({userId:recoveryOwner,courseId,id:recoveryId.current});
      const interrupted = session.expired || session !== expiredSession.current;
      unavailableBase.current=null;setEditing(saved); setPaused(interrupted);
      setStatus(expiredSession.current.expired ? "登录已过期 · 本地草稿已保留" : interrupted ? "保存请求已完成 · 请核对剩余草稿并手动保存" : "已保存到本地服务");
      setNotes((rows) => [noteSummary(saved), ...rows.filter((row) => row.id !== saved.id)]);
    } catch (error) {
      setPaused(true); setStatus(expiredSession.current.expired ? "登录已过期 · 本地草稿已保留" : "未保存 · 请处理后重试");
      setNetworkRetry(!session.expired && session === expiredSession.current && error instanceof ApiError && error.status === 0);
      if (error instanceof ApiError && error.status === 422) pendingCreate.current = null;
      if (error instanceof ApiError && error.status === 409 && error.details) {
        if (!editing && error.details.server_id === pendingCreate.current?.request_id) {
          unavailableBase.current={id:String(error.details.server_id),revision:Number(error.details.server_revision)};
          setEditing({id: String(error.details.server_id), course_id: courseId, title: String(error.details.server_title || ""), content: String(error.details.server_content || ""), tags: Array.isArray(error.details.server_tags) ? error.details.server_tags as string[] : [], folder_id: error.details.server_folder_id as string | null ?? null, revision: Number(error.details.server_revision), updated_at: ""});
          pendingCreate.current = null;
        }
        setConflict({ title: String(error.details.server_title || ""), content: String(error.details.server_content || ""), tags: Array.isArray(error.details.server_tags) ? error.details.server_tags as string[] : [], folder_id: error.details.server_folder_id as string | null ?? null, revision: Number(error.details.server_revision), base: confirmedBase(editing) });
      } else onError(error);
    } finally { lock.current = false; setBusy(false); }
  };
  useEffect(() => {
    const session = expiredSession.current;
    const recover = () => {
      if (!session.expired && session === expiredSession.current && session.token === token && autoSave && networkRetry && navigator.onLine && document.visibilityState === "visible") {
        setPaused(false); setNetworkRetry(false); setStatus("连接已恢复 · 等待保存");
      }
    };
    window.addEventListener("online", recover);
    document.addEventListener("visibilitychange", recover);
    const timer = networkRetry ? window.setTimeout(recover, 15000) : undefined;
    return () => { window.clearTimeout(timer); window.removeEventListener("online", recover); document.removeEventListener("visibilitychange", recover); };
  }, [networkRetry, autoSave, token]);
  useEffect(() => {
    const session = expiredSession.current;
    if (session.expired || session.token !== token || !autoSave || workspaceView === 'read' || tool === 'assistant' || !foreground || !dirty || busy || paused || conflict || !draft.title.trim() || tagInput.trim()) return;
    const timer = window.setTimeout(() => { if (!session.expired && session === expiredSession.current && document.visibilityState === "visible") void save(); }, 2000);
    return () => window.clearTimeout(timer);
  }, [draft, editing, busy, paused, conflict, tagInput, foreground, workspaceView, autoSave, token, tool]);

  const changeView = (view: 'manage' | 'edit' | 'read') => {setFocusedEditor(false); setWorkspaceView(view);};
  const open = async (note?: NoteSummary, view: 'edit' | 'read' = 'edit') => {
    if (lock.current) return;
    if (note && note.id === editing?.id) {changeView(view); return true;}
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable: true}))) return;
    if (dirty && !window.confirm("当前有未保存内容。确认放弃这些修改并切换？")) return;
    lock.current = true; setBusy(true); setOpeningNote(true);
    try {
      const fresh = note ? await api.note(token, note.id) : null;
      if (fresh) setNotes(rows => [noteSummary(fresh), ...rows.filter(row => row.id !== fresh.id)]);
      persistRecovery();recoveryId.current=crypto.randomUUID();
      unavailableBase.current=null;setMergeSession(null);
      setEditing(fresh); setDraft({ title: fresh?.title || "", content: fresh?.content || "", tags: fresh?.tags ?? [], folder_id: fresh ? fresh.folder_id ?? null : folders.some(f => f.id === folderFilter) ? folderFilter : null });
      setEditorSession(value => value + 1); changeView(view);
      setTagInput(""); setTagError(""); setUploadError("");
      setUploadFailures([]); setUploadSummary("");
      pendingCreate.current = null;draftCitations.current=[]; setNetworkRetry(false);
      setConflict(null); setPaused(false); setStatus(fresh ? "已载入保存版本" : "新笔记 · 请填写标题和正文");
      return true;
    } catch (error) { onError(error); } finally { lock.current = false; setBusy(false); setOpeningNote(false); }
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
        setConflict({title: String(error.details.server_title || ""), content: String(error.details.server_content || ""), tags: Array.isArray(error.details.server_tags) ? error.details.server_tags as string[] : [], folder_id: error.details.server_folder_id as string | null ?? null, revision: Number(error.details.server_revision),base:confirmedBase(editing)});
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
  const filtered = courseNotes.filter(note => ((!search.trim()&&!tagFilter)||matchIds?.includes(note.id)) && (folderFilter === "*" || (folderFilter === "" ? !note.folder_id : insideFolder(folders, note.folder_id, folderFilter))));
  const visibleNotes=filtered.slice(pageOffset,pageOffset+20);
  useEffect(()=>{setPageOffset(0);},[search,tagFilter,folderFilter]);
  useEffect(()=>{if(pageOffset&&pageOffset>=filtered.length)setPageOffset(filtered.length?Math.floor((filtered.length-1)/20)*20:0);},[filtered.length,pageOffset]);
  useEffect(()=>{
    let live=true;setMatchFailed(false);setMatchIds(null);
    if(!search.trim()&&!tagFilter){setMatchLoading(false);return;}
    setMatchLoading(true);
    const timer=window.setTimeout(()=>{void api.noteMatches(token,courseId,search,tagFilter).then(result=>{if(live)setMatchIds(result.ids);}).catch(error=>{if(live){setMatchFailed(true);onError(error);}}).finally(()=>{if(live)setMatchLoading(false);});},180);
    return()=>{live=false;window.clearTimeout(timer);};
  },[token,courseId,search,tagFilter,notes,matchReload]);
  const refreshCatalog=async()=>{
    setCatalogLoading(true);setCatalogFailed(false);
    try{const rows=await loadNoteCatalog(token);setNotes(rows);}
    catch(error){setCatalogFailed(true);onError(error);}
    finally{setCatalogLoading(false);}
  };
  const notePages=(label:string)=><nav className="catalogue-pages" aria-label={label}><button className="secondary" disabled={pageOffset===0||catalogLoading||matchLoading} onClick={()=>setPageOffset(Math.max(0,pageOffset-20))}>上一页笔记</button><span>{Math.floor(pageOffset/20)+1} / {Math.max(1,Math.ceil(filtered.length/20))} 页 · {filtered.length} 篇</span><button className="secondary" disabled={pageOffset+20>=filtered.length||catalogLoading||matchLoading} onClick={()=>setPageOffset(pageOffset+20)}>下一页笔记</button></nav>;

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
    <header className="notes-workspace-heading"><div><span className="eyebrow">PERSONAL KNOWLEDGE</span><h1>我的笔记 <small>{courseNotes.length}</small></h1></div><div className="notes-workspace-tools"><button className="secondary" onClick={() => {setGraphFocus(undefined);showTool('graph');}}>关系图谱</button><button className="secondary" onClick={() => showTool('trash')}>回收站</button><button className="secondary" onClick={() => showTool('import')}>导入 Markdown</button><button className="secondary" onClick={()=>showPackage("import",folderFilter!=="*"&&folderFilter?folderFilter:undefined)}>标准数据包</button><button className="secondary" onClick={() => showTool('export')}>选择笔记导出</button><button className="secondary" onClick={() => showTool('tags')}>标签管理</button><button className="secondary" onClick={() => showTool('recommend')}>推荐归类</button><button className="primary" disabled={busy} onClick={() => void open()}><Icon name="plus" size={16}/>新建笔记</button></div></header>
    <NoteRecoveryPanel items={copies} busy={busy} error={recoveryError} message={recoveryMessage} onRestore={row=>void restoreCopy(row)} onRefresh={refreshRecovery} onRemove={row=>{if(window.confirm("删除这份本机恢复副本？不会删除服务端笔记。")){if(removeRecovery(row))refreshRecovery();else setRecoveryError("无法删除副本，请检查浏览器存储权限。");}}}/>
    {catalogLoading&&<p role="status">正在读取笔记目录，正文按需打开…</p>}
    {catalogFailed&&<p role="alert">笔记目录暂未完整加载。<button className="secondary" onClick={()=>void refreshCatalog()}>重试笔记目录</button></p>}
    {matchLoading&&<p role="status">正在查找笔记标题、正文与标签…</p>}
    {matchFailed&&<p role="alert">笔记筛选未完成。<button className="secondary" onClick={()=>setMatchReload(value=>value+1)}>重试笔记筛选</button></p>}
    {moveNotice && <p className="note-operation-notice" role="status">{moveNotice}</p>}
    <div className="knowledge-layout">
      <CompactLibrary className="panel knowledge-library" label="笔记列表与新建">
        <div className="panel-title"><h3>课程笔记</h3><span className="count-pill">{courseNotes.length}</span></div>
        <FolderLibrary token={token} courseId={courseId} folders={folders} notes={courseNotes} selected={folderFilter} onSelect={setFolderFilter} disabled={organizationDisabled} perform={performOrganization} refresh={refreshFolders} drag={drag} startDrag={startDrag} endDrag={endDrag} drop={drop} error={organizationError} onImportPackage={id=>showPackage("import",id)} onExportPackage={id=>showPackage("export",id)}/>
        <p className="hint note-nav-caption">快速打开 · {filtered.length} 篇</p>
        <div className="list">{visibleNotes.map((note) => <button key={note.id} title={note.title} draggable={!organizationDisabled} onDragStart={e => dragNote(e, note)} onDragEnd={endDrag} disabled={busy} className={`knowledge-item ${note.id === editing?.id ? "selected" : ""}`} onClick={() => void open(note, workspaceView === 'read' ? 'read' : 'edit')}><Icon name="notes" size={15}/><strong>{note.title}</strong></button>)}</div>
        {notePages("目录翻页")}
        {!filtered.length && !catalogFailed && !matchFailed && !catalogLoading && !matchLoading && <EmptyInline text={search || tagFilter ? "未找到匹配笔记，试试其他关键词或标签" : "从一个概念开始记录"} />}
      </CompactLibrary>
      <div className="notes-main"><nav className="notes-view-tabs" aria-label="笔记工作区视图"><button aria-pressed={workspaceView === 'manage'} onClick={() => changeView('manage')}>笔记管理</button><button aria-label={editing ? '编辑笔记' : '编辑草稿'} aria-description={dirty ? '有未保存修改' : undefined} aria-pressed={workspaceView === 'edit'} onClick={() => changeView('edit')}>{editing ? '编辑笔记' : '编辑草稿'}{dirty && <span className="draft-dot" aria-hidden="true"/>}</button><button aria-pressed={workspaceView === 'read'} disabled={busy || (!editing && !draft.content && !draft.title)} onClick={() => changeView('read')}><Icon name="preview" size={16}/>阅读模式</button></nav>
      <div hidden={workspaceView !== 'manage'}><NoteManager notes={visibleNotes} total={filtered.length} folders={folders} selected={selectedNotes} setSelected={setSelectedNotes} disabled={organizationDisabled} search={search} setSearch={setSearch} tag={tagFilter} setTag={setTagFilter} tags={availableTags} path={folderFilter === '*' ? '全部笔记' : folderPath(folders, folderFilter)} onOpen={note => void open(note)} onRead={note => void open(note, 'read')} onTool={showTool} onRefresh={()=>void refreshCatalog()} onDrag={dragNote} onDragEnd={endDrag} onDelete={removeSelected}/>{notePages("笔记管理分页")}{organizationDisabled && <p className="hint">请先保存或处理编辑区的草稿，再批量整理或拖动笔记。</p>}</div>
      {workspaceView === 'read' && <NoteReader
        title={draft.title} content={draft.content} tags={draft.tags}
        path={editing && editing.course_id !== courseId ? editing.course_id ? '其他课程的关联笔记' : '未分类的关联笔记' : folderPath(folders, draft.folder_id)}
        noteId={editing?.id} token={token} notes={notes} courseId={editing?.course_id||courseId} assetRevision={assetRevision} disabled={busy}
        notice={conflict ? '存在版本冲突，当前显示本地草稿。请返回编辑处理冲突。' : dirty ? '当前显示未保存草稿，阅读期间暂停自动保存；返回编辑后继续处理。' : busy ? '正在处理，请稍候…' : ''}
        onNote={note => void open(note, 'read')}
        onEdit={() => {changeView('edit'); requestAnimationFrame(() => textarea.current?.focus({preventScroll: true}));}}
        sources={<NoteCitations key={editing?.id || 'new'} noteId={editing?.id} token={token} disabled={busy} readOnly onSource={onSource} onError={onError} onNotice={onNotice}/>}
      />}
      <section hidden={workspaceView !== 'edit'} className={`panel knowledge-editor ${focusedEditor ? "is-focused" : ""}`} inert={organizing || openingNote} aria-busy={organizing || openingNote}>
        {editing && editing.course_id !== courseId && <p className="hint" role="status">当前打开的是{editing.course_id ? "其他课程" : "未分类"}的关联笔记；保存会保留其原有归属。</p>}
        <div className="panel-title"><h3>{editing ? "编辑笔记" : "新建笔记"}</h3><span className={`save-indicator ${dirty ? "unsaved" : ""}`} role="status"><Icon name={busy ? "refresh" : paused || conflict ? "info" : dirty ? "edit" : editing ? "check" : "notes"} size={13} className={busy ? "is-spinning" : ""}/>{openingNote ? "正在打开笔记…" : uploading ? "正在上传图片…" : busy ? "保存中…" : dirty && !paused ? autoSave ? "有修改待保存" : "未保存 · 手动保存" : status}</span></div>
        <div className="note-save-preference"><label><input type="checkbox" aria-label="自动保存笔记" checked={autoSave} disabled={!recoveryOwner} onChange={event => chooseAutoSave(event.target.checked)}/>自动保存</label><span className="hint">{autoSave ? '停止输入约 2 秒保存；阅读时暂停。' : '手动保存 · 点击“立即保存”或按 Ctrl/Cmd+S。'}本机恢复副本不等于已保存。</span>{preferenceNotice && <span className="hint" role="status">{preferenceNotice}</span>}</div>
        <input className="title-input" aria-label="笔记标题" maxLength={240} placeholder="为这份理解起一个名字" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
        <button className="text-button note-preview-toggle" aria-pressed={preview} onClick={() => setPreview(!preview)}>{preview ? '继续编辑' : 'Markdown 预览'}</button>
        <div className="note-editor-tools"><button className="primary" disabled={busy || !!conflict || !draft.content.trim()} onClick={() => showTool("assistant")}>笔记AI助手</button><button className="primary" disabled={busy || !!conflict} onClick={() => showTool('speech')}>语音输入</button><button className="secondary" onClick={() => showTool('capture')}>文字识别</button><button className="secondary" onClick={() => showTool('metadata')}>文件夹与标签{draft.tags.length ? ` · ${draft.tags.length}` : ''}</button><button className="secondary" onClick={() => showTool('images')}>管理图片</button><button className="secondary" onClick={() => showTool('context')}>引用与关联 · {outgoing.length + backlinks.length}</button><button className="secondary" onClick={() => showTool('templates')}>学习模板</button><span className="hint">{folderPath(folders, draft.folder_id)}</span></div>
        <NotesDialog open={tool === "assistant"} title="笔记AI助手" onClose={() => setTool(null)}>{tool === "assistant" && assistantSource && <NoteAssistant token={token} source={assistantSource} notes={notes} onApply={applyAssistant} onError={onError}/>}</NotesDialog>
        <NotesDialog open={tool === 'metadata'} title="文件夹与标签" onClose={() => setTool(null)} busy={busy}>
        {conflict ? <p role="alert">检测到另一处修改，本地标签和草稿已保留。关闭窗口后在编辑区处理冲突。</p> : organizationError ? <p role="alert">{organizationError}</p> : <p className="hint" role="status">{dirty ? autoSave ? '已开启自动保存。' : '修改尚未保存，请点击立即保存或使用 Ctrl/Cmd+S。' : status}</p>}
        <label className="note-filter">所在文件夹<select aria-label="笔记所在文件夹" value={draft.folder_id || ""} disabled={busy || !!conflict || (!!editing && editing.course_id !== courseId)} onChange={e => setDraft(value => ({...value, folder_id: e.target.value || null}))}><option value="">未归档</option>{folderOptions(folders).map(f => <option key={f.id} value={f.id}>{f.path}</option>)}{draft.folder_id && !folders.some(f => f.id === draft.folder_id) && <option value={draft.folder_id}>保留原文件夹归属</option>}</select></label>
        <section className="note-tag-editor" aria-label="笔记标签">
          <div className="note-tag-heading"><strong>标签</strong><span className="hint">{draft.tags.length} / 12</span></div>
          <div className="note-tags">{draft.tags.map(tag => <span className="note-tag" key={tag}><span>#{tag}</span><button type="button" className="text-button" aria-label={`移除标签 ${tag}`} onClick={() => { setDraft(value => ({ ...value, tags: value.tags.filter(item => item !== tag) })); setTagError(""); }}>×</button></span>)}</div>
          <div className="note-tag-input"><input aria-label="新标签" aria-describedby="note-tag-help" value={tagInput} placeholder="例如：期末重点" onChange={e => { setTagInput(e.target.value); setTagError(""); }} onKeyDown={e => { if (e.key === "Enter" && !e.nativeEvent.isComposing) { e.preventDefault(); addTag(); } }} /><button type="button" className="secondary" disabled={!tagInput.trim()} onClick={addTag}>添加标签</button></div>
          <p id="note-tag-help" className="hint">输入后按 Enter 或点击添加，每项最多 32 字；{tagInput.trim() ? "请先添加或清空输入，再保存笔记。" : "标签随笔记一起保存。"}</p>
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
        <MarkdownEditor key={editorSession} active={workspaceView === 'edit'} value={draft.content} onChange={content => setDraft(value => ({...value, content}))} textarea={textarea} preview={preview} setPreview={setPreview} token={token} notes={notes} onNote={note => void open(note)} onSave={() => {setPaused(false); void save();}} assetRevision={assetRevision} focused={focusedEditor} setFocused={setFocusedEditor} onImage={() => showTool('insert')}/>
        <div className="editor-footer"><span className="hint">{Array.from(draft.content).length} 字符 · Markdown</span>{(dirty || conflict) && <button className="secondary" onClick={() => downloadDraft(draft)}>下载当前草稿</button>}<button className="secondary" disabled={!editing || dirty || busy} onClick={() => void download()}><Icon name="download" size={15}/>导出 .md</button><button className="primary" disabled={busy || !dirty || !draft.title.trim() || !!conflict || !!tagInput.trim()} onClick={() => { setPaused(false); void save(); }}><Icon name="check" size={15}/>立即保存</button></div>
        {editing && <button className="text-button note-delete" disabled={busy || !!conflict} onClick={() => void remove()}>删除这篇笔记</button>}
        {paused && !conflict && dirty && <p role="alert">{networkRetry && autoSave ? "网络连接失败，本地内容仍在；联网或返回页面后自动重试，也可点击“立即保存”。" : "保存未完成，本地内容仍在。核对后点击“立即保存”。"}</p>}
        {conflict && <section className="conflict-panel" role="alert">
          <h3>检测到另一处修改</h3><p>你的本地草稿已保留。可以逐段核对两处修改，合并后明确保存；也可以下载完整正文留存。</p>
          <strong>{conflict.title} · 版本 {conflict.revision}</strong><p>服务端标签：{conflict.tags.join("、") || "无标签"}</p><p>服务端文件夹：{folderPath(folders, conflict.folder_id)}</p><pre>{conflict.content}</pre>
          <div className="note-conflict-actions">
            <button ref={mergeTrigger} className="primary" disabled={!editing || busy || !!tagInput.trim()} onClick={() => {if(editing)setMergeSession({noteId:editing.id,local:{...draft},server:conflict,tagInput});}}>逐段合并</button>
            <button className="secondary" onClick={() => downloadDraft(draft,'本地草稿')}>下载本地草稿</button><button className="secondary" onClick={() => downloadDraft(conflict,'服务端版本')}>下载服务端版本</button>
            <button className="secondary" disabled={busy} onClick={() => { if (editing && window.confirm("确认载入服务端版本？当前本地草稿会保留为恢复副本，再替换编辑区内容。")) { if(retainOriginalDraft())return;unavailableBase.current=null;setEditing({ ...editing, ...noteDraft(conflict),revision:conflict.revision }); setDraft(noteDraft(conflict)); setTagInput(""); setTagError(""); setConflict(null); setPaused(false); setStatus("已载入服务端版本"); } }}>载入服务端版本</button>
            <button className="secondary" disabled={busy} onClick={()=>{if(editing&&window.confirm("已核对服务端内容，保留本地正文与标签？不会立即写入，仍需点击立即保存。")){retainOriginalDraft();unavailableBase.current=null;setEditing({...editing,...noteDraft(conflict),revision:conflict.revision});setConflict(null);setPaused(true);setNetworkRetry(false);setStatus("已核对新版本 · 本地草稿等待明确保存");}}}>核对后保留本地草稿</button>
          </div>{tagInput.trim() && <p className="hint">请在「文件夹与标签」中添加或清空尚未提交的标签，再逐段合并。</p>}
        </section>}
        {mergeSession && <NoteMergeDialog base={mergeSession.server.base} local={mergeSession.local} server={mergeSession.server} folders={folders} onClose={closeMerge} onApply={applyMerge}/>}
      </section>
      </div>
      <NotesDialog open={tool === 'context'} title="引用与关联" onClose={() => {if (window.dispatchEvent(new Event('hustudy:before-material-change', {cancelable: true}))) setTool(null);}} busy={busy}>
        {editing?.course_id === courseId && <button className="secondary" onClick={() => {setGraphFocus(editing.id);showTool('graph');}}>查看这篇笔记的关系图谱</button>}
        {organizationError && <p role="alert">{organizationError}</p>}
        <NoteCitations key={editing?.id || "new"} noteId={editing?.id} token={token} disabled={busy} onSource={onSource} onError={onError} onNotice={onNotice}/>
        <section className="panel"><h3>关联笔记</h3>{outgoing.map((match, index) => { const target = notes.find((note) => note.id === match[1]); return <button className="relation-link" disabled={!target || busy} key={`${match[1]}-${index}`} onClick={() => {if (target) {setTool(null); void open(target);}}}>↗ {target?.title || "目标笔记已删除或不可用"}</button>; })}{!outgoing.length && <EmptyInline text="插入双链，连接相关概念" />}<h4>被这些笔记引用</h4>{backlinks.map((note) => <button className="relation-link" key={note.id} disabled={busy} onClick={() => {setTool(null); void open(note);}}>↙ {note.title}</button>)}{!backlinks.length && <EmptyInline text="暂无反向链接" />}</section>
      </NotesDialog>
    </div>
    {packageVisited&&<Suspense fallback={packageIntent?<p role="status">正在打开标准包工具…</p>:null}><PackageTransfer token={token} intent={packageIntent} disabled={organizationDisabled} onClose={()=>setPackageIntent(null)} onError={onError} onNotice={onNotice} beforeCommit={()=>!organizationDisabled&&window.dispatchEvent(new Event("hustudy:before-material-change",{cancelable:true}))} onChanged={async()=>{await Promise.all([refreshCatalog(),refreshFolders()]);setAssetRevision(value=>value+1);await onCoursesChanged?.();}}/></Suspense>}
    <NotesDialog open={tool === 'graph'} title="笔记关系图谱" onClose={() => setTool(null)} busy={busy} className="note-graph-dialog">
      {organizationError && <p role="alert">{organizationError}</p>}
      {tool === 'graph' && <Suspense fallback={<p role="status">正在打开关系图谱…</p>}><NoteGraph key={courseId} token={token} courseId={courseId} isOpen hasDraft={dirty} initialFocusId={graphFocus} disabled={busy} onError={onError} onOpen={async node => {setOrganizationError('');if(await open(node))setTool(null);}}/></Suspense>}
    </NotesDialog>
    <NotesDialog open={tool === 'templates'} title="学习模板" onClose={() => setTool(null)}><p className="hint">追加到正文，保留已有内容。</p>{templates.map(template => <button key={template.name} className="template-card" onClick={() => {setDraft(value => ({...value, title: value.title || template.name, content: value.content + '\n' + template.content})); setTool(null);}}><Icon name="notes" size={16}/><span>{template.name}</span><Icon name="plus" size={15}/></button>)}</NotesDialog>
    <NotesDialog open={tool === 'speech'} title="语音输入" onClose={() => setTool(null)}>{recognitionError && <p role="alert">{recognitionError}</p>}<SpeechInput open={tool === 'speech'} disabled={busy || !!conflict} onInsert={insertRecognition}/></NotesDialog>
    <NotesDialog open={tool === 'capture'} title="文字识别" onClose={() => setTool(null)} busy={captureBusy}>{recognitionError && <p role="alert">{recognitionError}</p>}<NoteCapture token={token} courseId={imageCourse} isOpen={tool === 'capture'} disabled={busy || !!conflict} onInsert={insertRecognition} onError={onError} onBusy={setCaptureBusy}/></NotesDialog>
    <NotesDialog open={tool === 'import'} title="导入 Markdown" onClose={() => setTool(null)} busy={busy}>{organizationError && <p role="alert">{organizationError}</p>}<MarkdownImport token={token} courseId={courseId} folders={folders} disabled={organizationDisabled} perform={performOrganization} onImported={mergeNotes}/></NotesDialog>
    <NotesDialog open={tool === 'export'} title="导出笔记" onClose={() => setTool(null)} busy={exportBusy}>{organizationError && <p role="alert">{organizationError}</p>}<NoteExports token={token} notes={notes} courseId={courseId} unsaved={organizationDisabled} onError={onError} selection={exportSelection} onBusyChange={setExportBusy} isOpen={tool === 'export'}/></NotesDialog>
    {(['batch', 'tags', 'recommend'] as const).map(mode => <NotesDialog key={mode} open={tool === mode} title={{batch: '批量整理', tags: '标签管理', recommend: '推荐归类'}[mode]} onClose={() => setTool(null)} busy={busy}>{organizationError && <p role="alert">{organizationError}</p>}<NoteOrganizer mode={mode} token={token} notes={courseNotes} folders={folders} selected={selectedNotes} setSelected={setSelectedNotes} disabled={organizationDisabled} perform={performOrganization} onChanged={mergeNotes} suggestedFolder={folderFilter}/></NotesDialog>)}
    <NotesDialog open={tool === 'trash'} title="笔记回收站" onClose={() => setTool(null)} busy={busy}>
      <NoteTrash token={token} courseId={courseId} open={tool === 'trash'} disabled={organizationDisabled} perform={performOrganization} onChanged={async () => {setNotes(await loadNoteCatalog(token)); setSelectedNotes([]); if (editing) setBacklinks(await api.backlinkOptions(token, editing.id));}} onError={onError} onNotice={onNotice}/>
    </NotesDialog>
  </div>;
}
