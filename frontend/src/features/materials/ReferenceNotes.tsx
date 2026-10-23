import {useEffect,useRef,useState} from "react";
import {api,ApiError,type Chunk,type ReferenceNotePage} from "../../api/client";
import {sessionPartition} from "../../api/query";
import {Icon} from "../../components/Icon";
import "./reference-notes.css";

type Props={token:string;courseId:string;documentId:string;versionId:string;chunks:Chunk[];refresh:number;active?:boolean;compact?:boolean;onSelect:(id:string)=>void;onReload?:()=>void;onError:(error:unknown)=>void};
export function ReferenceNotes({token,courseId,documentId,versionId,chunks,refresh,active=true,compact=false,onSelect,onReload,onError}:Props){
  const [draft,setDraft]=useState(""),[q,setQ]=useState(""),[chunkId,setChunkId]=useState(""),[offset,setOffset]=useState(0),[reload,setReload]=useState(0);
  const [result,setResult]=useState<{key:string;page:ReferenceNotePage}|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState(""),[paused,setPaused]=useState(false);
  const [controlsExpanded,setControlsExpanded]=useState(false);
  const callbacks=useRef({onError});callbacks.current={onError};
  const key=JSON.stringify([token,courseId,documentId,versionId,q,chunkId,offset,refresh,reload]);
  const page=result?.key===key?result.page:null;
  const minimal=!compact&&!controlsExpanded&&!draft&&!q&&!chunkId&&!error&&(!page||page.total===0);
  useEffect(()=>{if(page?.total)setControlsExpanded(true);},[page?.total]);
  const retry=()=>{setPaused(false);setReload(value=>value+1);};
  useEffect(()=>{
    const expired=(event:Event)=>{if((event as CustomEvent).detail!==sessionPartition(token))return;setPaused(true);setLoading(false);setResult(null);setError("登录已过期，请登录原账户后明确重新读取关联笔记。");};
    window.addEventListener("hustudy:unauthorized",expired);return()=>window.removeEventListener("hustudy:unauthorized",expired);
  },[token]);
  useEffect(()=>{
    if(!active||paused)return;
    let live=true;const controller=new AbortController();setLoading(true);setError("");setResult(null);
    void api.referenceNotes(token,versionId,q,chunkId,offset,controller.signal).then(value=>{
      if(!live)return;
      if(value.course_id!==courseId||value.document_id!==documentId||value.version_id!==versionId||value.chunk_id!==(chunkId||null))throw new Error("返回的原文范围不一致，请重新核对关联笔记。");
      if(offset&&offset>=value.total){setOffset(value.total?Math.floor((value.total-1)/6)*6:0);return;}
      setResult({key,page:value});
    }).catch(reason=>{if(!live)return;setError(reason instanceof Error?reason.message:"暂时无法读取关联笔记，请重试。");if(reason instanceof ApiError&&reason.status===401){setPaused(true);callbacks.current.onError(reason);}}).finally(()=>{if(live)setLoading(false);});
    return()=>{live=false;controller.abort();};
  },[active,paused,key]);
  return <section className={`reference-note-browser${compact?" is-compact":""}`} aria-label={compact?"阅读关联笔记检索":"引用当前资料的笔记"}>
    <header className="reference-note-heading"><span className="reference-note-symbol"><Icon name="notes" size={19}/></span><div><p className="eyebrow">SOURCE · UNDERSTANDING · CONNECTION</p><h4>{compact?"找回已经写下的理解":"引用这份原文的笔记"}</h4></div><button className="icon-button secondary" disabled={loading} aria-label="刷新原文引用笔记" onClick={()=>{retry();onReload?.();}}><Icon name="refresh" size={16}/></button></header>
    <p className="hint">按笔记合并有效引用；预览摘录不代替完整原文，笔记保留原有课程归属。</p>
    {minimal?<div className="reference-note-start">{page?<><p>还没有笔记引用这个版本，可在阅读笔记中保存理解并附上来源。</p><button className="secondary" onClick={()=>setControlsExpanded(true)}>展开笔记检索</button></>:<p role="status">正在查找关联笔记…</p>}</div>:<>
    <form className="reference-note-filters" onSubmit={event=>{event.preventDefault();setQ(draft.trim());setOffset(0);retry();}}><label>笔记标题<input aria-label="查找引用笔记标题" value={draft} maxLength={200} onChange={event=>setDraft(event.target.value)} placeholder="例如：进程、线程、我的疑问…"/></label><label>原文范围<select aria-label="筛选引用原文片段" value={chunkId} onChange={event=>{setChunkId(event.target.value);setOffset(0);setPaused(false);}}><option value="">当前版本全部片段</option>{chunkId&&!chunks.some(chunk=>chunk.id===chunkId)&&<option value={chunkId} disabled>原片段已不可用，请重置范围</option>}{chunks.map(chunk=><option key={chunk.id} value={chunk.id}>{chunk.locator_value}</option>)}</select></label><button className="secondary"><Icon name="search" size={15}/>查找引用笔记</button>{(draft||q||chunkId)&&<button type="button" className="text-button" onClick={()=>{setDraft("");setQ("");setChunkId("");setOffset(0);retry();}}>重置引用笔记筛选</button>}</form>
    <div className="reference-note-results" aria-busy={loading}>
    {error?<div className="reference-note-empty" role="alert"><Icon name="info" size={25}/><strong>关联笔记暂时无法读取</strong><p>{error}</p><button className="secondary" onClick={retry}>重试关联笔记列表</button></div>:loading||!page?<p className="hint" role="status">正在查找引用这份原文的笔记…</p>:<><p className="hint" role="status">匹配 {page.total} 篇 · {chunkId?"仅所选片段":"当前版本全部片段"}{q&&` · 标题包含“${q}”`}</p><div className="material-reference-grid reference-note-grid">{page.items.map(note=><button className="source-note-card reference-note-card" key={note.note_id} aria-label={note.note_title} onClick={()=>onSelect(note.note_id)}><span className="reference-note-card-title"><Icon name="notes" size={17}/><strong>{note.note_title}</strong><Icon name="arrow" size={15}/></span><span className="reference-note-badges"><small>{note.citation_count} 条有效引用</small>{!note.note_course_id?<small>未归课程</small>:note.note_course_id!==courseId?<small>原课程笔记</small>:null}<time dateTime={note.updated_at}>{new Date(note.updated_at).toLocaleDateString("zh-CN")}</time></span><p>{note.quote_excerpt}</p><small>{note.locator_value} · {compact?"预览所选笔记":"打开原笔记"}</small></button>)}</div>{!page.items.length&&<div className="reference-note-empty"><Icon name="notes" size={25}/><strong>{q||chunkId?"当前范围没有匹配笔记":"还没有笔记引用这个版本"}</strong><p>可调整标题或原文范围，或在阅读笔记中保存理解并附上原文。</p></div>}<nav className="catalogue-pages" aria-label="引用笔记分页"><button className="secondary" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-6))}>上一页引用笔记</button><span>{Math.floor(offset/6)+1} / {Math.max(1,Math.ceil(page.total/6))} 页 · {page.total} 篇</span><button className="secondary" disabled={offset+6>=page.total} onClick={()=>setOffset(offset+6)}>下一页引用笔记</button></nav></>}
    </div></>}
  </section>;
}
