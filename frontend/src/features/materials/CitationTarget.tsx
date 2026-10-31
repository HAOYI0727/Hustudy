import {useEffect,useRef,useState} from "react";
import {api,type NoteOption,type NoteOptionPage} from "../../api/client";
import {Icon} from "../../components/Icon";

type Props={token:string;courseId:string;disabled:boolean;onSelect:(id:string)=>void;refresh:number};
export function CitationTarget({token,courseId,disabled,onSelect,refresh}:Props){
  const [q,setQ]=useState(""),[offset,setOffset]=useState(0),[data,setData]=useState<NoteOptionPage|null>(null),[target,setTarget]=useState<NoteOption|null>(null);
  const [loading,setLoading]=useState(true),[failed,setFailed]=useState(false),[retry,setRetry]=useState(0);
  const generation=useRef(0);
  useEffect(()=>{
    const id=++generation.current;let active=true;setLoading(true);setFailed(false);setData(null);
    const timer=window.setTimeout(()=>{void api.noteOptions(token,courseId,q,offset).then(page=>{
      if(!active||id!==generation.current)return;setData(page);
      if(offset&&offset>=page.total)setOffset(page.total?Math.floor((page.total-1)/20)*20:0);
    }).catch(()=>{if(active&&id===generation.current)setFailed(true);}).finally(()=>{if(active&&id===generation.current)setLoading(false);});},q?180:0);
    return()=>{active=false;window.clearTimeout(timer);};
  },[token,courseId,q,offset,retry,refresh]);
  useEffect(()=>()=>onSelect(""),[onSelect]);
  const options=data?.items||[];
  return <section className="citation-target-picker" aria-label="选择引用目标笔记"><div className="citation-toolbar"><Icon name="link" size={17}/><select aria-label="引用到笔记" value={target?.id||""} disabled={disabled} onChange={event=>{const value=options.find(row=>row.id===event.target.value)||null;setTarget(value);onSelect(value?.id||"");}}><option value="">选择接收引用的笔记…</option>{target&&!options.some(row=>row.id===target.id)&&<option value={target.id}>{target.title}（已选择）</option>}{options.map((note,index)=><option key={`${note.id}:${index}`} value={note.id}>{note.title}</option>)}</select><small>选中原文后引用，或保存片段前500字</small></div>
    <details className="citation-target-search"><summary>查找其他笔记{target?` · 当前：${target.title}`:""}</summary><div className="citation-target-controls"><label className="sr-only" htmlFor="citation-note-query">按标题查找引用目标</label><input id="citation-note-query" aria-label="按标题查找引用目标" placeholder="输入笔记标题…" maxLength={200} value={q} onChange={event=>{setQ(event.target.value);setOffset(0);}} disabled={disabled}/>{loading?<span role="status">正在读取笔记标题…</span>:failed?<span role="alert">笔记标题暂不可用<button className="secondary" onClick={()=>setRetry(value=>value+1)}>重试引用笔记</button></span>:data&&<><span className="hint">{data.total} 篇 · 第 {Math.floor(offset/20)+1} 页</span><button className="secondary" disabled={disabled||!offset} onClick={()=>setOffset(Math.max(0,offset-20))}>前一页笔记</button><button className="secondary" disabled={disabled||offset+20>=data.total} onClick={()=>setOffset(offset+20)}>后一页笔记</button></>}</div></details>
    {failed&&<p role="alert" className="hint">引用笔记暂时无法读取，资料仍可阅读。<button className="text-button" onClick={()=>setRetry(value=>value+1)}>重试引用笔记列表</button></p>}
  </section>;
}
