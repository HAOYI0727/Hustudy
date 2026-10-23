import {useEffect,useRef,useState,type FormEvent} from "react";
import {api,ApiError,type AgendaView,type CourseAgendaPage} from "../../api/client";
import {Icon} from "../../components/Icon";
import type {OpenWorkspace} from "./CourseWorkspace";
import "./course-agenda.css";

const views:{id:AgendaView;label:string;empty:string}[]=[
  {id:"due",label:"到期回顾",empty:"当前没有今天或逾期的计划，可查看未来安排或主动练习。"},
  {id:"overdue",label:"已逾期",empty:"没有逾期计划，按自己的节奏继续学习。"},
  {id:"today",label:"今天",empty:"今天没有安排计划，可在错题回顾中选择下次日期。"},
  {id:"upcoming",label:"未来安排",empty:"还没有未来计划，可在错题回顾中安排下一次复习。"},
  {id:"completed",label:"已完成",empty:"还没有已完成的计划；完成计划与掌握判断分别记录。"},
  {id:"pending",label:"全部待办",empty:"当前课程没有待办计划，可先从资料、笔记和练习开始。"},
];

export function CourseAgenda({token,courseId,courseName,onOpen,onError}:{token:string;courseId:string;courseName:string;onOpen:OpenWorkspace;onError:(error:unknown)=>void}){
  const [open,setOpen]=useState(false),[view,setView]=useState<AgendaView>("due");
  const [draft,setDraft]=useState(""),[q,setQ]=useState(""),[offset,setOffset]=useState(0),[reload,setReload]=useState(0);
  const [result,setResult]=useState<{key:string;data:CourseAgendaPage}|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState("");
  const callbacks=useRef({onError});callbacks.current={onError};
  const key=JSON.stringify([token,courseId,view,q,offset,reload]);
  const data=result?.key===key?result.data:null;
  useEffect(()=>{
    if(!open)return;
    let live=true;const controller=new AbortController();setLoading(true);setError("");setResult(null);
    void api.courseAgenda(token,courseId,view,q,offset,controller.signal).then(page=>{
      if(!live)return;
      if(!page||page.course_id!==courseId||!page.counts||views.some(row=>!Number.isSafeInteger(page.counts[row.id])||page.counts[row.id]<0))throw new Error("暂时无法核对当前课程日程，请刷新页面后重试。");
      if(offset&&offset>=page.total){setOffset(page.total?Math.floor((page.total-1)/6)*6:0);return;}
      setResult({key,data:page});
    }).catch(reason=>{
      if(!live)return;
      setError(reason instanceof Error?reason.message:"暂时无法读取日程，请重试。");
      if(reason instanceof ApiError&&reason.status===401)callbacks.current.onError(reason);
    }).finally(()=>{if(live)setLoading(false);});
    return()=>{live=false;controller.abort();};
  },[open,key]);
  const search=(event:FormEvent)=>{event.preventDefault();setQ(draft.trim());setOffset(0);setReload(v=>v+1);};
  const selected=views.find(row=>row.id===view)!;
  return <details className="course-agenda" open={open} onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary><span className="agenda-symbol"><Icon name="clock" size={23}/></span><span className="agenda-heading"><span className="eyebrow">RETURN · REFLECT · REMEMBER</span><strong>当前课程复习日程</strong><small>{courseName} · 看清今天与之后的安排</small></span><span className="agenda-toggle">{open?"收起日程":"展开日程"}<Icon name="arrow" size={16}/></span></summary>
    {open&&<div className="agenda-body"><p className="hint">先回顾原题与来源，再决定是否重做；计划完成与掌握状态分别记录。</p>
      <nav className="agenda-views" aria-label="课程日程范围">{views.map(row=><button key={row.id} className={view===row.id?"is-selected":""} aria-pressed={view===row.id} onClick={()=>{setError("");setView(row.id);setOffset(0);}}><span>{row.label}</span><strong>{data?.counts[row.id]??"—"}</strong></button>)}</nav>
      <div className="agenda-toolbar"><form onSubmit={search}><label className="sr-only" htmlFor="course-agenda-search">搜索复习计划标题</label><input id="course-agenda-search" aria-label="搜索复习计划标题" value={draft} maxLength={200} onChange={event=>setDraft(event.target.value)} placeholder="按计划标题查找…"/><button className="secondary" type="submit"><Icon name="search" size={16}/>查找日程</button>{(draft||q)&&<button className="text-button" type="button" onClick={()=>{setDraft("");setQ("");setOffset(0);setReload(v=>v+1);}}>清除日程查找</button>}</form><button className="secondary" disabled={loading} onClick={()=>setReload(v=>v+1)}><Icon name="refresh" size={16}/>刷新日程</button></div>
      <section className="agenda-results" aria-label="当前课程日程列表" aria-busy={loading}>
      {error?<div className="agenda-error" role="alert"><Icon name="info"/><div><strong>日程暂时无法读取</strong><p>{error}</p><button className="secondary" onClick={()=>setReload(v=>v+1)}>重试课程日程</button></div></div>:loading||!data?<p role="status">正在核对当前课程的复习安排…</p>:<><p className="agenda-context" role="status">{selected.label} · {data.total}项{q&&` · 标题包含“${q}”`}<span>今天 {data.today} · {data.timezone}</span></p>
      {data.items.length?<div className="agenda-timeline">{data.items.map(plan=><button key={plan.id} className="agenda-plan" disabled={!plan.mistake_id} aria-label={`回顾复习计划：${plan.title}`} onClick={()=>plan.mistake_id&&onOpen("review",{mistakeId:plan.mistake_id,reviewMode:"plan"})}><time dateTime={plan.due_date} className={plan.status==="COMPLETED"?"is-completed":plan.due_date<data.today?"is-overdue":""}><strong>{plan.due_date.slice(8,10)}</strong><span>{plan.due_date.slice(0,7).replace("-",".")}</span></time><span className="agenda-plan-copy"><strong>{plan.title}</strong><small>{plan.status==="COMPLETED"?"计划已完成 · 可以再次回顾":plan.due_date<data.today?"已逾期 · 仍可回到原题":plan.due_date===data.today?"今天回顾 · 按自己的节奏":"未来安排 · 提前回顾也可以"}</small></span><span className="agenda-open">回顾<Icon name={plan.status==="COMPLETED"?"check":"arrow"} size={16}/></span></button>)}</div>:<div className="agenda-empty"><Icon name={q?"search":"review"} size={26}/><strong>{q?"没有匹配的复习计划":selected.empty}</strong><p>{q?"换一个标题关键词，或清除查找查看当前课程。":"可从下方学习工作台继续；日程不会自动创建或改动计划。"}</p></div>}
      <nav className="catalogue-pages" aria-label="课程日程分页"><button className="secondary" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-6))}>上一页日程</button><span>{Math.floor(offset/6)+1} / {Math.max(1,Math.ceil(data.total/6))} 页 · {data.total} 项</span><button className="secondary" disabled={offset+6>=data.total} onClick={()=>setOffset(offset+6)}>下一页日程</button></nav></>}
      </section>
    </div>}
  </details>;
}
