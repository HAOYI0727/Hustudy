import {useEffect,useRef,useState} from "react";
import {api,ApiError,type MaterialHealthPage,type MaterialHealthIssue,type MaterialHealthItem,type MaterialHealthJob} from "../../api/client";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {Status} from "../../components/workspace";
import {Icon} from "../../components/Icon";
import "./material-health.css";

const filters:[MaterialHealthIssue,string][]=[["attention","需要检查"],["all","全部最新版本"],["text","缺少可用正文"],["parse","解析异常"],["index","索引异常"],["preview","兼容预览异常"],["processing","正在处理"]];
const stages=[{type:"PARSE",key:"parse_status",name:"解析"},{type:"INDEX",key:"index_status",name:"索引"},{type:"PREVIEW",key:"preview_status",name:"兼容预览"}] as const;
type Props={open:boolean;token:string;courseId:string;onClose:()=>void;onVersion:(item:MaterialHealthItem)=>Promise<unknown>;onRefresh:()=>Promise<unknown>;onBusy:(value:boolean)=>void;onError:(error:unknown)=>void};

export function MaterialHealth({open,token,courseId,onClose,onVersion,onRefresh,onBusy,onError}:Props){
 const [issue,setIssue]=useState<MaterialHealthIssue>("attention"),[draft,setDraft]=useState(""),[q,setQ]=useState(""),[offset,setOffset]=useState(0),[reload,setReload]=useState(0);
 const [data,setData]=useState<MaterialHealthPage|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[needsCheck,setNeedsCheck]=useState(false);
 const running=useRef(false),check=useRef(false),callbacks=useRef({onClose,onVersion,onRefresh,onBusy,onError});callbacks.current={onClose,onVersion,onRefresh,onBusy,onError};
 useEffect(()=>{const expired=()=>callbacks.current.onClose();window.addEventListener("hustudy:unauthorized",expired);return()=>window.removeEventListener("hustudy:unauthorized",expired);},[]);
 useEffect(()=>{
  if(!open)return;
  let live=true;const controller=new AbortController();setLoading(true);setError("");setData(null);
  queueMicrotask(()=>{if(!live)return;void api.materialHealth(token,courseId,issue,q,offset,controller.signal).then(value=>{
   if(!live)return;if(value.course_id!==courseId)throw new Error("返回的资料检查范围不一致，请重新读取。");setData(value);setNeedsCheck(false);if(check.current)setNotice("已重新核对任务状态，请按最新结果和剩余次数操作。");check.current=false;
  }).catch(reason=>{if(!live)return;if(reason instanceof ApiError&&reason.status===401){callbacks.current.onClose();callbacks.current.onError(reason);}else setError(reason instanceof Error?reason.message:"资料检查暂不可读");}).finally(()=>{if(live)setLoading(false);});});
  return()=>{live=false;controller.abort();};
 },[open,token,courseId,issue,q,offset,reload]);
 useEffect(()=>{const guard=(event:Event)=>{if(running.current)event.preventDefault();};const unload=(event:BeforeUnloadEvent)=>{if(running.current){event.preventDefault();event.returnValue="";}};window.addEventListener("hustudy:before-navigate",guard);window.addEventListener("beforeunload",unload);return()=>{window.removeEventListener("hustudy:before-navigate",guard);window.removeEventListener("beforeunload",unload);};},[]);
 const restore=async(job:MaterialHealthJob)=>{
  if(running.current||check.current)return;running.current=true;setBusy(true);callbacks.current.onBusy(true);setNotice("");
  try{await api.retryJob(token,job.id);setNotice("恢复请求已入队，实际处理结果请刷新检查；尝试次数沿用原任务。");setReload(value=>value+1);void callbacks.current.onRefresh().catch(callbacks.current.onError);}
  catch(reason){check.current=true;setNeedsCheck(true);setNotice((reason instanceof Error?reason.message:"任务提交未确认")+"；请先重新核对任务状态，再决定是否恢复。不会自动重试。");callbacks.current.onError(reason);}
  finally{running.current=false;setBusy(false);callbacks.current.onBusy(false);}
 };
 const expiredPage=!!data&&offset>0&&offset>=data.total;
 return <WorkspaceDialog open={open} title="资料检查" onClose={onClose} busy={busy} className="material-health-dialog">
  <header className="material-health-intro"><span><Icon name="check" size={25}/></span><div><h3>把资料准备好，再继续学习</h3><p>核对当前课程每份资料的最新版本；历史任务仍保留在处理记录。</p></div></header>
  <form className="material-health-filters" onSubmit={event=>{event.preventDefault();setQ(draft.trim());setOffset(0);setReload(value=>value+1);}}>
   <label>检查范围<select aria-label="资料检查范围" disabled={busy} value={issue} onChange={event=>{setIssue(event.target.value as MaterialHealthIssue);setOffset(0);}}>{filters.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
   <label>资料名称<input aria-label="查找检查资料名称" disabled={busy} maxLength={200} value={draft} onChange={event=>setDraft(event.target.value)} placeholder="按资料名称查找…"/></label><button className="primary" disabled={busy}>查找资料检查</button>
  </form>
  {notice&&<p role={needsCheck?"alert":"status"} className="material-health-notice">{notice}</p>}
  {needsCheck&&<button className="secondary" disabled={busy||loading} onClick={()=>setReload(value=>value+1)}>重新核对任务状态</button>}
  <section aria-live="polite" aria-busy={loading}>
   {loading?<p role="status">正在核对资料最新版本…</p>:error?<div role="alert"><p>资料检查暂时无法读取：{error}</p><button className="secondary" onClick={()=>setReload(value=>value+1)}>重试资料检查</button></div>:data?<>
    <div className="material-health-counts"><span>匹配资料 <strong>{data.counts.materials}</strong></span><span>需检查 <strong>{data.counts.attention}</strong></span><span>有可用正文 <strong>{data.counts.readable}</strong></span><span>处理中 <strong>{data.counts.processing}</strong></span></div>
    <p className="hint">当前范围 {data.total} 份 · 同一资料可有多项问题。兼容预览异常时仍可尝试文本或原格式阅读。</p>
    <div className="material-health-grid">{data.items.map((item,index)=><article className="material-health-card" key={`${item.document_id}:${index}`}>
     <header><span className="material-health-file"><Icon name="file" size={22}/></span><div><h4>{item.name}</h4><small>最新版本 v{item.version_no} · {item.has_text?"有可用正文":"暂无当前可用正文"}</small></div><button className="secondary" disabled={busy} aria-label={`打开检查资料：${item.name}`} onClick={()=>{onClose();void callbacks.current.onVersion(item).catch(callbacks.current.onError);}}>打开版本 <Icon name="arrow" size={14}/></button></header>
     <div className="material-health-issues">{item.issues.filter(value=>value!=="processing").map(value=><span key={value}>{filters.find(([key])=>key===value)?.[1]}</span>)}{!item.issues.length&&<span>当前检查正常</span>}</div>
     {item.issues.includes("text")&&<p className="hint">请核对原件与解析；扫描PDF可在阅读页人工补录并确认文字。</p>}
     <div className="material-health-stages">{stages.map(stage=>{const job=item.jobs.find(row=>row.type===stage.type),abnormal=["FAILED","CANCELLED"].includes(item[stage.key]);const actionable=job&&abnormal&&["FAILED","CANCELLED"].includes(job.status)&&job.attempt_count<job.max_attempts&&(stage.type!=="INDEX"||item.has_text);return <section key={stage.type} aria-label={`${stage.name}检查：${item.name}`}><div><strong>{stage.name}</strong><Status value={item[stage.key]}/>{job&&<small>已尝试 {job.attempt_count}/{job.max_attempts}</small>}</div>{job?.error&&abnormal&&<p>{job.error}</p>}{actionable?<button className="secondary" disabled={busy||needsCheck||loading} onClick={()=>void restore(job)}>恢复{stage.name}</button>:job&&abnormal&&job.attempt_count>=job.max_attempts?<small>已达尝试上限，请核对原件与失败原因。</small>:stage.type==="INDEX"&&abnormal&&!item.has_text?<small>请先完成解析或确认人工正文。</small>:null}</section>;})}</div>
    </article>)}</div>
    {!data.items.length&&<div className="material-health-empty"><Icon name="check" size={30}/><p>{expiredPage?"资料状态已有变化，请回第一页核对。":data.counts.materials?"当前匹配的最新版本没有这类检查项。":"没有匹配资料，可调整名称或先导入课件。"}</p>{expiredPage&&<button className="secondary" onClick={()=>setOffset(0)}>回第一页检查</button>}</div>}
    <nav className="catalogue-pages" aria-label="资料检查分页"><button className="secondary" disabled={busy||!offset} onClick={()=>setOffset(Math.max(0,offset-12))}>上一页检查</button><span>{expiredPage?"当前页已变化":`${Math.floor(offset/12)+1} / ${Math.max(1,Math.ceil(data.total/12))} 页`}</span><button className="secondary" disabled={busy||offset+12>=data.total} onClick={()=>setOffset(offset+12)}>下一页检查</button><button className="text-button" disabled={busy} onClick={()=>setReload(value=>value+1)}>刷新资料检查</button></nav>
   </>:null}
  </section><p className="hint material-health-footnote">检查仅核对已有正文和处理状态，不评估课件内容质量。恢复沿用原任务预算，排队不等于处理完成。</p>
 </WorkspaceDialog>;
}
