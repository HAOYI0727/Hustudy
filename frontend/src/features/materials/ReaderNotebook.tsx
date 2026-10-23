import {useEffect,useRef,useState} from "react";
import {api,ApiError,type Chunk,type MaterialReference,type Note,type NoteSummary} from "../../api/client";
import {NotePreview} from "../../components/knowledge";
import {Icon} from "../../components/Icon";
import {ReferenceNotes} from "./ReferenceNotes";
import {sessionPartition} from "../../api/query";
import {loadNoteCatalog} from "../notes/noteCatalog";
import {saveRecovery,removeRecovery,type PendingNote} from "../notes/noteRecovery";

type Props={token:string;courseId:string;documentId:string;active?:boolean;refresh?:number;name:string;versionId:string;chunks:Chunk[];references:MaterialReference[];initialChunkId?:string;onClose:()=>void;onNote:(id:string)=>void;onSaved:()=>Promise<void>;onError:(error:unknown)=>void};
type Request=PendingNote&{citations:{version_id:string;chunk_id:string;quote:string}[]};
export default function ReaderNotebook({token,courseId,documentId,active=true,refresh=0,name,versionId,chunks,references,initialChunkId,onClose,onNote,onSaved,onError}:Props){
 const [tab,setTab]=useState<"write"|"related">("write"),[title,setTitle]=useState(`${name} · 阅读笔记`.slice(0,240)),[content,setContent]=useState("");
 const [chunkId,setChunkId]=useState(chunks.some(row=>row.id===initialChunkId)?initialChunkId!:""),[busy,setBusy]=useState(false),[pending,setPending]=useState<Request|null>(null),[saved,setSaved]=useState<Note|null>(null),[message,setMessage]=useState("");
 const [owner,setOwner]=useState(""),[storageError,setStorageError]=useState("");
 const [preview,setPreview]=useState<Note|null>(null),[index,setIndex]=useState<NoteSummary[]>([]),[previewId,setPreviewId]=useState(""),[previewFailed,setPreviewFailed]=useState(false),[reload,setReload]=useState(0);
 const [previewPaused,setPreviewPaused]=useState(false);
 const running=useRef(false),identity=useRef(crypto.randomUUID()),savedTitle=useRef(title);
 const dirty=!!content||!!pending||title!==savedTitle.current;
 const source=chunks.find(chunk=>chunk.id===chunkId);
 const citations=source?[{version_id:versionId,chunk_id:source.id,quote:Array.from(source.text).slice(0,500).join("")}]:[];
 const local=useRef({title,content,pending,owner,dirty,citations});local.current={title,content,pending,owner,dirty,citations};
 const flush=()=>{
  const value=local.current;if(!value.owner||!value.dirty)return "";
  return saveRecovery({id:identity.current,userId:value.owner,courseId,noteId:null,noteCourseId:null,baseRevision:null,draft:{title:value.title,content:value.content,tags:[]},tagInput:"",pending:value.pending,citations:value.citations,updatedAt:new Date().toISOString()});
 };
 useEffect(()=>{let live=true;void api.me(token).then(user=>{if(live)setOwner(user.id);}).catch(onError);return()=>{live=false;};},[token]);
 useEffect(()=>{if(!dirty){if(owner)removeRecovery({userId:owner,courseId,id:identity.current});return;}const timer=window.setTimeout(()=>setStorageError(flush()),250);return()=>window.clearTimeout(timer);},[title,content,pending,owner,chunkId,dirty]);
 useEffect(()=>{
  const guard=(event:Event)=>{if(event.defaultPrevented)return;if(running.current){event.preventDefault();return;}const failure=flush();if(failure)setStorageError(failure);if(local.current.dirty&&!window.confirm(failure?"本机恢复副本未写入，请先复制正文。仍要离开阅读笔记？":"阅读笔记尚未保存，离开后可在知识笔记检查本机恢复副本。继续离开？"))event.preventDefault();};
  const unload=(event:BeforeUnloadEvent)=>{flush();if(local.current.dirty||running.current){event.preventDefault();event.returnValue="";}};
  const hidden=()=>{if(document.hidden)flush();},pagehide=()=>{flush();};
  window.addEventListener("hustudy:before-navigate",guard);window.addEventListener("hustudy:before-material-change",guard);window.addEventListener("hustudy:before-reader-notebook-close",guard);window.addEventListener("beforeunload",unload);window.addEventListener("pagehide",pagehide);document.addEventListener("visibilitychange",hidden);
  return()=>{flush();window.removeEventListener("hustudy:before-navigate",guard);window.removeEventListener("hustudy:before-material-change",guard);window.removeEventListener("hustudy:before-reader-notebook-close",guard);window.removeEventListener("beforeunload",unload);window.removeEventListener("pagehide",pagehide);document.removeEventListener("visibilitychange",hidden);};
 },[courseId]);
 useEffect(()=>{
  const expired=(event:Event)=>{if((event as CustomEvent).detail===sessionPartition(token)){setPreviewPaused(true);setPreview(null);setPreviewFailed(true);}};
  window.addEventListener("hustudy:unauthorized",expired);return()=>window.removeEventListener("hustudy:unauthorized",expired);
 },[token]);
 useEffect(()=>{
  if(!active||tab!=="related"||!previewId||previewPaused)return;let live=true;const controller=new AbortController();setPreview(null);setPreviewFailed(false);
  void Promise.all([api.note(token,previewId,controller.signal),loadNoteCatalog(token)]).then(([note,rows])=>{if(live){setPreview(note);setIndex(rows);}}).catch(()=>{if(live)setPreviewFailed(true);});
  return()=>{live=false;controller.abort();};
 },[active,tab,token,previewId,previewPaused,reload]);
 const related=Array.from(new Map(references.map(row=>[row.note_id,{id:row.note_id,title:row.note_title}])).values());
 return <aside className="panel reader-notebook" aria-label="阅读笔记侧栏"><div className="panel-title"><div><p className="eyebrow">WRITE BESIDE THE SOURCE</p><h3><Icon name="notes"/>阅读笔记</h3></div><button className="secondary" disabled={busy} aria-label="关闭阅读笔记" onClick={onClose}>收起</button></div><nav className="notes-view-tabs" aria-label="阅读笔记模式"><button aria-pressed={tab==="write"} onClick={()=>setTab("write")}>写下理解</button><button aria-pressed={tab==="related"} onClick={()=>setTab("related")}>关联笔记 · {related.length}</button></nav>
 <form hidden={tab!=="write"} onSubmit={async event=>{
  event.preventDefault();if(running.current||!content.trim()||!title.trim()||!owner)return;
  running.current=true;setBusy(true);setMessage("");
  const request=pending||{request_id:crypto.randomUUID(),course_id:courseId,title:title.trim(),content,tags:[],citations};
  setPending(request);local.current.pending=request;setStorageError(flush());
  try{
   const note=await api.createNote(token,request);savedTitle.current=title;setSaved(note);setContent("");setPending(null);local.current={...local.current,content:"",pending:null,dirty:false};removeRecovery({userId:owner,courseId,id:identity.current});setMessage("理解与所选原文引用已保存，可继续在完整编辑器整理。");await onSaved();
  }catch(error){if(error instanceof ApiError&&error.status>=400&&error.status<500&&error.status!==409){setPending(null);local.current.pending=null;}setMessage(error instanceof Error?error.message:"保存未确认，请核对后显式重试原请求。");onError(error);}
  finally{running.current=false;setBusy(false);}
 }}><label>阅读笔记标题<input aria-label="阅读笔记标题" required maxLength={240} disabled={busy||!!pending} value={title} onChange={event=>setTitle(event.target.value)}/></label><label>我的理解<textarea aria-label="阅读时记录理解" rows={9} disabled={busy||!!pending} value={content} onChange={event=>setContent(event.target.value)} placeholder="用自己的话解释这个概念，记录例子与疑问…"/></label><label>附加来源片段<select aria-label="阅读笔记来源片段" disabled={busy||!!pending} value={chunkId} onChange={event=>setChunkId(event.target.value)}><option value="">暂不附加原文引用</option>{chunks.map(chunk=><option key={chunk.id} value={chunk.id}>{chunk.locator_value}</option>)}</select></label>{source&&<blockquote className="reader-note-source">{source.text.slice(0,180)}</blockquote>}<p className="hint">支持Markdown和公式；本机恢复副本可在知识笔记中查看。保存不会调用AI。</p><button className="primary" disabled={busy||!owner||!content.trim()||!title.trim()}><Icon name="check" size={16}/>{busy?"正在保存…":pending?"重试保存原笔记":"保存阅读笔记"}</button>{pending&&!busy&&<p className="hint">原请求尚待确认，输入已保留；重试沿用同一身份，不另建一篇。</p>}</form><section hidden={tab!=="related"}><ReferenceNotes compact active={active&&tab==="related"} token={token} courseId={courseId} documentId={documentId} versionId={versionId} chunks={chunks} refresh={refresh} onError={onError} onSelect={id=>{setPreviewPaused(false);setPreviewId(id);setReload(value=>value+1);}}/>{previewId&&(previewFailed?<p role="alert">笔记暂不可读取。<button className="secondary" onClick={()=>{setPreviewPaused(false);setReload(value=>value+1);}}>重试阅读笔记预览</button></p>:preview?<><h4>{preview.title}</h4><NotePreview content={preview.content} token={token} notes={index} onNote={note=>onNote(note.id)}/><button className="secondary" onClick={()=>onNote(preview.id)}>在完整编辑器打开</button></>:<p role="status">正在读取所选笔记…</p>)}</section>
 {message&&<p role={saved?"status":"alert"}>{message}</p>}{storageError&&<p role="alert">{storageError}</p>}{saved&&<button className="secondary" disabled={busy} onClick={()=>onNote(saved.id)}>打开刚保存的阅读笔记</button>}
 </aside>;
}
