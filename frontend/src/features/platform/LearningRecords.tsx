import {useEffect,useRef,useState} from "react";
import {api,ApiError,type LearningRecordKind,type LearningRecordPage,type WorkspaceItem} from "../../api/client";
import {Icon,type IconName} from "../../components/Icon";
import {Status} from "../../components/workspace";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {openWorkspaceItem,type OpenWorkspace} from "./CourseWorkspace";
import "./learning-records.css";

const kinds:{id:LearningRecordKind;label:string;icon:IconName}[]=[
 {id:"all",label:"全部记录",icon:"list"},{id:"material",label:"课程资料",icon:"file"},
 {id:"note",label:"知识笔记",icon:"notes"},{id:"qa",label:"资料问答",icon:"ai"},
 {id:"report",label:"学习报告",icon:"file"},{id:"attempt",label:"练习作答",icon:"exam"},
 {id:"mistake",label:"错题复盘",icon:"review"},
];
export default function LearningRecords({open,token,courseId,courseName,onClose,onOpen,onError}:{
 open:boolean;token:string;courseId:string;courseName:string;onClose:()=>void;onOpen:OpenWorkspace;onError:(error:unknown)=>void;
}){
 const [kind,setKind]=useState<LearningRecordKind>("all"),[draft,setDraft]=useState(""),[q,setQ]=useState("");
 const [offset,setOffset]=useState(0),[reload,setReload]=useState(0),[loading,setLoading]=useState(false);
 const [result,setResult]=useState<LearningRecordPage|null>(null),[error,setError]=useState("");
 const callbacks=useRef({onClose,onError});callbacks.current={onClose,onError};
 useEffect(()=>{const expire=()=>callbacks.current.onClose();window.addEventListener("hustudy:unauthorized",expire);return()=>window.removeEventListener("hustudy:unauthorized",expire);},[]);
 useEffect(()=>{
  if(!open){setResult(null);setLoading(false);return;}
  let live=true;const controller=new AbortController();setLoading(true);setError("");setResult(null);
  // StrictMode cleans up its first effect before this task runs; do not send that abandoned read.
  queueMicrotask(()=>{if(!live)return;void api.learningRecords(token,courseId,kind,q,offset,controller.signal).then(page=>{
   if(live){if(page.course_id===courseId)setResult(page);else setError("返回的课程不一致，请重新读取记录。");}
  }).catch(reason=>{
   if(!live)return;
   if(reason instanceof ApiError&&reason.status===401){callbacks.current.onClose();callbacks.current.onError(reason);}
   else setError(reason instanceof Error?reason.message:"暂时无法读取学习记录");
  }).finally(()=>{if(live)setLoading(false);});});
  return()=>{live=false;controller.abort();};
 },[open,token,courseId,kind,q,offset,reload]);
 const first=()=>{setOffset(0);setReload(value=>value+1);};
 const pages=result?Math.max(1,Math.ceil(result.total/result.limit)):1;
 const expiredPage=!!result&&offset>0&&offset>=result.total;
 const openItem=(item:WorkspaceItem)=>{onClose();openWorkspaceItem(item,onOpen);};
 return <WorkspaceDialog open={open} title="课程学习记录" className="learning-records-dialog" onClose={onClose}>
  <div className="records-intro"><span><Icon name="clock" size={22}/></span><div><h3>找回每一步学习</h3><span className="records-course">当前课程 · {courseName}</span><p>资料、理解、笔记与练习，按最近更新排列，随时回到原工作区。</p></div></div>
  <form className="records-filters" onSubmit={event=>{event.preventDefault();setQ(draft.trim());setOffset(0);setReload(value=>value+1);}}>
   <label>记录类型<select aria-label="筛选学习记录类型" value={kind} onChange={event=>{setKind(event.target.value as LearningRecordKind);setOffset(0);}}>{kinds.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
   <label>查找标题<input aria-label="查找学习记录标题" placeholder="资料名、笔记标题或问题…" value={draft} maxLength={200} onChange={event=>setDraft(event.target.value)}/></label><button className="primary"><Icon name="search" size={16}/>查找记录</button>
  </form>
  {result&&<div className="records-type-counts" aria-label="匹配记录概览">{kinds.filter(row=>row.id!=="all").map(row=><span key={row.id} className={`record-tone-${row.id}`}><Icon name={row.icon} size={13}/>{row.label}<strong>{result.counts[row.id as WorkspaceItem["kind"]]}</strong></span>)}</div>}
  <div className="records-result" aria-live="polite" aria-busy={loading}>
   {loading?<p role="status" className="records-empty"><Icon name="refresh" className="is-spinning"/>正在连接课程学习记录…</p>:error?<div role="alert" className="records-empty"><p>学习记录暂时无法读取：{error}</p><button className="secondary" onClick={()=>setReload(value=>value+1)}>重新读取记录</button></div>:result?<>
    <p className="hint" role="status">找到 {result.total} 条{q?` · 标题包含「${q}」`:""}</p>
    <div className="records-grid">{result.items.map(item=>{
     const type=kinds.find(row=>row.id===item.kind)!;
     return <button key={`${item.kind}:${item.id}`} className={`record-card record-tone-${item.kind}`} onClick={()=>openItem(item)} aria-label={`打开${type.label}：${item.title}`}>
      <span className="record-symbol"><Icon name={type.icon} size={19}/></span><span className="record-copy"><small>{type.label}</small><strong>{item.title||type.label}</strong><span><time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleString("zh-CN",{month:"long",day:"numeric",hour:"2-digit",minute:"2-digit"})}</time><Status value={item.status}/></span></span><Icon name="arrow" size={16}/>
     </button>;
    })}</div>
    {!result.items.length&&<div className="records-empty"><Icon name="search" size={28}/><p>{expiredPage?"记录已有变化，请回到第一页重新查看。":q||kind!=="all"?"没有符合条件的记录，可以调整类型或标题。":"这里还没有学习记录，先导入资料或写下一篇笔记。"}</p>{expiredPage&&<button className="secondary" onClick={first}>回到第一页记录</button>}</div>}
    <nav className="records-pages" aria-label="学习记录分页"><button className="secondary" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-12))}>上一页记录</button><span>{expiredPage?"当前页已变化":`${Math.floor(offset/12)+1} / ${pages} 页`}</span><button className="secondary" disabled={offset+12>=result.total} onClick={()=>setOffset(offset+12)}>下一页记录</button><button className="text-button" onClick={()=>setReload(value=>value+1)}><Icon name="refresh" size={14}/>刷新记录</button></nav>
   </>:null}
  </div><p className="records-footnote">汇总当前可用内容；删除或移出后的记录不会继续列出。打开时会重新核对访问权限。</p>
 </WorkspaceDialog>;
}
