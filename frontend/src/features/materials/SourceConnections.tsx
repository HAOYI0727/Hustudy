import {useEffect,useRef,useState} from "react";
import {api,ApiError,type LearningLinkItem,type LearningLinkKind,type LearningLinkPage} from "../../api/client";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {Icon,type IconName} from "../../components/Icon";
import {Status} from "../../components/workspace";
import {openWorkspaceItem,type OpenWorkspace} from "../platform/CourseWorkspace";
import "./source-connections.css";

const kinds:{id:LearningLinkItem["kind"];label:string;icon:IconName}[]=[
 {id:"note",label:"知识笔记",icon:"notes"},{id:"qa",label:"资料问答",icon:"ai"},
 {id:"report",label:"学习报告",icon:"file"},{id:"topic",label:"关联知识点",icon:"link"},
 {id:"mistake",label:"相关错题",icon:"review"},
];
export function SourceConnections({open,token,courseId,documentId,versionId,versionNo,name,chunkId,locator,onClose,onOpen,onError}:{
 open:boolean;token:string;courseId:string;documentId:string;versionId:string;versionNo:number;name:string;chunkId:string|null;locator:string;
 onClose:()=>void;onOpen:OpenWorkspace;onError:(error:unknown)=>void;
}){
 const scope=versionId+":"+(chunkId||"");
 const [filters,setFilters]=useState({scope,kind:"all" as LearningLinkKind,draft:"",q:"",offset:0});
 const current=filters.scope===scope?filters:{scope,kind:"all" as LearningLinkKind,draft:"",q:"",offset:0};
 const change=(value:Partial<typeof filters>)=>setFilters({...current,...value});
 const {kind,draft,q,offset}=current;
 const [result,setResult]=useState<LearningLinkPage|null>(null),[error,setError]=useState(""),[loading,setLoading]=useState(false),[reload,setReload]=useState(0);
 const callbacks=useRef({onClose,onError});callbacks.current={onClose,onError};
 useEffect(()=>{const expired=()=>callbacks.current.onClose();window.addEventListener("hustudy:unauthorized",expired);return()=>window.removeEventListener("hustudy:unauthorized",expired);},[]);
 useEffect(()=>{
  if(!open||!versionId){setResult(null);setLoading(false);return;}
  let live=true;const controller=new AbortController();setLoading(true);setError("");setResult(null);
  queueMicrotask(()=>{if(!live)return;void api.sourceLearningLinks(token,versionId,chunkId,kind,q,offset,controller.signal).then(value=>{
   if(!live)return;
   if(value.course_id===courseId&&value.document_id===documentId&&value.version_id===versionId&&value.chunk_id===chunkId)setResult(value);
   else setError("返回的原文范围不一致，请重新读取关联。");
  }).catch(reason=>{
   if(!live)return;
   if(reason instanceof ApiError&&reason.status===401){callbacks.current.onClose();callbacks.current.onError(reason);}
   else setError(reason instanceof Error?reason.message:"暂时无法读取学习关联");
  }).finally(()=>{if(live)setLoading(false);});});
  return()=>{live=false;controller.abort();};
 },[open,token,courseId,documentId,versionId,chunkId,kind,q,offset,reload]);
 const navigate=(item:LearningLinkItem)=>{
  onClose();
  if(item.kind==="topic")onOpen("exam",{examTab:"practice",topicId:item.id});
  else if(item.kind==="mistake")onOpen("review",{mistakeId:item.id,reviewMode:"plan"});
  else openWorkspaceItem({...item,kind:item.kind},onOpen);
 };
 const expiredPage=!!result&&offset>0&&offset>=result.total;
 return <WorkspaceDialog open={open} title="原文学习关联" className="source-links-dialog" onClose={onClose}>
  <div className="source-links-intro"><span><Icon name="link" size={23}/></span><div><h3>从这一段原文，找回已有理解</h3><strong>{name} · v{versionNo}</strong><p>{chunkId?`仅当前片段 · ${locator}`:"当前资料版本 · 全部原文片段"}</p></div></div>
  <p className="hint">按已保存的原文引用或明确的题库版本来源关联；打开已有成果，继续理解与复盘。</p>
  <form className="source-links-filters" onSubmit={event=>{event.preventDefault();change({q:draft.trim(),offset:0});setReload(value=>value+1);}}>
   <label>关联类型<select aria-label="筛选原文关联类型" value={kind} onChange={event=>change({kind:event.target.value as LearningLinkKind,offset:0})}><option value="all">全部关联</option>{kinds.map(row=><option value={row.id} key={row.id}>{row.label}</option>)}</select></label>
   <label>查找标题<input aria-label="查找原文关联标题" maxLength={200} placeholder="笔记、问题、报告、知识点或试卷…" value={draft} onChange={event=>change({draft:event.target.value})}/></label><button className="primary"><Icon name="search" size={15}/>查找关联</button>
  </form>
  {result&&<div className="source-links-counts" aria-label="原文关联概览">{kinds.map(row=><button key={row.id} aria-pressed={kind===row.id} onClick={()=>change({kind:row.id,offset:0})}><Icon name={row.icon} size={14}/>{row.label}<strong>{result.counts[row.id]}</strong></button>)}</div>}
  <div className="source-links-results" aria-live="polite" aria-busy={loading}>
   {loading?<p role="status" className="source-links-empty"><Icon name="refresh" className="is-spinning"/>正在读取这份原文的学习关联…</p>:error?<div role="alert" className="source-links-empty"><p>学习关联暂时无法读取：{error}</p><button className="secondary" onClick={()=>setReload(value=>value+1)}>重新读取学习关联</button></div>:result?<>
    <p className="hint" role="status">匹配 {result.total} 条{q?` · 标题包含「${q}」`:""}</p>
    <div className="source-links-grid">{result.items.map(item=>{const type=kinds.find(row=>row.id===item.kind)!;return <article key={`${item.kind}:${item.id}`} className="source-link-card">
     <button className="source-link-open" aria-label={item.kind==="topic"?`按知识点设置练习：${item.title}`:`打开${type.label}：${item.title}`} onClick={()=>navigate(item)}><span className="source-link-symbol"><Icon name={type.icon} size={20}/></span><span className="source-link-copy"><small>{type.label}</small><strong>{item.title}</strong><span>{item.kind==="topic"?<span className="source-link-badge">有原文依据 · 设置练习</span>:<Status value={item.status}/>}<time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleDateString("zh-CN")}</time></span></span><Icon name="arrow" size={15}/></button>
     {item.kind==="mistake"&&item.review&&<section className="source-review-summary" aria-label="关联错题复习摘要">
      <div><span className={"source-review-mastery "+(item.review.mastered===true?"is-mastered":"")}>{item.review.mastered===null?"掌握状态需核对":item.review.mastered?"已掌握 · 保留复习":"待掌握"}</span><small>{item.source_relation==="version"?"题库版本来源 · 未定位片段":"有逐字原文依据"}</small></div>
      <p>{item.review.pending_count?<>待复习 {item.review.pending_count} 项{item.review.due_count>0&&<strong> · 今日或逾期 {item.review.due_count} 项</strong>}<br/>最早日期 <time dateTime={item.review.next_due_date||undefined}>{item.review.next_due_date}</time></>:"尚无待复习计划，可进入错题页安排日期。"}</p>
      <button className="secondary" aria-label={`打开错题与复习：${item.title}`} onClick={()=>navigate(item)}><Icon name="review" size={15}/>错题与复习 <Icon name="arrow" size={14}/></button>
     </section>}
    </article>;})}</div>
    {!result.items.length&&<div className="source-links-empty"><Icon name="link" size={28}/><p>{expiredPage?"关联已有变化，请回第一页重新核对。":q||kind!=="all"?"没有匹配的关联，可以调整类型或标题。":"还没有引用这份原文的学习成果。可以先摘录为笔记，或核对知识点原文依据。"}</p>{expiredPage&&<button className="secondary" onClick={()=>change({offset:0})}>回到第一页关联</button>}</div>}
    <nav className="source-links-pages" aria-label="原文关联分页"><button className="secondary" disabled={!offset} onClick={()=>change({offset:Math.max(0,offset-12)})}>上一页关联</button><span>{expiredPage?"当前页已变化":`${Math.floor(offset/12)+1} / ${Math.max(1,Math.ceil(result.total/12))} 页`}</span><button className="secondary" disabled={offset+12>=result.total} onClick={()=>change({offset:offset+12})}>下一页关联</button><button className="text-button" onClick={()=>setReload(value=>value+1)}>刷新关联</button></nav>
   </>:null}
  </div>
  <div className="source-links-footer"><p>仅显示当前范围的有效来源关联，其他依据仍需在详情核对。{result&&`复习到期按 ${result.timezone} 的 ${result.today} 核对。`}完成计划与掌握状态分别记录，关联数量不表示掌握度。</p></div>
 </WorkspaceDialog>;
}
