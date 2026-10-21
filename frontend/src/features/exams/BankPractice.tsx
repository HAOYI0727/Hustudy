import {QuestionContext} from "./QuestionContext";
import {ReferenceAnswer} from "./ReferenceAnswer";
import {practiceQuestionGroups} from "./questionGroups";
import {TopicSearch} from "./TopicSearch";
import {BankMath} from "./BankMath";
import {useEffect, useRef, useState} from "react";
import "./bank.css";
import {BankFigure} from "./BankImages";
import {api, Attempt, ExamPaper, Question, Topic} from "../../api/client";

export type BankProps = {token:string;courseId:string;onNotice:(s:string)=>void;onError:(e:unknown)=>void};
const labels:Record<string,string>={single_choice:"选择题",fill_blank:"历史填空题",solution:"解答题",short_answer:"历史简答题",true_false:"历史判断题"};
const gradeLabels:Record<string,string>={correct:"正确",incorrect:"错误",unanswered:"未作答",pending_self_review:"待自行批改",submitted:"已提交（不批改）",self_correct:"自评正确",self_incorrect:"自评错误"};

export function BankPractice({token,courseId,onNotice,onError}:BankProps){
  const [topics,setTopics]=useState<Topic[]>([]),[selected,setSelected]=useState<string[]>([]);
  const [count,setCount]=useState(5),[kind,setKind]=useState(""),[duration,setDuration]=useState(30);
  const [paper,setPaper]=useState<ExamPaper|null>(null),[attempt,setAttempt]=useState<Attempt|null>(null);
  const [history,setHistory]=useState<Array<{id:string;title:string;status:string;attempts?:Array<{id:string;status:string}>}>>([]);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[dirty,setDirty]=useState<string[]>([]);
  const [tick,setTick]=useState(Date.now());
  const request=useRef<string|null>(null);
  const storageKey=`hustudy-bank-attempt:${courseId}`;
  const stateKey=`hustudy-bank-paper:${courseId}`;
  const handle=(e:unknown)=>{setError(e instanceof Error?e.message:"操作失败");onError(e);};
  const load=async()=>{setTopics(await api.topics(token,courseId));setHistory(await api.examHistory(token,courseId));};
  useEffect(()=>{let alive=true;void (async()=>{try{
    await load();const previous=localStorage.getItem(storageKey),previousPaper=localStorage.getItem(stateKey);
    if(previous){const a=await api.restoreAttempt(token,previous);const p=await api.examPaper(token,a.paper_id);if(!alive)return;setAttempt(a);setPaper(a.status==="IN_PROGRESS"?{...p,questions:a.questions||p.questions}:await api.attemptResult(token,a.id));}
    else if(previousPaper){const p=await api.examPaper(token,previousPaper);if(alive)setPaper(p);}
  }catch(e){if(alive)handle(e);}})();return()=>{alive=false;};},[token,courseId]);
  useEffect(()=>{const timer=window.setInterval(()=>setTick(Date.now()),1000);return()=>window.clearInterval(timer);},[]);
  useEffect(()=>{const guard=(event:Event)=>{if(busy||(dirty.length>0&&!window.confirm("有尚未保存的答案，放弃并离开？")))event.preventDefault();};const unload=(event:BeforeUnloadEvent)=>{if(busy||dirty.length){event.preventDefault();event.returnValue="";}};window.addEventListener("hustudy:before-navigate",guard);window.addEventListener("beforeunload",unload);return()=>{window.removeEventListener("hustudy:before-navigate",guard);window.removeEventListener("beforeunload",unload);};},[dirty,busy]);
  const act=async(work:()=>Promise<void>)=>{if(busy)return;setBusy(true);setError("");try{await work();}catch(e){handle(e);}finally{setBusy(false);}};
  const hasActive=attempt?.status==="IN_PROGRESS";
  const remaining=attempt?.deadline_at?Math.max(0,Math.ceil((new Date(attempt.deadline_at).getTime()-tick)/1000)):null;
  const changeSettings=()=>{request.current=null;};
  const save=async(qid:string,value:unknown)=>{const saved=await api.answer(token,attempt!.id,qid,value);setAttempt(current=>({...current!,...saved,deadline_at:current?.deadline_at}));setDirty(items=>items.filter(id=>id!==qid));onNotice("答案已保存到服务器");};
  return <section className="bank-practice"><h3>按知识标签随机抽题</h3><p className="hint">只使用用户已上传并确认的题目，不调用 AI。选择题四选项随机排列；同一套练习刷新后顺序保持。</p>
    <fieldset disabled={busy||hasActive} className="panel bank-controls"><legend>抽题设置</legend><TopicSearch topics={topics} ids={selected} disabled={busy||hasActive} onChange={ids=>{changeSettings();setSelected(ids);}}/><p className="hint">{selected.length?`已选${selected.length}个标签，从匹配任一标签的题目中随机抽取。`:"未选标签：从当前课程全部已确认题目中随机抽取。"}</p>{!topics.length&&<p>尚无知识标签，可不选标签，从当前课程已确认题目中抽取。</p>}<div className="bank-fields"><label>题型<select value={kind} onChange={e=>{changeSettings();setKind(e.target.value);}}><option value="">混合题型</option>{["single_choice","solution"].map(k=><option key={k} value={k}>{labels[k]}</option>)}</select></label><label>题数<input type="number" min={1} max={100} value={count} onChange={e=>{changeSettings();setCount(Number(e.target.value));}}/></label><label>时长（分钟）<input type="number" min={1} max={180} value={duration} onChange={e=>{changeSettings();setDuration(Number(e.target.value));}}/></label></div><button className="primary" disabled={!Number.isInteger(count)||count<1||count>100} onClick={()=>void act(async()=>{request.current||=crypto.randomUUID();const p=await api.bankDraw(token,courseId,{request_id:request.current,topic_ids:selected,count,question_type:kind||undefined,duration_minutes:duration});setPaper(p);setAttempt(null);setDirty([]);localStorage.removeItem(storageKey);localStorage.setItem(stateKey,p.id);request.current=null;await load();onNotice("题库草稿已抽取，请核对题干后确认");})}>随机抽取题库练习</button></fieldset>
    {error&&<p role="alert" className="course-conflict">{error}</p>}
    {paper&&<section className="panel"><h3>{paper.title} · {paper.status}</h3>{paper.status==="DRAFT"&&<button className="secondary" disabled={busy} onClick={()=>void act(async()=>{setPaper(await api.reviewPaper(token,paper.id));onNotice("已审阅并冻结为 READY");})}>已核对题干，确认练习</button>}{paper.status==="READY"&&!attempt&&<button className="primary" disabled={busy} onClick={()=>void act(async()=>{const started=await api.startAttempt(token,paper.id);const restored=await api.restoreAttempt(token,started.id);setAttempt(restored);setPaper({...paper,questions:restored.questions||paper.questions});localStorage.setItem(storageKey,started.id);})}>开始作答</button>}
      {hasActive&&<p role="status">剩余 {remaining===null?"以服务器为准":`${Math.floor(remaining/60)}分${remaining%60}秒`} · 保存成功后可刷新恢复；未保存答案不会提交。</p>}
      {practiceQuestionGroups(paper.questions).map(group=><section className="bank-question-group" key={group.key}>{group.items.length>1&&<header className="bank-group-heading"><h3>{group.label}</h3><span>{group.items.length} 小题 · 分别作答与判分</span></header>}{group.items.map(q=><article key={`${attempt?.id||paper.id}:${q.id}`} className="question-card"><strong>{paper.questions.findIndex(item=>item.id===q.id)+1}. {labels[q.type]||q.type} · {q.points}分</strong><QuestionContext question={q} token={token} courseId={courseId}/><BankMath text={q.stem} token={token}/>{q.illustrations?.map((image,n)=><BankFigure key={n} token={token} courseId={courseId} image={image}/>)}{q.type==="single_choice"&&<div className="options">{q.options?.map((option,n)=><button key={n} type="button" disabled={!hasActive||busy||remaining===0} className={`option ${attempt?.answers[q.id]==="ABCD"[n]?"selected-option":""}`} onClick={()=>void act(()=>save(q.id,"ABCD"[n]))}><span>{"ABCD"[n]}.</span><BankMath text={option} token={token}/></button>)}</div>}{hasActive&&["fill_blank","solution","short_answer"].includes(q.type)&&<TextAnswers q={q} saved={attempt!.answers[q.id]} disabled={busy||remaining===0} onDirty={value=>setDirty(ids=>value?Array.from(new Set([...ids,q.id])):ids.filter(id=>id!==q.id))} onSave={value=>void act(()=>save(q.id,value))}/>}
        {q.type==="fill_blank"&&<small>{q.unique_answer?"唯一答案：标准答案完整时自动批改；未提供答案则交卷后自评":"非唯一答案：交卷后自行判断正误"}</small>}
        {attempt?.grading?.[q.id]&&<p role="status">{gradeLabels[attempt.grading[q.id].status]||attempt.grading[q.id].status}</p>}
        {attempt&&attempt.status!=="IN_PROGRESS"&&<div className="bank-feedback">{["solution","short_answer"].includes(q.type)&&<p>解答题不自动判对错，可自行判断正误。</p>}<ReferenceAnswer token={token} question={q}/><p>你的答案：{Array.isArray(attempt.answers[q.id])?(attempt.answers[q.id] as string[]).join("；"):String(attempt.answers[q.id]??"未提交")}</p>{attempt.grading[q.id]&&!attempt.grading[q.id].automatic&&<div className="bank-self-review"><p className="hint">系统未自动判分，请结合参考答案或自己的核对判断。</p><button className="secondary" disabled={busy||typeof attempt.grading[q.id].self_correct==="boolean"} onClick={()=>void act(async()=>{setAttempt(await api.selfGrade(token,attempt.id,q.id,true));})}>我答对了</button><button className="secondary" disabled={busy||typeof attempt.grading[q.id].self_correct==="boolean"} onClick={()=>void act(async()=>{setAttempt(await api.selfGrade(token,attempt.id,q.id,false));})}>我答错了</button></div>}</div>}
      </article>)}</section>)}
      {hasActive&&<><p className="hint">{dirty.length?`${dirty.length}题尚未保存，请逐题保存后交卷。`:"当前输入已保存，可交卷。"}</p><button className="primary" disabled={busy||dirty.length>0} onClick={()=>void act(async()=>{const a=await api.submit(token,attempt!.id);setAttempt(a);setPaper(await api.attemptResult(token,a.id));await load();onNotice("已交卷，解答题不自动评分；未自动判分的题目可自行判断正误");})}>交卷并查看答案</button></>}
      {attempt&&attempt.status!=="IN_PROGRESS"&&(Object.values(attempt.grading||{}).some(g=>g.automatic)?<p>自动批改得分：{attempt.score??0} / {Object.values(attempt.grading||{}).reduce((s,g)=>s+(g.max_score||0),0)}（仅有完整标准答案的自动判分题；自评另列）</p>:<p className="hint">本次没有自动判分题，请使用逐题自评。</p>)}
    </section>}
    <details><summary>已保存练习（最近100套）</summary>{history.map(h=><div key={h.id}><button className="relation-link" key={h.id} disabled={busy||hasActive||dirty.length>0} onClick={()=>void act(async()=>{setPaper(await api.examPaper(token,h.id));setAttempt(null);localStorage.removeItem(storageKey);localStorage.setItem(stateKey,h.id);})}>{h.title} · {h.status}</button>{h.attempts?.map(a=><button key={a.id} className="link-button" disabled={busy||hasActive||dirty.length>0} onClick={()=>void act(async()=>{const restored=await api.restoreAttempt(token,a.id);const p=await api.examPaper(token,restored.paper_id);setAttempt(restored);setPaper(restored.status==="IN_PROGRESS"?{...p,questions:restored.questions||p.questions}:await api.attemptResult(token,a.id));localStorage.setItem(storageKey,a.id);})}>查看作答 · {a.status}</button>)}</div>)}</details>
  </section>;
}

function TextAnswers({q,saved,disabled,onDirty,onSave}:{q:Question;saved:unknown;disabled:boolean;onDirty:(dirty:boolean)=>void;onSave:(v:unknown)=>void}){
  const initial=Array.isArray(saved)?saved.map(String):[String(saved??"")];
  const size=q.type==="fill_blank"?q.blank_count||1:1;
  const [values,setValues]=useState(Array.from({length:size},(_,i)=>initial[i]||""));
  const changed=JSON.stringify(values)!==JSON.stringify(Array.from({length:size},(_,i)=>initial[i]||""));
  return <div>{values.map((value,i)=><label key={i}>{q.type==="fill_blank"?`第${i+1}空`:"解答内容"}<textarea aria-label={q.type==="fill_blank"?`第${i+1}空答案`:"解答内容"} rows={q.type==="fill_blank"?2:5} value={value} disabled={disabled} onChange={e=>{const next=values.map((v,n)=>n===i?e.target.value:v);setValues(next);onDirty(JSON.stringify(next)!==JSON.stringify(Array.from({length:size},(_,n)=>initial[n]||"")));}}/></label>)}<button className="secondary" disabled={disabled||!changed} onClick={()=>onSave(q.type==="fill_blank"?values:values[0])}>保存本题答案</button><small>{changed?"尚未保存":"与服务器保存内容一致"}</small></div>;
}
