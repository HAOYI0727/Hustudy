import {TopicSearch} from "./TopicSearch";
import {matchesTopic,topicPath} from "./TopicSearch";
import {useState} from "react";
import {api,BankTopicIndex,Topic} from "../../api/client";

export function BankTopicPicker({token,courseId,topics,ids,recommendation,busy,onCreated,onChange,onWorking}:{
  token:string;courseId:string;topics:Topic[];ids:string[];recommendation?:BankTopicIndex;busy:boolean;
  onCreated:(topic:Topic)=>void;onChange:(ids:string[])=>void;onWorking:(value:boolean)=>void;
}){
  const [creating,setCreating]=useState(false),[error,setError]=useState(""),[name,setName]=useState("");
  const [query,setQuery]=useState(""),[parent,setParent]=useState("");
  const inherited=new Set<string>();for(const id of ids){let t=topics.find(v=>v.id===id);const seen=new Set<string>();while(t?.parent_id&&!seen.has(t.id)){seen.add(t.id);inherited.add(t.parent_id);t=topics.find(v=>v.id===t!.parent_id);}}
  const ranked=recommendation?.existing||[];
  const order=new Map(ranked.map((r,i)=>[r.topic_id,i]));
  const sorted=topics.filter(t=>ids.includes(t.id)||order.has(t.id)||(query.trim()&&matchesTopic({...t,name:topicPath(t,topics)},query))).sort((a,b)=>(order.get(a.id)??999)-(order.get(b.id)??999)||a.name.localeCompare(b.name));
  const toggle=(id:string)=>{if(!ids.includes(id)&&ids.length>=5){setError("每题最多5个知识标签");return;}onChange(ids.includes(id)?ids.filter(v=>v!==id):[...ids,id]);setError("");};
  const create=async(value:string)=>{
    if(creating||busy)return;
    const clean=value.trim();if(!clean||clean.length>32){setError("新标签需为1–32字符");return;}
    if(ids.length>=5){setError("每题最多5个知识标签");return;}
    setError("");setCreating(true);onWorking(true);
    try{const existing=topics.find(t=>t.name.normalize("NFKC").toLowerCase()===clean.normalize("NFKC").toLowerCase()||t.aliases?.some(a=>a.normalize("NFKC").toLowerCase()===clean.normalize("NFKC").toLowerCase()));const topic=existing||await api.createTopic(token,courseId,clean,parent||null);onCreated(topic);onChange([...new Set([...ids,topic.id])]);setName("");}
    catch(e){setError(e instanceof Error?e.message:"标签创建失败，请重试");}
    finally{setCreating(false);onWorking(false);}
  };
  return <section className="bank-topic-index" aria-label="智能知识点索引">
    <strong>知识点归类</strong>{inherited.size>0&&<p className="hint" aria-label="自动归属父标签">自动归属：{topics.filter(t=>inherited.has(t.id)) .map(t=>t.name).join("、")}（选择子标签即生效，无需重复勾选）</p>}
    <p className="hint">蓝色为AI推荐的已有标签，默认勾选；可取消或调整，保存本题校正后生效。</p>
    {ranked.length>0&&<button type="button" className="secondary" disabled={busy||creating} onClick={()=>{const next=[...new Set([...ranked.map(r=>r.topic_id),...ids])];if(next.length>5){setError("合并推荐后超过5个标签，请先手动取消部分标签");return;}onChange(next);setError("");}}>选用AI推荐标签</button>}
    <label>搜索其他知识标签<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="按名称或别名查找"/></label><div className="tag-list bank-tag-choices">{sorted.slice(0,32).map(t=>{const match=ranked.find(r=>r.topic_id===t.id);return <label className={`bank-check bank-topic-option ${match?"bank-topic-match":""}`} key={t.id} title={match?.reason}><input type="checkbox" disabled={busy||creating} checked={ids.includes(t.id)} onChange={()=>toggle(t.id)}/><span>{t.name}{match&&<small>推荐 · {match.reason}</small>}</span></label>;})}</div>
    {sorted.length>32&&<p className="hint">请缩小搜索范围，当前最多显示32项。</p>}{!ranked.length&&<p className="hint">{recommendation?.version?.startsWith("bank-topic-ai-")&&recommendation.reason?recommendation.reason:"尚无AI推荐，可在上方题库审核区点击“AI归类”或手动选择标签。"}</p>}
    {Boolean(recommendation?.candidates?.length)&&<div className="bank-topic-candidates"><span>AI新标签备选（尚未创建）：</span>{recommendation!.candidates!.filter(n=>!topics.some(t=>t.name===n)).map(n=><button type="button" className="secondary" disabled={busy||creating} key={n} onClick={()=>void create(n)}>＋ {n}</button>)}</div>}
    <div className="bank-topic-create"><TopicSearch single topics={topics} ids={parent?[parent]:[]} onChange={ids=>setParent(ids[0]||"")} label="新标签的上级" disabled={busy||creating}/><label>自定义知识点<input value={name} maxLength={32} disabled={busy||creating} onChange={e=>setName(e.target.value)} placeholder="也可修改备选名称后创建"/></label><button type="button" className="secondary" disabled={busy||creating||!name.trim()} onClick={()=>void create(name)}>{creating?"创建中…":"创建并选中"}</button></div>
    {error&&<p role="alert" className="course-conflict">{error}</p>}
    <p className="hint">本题勾选调整需点击“保存本题校正”。修改题干/选项会清除旧建议，需重新AI归类。</p>
  </section>;
}
