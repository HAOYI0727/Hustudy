import {useEffect,useRef,useState} from "react";
import {api,Chunk,DocumentItem} from "../../api/client";

type Props={token:string;versions:string[];documents:DocumentItem[];selected:string[];disabled:boolean;onChange:(ids:string[])=>void;onError:(e:unknown)=>void};

export function ChunkPicker({token,versions,documents,selected,disabled,onChange,onError}:Props){
  const [version,setVersion]=useState("");const [chunks,setChunks]=useState<Chunk[]>([]);
  const [filter,setFilter]=useState("");const [busy,setBusy]=useState(false);
  const generation=useRef(0);
  const current=versions.includes(version)?version:versions[0]||"";
  useEffect(()=>{generation.current++;setChunks([]);setBusy(false);},[current,token]);
  useEffect(()=>()=>{generation.current++;},[]);
  const load=async()=>{const id=++generation.current;setBusy(true);try{const rows=await api.chunks(token,current);if(id===generation.current)setChunks(rows);}catch(e){if(id===generation.current)onError(e);}finally{if(id===generation.current)setBusy(false);}};
  const visible=chunks.filter(c=>`${c.locator_value}\n${c.text}`.includes(filter)).slice(0,100);
  return <details className="ai-scope-picker"><summary>精确选择片段 · {selected.length ? `已选${selected.length}段` : "可选"}</summary><p className="hint">不选择时使用默认上下文；选择后仅发送选中范围，最多6段。可查找后面的章节。</p>
    <label>读取片段的资料<select disabled={disabled||busy||!versions.length} value={current} onChange={e=>setVersion(e.target.value)}><option value="" disabled>先选择资料</option>{versions.map(id=><option key={id} value={id}>{documents.find(d=>d.latest_version_id===id)?.name||"已选历史版本"}</option>)}</select></label>
    <button type="button" className="secondary" disabled={disabled||busy||!current} onClick={()=>void load()}>{busy?"读取中…":"读取可选片段"}</button>
    {chunks.length>0&&<><label>查找片段<input value={filter} disabled={disabled} onChange={e=>setFilter(e.target.value)} placeholder="输入章节标题或原文关键词"/></label><p className="hint">共{chunks.length}段，显示前100条匹配项；每段发送最多2000字符。</p><div className="ai-scope-options">{visible.map(c=><label key={c.id}><input type="checkbox" disabled={disabled||(!selected.includes(c.id)&&selected.length>=6)} checked={selected.includes(c.id)} onChange={e=>onChange(e.target.checked?[...selected,c.id]:selected.filter(id=>id!==c.id))}/><span>{c.locator_value} · {c.text.slice(0,100)}</span></label>)}</div></>}
    {selected.length>0&&<button type="button" className="secondary" disabled={disabled} onClick={()=>onChange([])}>清除片段选择</button>}
  </details>;
}
