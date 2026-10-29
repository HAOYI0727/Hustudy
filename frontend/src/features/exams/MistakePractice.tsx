import {QuestionContext} from "./QuestionContext";
import {ReferenceAnswer} from "./ReferenceAnswer";
import {useEffect,useRef,useState} from "react";
import {api,Redo,Question} from "../../api/client";
import {BankMath} from "./BankMath";
export function MistakePractice({token,id,autoStart=false,mastered=false,credited=false,onDone,onRemoved,onError,onNext,nextAvailable=false}:{token:string;id:string;autoStart?:boolean;mastered?:boolean;credited?:boolean;onDone:()=>Promise<void>;onRemoved?:()=>void;onError:(e:unknown)=>void;onNext?:()=>void;nextAvailable?:boolean}){
 const [record,setRecord]=useState<Redo|null>(null),[answer,setAnswer]=useState<unknown>(""),[busy,setBusy]=useState(false),[keep,setKeep]=useState(false);const opened=useRef(false);
 const key=`hustudy-redo:${id}`;
 const draftKey=`${key}:draft`;
 const [removed,setRemoved]=useState(false);
 useEffect(()=>{if(removed&&!busy)onRemoved?.();},[removed,busy]);
 const run=async(work:()=>Promise<void>)=>{if(busy)return;setBusy(true);try{await work();}catch(e){onError(e);}finally{setBusy(false);}};
 const start=(fresh=false)=>run(async()=>{const request=fresh?crypto.randomUUID():localStorage.getItem(key)||crypto.randomUUID();localStorage.setItem(key,request);let value=await api.startRedo(token,id,request);if(!fresh&&!mastered&&value.status==="COMPLETED"&&value.correct){const next=crypto.randomUUID();localStorage.setItem(key,next);value=await api.startRedo(token,id,next);}setRecord(value);let draft:unknown=null;try{const stored=JSON.parse(sessionStorage.getItem(draftKey)||"null");if(stored?.id===value.id)draft=stored.answer;}catch{}setAnswer(draft??value.answer??(value.question.type==="fill_blank"?Array.from({length:value.question.blank_count||1},()=>""):""));setKeep(false);});
 useEffect(()=>{if(record?.status==="IN_PROGRESS")sessionStorage.setItem(draftKey,JSON.stringify({id:record.id,answer}));else if(record)sessionStorage.removeItem(draftKey);},[record,answer]);
 useEffect(()=>{if(!autoStart){opened.current=false;return;}if(!opened.current){opened.current=true;void start(record?.status==="COMPLETED");}},[autoStart]);
 useEffect(()=>{const guard=(e:Event)=>{if(busy)e.preventDefault();};window.addEventListener("hustudy:before-navigate",guard);return()=>window.removeEventListener("hustudy:before-navigate",guard);},[busy,record]);
 if(!record)return <button className="primary" disabled={busy} onClick={()=>void start()}>重做错题</button>;
 const q=record.question,active=record.status==="IN_PROGRESS";
 return <section className="mistake-redo" aria-label="错题重做"><h4>重新作答</h4><QuestionContext question={q} token={token}/>
 {active?<><RedoAnswer token={token} q={q} value={answer} disabled={busy} onChange={setAnswer}/><button className="primary" disabled={busy} onClick={()=>void run(async()=>{const saved=await api.submitRedo(token,id,record.id,answer);setRecord(saved);if(saved.status==="COMPLETED")await onDone();})}>提交重做答案</button></>:<><p>本次答案：</p><BankMath text={Array.isArray(record.answer)?record.answer.join("；"):String(record.answer??"")} token={token}/><ReferenceAnswer question={q} token={token}/></>}
 {record.status==="NEEDS_SELF_REVIEW"&&<div><p>本题不自动判分，请核对参考答案后自行判断。只有首次答对才计入每日任务。</p><button className="secondary" disabled={busy} onClick={()=>void run(async()=>{setRecord(await api.judgeRedo(token,id,record.id,true));await onDone();})}>重做答对了</button><button className="secondary" disabled={busy} onClick={()=>void run(async()=>{setRecord(await api.judgeRedo(token,id,record.id,false));await onDone();})}>重做答错了</button></div>}
 {record.status==="COMPLETED"&&<p role="status">{record.correct?`本次重做正确。${credited?"此题已计入今日答对数，不会重复计数。":"此题已掌握，重复练习不计入今日答对数。"}`:"本次重做错误，不计入今日答对数。可再次练习。"}</p>}
 {keep&&<p className="hint">已保留，可在以后继续复习。</p>}
 <div className="review-result-actions" role="group" aria-label="错题后续操作">
 <button className="primary" disabled={busy||record.status!=="COMPLETED"||!record.correct||keep} onClick={()=>void run(async()=>{await api.removeMistake(token,id);localStorage.removeItem(key);sessionStorage.removeItem(draftKey);setRemoved(true);})}>移出错题库</button>
 <button className="secondary" disabled={busy||record.status!=="COMPLETED"||!record.correct||keep} onClick={()=>setKeep(true)}>继续保留</button>
 <button className="secondary" disabled={busy||record.status!=="COMPLETED"} onClick={()=>void start(true)}>再做一次</button>
 {onNext&&<button className="secondary review-next-action" disabled={busy||!nextAvailable} onClick={onNext}>下一道错题 →</button>}
 </div>
 </section>;
}
function RedoAnswer({token,q,value,disabled,onChange}:{token:string;q:Question;value:unknown;disabled:boolean;onChange:(v:unknown)=>void}){
 if(q.type==="single_choice")return <div className="options">{q.options?.map((text,i)=><button className={`option ${value==="ABCD"[i]?"selected-option":""}`} disabled={disabled} key={i} onClick={()=>onChange("ABCD"[i])}><span>{"ABCD"[i]}.</span><BankMath text={text} token={token}/></button>)}</div>;
 if(q.type==="true_false")return <div><button className="secondary" disabled={disabled} onClick={()=>onChange(true)}>正确</button><button className="secondary" disabled={disabled} onClick={()=>onChange(false)}>错误</button></div>;
 if(q.type==="fill_blank"){const list=Array.isArray(value)?value:Array.from({length:q.blank_count||1},()=>"");return <div>{list.map((v,i)=><label key={i}>重做第{i+1}空<textarea aria-label={`重做第${i+1}空`} value={String(v)} disabled={disabled} onChange={e=>onChange(list.map((v,n)=>n===i?e.target.value:v))}/></label>)}</div>;}
 return <label>重做解答<textarea aria-label="重做解答" rows={5} value={String(value??"")} disabled={disabled} onChange={e=>onChange(e.target.value)}/></label>;
}
