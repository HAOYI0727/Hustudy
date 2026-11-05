import {useEffect,useRef,useState} from "react";
import {api,ExamPaper,Topic} from "../../api/client";
import {BankMath} from "./BankMath";
import {TopicSearch} from "./TopicSearch";

type Candidate={id:string;stem:string;number:string;points:number|null};
export function ManualPractice({token,courseId,topics,disabled,onCreated,onError}:{
  token:string;courseId:string;topics:Topic[];disabled:boolean;
  onCreated:(paper:ExamPaper)=>Promise<void>;onError:(error:unknown)=>void;
}){
  const [query,setQuery]=useState(""),[topic,setTopic]=useState<string[]>([]);
  const [items,setItems]=useState<Candidate[]>([]),[total,setTotal]=useState(0),[offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<Candidate[]>([]),[busy,setBusy]=useState(false);
  const [duration,setDuration]=useState(30),[title,setTitle]=useState("自行选题练习");
  const [scope,setScope]=useState<{query:string;topic:string}|null>(null);
  const epoch=useRef(0),request=useRef<string|null>(null);
  useEffect(()=>{
    if(!scope)return;
    let live=true;
    setBusy(true);
    const params=new URLSearchParams({query:scope.query,offset:String(offset)});
    if(scope.topic)params.set("topic_id",scope.topic);
    void api.manualCandidates(token,courseId,params).then(result=>{
      if(live){setItems(result.items);setTotal(result.total);}
    }).catch(error=>{if(live){setItems([]);setTotal(0);onError(error);}}).finally(()=>{if(live)setBusy(false);});
    return()=>{live=false;};
  },[token,courseId,scope,offset]);
  useEffect(()=>()=>{epoch.current++;},[token,courseId]);
  const changed=()=>{request.current=null;};
  return <fieldset className="panel bank-controls" disabled={disabled||busy}>
    <legend>自行选题组卷</legend>
    <form onSubmit={e=>{e.preventDefault();setOffset(0);setItems([]);setScope({query,topic:topic[0]||""});}}>
      <label>搜索题干<input maxLength={500} value={query} onChange={e=>setQuery(e.target.value)} /></label>
      <TopicSearch single topics={topics} ids={topic} onChange={setTopic} label="按知识点筛选" />
      <button className="secondary">搜索可练习题目</button>
    </form>
    {scope&&<p>符合条件 {total} 题 · 已选 {selected.length} / 100 题</p>}
    {items.map(q=><article key={q.id} className="panel">
      <label><input type="checkbox" checked={selected.some(s=>s.id===q.id)} disabled={selected.length>=100&&!selected.some(s=>s.id===q.id)} onChange={e=>{
        changed();setSelected(current=>e.target.checked?[...current,q]:current.filter(s=>s.id!==q.id));
      }}/>题号 {q.number} · {q.points===null?"分值未知":q.points+"分"}</label>
      <BankMath text={q.stem} token={token}/>
    </article>)}
    {scope&&<div className="bank-actions"><button className="secondary" disabled={!offset} onClick={()=>setOffset(offset-20)}>上一页</button><span>第 {Math.floor(offset/20)+1} 页</span><button className="secondary" disabled={offset+20>=total} onClick={()=>setOffset(offset+20)}>下一页</button></div>}
    <details open><summary>已选题目（按勾选顺序组卷）</summary>{selected.map(q=><div key={q.id}><span>{q.number} · {q.stem.slice(0,60)}</span><button className="secondary" onClick={()=>{changed();setSelected(current=>current.filter(s=>s.id!==q.id));}}>移除</button></div>)}</details>
    <label>练习名称<input maxLength={240} required value={title} onChange={e=>{changed();setTitle(e.target.value);}}/></label>
    <label>时长（分钟）<input type="number" min={1} max={180} value={duration} onChange={e=>{changed();setDuration(Number(e.target.value));}}/></label>
    <button className="primary" disabled={!selected.length||!title.trim()||!Number.isInteger(duration)||duration<1||duration>180} onClick={async()=>{
      const current=epoch.current;
      request.current||=crypto.randomUUID();setBusy(true);
      try{
        const paper=await api.manualPractice(token,courseId,{request_id:request.current,question_ids:selected.map(q=>q.id),title:title.trim(),duration_minutes:duration});
        if(current!==epoch.current)return;
        request.current=null;await onCreated(paper);
      }catch(error){if(current===epoch.current)onError(error);}
      finally{if(current===epoch.current)setBusy(false);}
    }}>生成练习（{selected.length}题）</button>
  </fieldset>;
}
