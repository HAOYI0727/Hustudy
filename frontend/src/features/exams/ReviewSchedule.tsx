import {useEffect,useRef,useState} from "react";
import {api,type ReviewPlan,type ReviewPlanPage} from "../../api/client";
import {Icon} from "../../components/Icon";

type Common={token:string;onError:(error:unknown)=>void};
function usePlanGuard(busy:boolean,dirty:boolean){
  useEffect(()=>{
    const guard=(event:Event)=>{if(event.defaultPrevented)return;if(busy||(dirty&&!window.confirm("复习计划尚有未保存的日期，放弃修改并离开？")))event.preventDefault();};
    const unload=(event:BeforeUnloadEvent)=>{if(busy||dirty){event.preventDefault();event.returnValue="";}};
    window.addEventListener("hustudy:before-navigate",guard);window.addEventListener("beforeunload",unload);
    return()=>{window.removeEventListener("hustudy:before-navigate",guard);window.removeEventListener("beforeunload",unload);};
  },[busy,dirty]);
}

export function ScheduleMistake({token,id,onError}:{id:string}&Common){
  const [today,setToday]=useState(""),[due,setDue]=useState(""),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  const [reload,setReload]=useState(0),[failed,setFailed]=useState(false);
  const running=useRef(false);
  useEffect(()=>{let live=true;setFailed(false);void api.reviewSchedule(token,"pending",0,1).then(result=>{if(live)setToday(result.today);}).catch(()=>{if(live)setFailed(true);});return()=>{live=false;};},[token,reload]);
  usePlanGuard(busy,!!due&&due!==today);
  return <section className="review-plan-create" aria-label="安排错题复习"><div><p className="eyebrow">COME BACK TO IT</p><h3>给这道错题，安排一次回顾</h3><p className="hint">计划只提醒你回来，不会自动改变掌握状态。</p></div>{failed?<button className="secondary" onClick={()=>setReload(value=>value+1)}>重试复习日期</button>:<form onSubmit={async event=>{
    event.preventDefault();if(running.current||!today)return;running.current=true;setBusy(true);setMessage("");
    try{const plan=await api.createReviewTask(token,{mistake_id:id,title:"回顾错题与相关原文",due_date:due||today});setDue("");setMessage(`已安排在 ${plan.due_date}；如已有待办，保留原计划，可返回复习计划改期。`);}
    catch(error){onError(error);}finally{running.current=false;setBusy(false);}
  }}><label>复习日期<input aria-label="安排复习日期" type="date" value={due||today} disabled={busy||!today} required onChange={event=>setDue(event.target.value)}/></label><button className="secondary" disabled={busy||!today}><Icon name="clock" size={16}/>{busy?"正在安排…":"安排这道错题复习"}</button></form>}{message&&<p role="status">{message}</p>}</section>;
}

export function ReviewSchedule({token,onOpen,onError}:Common&{onOpen:(id:string)=>void}){
  const [data,setData]=useState<ReviewPlanPage|null>(null),[state,setState]=useState<"pending"|"all">("pending"),[offset,setOffset]=useState(0);
  const [loading,setLoading]=useState(true),[failed,setFailed]=useState(false),[reload,setReload]=useState(0),[busy,setBusy]=useState(false);
  const [dates,setDates]=useState<Record<string,string>>({}),[message,setMessage]=useState("");
  const running=useRef(false);
  const current=useRef(0);
  useEffect(()=>{
    let active=true;const id=++current.current;setLoading(true);setFailed(false);setData(null);
    void api.reviewSchedule(token,state,offset).then(result=>{if(active&&id===current.current){setData(result);if(offset&&offset>=result.total)setOffset(result.total?Math.floor((result.total-1)/20)*20:0);}}).catch(()=>{if(active&&id===current.current)setFailed(true);}).finally(()=>{if(active&&id===current.current)setLoading(false);});
    return()=>{active=false;};
  },[token,state,offset,reload]);
  const dirty=Object.keys(dates).length>0;
  usePlanGuard(busy,dirty);
  const act=async(plan:ReviewPlan,work:()=>Promise<unknown>,success:string)=>{
    if(running.current)return;running.current=true;setBusy(true);setMessage("");
    try{await work();setDates(values=>{const next={...values};delete next[plan.id];return next;});setMessage(success);setReload(value=>value+1);}
    catch(error){onError(error);}finally{running.current=false;setBusy(false);}
  };
  const changeView=(work:()=>void)=>{if(!busy&&(!dirty||window.confirm("复习日期尚未保存，放弃修改并切换列表？"))){setDates({});work();}};
  return <details className="panel review-schedule" open><summary><span><Icon name="clock"/>复习计划</span><span className="hint">日期由你安排 · 与每日答对目标独立</span></summary><div className="review-plan-intro"><p className="hint">在错题详情安排回顾；完成计划不会替你判定“已掌握”。{data&&`日期按账户时区 ${data.timezone}，今天 ${data.today}。`}</p><label>复习计划范围<select aria-label="复习计划范围" value={state} disabled={busy} onChange={event=>changeView(()=>{setState(event.target.value as "pending"|"all");setOffset(0);})}><option value="pending">待复习（含未来日期）</option><option value="all">全部计划</option></select></label></div>
    {message&&<p role="status" className="review-plan-message">{message}</p>}
    {loading?<p role="status">正在读取复习计划…</p>:failed?<div role="alert">复习计划暂时无法读取。<button className="secondary" onClick={()=>setReload(value=>value+1)}>重试复习计划</button></div>:data?.items.length?<div className="review-plan-list">{data.items.map(plan=><article className="review-plan-row" key={plan.id} aria-label={plan.title}><span className={`review-plan-date ${plan.status==="PENDING"&&plan.due_date<=data.today?"is-due":""}`}><Icon name="clock" size={15}/>{plan.due_date}</span><div className="review-plan-title"><strong>{plan.title}</strong><small>{plan.status==="COMPLETED"?"计划已完成":plan.due_date<data.today?"已逾期，仍可打开回顾":plan.due_date===data.today?"今天回顾":"等待计划日期"}</small></div><div className="review-plan-actions"><label className="sr-only" htmlFor={`plan-${plan.id}`}>调整复习日期</label><input id={`plan-${plan.id}`} aria-label={`调整复习日期：${plan.title}`} type="date" value={dates[plan.id]||plan.due_date} disabled={busy} onChange={event=>{const value=event.target.value;setDates(values=>{const next={...values};if(value===plan.due_date)delete next[plan.id];else next[plan.id]=value;return next;});}}/><button className="secondary" disabled={busy||!(dates[plan.id]||plan.due_date)||(plan.status==="PENDING"&&(!dates[plan.id]||dates[plan.id]===plan.due_date))} onClick={()=>void act(plan,()=>api.rescheduleReview(token,plan.id,dates[plan.id]||plan.due_date,plan.due_date),"复习日期已更新")}>{plan.status==="COMPLETED"?"重新安排":"保存改期"}</button>{plan.mistake_id&&<button className="secondary" disabled={busy} onClick={()=>onOpen(plan.mistake_id!)}>打开错题</button>}{plan.status==="PENDING"&&<button className="secondary" disabled={busy} onClick={()=>void act(plan,()=>api.completeReviewTask(token,plan.id),"本次复习计划已完成，错题掌握状态保持原判定")}>完成计划</button>}</div></article>)}</div>:<p className="hint">暂无{state==="pending"?"待复习":""}计划。打开一道错题，安排下次回顾日期。</p>}
    {data&&<nav className="catalogue-pages" aria-label="复习计划分页"><button className="secondary" disabled={busy||loading||offset===0} onClick={()=>changeView(()=>setOffset(Math.max(0,offset-20)))}>上一页计划</button><span>{Math.floor(offset/20)+1} / {Math.max(1,Math.ceil(data.total/20))} 页 · {data.total} 项</span><button className="secondary" disabled={busy||loading||offset+20>=data.total} onClick={()=>changeView(()=>setOffset(offset+20))}>下一页计划</button></nav>}
  </details>;
}
