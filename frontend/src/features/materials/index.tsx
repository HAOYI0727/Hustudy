import {ReferenceNotes} from "./ReferenceNotes";
import {sourceReadingPage,type ReadingCursor} from "./readingPage";
import {SourceConnections} from "./SourceConnections";
import ReaderAI from "./ReaderAI";
import {MaterialHealth} from "./MaterialHealth";
import {matchingText,textWindow,pageForChunk} from "./textWindow";
import "./reading-layout.css";
import type {OpenWorkspace} from "../platform/CourseWorkspace";
import { CompactLibrary } from "../../components/CompactLibrary";
import "./reading-tools.css";
import { PreviewStatus } from "./PreviewStatus";
import {readingPositions, rememberReading, forgetReading, type ReadingPosition} from "./readingPositions";
import {MaterialOrganize} from "./MaterialOrganize";
import {CitationTarget} from "./CitationTarget";
import { MaterialUpload } from "./MaterialUpload";
import {ReadingBookmarks} from "./BookmarkLibrary";
import type {BookmarkTarget,ReadingBookmark} from "./readingBookmarks";
import {shortReadingLabel} from "./readingBookmarks";
import {SavedMaterialViews} from "./SavedMaterialViews";
import {MaterialCard,materialSizeLabel as sizeLabel,materialDateLabel as timeLabel} from "./MaterialCard";
import type {MaterialViewFilters} from "./materialViews";
import type { StudyTarget } from "../platform/routing";
import { FormEvent, lazy, Suspense, useEffect, useRef, useState } from "react";
import { api, ApiError, Chunk, DocumentItem, Job, MaterialReference, type DocumentMetadata, Version } from "../../api/client";
import { AssetLibrary } from "./AssetLibrary";
import { Icon } from "../../components/Icon";
import { Transcripts } from "./Transcripts";
import { MaterialExports } from "./MaterialExports";
import { PageTitle, Status, EmptyInline, EmptyState, ModuleStats } from "../../components/workspace";

const VersionCompare = lazy(()=>import("./VersionCompare"));
const ReaderNotebook = lazy(()=>import("./ReaderNotebook"));
const OfficeReader = lazy(() => import("./OfficeReader"));
const PdfReader = lazy(() => import("./PdfReader"));
type Target = { documentId: string; versionId: string; chunkId: string; previewPage?: number };
type Props = { onWorkspace:OpenWorkspace; onStudy: (target: StudyTarget) => void; initialTarget?: Target; token: string; courseId: string; onNote: (id: string) => void; onNotice: (s: string) => void; onError: (e: unknown) => void };

// A legacy transcript history can make the chunks endpoint return the same
// source UUID more than once. Keep one stable row at the reader boundary so
// React keys, DOM anchors and page counts remain deterministic.
function uniqueChunks(rows: Chunk[]): Chunk[] {
  return Array.from(new Map(rows.map(row => [row.id, row])).values());
}

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
export function Materials({ token, courseId, onNote, onNotice, onError, initialTarget, onStudy, onWorkspace }: Props) {
  const [healthOpen,setHealthOpen]=useState(false);
  const [connections,setConnections]=useState<{versionId:string;chunkId:string|null;locator:string}|null>(null);
  const account = localStorage.getItem("hustudy_user") || "";
  const [resume,setResume] = useState<ReadingPosition|null>(()=>readingPositions(account,courseId)[0]||null);
  const tracking = useRef(false), creatingNote = useRef(false), savingMetadata=useRef(false);
  const excerptRequest=useRef<{chunk:string;id:string}|null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [citationRefresh,setCitationRefresh]=useState(0);
  const [selection,setSelection]=useState<DocumentMetadata[]>([]),[selecting,setSelecting]=useState(false);
  const [metadataConflict,setMetadataConflict]=useState<DocumentMetadata|null>(null);
  const [jobsFailed,setJobsFailed]=useState(false),[jobsLoading,setJobsLoading]=useState(false);
  const [filter, setFilter] = useState("");
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [stateFilter, setStateFilter] = useState<MaterialViewFilters["state"]>("all");
  const [sort, setSort] = useState<MaterialViewFilters["sort"]>("recent");
  const [cardDetails,setCardDetails] = useState(true);
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
  const [readingCursor,setReadingCursor]=useState<ReadingCursor|null>(null);
  const [transcriptRequest,setTranscriptRequest] = useState<{page:number;serial:number}>();
  const [view, setView] = useState("text");
  const [targetNote, setTargetNote] = useState("");
  const [focused, setFocused] = useState(false);
  const [notebookOpen,setNotebookOpen]=useState(false);
  const [notebookVisited,setNotebookVisited]=useState(false),[aiVisited,setAiVisited]=useState(false),[aiOpen,setAiOpen]=useState(false);
  const aiSourceSequence=useRef(0);
  const [bookmarkRequest,setBookmarkRequest]=useState<{target:BookmarkTarget;serial:number}>();
  const [readingTarget,setReadingTarget]=useState(initialTarget?.chunkId||"");
  const [readerQuery, setReaderQuery] = useState("");
  const [textPage,setTextPage]=useState({scope:"",page:0});
  const paperHost=useRef<HTMLDivElement>(null),assetTools=useRef<HTMLDetailsElement>(null);
  const autoFocusNative=useRef("");
  const [references, setReferences] = useState<MaterialReference[]>([]);
  const [referencesFailed, setReferencesFailed] = useState(false);
  const [referencesLoading, setReferencesLoading] = useState(false);
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftCategory, setDraftCategory] = useState("");
  const [draftTags, setDraftTags] = useState("");
  const [jobFilter, setJobFilter] = useState("all");
  const [jobKind,setJobKind]=useState("all"),[exportSelection,setExportSelection]=useState(0);
  const sequence = useRef(0), listSequence = useRef(0), jobSequence=useRef(0), refSequence = useRef(0);
  const alive = useRef(true);
  const openedInitial = useRef(false);
  const rebuildRequest = useRef<{version: string; id: string} | null>(null);
  const currentVersion = versions.find(row => row.id === versionId);
  const officeKind = currentVersion?.original_filename.toLowerCase().endsWith(".pptx") ? "pptx" : currentVersion?.original_filename.toLowerCase().endsWith(".docx") ? "docx" : undefined;
  const nativePdf = currentVersion?.original_filename.toLowerCase().endsWith(".pdf");
  const categories = docInfo.categories;
  const tags = docInfo.tags;
  const listKey = JSON.stringify([filter,category,tag,stateFilter,sort,docOffset]);
  const jobKey=JSON.stringify([jobOffset,jobFilter,jobKind]);
  const lastJobKey=useRef(jobKey),currentJobKey=useRef(jobKey);currentJobKey.current=jobKey;
  const lastListKey = useRef(listKey);
  const currentListKey = useRef(listKey); currentListKey.current = listKey;
  const parsedTags = Array.from(new Set(draftTags.split(/[,，]/).map(s => s.trim()).filter(Boolean)));
  const metadataDirty = !!active && (draftName !== active.name || draftCategory !== active.category || draftTags !== active.tags.join("，"));
  const canLeave = () => !metadataDirty || window.confirm("资料整理尚未保存，确定放弃这次改名或标签修改吗？");

  const loadDocuments = async () => {
    const generation=++listSequence.current, requestedKey=listKey;
    try{
      const page=await api.documentPage(token,courseId,{q:filter,category,tag,state:stateFilter,sort,offset:docOffset,limit:12});
      if(alive.current&&generation===listSequence.current&&requestedKey===currentListKey.current){
        setDocuments(page.items);setDocInfo(page);setLoadFailed(false);
        if(docOffset>0&&!page.items.length)setDocOffset(page.total?Math.floor((page.total-1)/12)*12:0);
      }
      return page.items;
    }catch(error){if(alive.current&&generation===listSequence.current&&requestedKey===currentListKey.current){setLoadFailed(true);throw error;}return [];}
    finally{if(alive.current&&generation===listSequence.current&&requestedKey===currentListKey.current)setLoading(false);}
  };
  const loadJobs = async () => {
    const generation=++jobSequence.current,requestedKey=jobKey;setJobsLoading(true);
    try{
      const queue=await api.jobPage(token,courseId,jobFilter,jobOffset,jobKind);
      if(alive.current&&generation===jobSequence.current&&requestedKey===currentJobKey.current){
        setJobs(queue.items);setJobInfo(queue);setJobsFailed(false);
        if(jobOffset>0&&!queue.items.length)setJobOffset(queue.total?Math.floor((queue.total-1)/10)*10:0);
      }
    }catch(error){if(alive.current&&generation===jobSequence.current&&requestedKey===currentJobKey.current){setJobsFailed(true);throw error;}}
    finally{if(alive.current&&generation===jobSequence.current&&requestedKey===currentJobKey.current)setJobsLoading(false);}
  };
  const load = async () => {
    const [page,queue]=await Promise.allSettled([loadDocuments(),loadJobs()]);
    if(page.status==="rejected")onError(page.reason);
    if(queue.status==="rejected")onError(queue.reason);
    return page.status==="fulfilled"?page.value:[];
  };
  const openDocument = async (doc: DocumentItem, target?: Target, bypassGuard = false, throwFailure = false) => {
    if (!bypassGuard && !window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable:true}))) return false;
    if (!bypassGuard && !canLeave()) return false;
    aiSourceSequence.current++;setNotebookOpen(false);setAiOpen(false);setNotebookVisited(false);setAiVisited(false);
    tracking.current=false;autoFocusNative.current="";
    const current = ++sequence.current;
    setPreviewOpenFailed(false);
    setActive(doc); setSelected([]); setPreviewUrl(""); setView("text"); setReading(true); setVersions([]); setVersionId(""); setReaderQuery("");
    setDraftName(doc.name); setDraftCategory(doc.category); setDraftTags(doc.tags.join("，")); setMetadataOpen(false);setMetadataConflict(null);
    setPreviewPage(target?.previewPage || 1);setReadingTarget(target?.chunkId||"");
    try {
      const list = await api.versions(token, doc.id);
      const chosen = target?.versionId || list[0]?.id;
      if(target?.versionId&&!list.some(version=>version.id===target.versionId&&version.document_id===doc.id))throw new Error("原版本已不可用，未切换到其他版本");
      const rows = chosen ? uniqueChunks(await api.chunks(token, chosen)) : [];
      if(rows.some(chunk=>chunk.version_id!==chosen))throw new Error("片段与资料版本不一致，请重新加载");
      if(target?.chunkId&&!rows.some(chunk=>chunk.id===target.chunkId))throw new Error("原文片段已不可用，书签或引用仍保留");
      if (current === sequence.current && alive.current) {
        setVersions(list); setVersionId(chosen || ""); setSelected(rows);
        setTextPage({scope:(chosen||"")+"|",page:pageForChunk(rows,target?.chunkId||"",list.find(version=>version.id===chosen)?.original_filename.toLowerCase().endsWith(".pptx")?1:6)});
        if(!target?.chunkId&&!target?.previewPage&&list.find(version=>version.id===chosen)?.original_filename.toLowerCase().endsWith(".pptx")){
          autoFocusNative.current=chosen||"";setView("native");requestAnimationFrame(()=>requestAnimationFrame(()=>{if(alive.current&&current===sequence.current)document.querySelector(".reader-stage")?.scrollIntoView({block:"start"});}));
        }
        if (target?.previewPage && chosen) {
          const blob = await api.preview(token, chosen);
          if (current === sequence.current && alive.current) { setPreviewUrl(URL.createObjectURL(blob)); setView("pdf"); }
        }
      }
      return current === sequence.current && alive.current;
    } catch (reason) { if(throwFailure)throw reason; if (current === sequence.current && alive.current) onError(reason); return false; }
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
    void loadJobs().catch(onError);
    void loadDocuments().catch(onError);
    void (async () => {
      if (!alive.current || !initialTarget || openedInitial.current) return;
      const doc = await api.document(token, initialTarget.documentId);
      if (alive.current && !openedInitial.current) { openedInitial.current = true; void openDocument(doc, initialTarget, true); }
    })().catch(onError);
    return () => { alive.current = false; sequence.current++; listSequence.current++; jobSequence.current++; refSequence.current++; };
  }, [courseId, token]);
  useEffect(() => {
    if (lastListKey.current === listKey) return;
    lastListKey.current = listKey;
    setLoading(true);
    const timer = window.setTimeout(() => { void loadDocuments().catch(onError); }, 180);
    return () => window.clearTimeout(timer);
  }, [listKey]);
  useEffect(()=>{
    if(lastJobKey.current===jobKey)return;
    lastJobKey.current=jobKey;setJobs([]);setJobsLoading(true);
    const timer=window.setTimeout(()=>{void loadJobs().catch(onError);},180);
    return()=>window.clearTimeout(timer);
  },[jobKey]);
  useEffect(() => {
    if (!jobInfo.pending_count || jobsFailed) return;
    const timer = window.setTimeout(() => { void Promise.allSettled([loadDocuments(),loadJobs()]).then(results=>results.forEach(result=>{if(result.status==="rejected")onError(result.reason);})); }, 2000);
    return () => window.clearTimeout(timer);
  }, [jobs, jobInfo.pending_count, listKey, jobKey, jobsFailed]);
  useEffect(() => {
    if (!active) return;
    const current = sequence.current;
    void api.versions(token, active.id).then(list => {
      if (alive.current && current === sequence.current) {
        setVersions(list);
        if (list.find(v => v.id === versionId)?.parse_status === "SUCCEEDED" && !selected.length && !reading) {
          // Background completion must not reset the user's native/PDF reading mode.
          void api.chunks(token,versionId).then(rows => {
            if(alive.current && current===sequence.current)setSelected(uniqueChunks(rows));
          }).catch(onError);
        }
      }
    }).catch(onError);
  }, [jobs]);
  useEffect(() => { if (versionId) void loadReferences(versionId); else { refSequence.current++; setReferences([]); setReferencesFailed(false); setReferencesLoading(false); } }, [versionId]);
  useEffect(() => {
    const navigate = (event: Event) => { if (creatingNote.current || savingMetadata.current || !canLeave()) event.preventDefault(); };
    const unload = (event: BeforeUnloadEvent) => { if (metadataDirty || creatingNote.current || savingMetadata.current) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("hustudy:before-navigate", navigate);
    window.addEventListener("beforeunload", unload);
    return () => { window.removeEventListener("hustudy:before-navigate", navigate); window.removeEventListener("beforeunload", unload); };
  }, [metadataDirty]);
  useEffect(() => {
    if (initialTarget && selected.some(chunk => chunk.id === initialTarget.chunkId)) scrollToChunk(initialTarget.chunkId);
  }, [selected, reading]);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  useEffect(()=>{setReadingCursor(null);},[versionId,view]);
  const recordPosition = (page:number, mode:"text"|"native"|"pdf", chunkId="") => {
    if(mode==="native"||mode==="pdf")setReadingCursor({versionId,view:mode,page});
    if(active && versionId) rememberReading(account,{courseId,documentId:active.id,versionId,chunkId,page,view:mode,name:active.name});
  };
  useEffect(()=>{
    if(!active || !versionId || reading || view!=="text")return;
    let timer:number|undefined;
    const record=()=>{
      if(!tracking.current)return;
      window.clearTimeout(timer);
      timer=window.setTimeout(()=>{
        const visible=selected.map(chunk=>({chunk,rect:document.getElementById("chunk-"+chunk.id)?.getBoundingClientRect()})).filter(item=>item.rect&&item.rect.bottom>100&&item.rect.top<innerHeight*.7).sort((a,b)=>Math.abs(a.rect!.top-150)-Math.abs(b.rect!.top-150))[0];
        if(visible)recordPosition(1,"text",visible.chunk.id);
      },250);
    };
    window.addEventListener("scroll",record,{passive:true});
    const host=paperHost.current;host?.addEventListener("scroll",record,{passive:true});
    return()=>{window.removeEventListener("scroll",record);host?.removeEventListener("scroll",record);window.clearTimeout(timer);};
  },[active?.id,versionId,reading,view,selected]);
  const continueReading = async () => {
    if(!resume || busy)return;
    const position=resume;
    try {
      const doc=await api.document(token,position.documentId);
      if(doc.course_id!==courseId)throw new Error("阅读位置不属于当前课程");
      const opened=await openDocument(doc,{documentId:doc.id,versionId:position.versionId,chunkId:position.chunkId,previewPage:position.view==="pdf"?position.page:undefined});
      if(!opened)return;
      setPreviewPage(position.page);
      if(position.view==="native")setView("native");
      if(position.view==="text"&&position.chunkId){const current=sequence.current;requestAnimationFrame(()=>requestAnimationFrame(()=>{if(current===sequence.current)document.getElementById("chunk-"+position.chunkId)?.scrollIntoView({block:"center"});}));}
    }catch(error){if(error instanceof ApiError && error.status===404){forgetReading(account,position.versionId);setResume(null);}onError(error);}
  };
  const excerptNote = async (chunk:Chunk) => {
    if(busy || creatingNote.current || metadataDirty || !active)return;
    creatingNote.current=true;setBusy(true);
    try{
      const quote=chunk.text.slice(0,500);
      if(excerptRequest.current?.chunk!==chunk.id)excerptRequest.current={chunk:chunk.id,id:crypto.randomUUID()};
      const note=await api.createNote(token,{request_id:excerptRequest.current.id,course_id:courseId,title:`${active.name} · ${chunk.locator_value}`.slice(0,240),content:`## 阅读摘录\n\n${quote.split("\n").map(line=>"> "+line).join("\n")}\n\n## 我的理解\n\n`,citations:[{version_id:chunk.version_id,chunk_id:chunk.id,quote}]});
      excerptRequest.current=null;
      setCitationRefresh(value=>value+1);await load().catch(onError);onNotice("摘录与原文引用已保存为新笔记，可继续补充理解");creatingNote.current=false;onNote(note.id);
    }catch(error){onError(error);}finally{creatingNote.current=false;if(alive.current)setBusy(false);}
  };
  const scrollToChunk = (id: string) => {
    const matches=matchingText(selected,readerQuery),found=matches.some(chunk=>chunk.id===id),query=found?readerQuery:"";
    if(!found)setReaderQuery("");
    setTextPage({scope:versionId+"|"+query.trim().toLocaleLowerCase(),page:pageForChunk(found?matches:selected,id,officeKind==="pptx"?1:6)});
    const generation=sequence.current;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{if(alive.current&&generation===sequence.current)document.getElementById("chunk-"+id)?.scrollIntoView({block:"center",behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"});}));
  };
  const uploaded = async (jobs: Job[]) => {
    // A refresh/open failure must never cause a saved upload to be replayed.
    await load();
    const job = jobs[jobs.length - 1];
    const version = await api.version(token, job.resource_id);
    const document = await api.document(token, version.document_id);
    if (alive.current) await openDocument(document, { documentId: document.id, versionId: version.id, chunkId: "" }, true);
    onNotice(`本次已保存 ${jobs.length} 份资料；可在处理记录查看解析、索引与预览进度`);
  };
  const study = (mode: "qa" | "report", chunkId = "") => {
    if (active && currentVersion) onStudy({documentId: active.id, versionId: currentVersion.id, chunkId, mode});
  };
  const readVersion = async (id: string) => {
    if (!window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable:true}))) return;
    aiSourceSequence.current++;setNotebookOpen(false);setAiOpen(false);setNotebookVisited(false);setAiVisited(false);
    setPreviewPage(1);setReadingTarget("");
    const current = ++sequence.current; setVersionId(id); setSelected([]); setPreviewUrl(""); setView("text"); setReading(true); setReaderQuery("");
    if(versions.find(version=>version.id===id)?.original_filename.toLowerCase().endsWith(".pptx"))setView("native");
    try { const rows = await api.chunks(token, id); if (current === sequence.current && alive.current) setSelected(rows); }
    catch (reason) { if (current === sequence.current && alive.current) onError(reason); }
    finally { if (current === sequence.current && alive.current) setReading(false); }
  };
  const saveMetadata = async (event: FormEvent) => {
    event.preventDefault(); if (!active || busy) return;
    if (!draftName.trim() || parsedTags.length > 12 || parsedTags.some(t => t.length > 32)) { onError(new Error("请填写资料名称；标签最多 12 个，每个不超过 32 字")); return; }
    const payload: {name?: string; category?: string; tags?: string[];expected_updated_at:string} = {expected_updated_at:active.updated_at};
    if (draftName !== active.name) payload.name = draftName.trim();
    if (draftCategory !== active.category) payload.category = draftCategory.trim() || "未分类";
    if (draftTags !== active.tags.join("，")) payload.tags = parsedTags;
    setBusy(true);savingMetadata.current=true;
    try {
      const updated = await api.updateDocument(token, active.id, payload);setMetadataConflict(null);
      if (alive.current) { setActive(updated); setDraftName(updated.name); setDraftCategory(updated.category); setDraftTags(updated.tags.join("，")); }
      await load(); onNotice("资料整理已保存，原有版本与引用保持有效");
    } catch (reason) {
      if(reason instanceof ApiError&&reason.status===409&&reason.details?.server_document)setMetadataConflict(reason.details.server_document as DocumentMetadata);
      onError(reason);
    } finally {savingMetadata.current=false; if (alive.current) setBusy(false); }
  };
  const showPreview = async () => {
    const current = sequence.current; setBusy(true); setPreviewOpenFailed(false);
    try { const blob = await api.preview(token, versionId); if (current === sequence.current && alive.current) { setPreviewUrl(URL.createObjectURL(blob)); setView("pdf"); } }
    catch (reason) { if (current === sequence.current && alive.current) {setPreviewOpenFailed(true);onError(reason);} }
    finally { if (alive.current) setBusy(false); }
  };
  const openOrQueueCompatibilityPreview = async () => {
    if (officeKind && currentVersion && currentVersion.preview_status !== "SUCCEEDED") {
      setBusy(true);
      try { await api.requestPreview(token, currentVersion.id); await load(); onNotice("兼容 PDF 预览已按需提交；原格式阅读无需等待转换"); }
      catch (reason) { onError(reason); }
      finally { if (alive.current) setBusy(false); }
      return;
    }
    await showPreview();
  };
  const previewAt = async (page:number) => { setPreviewPage(page); await showPreview(); };
  const refreshTranscripts = async () => {
    setAssetRefresh(value => value + 1);setCitationRefresh(value=>value+1);
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
    try { await api.deleteDocument(token, active.id); sequence.current++; setActive(null); setVersions([]); setVersionId(""); setSelected([]); setPreviewUrl(""); setFocused(false); setAssetRefresh(s => s + 1); await load(); onNotice("资料已删除，引用已标记不可用"); }
    catch (reason) { onError(reason); } finally { if (alive.current) setBusy(false); }
  };
  const cite = async (chunk: Chunk) => {
    if (!targetNote || busy) return; setBusy(true);
    const highlighted = window.getSelection()?.toString().trim();
    const quote = highlighted && chunk.text.includes(highlighted) ? highlighted : chunk.text.slice(0, 500);
    try { await api.citation(token, targetNote, { version_id: chunk.version_id, chunk_id: chunk.id, quote }); setCitationRefresh(value=>value+1); await loadReferences(chunk.version_id); onNotice("原文引用已添加到笔记，关联列表已更新"); }
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
  const openReadingSource = async (documentId:string, sourceVersion:string, chunkId:string,stillCurrent=()=>true) => {
    const doc=await api.document(token,documentId);
    if(!alive.current||!stillCurrent())return false;
    if(doc.course_id!==courseId)throw new Error("来源不属于当前课程，未打开原文");
    const opened=await openDocument(doc,{documentId,versionId:sourceVersion,chunkId},false,true);
    if(opened){
      const current=sequence.current;
      rememberReading(account,{courseId,documentId,versionId:sourceVersion,chunkId,page:1,view:"text",name:doc.name});
      requestAnimationFrame(()=>requestAnimationFrame(()=>{
        if(alive.current&&current===sequence.current){const target=document.getElementById("chunk-"+chunkId);target?.focus({preventScroll:true});target?.scrollIntoView({block:"center"});}
      }));
    }
    return opened;
  };
  const assistantSource=(sourceVersion:string,chunkId:string)=>{
    if(sourceVersion===versionId){
      if(chunkId&&!selected.some(chunk=>chunk.id===chunkId)){onError(new Error("引用片段已不可用，请重新核对来源"));return;}
      setView("text");setReadingTarget(chunkId);if(chunkId){scrollToChunk(chunkId);recordPosition(1,"text",chunkId);}
      return;
    }
    const current=sequence.current,request=++aiSourceSequence.current;
    const valid=()=>alive.current&&current===sequence.current&&request===aiSourceSequence.current;
    void api.version(token,sourceVersion).then(version=>{if(valid())return openReadingSource(version.document_id,sourceVersion,chunkId,valid);}).catch(error=>{if(valid())onError(error);});
  };
  const bookmark = (chunk:Chunk) => {
    if(!active||!currentVersion)return;
    setBookmarkRequest(previous=>({serial:(previous?.serial||0)+1,target:{documentId:active.id,documentName:active.name,versionId:currentVersion.id,versionNo:currentVersion.version_no,chunkId:chunk.id,locatorType:chunk.locator_type,locatorValue:shortReadingLabel(chunk.locator_value||"原文",240)}}));
  };
  const clearFilters = () => { setDocOffset(0); setFilter(""); setCategory(""); setTag(""); setStateFilter("all"); };
  const visible = documents;
  const shownChunks=matchingText(selected,readerQuery),textScope=versionId+"|"+readerQuery.trim().toLocaleLowerCase(),textSize=officeKind==="pptx"?1:6;
  const windowPage=textWindow(shownChunks.length,textPage.scope===textScope?textPage.page:0,textSize),visibleChunks=shownChunks.slice(windowPage.start,windowPage.end);
  const currentReadingPage=reading?null:sourceReadingPage({versionId,view,kind:officeKind|| (nativePdf?"pdf":undefined),cursor:readingCursor,chunks:visibleChunks});
  const changeTextPage=(page:number)=>{const next=textWindow(shownChunks.length,page,textSize);setTextPage({scope:textScope,page:next.page});paperHost.current?.scrollTo({top:0});const first=shownChunks[next.start];if(first)recordPosition(1,"text",first.id);};
  const shownJobs = jobs;
  const pending = jobInfo.pending_count;

  return <div className={"page materials-page" + (focused ? " reading-focused" : "")} data-reading-active={!!active}>
    <PageTitle eyebrow="MATERIAL HUB / READ & DISCOVER" title="每一份资料，都是理解的起点" text="整理章节与标签，读懂原文，再把资料连到自己的知识笔记。"/>
    <ModuleStats items={[{ label: "课程资料", value: loadFailed ? "—" : docInfo.stats.total || 0, hint: "在当前课程积累" }, { label: "可检索", value: loadFailed ? "—" : docInfo.stats.ready || 0, hint: "原文索引或已确认人工补录" }, { label: "处理中", value: jobsFailed ? "—" : pending, hint: jobsFailed ? "处理状态暂不可读" : pending ? "全部页面任务 · 后台更新" : "可以开始阅读与整理" }]}/>
    <section className="material-health-launch" aria-label="资料检查入口"><p>核对最新版本的正文、索引和预览，恢复需处理的任务。</p><button className="secondary" disabled={busy||reading} onClick={()=>setHealthOpen(true)}><Icon name="check" size={16}/>资料检查</button></section>
    {resume && <section className="reading-resume" aria-label="继续上次阅读"><span className="resume-symbol"><Icon name="clock"/></span><div><strong>继续上次阅读 · {resume.name}</strong><p>{resume.view==="text"?"回到上次阅读的原文片段":`回到上次的第 ${resume.page} ${resume.view==="native"?"阅读页":"页"}`} · 仅保存在当前浏览器</p></div><button className="secondary" disabled={busy||reading} onClick={()=>void continueReading()}>继续上次阅读 <Icon name="arrow" size={16}/></button><button className="icon-button secondary" aria-label="清除这条阅读位置" onClick={()=>{forgetReading(account,resume.versionId);setResume(null);}}><Icon name="close" size={15}/></button></section>}
    <div className="reading-layout">
      <CompactLibrary className="panel material-library" label="资料库与上传">
        <div className="panel-title"><h3><Icon name="folder"/>资料库</h3><button className="icon-button secondary" title="刷新资料与处理状态" aria-label="刷新资料与处理状态" disabled={loading || busy} onClick={() => void load().catch(onError)}><Icon name="refresh"/></button></div>
        <MaterialUpload pending={jobInfo.pending_count>0} token={token} courseId={courseId} active={active} disabled={busy} onBusy={setBusy} onBeforeUpload={() => window.dispatchEvent(new Event("hustudy:before-material-change", {cancelable:true})) && canLeave()} onComplete={uploaded} onError={onError}/>
        <div className="material-list-filters">
          <div className="input-with-icon"><Icon name="search" size={16}/><input aria-label="筛选资料名称或标签" placeholder="查找名称、文件或标签…" value={filter} onChange={e => { setDocOffset(0); setFilter(e.target.value); }}/>{filter && <button className="icon-button" aria-label="清空名称筛选" onClick={() => { setDocOffset(0); setFilter(""); }}><Icon name="close" size={14}/></button>}</div>
          <div className="filter-pair"><select aria-label="按资料分类筛选" value={category} onChange={e => { setDocOffset(0); setCategory(e.target.value); }}><option value="">全部分类</option>{category&&!categories.includes(category)&&<option value={category}>{category}（当前无资料）</option>}{categories.map(value => <option key={value}>{value}</option>)}</select><select aria-label="按资料标签筛选" value={tag} onChange={e => { setDocOffset(0); setTag(e.target.value); }}><option value="">全部标签</option>{tag&&!tags.includes(tag)&&<option value={tag}>{tag}（当前无资料）</option>}{tags.map(value => <option key={value}>{value}</option>)}</select></div>
          <div className="filter-pair"><select aria-label="按处理状态筛选" value={stateFilter} onChange={e => { setDocOffset(0); setStateFilter(e.target.value as MaterialViewFilters["state"]); }}><option value="all">全部状态</option><option value="ready">可检索</option><option value="processing">处理中</option><option value="failed">需要处理</option></select><select aria-label="资料排序" value={sort} onChange={e => { setDocOffset(0); setSort(e.target.value as MaterialViewFilters["sort"]); }}><option value="recent">最近更新</option><option value="name">名称顺序</option><option value="size">文件大小</option></select></div>
        </div>
        <SavedMaterialViews token={token} courseId={courseId} current={{q:filter,category,tag,state:stateFilter,sort}} disabled={busy} onError={onError} onApply={value=>{setDocOffset(0);setFilter(value.q);setCategory(value.category);setTag(value.tag);setStateFilter(value.state);setSort(value.sort);}}/>
        <MaterialOrganize token={token} courseId={courseId} onExport={()=>setExportSelection(value=>value+1)} items={selection} visible={documents} selecting={selecting} disabled={busy||loading} metadataDirty={metadataDirty} categories={categories} onSelecting={setSelecting} onSelection={setSelection} onBusy={setBusy} onError={onError} onComplete={async(items,changed)=>{
          const updated=items.find(row=>row.id===active?.id);
          if(updated){setActive(value=>value?{...value,...updated}:value);setDraftName(updated.name);setDraftCategory(updated.category);setDraftTags(updated.tags.join("，"));setMetadataConflict(null);}
          await load();onNotice(`已核对 ${items.length} 份资料，更新 ${changed} 份；原文与引用保持有效`);
        }}/>
        <div className="library-result-label"><span>匹配 {docInfo.total} / {docInfo.stats.total || 0} 份资料</span>{(filter || category || tag || stateFilter !== "all") && <button className="text-button" onClick={clearFilters}>清除筛选</button>}</div>
        <div className="material-display-controls"><span>资料显示</span><div className="material-display-switch" role="group" aria-label="资料卡片显示方式"><button type="button" aria-pressed={cardDetails} onClick={()=>setCardDetails(true)}><Icon name="file" size={14}/>详细</button><button type="button" aria-pressed={!cardDetails} onClick={()=>setCardDetails(false)}><Icon name="list" size={14}/>精简</button></div></div>
        {loading ? <div className="material-loading" role="status"><Icon name="refresh" className="is-spinning"/>正在加载课程资料…</div> : loadFailed ? <div className="inline-retry" role="alert">资料加载未完成<button className="secondary" onClick={() => void loadDocuments().catch(onError)}>重新加载</button></div> : <div className="list material-document-list">{visible.map((doc,index) => {
          return <div className={"material-selectable-row"+(selection.some(item=>item.id===doc.id)?" is-checked":"")} key={`${doc.id}:${index}`}>
            {selecting&&<label className="material-select-label"><input type="checkbox" aria-label={`选择资料：${doc.name}`} checked={selection.some(item=>item.id===doc.id)} disabled={busy} onChange={event=>{
              if(event.target.checked&&selection.length>=100){onError(new Error("每批最多选择100份资料"));return;}
              setSelection(value=>event.target.checked?[...value,doc]:value.filter(item=>item.id!==doc.id));
            }}/></label>}
            <MaterialCard doc={doc} active={active?.id===doc.id} disabled={busy} details={cardDetails} onOpen={()=>void openDocument(doc)}/></div>;
        })}</div>}
        <nav className="catalogue-pages" aria-label="资料分页"><button className="secondary" disabled={busy || loading || docOffset===0} onClick={() => setDocOffset(Math.max(0,docOffset-12))}>上一页</button><span role="status">{Math.floor(docOffset/12)+1} / {Math.max(1,Math.ceil(docInfo.total/12))} 页</span><button className="secondary" disabled={busy || loading || docOffset+12>=docInfo.total} onClick={() => setDocOffset(docOffset+12)}>下一页</button></nav>
        {!loading && !loadFailed && !visible.length && <EmptyInline text={docInfo.stats.total ? "没有匹配资料，试试清除筛选" : "从第一份课件开始积累"}/>}
      </CompactLibrary>
      <div className={"reader-stage"+(notebookOpen?" has-notebook":"")+(aiOpen?" has-ai":"")}><section className="panel reader-workspace" onPointerDown={()=>{tracking.current=true;}} onKeyDown={()=>{tracking.current=true;}}>
        <div className="panel-title reader-title"><div><p className="eyebrow">READING DESK</p><h3>{active?.name || "留一张桌子，给新的理解"}</h3></div><div className="reading-tools"><button className="secondary" disabled={busy||reading||!versionId} onClick={()=>setConnections({versionId,chunkId:null,locator:""})}><Icon name="link" size={16}/>学习关联</button><ReadingBookmarks token={token} courseId={courseId} target={bookmarkRequest?.target} serial={bookmarkRequest?.serial||0} disabled={busy||reading} onError={onError} onOpen={(row:ReadingBookmark)=>openReadingSource(row.documentId,row.versionId,row.chunkId)}/>{active&&versionId&&<><button className="secondary" aria-pressed={notebookOpen} disabled={busy||reading} onClick={()=>{if(notebookOpen){if(window.dispatchEvent(new Event("hustudy:before-reader-notebook-close",{cancelable:true})))setNotebookOpen(false);}else{aiSourceSequence.current++;setAiOpen(false);setNotebookVisited(true);setNotebookOpen(true);setFocused(true);}}}><Icon name="notes" size={16}/>阅读笔记</button><button className="secondary" aria-pressed={aiOpen} disabled={busy||reading||!selected.length} onClick={()=>{aiSourceSequence.current++;if(aiOpen)setAiOpen(false);else{setAiVisited(true);setAiOpen(true);setNotebookOpen(false);setFocused(true);if(innerWidth<=1100)requestAnimationFrame(()=>document.querySelector(".reader-ai-panel")?.scrollIntoView({block:"start"}));}}}><Icon name="ai" size={16}/>AI阅读助手</button></>}<button title="减小字号" aria-label="减小阅读字号" className="icon-button secondary" disabled={fontSize <= 14} onClick={() => setFontSize(s => s - 1)}>A−</button><span className="reader-font-size">{fontSize}</span><button title="增大字号" aria-label="增大阅读字号" className="icon-button secondary" disabled={fontSize >= 24} onClick={() => setFontSize(s => s + 1)}>A＋</button><button title={focused ? "返回完整工作台" : "展开专注阅读"} aria-label={focused ? "返回完整工作台" : "展开专注阅读"} aria-pressed={focused} className="icon-button secondary" onClick={() => setFocused(s => !s)}><Icon name={focused ? "collapse" : "expand"}/></button></div></div>
        {active && <>
          <div className="material-toolbar reader-primary-actions"><select aria-label="资料版本" value={versionId} disabled={busy || reading} onChange={e => void readVersion(e.target.value)}>{versions.map((v,index) => <option value={v.id} key={`${v.id}:${index}`}>v{v.version_no} · {v.original_filename}</option>)}</select><button className="secondary" disabled={!versionId || busy} onClick={() => void download()}><Icon name="download" size={16}/>原件</button>{selected.length>0&&<button className={"secondary "+(view==="text"?"button-selected":"")} aria-pressed={view==="text"} disabled={busy||reading} onClick={()=>setView("text")}><Icon name="list" size={16}/>文本与引用</button>}{officeKind && <button className={"secondary "+(view==="native"?"button-selected":"")} disabled={busy} onClick={() => setView("native")} title="直接读取原文件，无需等待PDF转换"><Icon name="preview" size={16}/>{officeKind==="pptx"?"PPT 预览":"Word 预览"}</button>}{(officeKind || nativePdf) && <button className="secondary" disabled={busy || (nativePdf && currentVersion?.preview_status !== "SUCCEEDED")} onClick={() => void openOrQueueCompatibilityPreview()} title={officeKind && currentVersion?.preview_status !== "SUCCEEDED" ? "按需生成兼容 PDF；原格式预览无需等待转换" : "打开按页预览"}><Icon name="preview" size={16}/>{officeKind && currentVersion?.preview_status !== "SUCCEEDED" ? "生成兼容 PDF" : officeKind?"兼容预览（PDF）":"PDF 预览"}</button>}<button className="secondary" disabled={!versionId || busy || reading || currentVersion?.index_status === "QUEUED" || currentVersion?.index_status === "RUNNING" || !selected.length} onClick={() => void rebuild()} title="重建当前版本关键词索引，不修改原文或引用"><Icon name="refresh" size={16}/>重建索引</button><button className={"secondary " + (metadataOpen ? "button-selected" : "")} aria-expanded={metadataOpen} onClick={() => setMetadataOpen(s => !s)}><Icon name="edit" size={16}/>整理</button><Suspense fallback={null}><VersionCompare key={active.id} token={token} documentId={active.id} name={active.name} versions={versions} currentVersionId={versionId} disabled={busy||reading} onSource={(version,chunk)=>openReadingSource(active.id,version,chunk)}/></Suspense></div>
          <div className="material-statuses"><span>解析 <Status value={currentVersion?.parse_status || "QUEUED"}/></span><span>索引 <Status value={currentVersion?.index_status || "PENDING"}/></span><span>{officeKind?"兼容 PDF":"预览"} <Status value={currentVersion?.preview_status || "PENDING"}/></span></div>
          {metadataOpen && <form className="material-metadata" onSubmit={saveMetadata}><div className="metadata-heading"><h4><Icon name="tag"/>整理这份资料</h4><span className={metadataDirty ? "unsaved-indicator" : "hint"}>{metadataDirty ? "有未保存的修改" : "已保存"}</span></div><label>资料名称<input required maxLength={240} value={draftName} onChange={e => setDraftName(e.target.value)} disabled={busy}/></label><div className="metadata-fields"><label>分类<input list="material-categories" maxLength={40} placeholder="例如：核心章节" value={draftCategory} onChange={e => setDraftCategory(e.target.value)} disabled={busy}/><datalist id="material-categories">{categories.map(value => <option value={value} key={value}/>)}</datalist></label><label>标签<input value={draftTags} onChange={e => setDraftTags(e.target.value)} placeholder="进程，期末，重点" disabled={busy}/></label></div><p className="hint">逗号分隔，最多 12 个标签；改名不会改变原文版本和引用。</p><div className="metadata-actions"><button className="primary" disabled={!metadataDirty || busy || !draftName.trim()}><Icon name="check" size={16}/>保存整理</button><button type="button" className="secondary" disabled={!metadataDirty || busy} onClick={() => { setDraftName(active.name); setDraftCategory(active.category); setDraftTags(active.tags.join("，")); }}>撤销修改</button><button type="button" className="text-button danger" disabled={busy} onClick={() => void remove()}><Icon name="trash" size={15}/>删除资料</button></div></form>}
          {metadataConflict&&active&&<section className="material-metadata-conflict" role="alert"><strong>资料整理已有新版本，本地输入仍保留</strong><p>服务端：{metadataConflict.name} · {metadataConflict.category} · {metadataConflict.tags.join("，")||"无标签"}</p><div><button className="secondary" disabled={busy} onClick={()=>{setActive({...active,...metadataConflict});setDraftName(metadataConflict.name);setDraftCategory(metadataConflict.category);setDraftTags(metadataConflict.tags.join("，"));setMetadataConflict(null);}}>载入服务端整理</button><button className="secondary" disabled={busy} onClick={()=>{
            if(draftName===active.name)setDraftName(metadataConflict.name);
            if(draftCategory===active.category)setDraftCategory(metadataConflict.category);
            if(draftTags===active.tags.join("，"))setDraftTags(metadataConflict.tags.join("，"));
            setActive({...active,...metadataConflict});setMetadataConflict(null);onNotice("已核对新快照，本地修改保留；请检查后再次保存整理");
          }}>核对后保留本地修改</button></div></section>}
          {currentVersion?.parse_error && <p className="dashboard-warning" role="alert"><Icon name="info" size={16}/>{currentVersion.parse_error}</p>}{currentVersion && (officeKind ? <details className="native-compatibility-status"><summary><Icon name="info" size={14}/>兼容 PDF 状态与修复</summary><PreviewStatus key={currentVersion.id} token={token} version={currentVersion} openFailed={previewOpenFailed} onQueued={load} onError={onError} onNotice={onNotice}/></details> : <PreviewStatus key={currentVersion.id} token={token} version={currentVersion} openFailed={previewOpenFailed} onQueued={load} onError={onError} onNotice={onNotice}/>)}
          {currentVersion && <div className="version-caption"><Icon name="clock" size={14}/><span>导入于 {timeLabel(currentVersion.created_at)} · {sizeLabel(currentVersion.size_bytes)} · {versions.length} 个版本</span><span className="metadata-chips"><span>{active.category}</span>{active.tags.map(t => <span key={t}>{t}</span>)}</span></div>}
          <div className="reader-source-tools" hidden={view!=="text"}><section className="material-study-actions" aria-label="从当前资料继续学习"><div><strong><Icon name="ai" size={17}/>读到这里，继续深入</strong><p>沿用当前 v{currentVersion?.version_no} 原文 · 先预览，再确认发送</p></div><button className="secondary" disabled={busy || reading || !selected.length} onClick={() => study("qa")}><Icon name="ai" size={16}/>向这份资料提问</button><button className="secondary" disabled={busy || reading || !selected.length} onClick={() => study("report")}><Icon name="list" size={16}/>整理学习报告</button></section>
          <CitationTarget token={token} courseId={courseId} disabled={busy} onSelect={setTargetNote} refresh={citationRefresh}/></div>

        </>}
        {view === "native" && officeKind ? <><button className="secondary" onClick={() => setView("text")}><Icon name="list" size={16}/>返回文本与引用</button><Suspense fallback={<p className="material-loading" role="status">正在打开原格式阅读器…</p>}><OfficeReader onPageChange={page=>{recordPosition(page,"native");if(autoFocusNative.current===versionId){autoFocusNative.current="";if(!tracking.current)document.querySelector(".native-office-reader")?.scrollIntoView({block:"start"});}}} key={versionId} token={token} versionId={versionId} kind={officeKind} name={active?.name || "课程资料"} initialPage={officeKind==="pptx"?previewPage:1} compatibilityReady={currentVersion?.preview_status==="SUCCEEDED"} onCompatibility={() => void showPreview()} onDownload={() => void download()}/></Suspense></> : view === "pdf" && previewUrl ? <><button className="secondary" onClick={() => setView("text")}><Icon name="list" size={16}/>返回文本与引用</button><Suspense fallback={<p className="material-loading" role="status">正在打开按页阅读器…</p>}><PdfReader onPageChange={page=>recordPosition(page,"pdf")} key={versionId} url={previewUrl} initialPage={previewPage} name={active?.name || "课程资料"} sourceType={currentVersion?.original_filename.toLowerCase().endsWith(".pptx") ? "slide" : currentVersion?.original_filename.toLowerCase().endsWith(".docx") ? "preview_page" : "page"} onDownload={() => void download()} onTranscribe={currentVersion?.original_filename.toLowerCase().endsWith(".pdf") ? page => setTranscriptRequest({page,serial:Date.now()}) : undefined} onCapture={async (file, page) => {
          await api.uploadAsset(token, courseId, file, `${active?.name || "课程资料"} · 第 ${page} 页`, {versionId, page});
          if (alive.current) { if(assetTools.current)assetTools.current.open=true;setAssetRefresh(s => s + 1); onNotice("当前页图片已保存，来源版本与页号已记录"); }
        }}/></Suspense></> : reading ? <div className="material-loading" role="status"><Icon name="refresh" className="is-spinning"/>正在读取这个版本…</div> : selected.length ? <>
          <div className="reader-searchbar"><div className="input-with-icon"><Icon name="search" size={16}/><input aria-label="在当前版本原文中查找" value={readerQuery} onChange={e => setReaderQuery(e.target.value)} placeholder="在这份原文中查找…"/>{readerQuery && <button className="icon-button" aria-label="清空原文查找" onClick={() => setReaderQuery("")}><Icon name="close" size={14}/></button>}</div><small role="status">{shownChunks.length} / {selected.length} 个片段</small></div>
          <details className="reader-directory" open><summary><Icon name="list" size={16}/>原文目录<span>{shownChunks.length}</span></summary><div className="reader-outline" aria-label="资料目录">{shownChunks.map((chunk, index) => <button className="secondary" key={`${chunk.id}:${index}`} onClick={() => {recordPosition(1,"text",chunk.id);scrollToChunk(chunk.id);}}>{index + 1}. {chunk.locator_value}</button>)}</div></details>
          <nav className="reader-text-pagination" aria-label="原文分页"><button className="secondary" disabled={!windowPage.page} onClick={()=>changeTextPage(windowPage.page-1)}>上一组原文</button><label>跳转<select aria-label="跳到原文页" value={windowPage.page} onChange={event=>changeTextPage(Number(event.target.value))}>{Array.from({length:windowPage.pages},(_,index)=><option key={index} value={index}>第 {index+1} / {windowPage.pages} 页</option>)}</select></label><span>{shownChunks.length?`${windowPage.start+1}–${windowPage.end} / ${shownChunks.length} 个片段`:"无匹配片段"}</span><button className="secondary" disabled={windowPage.page+1>=windowPage.pages} onClick={()=>changeTextPage(windowPage.page+1)}>下一组原文</button></nav><div ref={paperHost} className="reading-paper" style={{ fontSize }}>{visibleChunks.map((chunk,index) => <article id={"chunk-" + chunk.id} tabIndex={-1} className={"chunk " + (chunk.id === readingTarget ? "chunk-highlight" : "")} key={`${chunk.id}:${index}`}><div className="chunk-heading"><span className="locator">{({slide:"幻灯片",page:"页",heading:"标题",docx_block:"正文块"} as Record<string,string>)[chunk.locator_type] || chunk.locator_type} · {chunk.locator_value}</span><span className="chunk-source-label">{chunk.source_kind === "manual_transcript" ? chunk.transcript_status === "SUPERSEDED" ? "人工补录 · 历史确认" : "人工补录 · 已确认" : "文件提取"}</span><span className="chunk-reference-count">{referencesFailed ? "引用标记暂不可用" : referencesLoading ? "正在核对引用…" : references.filter(r => r.chunk_id === chunk.id).length > 0 ? references.filter(r => r.chunk_id === chunk.id).length + " 条笔记引用" : ""}</span></div><p><Highlight text={chunk.text} query={readerQuery}/></p><div className="chunk-actions"><button className="secondary" disabled={busy||reading} onClick={()=>setConnections({versionId,chunkId:chunk.id,locator:chunk.locator_value})}><Icon name="link" size={15}/>查看这段关联</button><button className="secondary" disabled={busy||reading} onClick={()=>bookmark(chunk)}><Icon name="bookmark" size={15}/>添加书签</button><button className="secondary citation-action" disabled={!targetNote || busy} onClick={() => void cite(chunk)}><Icon name="link" size={15}/>引用到所选笔记<Icon name="arrow" size={14}/></button><button className="secondary" disabled={busy||metadataDirty} onClick={()=>void excerptNote(chunk)}><Icon name="notes" size={15}/>摘录为新笔记</button><button className="secondary" disabled={busy} onClick={() => study("qa", chunk.id)}><Icon name="ai" size={15}/>就此片段提问</button></div></article>)}</div>
          {!shownChunks.length && <EmptyInline text="当前版本没有匹配片段，试试更短的关键词"/>}<p className="hint reader-footnote">结构化文本保留原文定位；阅读原始版式请打开 PDF 预览。</p>
        </> : <EmptyState title={active ? "这个版本暂时没有可读文本" : "从一份资料，开启一段学习"} text={active ? "处理完成后将自动显示正文；扫描 PDF 可预览原页，并在下方人工补录文字。" : "在左侧上传或选择资料。整理、查找、引用，都从这里开始。"}/>}
        {versionId && currentVersion?.original_filename.toLowerCase().endsWith(".pdf") && <Transcripts key={`transcripts:${versionId}`} token={token} versionId={versionId} request={transcriptRequest} onPreview={page => void previewAt(page)} onChanged={refreshTranscripts} onError={onError}/>}
        {versionId&&active&&<ReferenceNotes key={`references:${versionId}`} token={token} courseId={courseId} documentId={active.id} versionId={versionId} chunks={selected} refresh={citationRefresh} onSelect={onNote} onError={onError} onReload={()=>void loadReferences(versionId)}/>}
      </section>{notebookVisited&&active&&versionId&&<div className="reader-companion" hidden={!notebookOpen}><Suspense fallback={<p role="status">正在打开阅读笔记…</p>}><ReaderNotebook key={versionId} token={token} courseId={courseId} documentId={active.id} active={notebookOpen} refresh={citationRefresh} name={active.name} versionId={versionId} chunks={selected} initialChunkId={initialTarget?.chunkId} references={references} onNote={onNote} onError={onError} onSaved={async()=>{setCitationRefresh(value=>value+1);await loadReferences(versionId);}} onClose={()=>{if(window.dispatchEvent(new Event("hustudy:before-reader-notebook-close",{cancelable:true})))setNotebookOpen(false);}}/></Suspense></div>}{aiVisited&&active&&currentVersion&&<div className="reader-companion" hidden={!aiOpen}><Suspense fallback={<p role="status">正在打开AI阅读助手…</p>}><ReaderAI key={versionId} currentPage={currentReadingPage} token={token} courseId={courseId} documentId={active.id} versionId={versionId} versionNo={currentVersion.version_no} name={active.name} onClose={()=>{aiSourceSequence.current++;setAiOpen(false);}} onSource={assistantSource} onNote={onNote} onSaved={()=>{setCitationRefresh(value=>value+1);void loadReferences(versionId);}} onNotice={onNotice} onError={onError}/></Suspense></div>}</div>
    </div>
    <MaterialExports hidden={focused} refreshKey={assetRefresh} selected={selection} openSelection={exportSelection} disabled={busy} key={courseId} token={token} courseId={courseId} onError={onError} onNotice={onNotice}/>
    <details ref={assetTools} className="panel material-image-tools" hidden={focused}><summary><Icon name="image" size={17}/>课程图片与截图 <span>按需打开 · 保留原页来源</span></summary><AssetLibrary onChanged={() => setAssetRefresh(value => value + 1)} onNote={onNote} refreshKey={assetRefresh} onSource={target => {
      void api.document(token, target.documentId).then(doc => { if (alive.current) void openDocument(doc, target); }).catch(onError);
    }} token={token} courseId={courseId} onError={onError} onNotice={onNotice}/></details>
    {!focused && <details className="panel material-jobs"><summary className="jobs-summary"><span><Icon name="clock"/>处理记录</span><span className="hint">{jobsFailed ? "处理记录暂不可用" : pending ? pending + " 个任务正在排队或处理" : jobInfo.total + " 条匹配任务记录"}<Icon name="arrow" size={16}/></span></summary><div className="panel-title jobs-filter"><span className="hint">解析、索引与预览独立记录 · 全部历史可翻页 · 取消保留原件和引用</span><div className="material-job-filter-controls"><select aria-label="按任务类型筛选" value={jobKind} onChange={e=>{setJobOffset(0);setJobKind(e.target.value);}}><option value="all">全部类型</option><option value="PARSE">原文解析</option><option value="INDEX">关键词索引</option><option value="PREVIEW">预览转换</option></select><select aria-label="筛选处理记录" value={jobFilter} onChange={e => { setJobOffset(0); setJobFilter(e.target.value); }}><option value="all">全部任务</option><option value="pending">正在处理</option><option value="failed">失败任务</option><option value="cancelled">已取消</option><option value="succeeded">已完成</option></select></div></div>{jobsFailed&&<p role="alert" className="inline-retry">处理记录暂不可用，资料仍可阅读。<button className="secondary" disabled={jobsLoading} onClick={()=>void loadJobs().catch(onError)}>重试处理记录</button></p>}{shownJobs.map((job,index) => <div className="job-row material-job" key={`${job.id}:${index}`}><div className="job-identity"><strong>{job.document_name || "课程资料"}{job.version_no ? " · v" + job.version_no : ""}</strong><small>{({PARSE:"原文解析", INDEX:"关键词索引", PREVIEW:"预览转换"} as Record<string,string>)[job.type] || job.type} · 第 {job.attempt_count}/{job.max_attempts} 次尝试</small></div><Status value={job.status}/><div className="job-progress"><progress aria-label={(job.document_name || "资料") + " " + job.type + "处理进度"} value={job.progress} max={100}/><span>{job.error || (job.status === "QUEUED" ? "等待后台处理" : job.status === "SUCCEEDED" ? "处理完成" : job.status === "CANCELLED" ? "已取消，结果不会写入" : "处理中")}</span></div>{job.document_id&&job.resource_id&&<button className="secondary material-job-source" disabled={busy||reading} onClick={()=>void openReadingSource(job.document_id!,job.resource_id,"").then(opened=>{if(opened)document.querySelector<HTMLElement>(".reader-workspace")?.scrollIntoView({block:"start"});}).catch(onError)}><Icon name="file" size={15}/>回到资料版本</button>}{["QUEUED", "RUNNING"].includes(job.status) && <button className="secondary" disabled={busy} onClick={() => void cancel(job)}><Icon name="close" size={15}/>取消</button>}{["FAILED", "CANCELLED"].includes(job.status) && <button className="secondary" disabled={job.attempt_count >= job.max_attempts || busy} onClick={() => void retry(job)}><Icon name="refresh" size={15}/>{job.status === "CANCELLED" ? "恢复" : "重试"}</button>}</div>)}<nav className="catalogue-pages" aria-label="任务分页"><button className="secondary" disabled={busy || jobsLoading || jobOffset===0} onClick={() => setJobOffset(Math.max(0,jobOffset-10))}>上一页</button><span role="status">{Math.floor(jobOffset/10)+1} / {Math.max(1,Math.ceil(jobInfo.total/10))} 页 · {jobInfo.total} 条</span><button className="secondary" disabled={busy || jobsLoading || jobOffset+10>=jobInfo.total} onClick={() => setJobOffset(jobOffset+10)}>下一页</button></nav>{!shownJobs.length && !jobsFailed && !jobsLoading && <EmptyInline text={jobs.length ? "没有符合条件的任务" : "上传后可在这里查看处理状态"}/>}</details>}
    <MaterialHealth open={healthOpen} token={token} courseId={courseId} onClose={()=>setHealthOpen(false)} onVersion={item=>openReadingSource(item.document_id,item.version_id,"")} onRefresh={load} onBusy={setBusy} onError={onError}/>
    <SourceConnections open={!!connections&&connections.versionId===versionId} token={token} courseId={courseId} documentId={active?.id||""} versionId={versionId} versionNo={currentVersion?.version_no||1} name={active?.name||"课程资料"} chunkId={connections?.chunkId??null} locator={connections?.locator||""} onClose={()=>setConnections(null)} onOpen={onWorkspace} onError={onError}/>
  </div>;
}
