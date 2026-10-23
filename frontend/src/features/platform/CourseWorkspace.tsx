import {useEffect, useRef, useState} from "react";
import {api, type WorkspaceDomain, type WorkspaceItem, type WorkspaceSection} from "../../api/client";
import {Icon, type IconName} from "../../components/Icon";
import {Status} from "../../components/workspace";
import type {Section, WorkspaceExtra} from "./routing";

export type OpenWorkspace = (section:Section, extra?:WorkspaceExtra) => void;
type Part = {data?:WorkspaceSection; loading:boolean; error:boolean};
type Parts = Record<WorkspaceDomain,Part>;
const domains: WorkspaceDomain[] = ["materials","study","notes","practice"];
const initial = (): Parts => Object.fromEntries(domains.map(domain=>[domain,{loading:true,error:false}])) as Parts;

export function useCourseWorkspace(token:string, courseId:string) {
  const currentScope=token+":"+courseId;
  const [scope,setScope]=useState(currentScope);
  const [parts,setParts] = useState<Parts>(initial);
  const generation=useRef(0);
  const load = async (domain:WorkspaceDomain, current:number) => {
    setParts(state=>({...state,[domain]:{loading:true,error:false}}));
    try {
      const data=await api.workspace(token,courseId,domain);
      if(generation.current===current) setParts(state=>({...state,[domain]:{data,loading:false,error:false}}));
    } catch {
      if(generation.current===current) setParts(state=>({...state,[domain]:{loading:false,error:true}}));
    }
  };
  useEffect(()=>{
    const current=++generation.current;setScope(currentScope);setParts(initial());
    if(courseId) for(const domain of domains) void load(domain,current);
    else setParts(Object.fromEntries(domains.map(domain=>[domain,{loading:false,error:false}])) as Parts);
    return()=>{generation.current++;};
  },[token,courseId]);
  return {parts:scope===currentScope?parts:initial(),retry:(domain:WorkspaceDomain)=>void load(domain,generation.current)};
}

export function openWorkspaceItem(item:WorkspaceItem, open:OpenWorkspace) {
  if(item.kind==="material" && item.document_id && item.version_id) open("materials",{material:{documentId:item.document_id,versionId:item.version_id,chunkId:""}});
  if(item.kind==="note") open("notes",{noteId:item.id});
  if(item.kind==="qa" || item.kind==="report") open("ai",{aiResultId:item.id,aiMode:item.kind});
  if(item.kind==="attempt") open("exam",{examTab:"practice",attemptId:item.id});
  if(item.kind==="mistake") open("review",{mistakeId:item.id});
}
/** A shortcut into an existing object, never a request to create a new one. */
export function continuationItem(domain:WorkspaceDomain, rows:WorkspaceItem[]):WorkspaceItem|undefined {
  return rows.filter(item=> {
    if(domain==="materials")return item.kind==="material"&&item.status==="SUCCEEDED"&&!!item.document_id&&!!item.version_id;
    if(domain==="notes")return item.kind==="note"&&item.status==="SAVED";
    if(domain==="study")return (item.kind==="qa"||item.kind==="report")&&item.status==="grounded";
    return item.kind==="attempt"&&item.status==="IN_PROGRESS";
  }).sort((a,b)=>b.updated_at.localeCompare(a.updated_at)||a.id.localeCompare(b.id))[0];
}
const continuationCopy:Record<WorkspaceDomain,{action:string;empty:string}>={
  materials:{action:"继续阅读",empty:"导入课件，解析后从原文开始。"},
  study:{action:"回看学习结果",empty:"选定资料，带着问题深入理解。"},
  notes:{action:"继续编辑笔记",empty:"把阅读中的理解记成第一篇笔记。"},
  practice:{action:"恢复进行中的练习",empty:"暂无进行中的作答，可从题库开始练习。"},
};
const steps: {domain:WorkspaceDomain;title:string;icon:IconName;label:string;key:string;description:string;section:Section;extra?:WorkspaceExtra}[] = [
  {domain:"materials",title:"读懂课程资料",icon:"file",label:"可检索资料",key:"ready",description:"从原文出发，保留每个知识点的来处。",section:"materials"},
  {domain:"study",title:"理清知识脉络",icon:"ai",label:"有来源结果",key:"grounded",description:"带着问题理解，用引用核对解释。",section:"ai",extra:{aiMode:"report"}},
  {domain:"notes",title:"写成自己的理解",icon:"notes",label:"已保存笔记",key:"total",description:"把概念、例子与来源连接起来。",section:"notes"},
  {domain:"practice",title:"在练习中巩固",icon:"exam",label:"已核验题目",key:"confirmed",description:"核对自己的题库，练习后回到薄弱处。",section:"exam",extra:{examTab:"practice"}},
];
export function CourseWorkspace({parts,retry,onOpen,onRecords}: {parts:Parts;retry:(domain:WorkspaceDomain)=>void;onOpen:OpenWorkspace;onRecords:()=>void}) {
  const material=parts.materials.data?.counts, notes=parts.notes.data?.counts, practice=parts.practice.data?.counts;
  const actions: {title:string;description:string;section:Section;extra?:WorkspaceExtra;icon:IconName}[]=[];
  const pendingAttempt=parts.practice.data?.recent.find(row=>row.status==="IN_PROGRESS");
  if(pendingAttempt)actions.push({title:"继续未完成作答",description:pendingAttempt.title,section:"exam",extra:{examTab:"practice",attemptId:pendingAttempt.id},icon:"clock"});
  if(material?.attention_materials)actions.push({title:"检查资料处理",description:`${material.attention_materials} 份资料的最新版本需要检查，可在资料检查中定位。`,section:"materials",icon:"info"});
  if(material?.total===0)actions.push({title:"导入第一份资料",description:"课件、教材或章节讲义，都可以成为学习起点。",section:"materials",icon:"upload"});
  if(practice?.pending)actions.push({title:"核对题库草稿",description:`${practice.pending} 道题尚待核验，核对后再加入练习。`,section:"exam",extra:{examTab:"bank"},icon:"exam"});
  if(practice?.due_reviews)actions.push({title:"回顾待复习错题",description:`当前课程有 ${practice.due_reviews} 项今日或逾期复习任务。`,section:"review",icon:"review"});
  if(notes?.total===0 && material && material.total>0)actions.push({title:"记录第一个理解",description:"阅读原文时可直接摘录为带来源的新笔记。",section:"materials",icon:"notes"});
  const recent=Object.values(parts).flatMap(part=>part.data?.recent||[]).sort((a,b)=>b.updated_at.localeCompare(a.updated_at)||a.id.localeCompare(b.id)).slice(0,6);
  const kinds:Record<WorkspaceItem["kind"],{text:string;icon:IconName}>={material:{text:"课程资料",icon:"file"},note:{text:"知识笔记",icon:"notes"},report:{text:"学习报告",icon:"ai"},qa:{text:"资料问答",icon:"ai"},attempt:{text:"练习作答",icon:"exam"},mistake:{text:"错题复盘",icon:"review"}};
  return <section className="course-workspace" aria-label="当前课程学习工作台">
    <div className="section-heading"><div><p className="eyebrow">ONE COURSE · ONE LEARNING LOOP</p><h2>让学习，连成一条线</h2></div><span className="workspace-live"><span/>当前课程 · 实际记录</span></div>
    <button className="hub-overview-link" onClick={()=>onOpen("topics")}><span><Icon name="link"/><strong>知识点学习中心</strong><small>把同一个概念的原文、理解和错题放在一起</small></span><Icon name="arrow"/></button><div className="course-learning-grid">{steps.map((step,index)=>{
      const part=parts[step.domain];
      const item=!part.loading&&!part.error?continuationItem(step.domain,part.data?.recent||[]):undefined;
      return <article key={step.domain} className={`learning-stage stage-${step.domain}`} aria-label={step.title}>
        <Icon name={step.icon} size={90} className="stage-watermark"/><div className="stage-heading"><span className="stage-symbol"><Icon name={step.icon} size={22}/></span><span className="stage-number">0{index+1} · {({materials:"阅读",study:"理解",notes:"连接",practice:"检验"})[step.domain]}</span></div>
        <h3>{step.title}</h3><p>{step.description}</p>
        <div className="stage-count"><strong>{part.loading?"…":part.error?"—":part.data?.counts[step.key]??"—"}</strong><span>{step.label}</span></div>
        <div className="stage-continuation">{item?<button className="stage-continue" onClick={()=>openWorkspaceItem(item,onOpen)}><span className="stage-continue-label"><Icon name={step.domain==="practice"?"clock":"arrow"} size={14}/>{continuationCopy[step.domain].action}</span><strong>{item.title}</strong><span className="stage-continue-meta"><Status value={item.status}/><time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleDateString("zh-CN",{month:"short",day:"numeric"})}更新</time></span></button>:<div className="stage-start"><Icon name={part.error?"info":part.loading?"clock":step.icon} size={18}/><span>{part.error?"恢复连接后可读取最近记录。":part.loading?"正在核对当前课程记录…":continuationCopy[step.domain].empty}</span></div>}</div>
        {part.error?<div className="stage-error" role="alert">暂时无法读取<button className="text-button" onClick={()=>retry(step.domain)}>重试{step.label}</button></div>:<button className="stage-action" onClick={()=>onOpen(step.section,step.extra)}>{step.domain==="practice"?"进入题库练习":"打开工作区"}<Icon name="arrow" size={16}/></button>}
      </article>;
    })}</div>
    {!!actions.length && <section className="next-actions" aria-label="接下来可以做"><div><p className="eyebrow">YOUR NEXT STEP</p><h3>接下来，可以从这里继续</h3></div><div className="next-action-list">{actions.slice(0,3).map(action=><button key={action.title} onClick={()=>onOpen(action.section,action.extra)}><span className="next-action-icon"><Icon name={action.icon}/></span><span><strong>{action.title}</strong><small>{action.description}</small></span><Icon name="arrow" size={16}/></button>)}</div></section>}
    <section className="workspace-recent" aria-label="当前课程近期活动"><div className="panel-title"><h3>最近的学习足迹</h3><button className="secondary" onClick={event=>{event.currentTarget.focus({preventScroll:true});onRecords();}}><Icon name="clock" size={15}/>全部学习记录<Icon name="arrow" size={14}/></button></div><div className="workspace-activity-list">{recent.map(item=><button key={`${item.kind}-${item.id}`} onClick={()=>openWorkspaceItem(item,onOpen)}><span className={`activity-icon activity-${item.kind}`}><Icon name={kinds[item.kind].icon}/></span><span className="activity-copy"><strong>{item.title}</strong><small>{kinds[item.kind].text} · {new Date(item.updated_at).toLocaleDateString("zh-CN",{month:"long",day:"numeric"})}</small></span><Status value={item.status}/><Icon name="arrow" size={15}/></button>)}</div>{!recent.length&&<p className="hint">{Object.values(parts).some(part=>part.loading)?"正在读取近期记录…":"还没有近期记录，可以从导入资料或新建笔记开始。"}</p>}</section>
    <p className="workspace-footnote"><Icon name="info" size={14}/>记录数帮助你安排下一步；已核验题目在抽取时仍会检查来源与题库规则。</p>
  </section>;
}
