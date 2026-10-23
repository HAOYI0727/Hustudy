import {useMemo} from "react";
import {Icon} from "../../components/Icon";
import {ReaderStudySession} from "../ai";
import "./reader-ai.css";

type Props={currentPage?:number|null;token:string;courseId:string;documentId:string;versionId:string;versionNo:number;name:string;onClose:()=>void;onSource:(version:string,chunk:string)=>void;onNote:(id:string)=>void;onSaved:()=>void;onNotice:(value:string)=>void;onError:(error:unknown)=>void};

export default function ReaderAI({currentPage,token,courseId,documentId,versionId,versionNo,name,onClose,onSource,onNote,onSaved,onNotice,onError}:Props){
 const target=useMemo(()=>({documentId,versionId,chunkId:"",mode:"report" as const}),[documentId,versionId]);
 return <aside className="panel reader-ai-panel" aria-label="AI阅读助手"><div className="panel-title"><div><p className="eyebrow">READ · UNDERSTAND · NOTE</p><h3><Icon name="ai" size={18}/>AI阅读助手</h3></div><button className="secondary" aria-label="收起AI阅读助手" onClick={onClose}>收起</button></div><p className="reader-ai-context">{name} · v{versionNo}</p><p className="hint">围绕当前课件梳理知识点、对应页码和学习笔记。先核对发送范围；图片和图表未提取时不会自动识别。</p><ReaderStudySession readingPage={currentPage} documentName={name} noteTitlePrefix={name} initialStudy={target} token={token} courseId={courseId} onSource={onSource} onNote={onNote} onNoteSaved={onSaved} onNotice={onNotice} onError={onError}/></aside>;
}
