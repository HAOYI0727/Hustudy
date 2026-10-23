import {Icon, type IconName} from "./Icon";
import type {Section, WorkspaceExtra} from "../features/platform/routing";

const stages: {section:Section;label:string;icon:IconName;extra?:WorkspaceExtra}[]=[
  {section:"materials",label:"阅读资料",icon:"file"},
  {section:"ai",label:"理解概念",icon:"ai"},
  {section:"notes",label:"整理笔记",icon:"notes"},
  {section:"exam",label:"题库练习",icon:"exam",extra:{examTab:"practice"}},
  {section:"review",label:"错题复盘",icon:"review"},
];
export function LearningPath({section,onOpen}:{section:Section;onOpen:(section:Section,extra?:WorkspaceExtra)=>void}){
  return <nav className="learning-path" aria-label="学习闭环导航"><span className="learning-path-caption">每一步，都有来处</span><ol>{stages.map((stage,index)=><li key={stage.section}><button aria-label={`学习路径：${stage.label}`} aria-current={section===stage.section?"step":undefined} onClick={()=>onOpen(stage.section,stage.extra)}><span className="path-step-index">{String(index+1).padStart(2,"0")}</span><Icon name={stage.icon} size={16}/><span>{stage.label}</span></button>{index<stages.length-1&&<span className="path-connector" aria-hidden="true">›</span>}</li>)}</ol></nav>;
}
