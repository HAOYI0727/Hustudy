import {useCallback,useEffect,useRef,useState} from "react";
import {api,DailyRedo,MistakeItem} from "../../api/client";
import {PageTitle,EmptyInline,EmptyState,ModuleStats} from "../../components/workspace";
import {Icon} from "../../components/Icon";
import {TopicSearch} from "./TopicSearch";
import {BankMath} from "./BankMath";
import {MistakePractice} from "./MistakePractice";
import "./bank.css";
import "./review.css";

type Props={token:string;mistakeId?:string;onOpen:(id:string)=>void;onBack:()=>void;onError:(e:unknown)=>void};

function savedGoal(key:string){const value=localStorage.getItem(key);const n=Number(value);return value!==null&&Number.isInteger(n)&&n>=0&&n<=1000?n:3;}

export function Review({token,mistakeId,onOpen,onBack,onError}:Props){
 const goalKey=`hustudy-daily-redo-goal:${localStorage.getItem("hustudy_user")||"default"}`;
 const [goal,setGoal]=useState(()=>savedGoal(goalKey)),[goalDraft,setGoalDraft]=useState(()=>String(savedGoal(goalKey)));
 const [mistakes,setMistakes]=useState<MistakeItem[]>([]),[daily,setDaily]=useState<DailyRedo|null>(null);
 const [loaded,setLoaded]=useState(false),[failed,setFailed]=useState(false);
 const requestNumber=useRef(0);
 const [topicIds,setTopicIds]=useState<string[]>([]),[filter,setFilter]=useState("");
 const load=useCallback(async()=>{
  const request=++requestNumber.current;
  const [progress,items]=await Promise.all([api.dailyRedo(token,goal),api.mistakes(token)]);
  if(request!==requestNumber.current)return;
  setDaily(progress);setMistakes(items);setLoaded(true);setFailed(false);
 },[token,goal]);
 useEffect(()=>{void load().catch(e=>{setFailed(true);onError(e);});},[load,mistakeId]);
 useEffect(()=>{const timer=window.setInterval(()=>{void load().catch(onError);},60000);return()=>window.clearInterval(timer);},[load]);
 const topics=[...new Map(mistakes.flatMap(m=>m.topics||[]).map(t=>[t.id,t])).values()];
 const unmastered=mistakes.filter(m=>!m.mastered).length;
 const visible=mistakes.filter(m=>m.question.stem.toLowerCase().includes(filter.toLowerCase())&&(!topicIds.length||m.topics?.some(t=>topicIds.includes(t.id))));
 const nextId=daily?.remaining_ids.find(id=>id!==mistakeId)||mistakes.find(m=>m.id!==mistakeId)?.id;
 const next=()=>{if(nextId)onOpen(nextId);};
 const dailyPanel=daily&&<section className="panel daily-redo" aria-label="每日任务"><div><span className="review-eyebrow">每日任务 · {daily.date}</span><h3>{daily.goal===0?"每日错题目标已暂停":`每天答对 ${daily.goal} 道错题`}</h3><p>{daily.goal===0?"可以随时自行练习，或设置每日目标。":daily.target===0?"当前没有未掌握的错题，今日目标已完成。":`今日已答对 ${daily.completed} / ${daily.goal} 题；目标达成后仍可继续重做。${daily.target<daily.goal?`当前有效目标题量为 ${daily.target} 道，题量不足也可达标。`:""}`}</p><p className="hint">答错不计数；再次答错恢复待掌握，当日该题有效答对数撤回。</p><progress value={daily.completed} max={Math.max(1,daily.target)} aria-label="今日错题完成进度"/>{daily.done&&daily.goal>0&&<strong>今日目标已完成</strong>}</div>{!mistakeId&&<div className="review-daily-actions"><form onSubmit={e=>{e.preventDefault();const value=Number(goalDraft);if(goalDraft.trim()&&Number.isInteger(value)&&value>=0&&value<=1000){localStorage.setItem(goalKey,String(value));setGoal(value);}}}><label>每天练习几道<input aria-label="每日错题目标题数" type="number" min={0} max={1000} step={1} required value={goalDraft} onChange={e=>setGoalDraft(e.target.value)}/></label><button className="secondary" type="submit">保存目标</button></form><span className="hint">0表示暂停；按账号保存在当前浏览器。</span><button className="primary" disabled={!nextId||daily.goal!==goal} onClick={next}>{daily.goal===0?"自由重做错题":daily.done?"继续重做错题":"开始今日重做"}</button></div>}</section>;

 if(mistakeId){
  const item=mistakes.find(m=>m.id===mistakeId);
  return <div className="page review-page review-practice-page"><button className="secondary review-back" onClick={onBack}>← 返回错题库</button><PageTitle eyebrow="MISTAKE PRACTICE" title="错题重做" text="专心完成当前题目；答对后可以移出错题库，也可以保留复习。"/>{dailyPanel}{!loaded||failed?<section className="panel"><p role="status">{failed?"错题暂时读取失败，请重试。":"正在读取错题…"}</p>{failed&&<button className="secondary" onClick={()=>void load().catch(onError)}>重新读取</button>}</section>:item?<section className="panel review-practice-body"><div className="tag-list">{item.topics.map(t=><span className="review-tag" key={t.id}>{t.name}</span>)}<span className={`review-mastery ${item.mastered?"mastered":""}`}>{item.mastered?"已掌握 · 保留复习":"待掌握"}</span></div><MistakePractice key={mistakeId} token={token} id={mistakeId} autoStart mastered={item.mastered} credited={!!daily?.completed_ids.includes(mistakeId)} onDone={load} onRemoved={onBack} onError={onError}/>{nextId&&<button className="secondary" onClick={next}>下一道错题 →</button>}</section>:<EmptyState icon="review" title="此题已移出或不可访问" text="返回错题库选择其他题目。" action="返回错题库" onAction={onBack}/>}</div>;
 }
 return <div className="page review-page">{dailyPanel}<PageTitle eyebrow="REVIEW LOOP" title="错题库" text="未掌握的题目优先显示；已经掌握的题目可继续保留复习。"/><ModuleStats items={[{label:"待掌握错题",value:unmastered,hint:"不包含当前已掌握的题目"},{label:"已掌握保留",value:mistakes.length-unmastered,hint:"可继续练习，不计入每日目标"},{label:"今日答对",value:daily?`${daily.completed} / ${daily.goal}`:"—",hint:"只计当前已掌握的不同错题"}]}/><section className="panel review-library" aria-label="错题库"><div className="panel-title"><h3><Icon name="review"/>我的错题</h3><span className="hint">待掌握 {unmastered} 道 · 已掌握保留 {mistakes.length-unmastered} 道</span></div><div className="review-filters"><label>搜索题目<input aria-label="搜索错题" placeholder="输入题干关键词…" value={filter} onChange={e=>setFilter(e.target.value)}/></label><TopicSearch topics={topics} ids={topicIds} onChange={setTopicIds} label="按知识标签查找错题"/></div>{!loaded&&!failed&&<p role="status">正在读取错题…</p>}{failed&&<button className="secondary" onClick={()=>void load().catch(onError)}>重新读取错题</button>}<div className="review-question-list">{visible.map(m=><article className={`mistake-card ${m.mastered?"is-mastered":""}`} key={m.id}><div className="review-question-body"><div className="review-question-heading"><span className={`review-mastery ${m.mastered?"mastered":""}`}>{m.mastered?"已掌握 · 保留复习":"待掌握"}</span><div className="tag-list">{m.topics.length?m.topics.map(t=><button className="secondary bank-topic-match" key={t.id} onClick={()=>setTopicIds([t.id])}>{t.name}</button>):<span className="hint">未归类</span>}</div></div><BankMath token={token} text={m.question.stem}/><div className="review-question-footer"><span className="hint">{m.mastered?"重复练习不计入每日答对数":"答对后可计入今日任务"}</span><button className={m.mastered?"secondary":"primary"} onClick={()=>onOpen(m.id)}>{m.mastered?"再次练习":"重做错题"}</button></div></div></article>)}</div>{loaded&&!visible.length&&(mistakes.length?<EmptyInline text="没有符合筛选条件的错题"/>:<EmptyState icon="review" title="还没有错题" text="完成练习后，错题会显示在这里。"/>)}</section></div>;
}
