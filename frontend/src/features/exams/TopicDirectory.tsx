import {directTopicQuestions,subtreeQuestionCount} from "./topicQuestionView";
import {useEffect,useMemo,useRef,useState,type ReactNode} from "react";
import {api,Topic,PastQuestion,QuestionDirectoryItem} from "../../api/client";
import {topicDescendants,topicPath,matchesTopic} from "./TopicSearch";
import {BankMath} from "./BankMath";
import {BankFigure} from "./BankImages";

type Props={token:string;courseId:string;topics:Topic[];questions:QuestionDirectoryItem[];busy:boolean;move:(topic:Topic,parent:string|null)=>Promise<boolean>;renderEditor:(topic:Topic)=>ReactNode;onOpen:(id:string)=>void;creation:ReactNode};
export function TopicDirectory({token,courseId,topics,questions,busy,move,renderEditor,onOpen,creation}:Props){
 const [expanded,setExpanded]=useState<string[]>([]),[selected,setSelected]=useState<string|null>(null),[query,setQuery]=useState(""),[over,setOver]=useState<string|null>(null),[dragging,setDragging]=useState(false);
 const [questionOffset,setQuestionOffset]=useState(0);
 useEffect(()=>setQuestionOffset(0),[selected]);
 const dragged=useRef<Topic|null>(null);
 const pointerDrag=useRef<{topic:Topic;x:number;y:number;id:number;armed:boolean}|null>(null),suppressClick=useRef(false);
 const [ghost,setGhost]=useState<{name:string;x:number;y:number}|null>(null);
 const known=new Set(topics.map(t=>t.id));
 const ids=(q:QuestionDirectoryItem)=>(q.bank_data.topic_ids||[q.topic_id]).filter((id):id is string=>Boolean(id)&&known.has(id!));
 const unclassified=questions.filter(q=>!ids(q).length);
 const target=topics.find(t=>t.id===selected);
 const children=(parent:string|null)=>topics.filter(t=>(t.parent_id||null)===parent).sort((a,b)=>a.name.localeCompare(b.name,'zh-CN'));
 const canDrop=(parent:string|null)=>{const source=dragged.current;if(busy||!source||(source.parent_id||null)===parent||(parent&&!known.has(parent)))return false;
  const links=new Map(topics.map(t=>[t.id,t.parent_id||null]));links.set(source.id,parent);
  for(const t of topics){let at:string|null=t.id;const seen=new Set<string>();while(at){if(seen.has(at)||seen.size>=6||!links.has(at))return false;seen.add(at);at=links.get(at)||null;}}return true;};
 const end=()=>{dragged.current=null;pointerDrag.current=null;setDragging(false);setOver(null);setGhost(null);};

 const counts=useMemo(()=>new Map(topics.map(t=>[t.id,subtreeQuestionCount(topics,questions,t.id)])),[topics,questions]);
 const count=(id:string)=>counts.get(id)||0;
 const mayLeave=()=>window.dispatchEvent(new Event("hustudy:before-navigate",{cancelable:true}));
 const choose=(t:Topic)=>{if(selected!==t.id&&!mayLeave())return;setSelected(t.id);setExpanded(v=>v.includes(t.id)?v:[...v,t.id]);};
 useEffect(()=>{
  const destination=(x:number,y:number)=>{const el=document.elementFromPoint(x,y)?.closest<HTMLElement>("[data-topic-id],[data-topic-root]");return el?{parent:el.dataset.topicId||null}:null;};
  const moving=(e:PointerEvent)=>{const start=pointerDrag.current;if(!start||start.id!==e.pointerId)return;
   if(!start.armed){if(Math.hypot(e.clientX-start.x,e.clientY-start.y)<6)return;if(busy||!mayLeave()){end();return;}start.armed=true;dragged.current={...start.topic};setDragging(true);}
   e.preventDefault();setGhost({name:start.topic.name,x:e.clientX,y:e.clientY});const dest=destination(e.clientX,e.clientY);setOver(dest&&canDrop(dest.parent)?dest.parent||"root":null);
  };
  const finish=(e:PointerEvent)=>{const start=pointerDrag.current;if(!start||start.id!==e.pointerId)return;if(!start.armed){pointerDrag.current=null;return;}e.preventDefault();suppressClick.current=true;window.setTimeout(()=>{suppressClick.current=false;},0);const source=dragged.current,dest=destination(e.clientX,e.clientY),allowed=dest&&canDrop(dest.parent);end();if(source&&dest&&allowed)void move(source,dest.parent).then(ok=>{if(ok&&dest.parent)setExpanded(v=>Array.from(new Set([...v,dest.parent!])));});};
  const cancel=()=>end();const key=(e:KeyboardEvent)=>{if(e.key==="Escape")end();};window.addEventListener("keydown",key);window.addEventListener("pointermove",moving,{passive:false});window.addEventListener("pointerup",finish);window.addEventListener("pointercancel",cancel);window.addEventListener("blur",cancel);
  return()=>{window.removeEventListener("keydown",key);window.removeEventListener("pointermove",moving);window.removeEventListener("pointerup",finish);window.removeEventListener("pointercancel",cancel);window.removeEventListener("blur",cancel);};
 });
 const branch=(parent:string|null,depth=0):ReactNode=>children(parent).map(t=>{
  const descendants=topicDescendants(topics,[t.id]);
  const visible=!query.trim()||topics.some(v=>descendants.has(v.id)&&matchesTopic({...v,name:topicPath(v,topics)},query));
  if(!visible)return null;
  const open=query.trim()?true:expanded.includes(t.id),hasChildren=children(t.id).length>0;
  return <li key={t.id}><div className={`bank-topic-tree-row ${over===t.id?"drop-target":""} ${dragged.current?.id===t.id?"is-dragging":""}`} data-topic-id={t.id} draggable={false} onPointerDown={e=>{if(busy||e.button!==0||(e.target as HTMLElement).closest(".bank-topic-toggle"))return;pointerDrag.current={topic:{...t},x:e.clientX,y:e.clientY,id:e.pointerId,armed:false};}} onClickCapture={e=>{if(suppressClick.current){e.preventDefault();e.stopPropagation();}}}>{hasChildren?<button type="button" className="bank-topic-toggle" disabled={busy} aria-label={`${open?"折叠":"展开"}标签 ${t.name}`} aria-expanded={open} onClick={()=>setExpanded(v=>open?v.filter(id=>id!==t.id):[...v,t.id])}>{open?"▾":"▸"}</button>:<span className="bank-topic-toggle"/>}<button type="button" className={`bank-topic-folder ${selected===t.id?"active":""}`} aria-pressed={selected===t.id} aria-label={`${t.name} · ${count(t.id)}题`} disabled={busy} title={`拖动“${t.name}”到其他标签或根级`} onClick={()=>choose(t)}><span>▱ {t.name}</span><small>{count(t.id)}</small></button></div>{hasChildren&&open&&depth<5&&<ul>{branch(t.id,depth+1)}</ul>}</li>;
 });
 const direct=useMemo(()=>selected==="unclassified"?questions.filter(q=>!ids(q).length):target?directTopicQuestions(topics,questions,target.id):[],[selected,topics,questions]);
 useEffect(()=>{if(questionOffset&&questionOffset>=direct.length)setQuestionOffset(0);},[questionOffset,direct.length]);
 return <section className="panel bank-topic-directory" aria-label="考点目录">{ghost&&<div className="bank-topic-drag-preview" style={{left:ghost.x+12,top:ghost.y+12}} aria-hidden="true">▱ {ghost.name}</div>}<div className="bank-section-heading"><div><h3>考点目录</h3><p className="hint">展开标签逐级查看，最内层是题目。整行拖到目标标签可归类，拖到“移到根级”可取消父级；也可在管理中搜索上级。</p></div>{creation}</div><div className="bank-topic-workspace"><aside className="bank-topic-sidebar"><label>搜索考点<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="名称、别名或路径"/></label><button className={`bank-topic-folder bank-topic-root-drop ${selected==="unclassified"?"active":""} ${dragging?"is-root-target":""} ${over==="root"?"drop-target":""}`} disabled={busy} data-topic-root="true" onClick={()=>{if(selected==="unclassified"||mayLeave())setSelected("unclassified");}}><span>{dragging?"移到根级":"未归类"}</span><small>{unclassified.length}</small></button><ul className="bank-topic-tree" aria-label="标签目录">{branch(null)}</ul>{!topics.length&&<p className="hint">暂无知识标签，可先创建大标签。</p>}</aside><div className="bank-topic-content">{!target&&selected!=="unclassified"?<p className="hint">选择左侧标签或“未归类”查看题目。</p>:<><div className="bank-section-heading"><h4>{target?target.name:"未归类"}</h4>{target&&<button className="link-button" disabled={busy} onClick={()=>{if(mayLeave())onOpen(target.id);}}>在上传与校正中查看</button>}</div>{target&&renderEditor(target)}{target&&children(target.id).length>0&&<p className="hint">展开左侧目录查看子标签；下方仅列本级独有题目；子树已有的同题不在本级重复显示。</p>}<p className="hint">{target&&children(target.id).length?"本级题目":"题目"} · {direct.length}道</p>{direct.slice(questionOffset,questionOffset+20).map(q=><DirectoryQuestion key={`${q.id}:${q.revision}`} item={q} token={token} courseId={courseId}/>)}<nav className="catalogue-pages" aria-label="考点题目分页"><button className="secondary" disabled={!questionOffset||busy} onClick={()=>setQuestionOffset(Math.max(0,questionOffset-20))}>上一页题目</button><span>{Math.floor(questionOffset/20)+1} / {Math.max(1,Math.ceil(direct.length/20))} 页</span><button className="secondary" disabled={questionOffset+20>=direct.length||busy} onClick={()=>setQuestionOffset(questionOffset+20)}>下一页题目</button></nav>{!direct.length&&<p className="hint">{target&&children(target.id).length?"本级没有独有题目，请展开子标签查看。":"这里还没有题目。"}</p>}</>}</div></div></section>;
}

function DirectoryQuestion({token,courseId,item}:{token:string;courseId:string;item:QuestionDirectoryItem}){
 const [open,setOpen]=useState(false),[question,setQuestion]=useState<PastQuestion|null>(null),[failed,setFailed]=useState(false),[reload,setReload]=useState(0);
 useEffect(()=>{
  if(!open)return;let live=true;setQuestion(null);setFailed(false);
  void api.bankQuestion(token,item.id).then(value=>{if(live)setQuestion(value);}).catch(()=>{if(live)setFailed(true);});
  return()=>{live=false;};
 },[token,item.id,item.revision,open,reload]);
 return <details className="bank-directory-question" open={open} onToggle={event=>setOpen(event.currentTarget.open)}><summary>题号 {item.number} · {item.stem}</summary>{open&&(failed?<p role="alert">题目暂不可读取。<button className="secondary" onClick={()=>setReload(value=>value+1)}>重试题目详情</button></p>:question?<>{question.revision!==item.revision&&<p className="hint">题目已更新，显示当前版本；目录计数可刷新后核对。</p>}<BankMath token={token} text={question.stem}/>{question.bank_data.options?.map((option,i)=><div key={i}><strong>{"ABCD"[i]}.</strong><BankMath token={token} text={option}/></div>)}{question.bank_data.illustrations?.map((image,i)=><BankFigure key={i} token={token} courseId={courseId} image={image}/>)}<span className="bank-badge">{question.status==="CONFIRMED"?"已确认":"待校正"}</span></>:<p role="status">正在读取题目正文…</p>)}</details>;
}
