import {useEffect,useRef,useState} from "react";
import {api,type DocumentItem,type DocumentPage} from "../../api/client";
export function SourceScopePicker({token,courseId,documents,onDocuments,versions,onChange,disabled}:{token:string;courseId:string;documents:DocumentItem[];onDocuments:(rows:DocumentItem[])=>void;versions:string[];onChange:(ids:string[])=>void;disabled:boolean}){
 const [q,setQ]=useState(""),[offset,setOffset]=useState(0),[page,setPage]=useState<DocumentPage|null>(null),[loading,setLoading]=useState(true),[failed,setFailed]=useState(false),[reload,setReload]=useState(0),[missing,setMissing]=useState(false);
 const latest=useRef({documents,onDocuments,versions});latest.current={documents,onDocuments,versions};
 const selection=versions.join(",");
 useEffect(()=>{
  let live=true;setLoading(true);setFailed(false);setPage(null);
  const timer=window.setTimeout(()=>{void api.documentPage(token,courseId,{q,category:"",tag:"",state:"all",sort:"name",offset,limit:12}).then(result=>{
   if(!live)return;setPage(result);
   const current=latest.current;const pins=current.documents.filter(doc=>current.versions.includes(doc.latest_version_id||""));
   current.onDocuments([...pins,...result.items.filter(doc=>!pins.some(pin=>pin.latest_version_id===doc.latest_version_id))]);
   if(offset&&offset>=result.total)setOffset(result.total?Math.floor((result.total-1)/12)*12:0);
  }).catch(()=>{if(live)setFailed(true);}).finally(()=>{if(live)setLoading(false);});},q?180:0);
  return()=>{live=false;window.clearTimeout(timer);};
 },[token,courseId,q,offset,reload]);
 useEffect(()=>{
  let live=true;setMissing(false);
  const unknown=versions.filter(id=>!latest.current.documents.some(doc=>doc.latest_version_id===id));
  if(unknown.length)void Promise.all(unknown.map(async id=>{const version=await api.version(token,id);const doc=await api.document(token,version.document_id);if(doc.course_id!==courseId)throw new Error("资料课程不匹配");return {...doc,latest_version_id:version.id,latest_version_no:version.version_no};})).then(rows=>{
    if(live){const current=latest.current;current.onDocuments([...current.documents,...rows.filter(row=>!current.documents.some(doc=>doc.latest_version_id===row.latest_version_id))]);}
   }).catch(()=>{if(live)setMissing(true);});
  return()=>{live=false;};
 },[token,courseId,selection,reload]);
 const visible=page?.items||[],pins=documents.filter(doc=>versions.includes(doc.latest_version_id||"")&&!visible.some(row=>row.latest_version_id===doc.latest_version_id));
 const choices=[...pins,...visible].filter(doc=>doc.latest_version_id);
 return <section className="ai-source-catalog" aria-label="分页选择AI资料"><div className="ai-source-search"><label>查找资料<input aria-label="查找AI资料范围" value={q} maxLength={200} placeholder="名称、分类或标签…" disabled={disabled} onChange={event=>{setQ(event.target.value);setOffset(0);}}/></label><span className="hint">已选 {versions.length} / 20 · 跨页保留</span></div>
 {loading&&<p role="status">正在读取资料目录…</p>}{failed&&<p role="alert">资料列表暂不可用，已有选择保留。<button type="button" className="secondary" onClick={()=>setReload(value=>value+1)}>重试资料目录</button></p>}
 {missing&&<p role="alert">部分已选版本暂不可用，请核对或移除后重试。<button type="button" className="secondary" onClick={()=>setReload(value=>value+1)}>重新核对已选版本</button></p>}
 <div className="ai-scope-options">{choices.map(doc=><label key={doc.latest_version_id}><input type="checkbox" disabled={disabled||!versions.includes(doc.latest_version_id!)&&versions.length>=20} checked={versions.includes(doc.latest_version_id!)} onChange={event=>onChange(event.target.checked?[...versions,doc.latest_version_id!]:versions.filter(id=>id!==doc.latest_version_id))}/><span>{doc.name} <small>v{doc.latest_version_no}{pins.some(pin=>pin.latest_version_id===doc.latest_version_id)?" · 已选保留":""}</small></span></label>)}</div>
 {versions.filter(id=>!documents.some(doc=>doc.latest_version_id===id)).map(id=><p key={id} className="hint">已选版本 {id.slice(0,8)} · 等待核对 <button type="button" className="text-button" disabled={disabled} onClick={()=>onChange(versions.filter(value=>value!==id))}>移除此版本</button></p>)}
 {!loading&&!failed&&page&&!page.items.length&&<p className="hint">没有匹配的资料，可调整关键词；已有选择保留。</p>}
 {page&&<nav className="catalogue-pages" aria-label="AI资料分页"><button type="button" className="secondary" disabled={disabled||loading||!offset} onClick={()=>setOffset(Math.max(0,offset-12))}>上一页资料</button><span>{Math.floor(offset/12)+1} / {Math.max(1,Math.ceil(page.total/12))} 页 · {page.total}份</span><button type="button" className="secondary" disabled={disabled||loading||offset+12>=page.total} onClick={()=>setOffset(offset+12)}>下一页资料</button></nav>}
 </section>;
}
