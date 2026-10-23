import type {DocumentItem} from "../../api/client";
import {Icon} from "../../components/Icon";
import {Status} from "../../components/workspace";
import "./material-cards.css";

export const materialSizeLabel = (bytes:number) => bytes<1024*1024?Math.max(1,Math.round(bytes/1024))+" KB":(bytes/1024/1024).toFixed(1)+" MB";
export const materialDateLabel = (value:string) => new Date(value).toLocaleDateString("zh-CN",{month:"short",day:"numeric"});

export function MaterialCard({doc,active,disabled,details,onOpen}:{doc:DocumentItem;active:boolean;disabled:boolean;details:boolean;onOpen:()=>void}) {
  const type=doc.original_filename.split(".").pop()?.toLowerCase()||"file";
  const states=[["解析",doc.parse_status||"QUEUED"],["索引",doc.index_status||"PENDING"],["预览",doc.preview_status||"PENDING"]];
  return <button className={`document-row material-document material-cover-card ${details?"is-detailed":"is-compact"}${active?" selected-document":""}`} aria-pressed={active} disabled={disabled} onClick={onOpen}>
    <span className="material-card-heading"><span className={`file-icon file-type-${type}`}><Icon name="file" size={20}/><small>{type.toUpperCase()}</small></span><span className="material-edition">课程资料 <span>v{doc.latest_version_no||1}</span></span>{active&&<span className="material-open-marker"><Icon name="check" size={12}/>当前打开</span>}</span>
    <span className="row-main"><strong>{doc.name}</strong><small className="material-card-description">{doc.category||"未分类"} · {materialSizeLabel(doc.size_bytes)}</small>
      {details&&<span className="document-tags">{doc.tags.slice(0,3).map(value=><span key={value}>{value}</span>)}{doc.tags.length>3&&<span>＋{doc.tags.length-3}</span>}</span>}
      <span className="material-card-states">{states.map(([label,value])=><span key={label} aria-label={`${label}状态`}><span>{label}</span><Status value={value}/></span>)}</span>
      <span className="document-bottom">{!!doc.confirmed_transcript_count?<span className="manual-count">补录 {doc.confirmed_transcript_count} 页</span>:<span className="material-read-hint">{active?"正在阅读":"打开资料"}<Icon name="arrow" size={12}/></span>}<time dateTime={doc.updated_at}>{materialDateLabel(doc.updated_at)}更新</time></span>
    </span>
  </button>;
}
