import {useEffect,useRef,useState} from "react";
import {api,type Version,type Chunk} from "../../api/client";
import {sessionPartition} from "../../api/query";
import {Icon} from "../../components/Icon";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {compareVersionText,filterComparison,type VersionComparison} from "./versionComparison";
type Props={token:string;documentId:string;name:string;versions:Version[];currentVersionId:string;disabled:boolean;onSource:(versionId:string,chunkId:string)=>Promise<boolean>};
const statusLabel={same:"文本相同",changed:"文本变化",left:"仅左侧定位",right:"仅右侧定位"};
export default function VersionCompare({token,documentId,name,versions,currentVersionId,disabled,onSource}:Props){
  const [open,setOpen]=useState(false),[left,setLeft]=useState(""),[right,setRight]=useState(""),[busy,setBusy]=useState(false),[opening,setOpening]=useState(false),[error,setError]=useState("");
  const [result,setResult]=useState<VersionComparison>(),[loaded,setLoaded]=useState<{left:string;right:string}>(),[mode,setMode]=useState<"changed"|"all">("changed"),[query,setQuery]=useState(""),[offset,setOffset]=useState(0);
  const generation=useRef(0),live=useRef(true),openRef=useRef(false);
  const eligible=versions.filter(v=>v.document_id===documentId&&v.parse_status==="SUCCEEDED");
  useEffect(()=>{live.current=true;return()=>{live.current=false;generation.current++;};},[]);
  useEffect(()=>{generation.current++;setOpen(false);openRef.current=false;setResult(undefined);setLoaded(undefined);setBusy(false);setError("");},[documentId,token]);
  const close=()=>{generation.current++;openRef.current=false;setBusy(false);setOpen(false);};
  useEffect(()=>{
    const unauthorized=(event:Event)=>{if((event as CustomEvent).detail===sessionPartition(token)){generation.current++;openRef.current=false;setOpen(false);setBusy(false);setResult(undefined);setError("登录已过期，请恢复登录后重新加载对照。");}};
    window.addEventListener("hustudy:unauthorized",unauthorized);return()=>window.removeEventListener("hustudy:unauthorized",unauthorized);
  },[token]);
  const invalidate=()=>{generation.current++;setBusy(false);setResult(undefined);setLoaded(undefined);setError("");setOffset(0);};
  const load=async()=>{
    if(!left||!right||left===right||!eligible.some(v=>v.id===left)||!eligible.some(v=>v.id===right))return;
    const request=++generation.current;setBusy(true);setResult(undefined);setLoaded(undefined);setError("");setOffset(0);
    try {
      const [a,b]=await Promise.all([api.chunks(token,left),api.chunks(token,right)]);
      if(a.some(c=>c.version_id!==left)||b.some(c=>c.version_id!==right))throw new Error("版本片段不一致，请重新加载");
      if(live.current&&openRef.current&&generation.current===request){setResult(compareVersionText(a,b));setLoaded({left,right});}
    }catch(error){if(live.current&&openRef.current&&generation.current===request)setError(error instanceof Error?error.message:"对照加载失败，请重试");}
    finally{if(live.current&&generation.current===request)setBusy(false);}
  };
  const rows=result?filterComparison(result.rows,mode,query):[],counts=result?.rows.reduce((all,row)=>({...all,[row.status]:all[row.status]+1}),{same:0,changed:0,left:0,right:0});
  const shownOffset=rows.length?Math.min(offset,Math.floor((rows.length-1)/12)*12):0;
  const versionName=(id:string)=>{const version=versions.find(v=>v.id===id);return version?`v${version.version_no} · ${version.original_filename}`:"版本不可用";};
  const source=async(chunk:Chunk)=>{
    setOpening(true);setError("");
    try{if(await onSource(chunk.version_id,chunk.id))close();}catch(error){if(live.current)setError(error instanceof Error?error.message:"原文暂不可读");}
    finally{if(live.current)setOpening(false);}
  };
  return <>
    <button className="secondary" disabled={disabled||eligible.length<2} title={eligible.length<2?"同一资料需要至少两个解析成功的版本":"对照同一资料不同版本的提取文本"} onClick={()=>{
      invalidate();const current=eligible.find(v=>v.id===currentVersionId)||eligible[0];
      setRight(current.id);setLeft((eligible.find(v=>v.version_no<current.version_no)||eligible.find(v=>v.id!==current.id))!.id);
      setMode("changed");setQuery("");openRef.current=true;setOpen(true);
    }}><Icon name="split" size={16}/>版本对照</button>
    <WorkspaceDialog open={open} title="版本文本对照" className="version-compare-dialog" busy={opening} onClose={close}>
      <div className="reading-tool-intro"><span className="reading-tool-symbol"><Icon name="split" size={24}/></span><div><h3>{name}</h3><p>查看两次导入的文字变化，确认后仍可回到各自原文。</p></div></div>
      <div className="compare-versions"><label>左侧版本<select aria-label="对照左侧版本" value={left} disabled={opening} onChange={event=>{invalidate();setLeft(event.target.value);}}>{eligible.map(v=><option key={v.id} value={v.id}>v{v.version_no} · {v.original_filename}</option>)}</select></label><Icon name="arrow"/><label>右侧版本<select aria-label="对照右侧版本" value={right} disabled={opening} onChange={event=>{invalidate();setRight(event.target.value);}}>{eligible.map(v=><option key={v.id} value={v.id}>v{v.version_no} · {v.original_filename}</option>)}</select></label><button className="primary" disabled={busy||opening||!left||!right||left===right} onClick={()=>void load()}>{busy?"正在读取版本…":"加载对照"}</button></div>
      <p className="hint compare-scope">只按相同且唯一的原文定位对照提取文本，不比较图片与排版。章节改名、页码移动或格式变化可能显示为单侧定位，请核对原文。</p>
      {left===right&&left&&<p className="reading-tool-error" role="status">请选择两个不同版本。</p>}
      {error&&<p className="reading-tool-error" role="alert">{error}</p>}
      {busy&&<p className="reading-tool-loading" role="status"><Icon name="refresh" className="is-spinning"/>正在读取两个历史版本，当前阅读和引用保持原位…</p>}
      {result&&loaded&&<>
        <div className="compare-stats" aria-label="版本文本对照统计">{counts&&Object.entries(counts).map(([key,value])=><div key={key} data-status={key}><strong>{value}</strong><span>{statusLabel[key as keyof typeof statusLabel]}</span></div>)}</div>
        {!!(result.excludedLeft+result.excludedRight)&&<p className="hint" role="status">人工补录或其他来源未参与对照：左侧 {result.excludedLeft} 段，右侧 {result.excludedRight} 段。</p>}
        {!!result.ambiguous&&<p className="reading-tool-error">有 {result.ambiguous} 组定位重复，已分别列出，请人工核对。</p>}
        {result.differentLocators&&<p className="reading-tool-error">两侧定位类型不同，无法自动配对；以下分别展示原文。</p>}
        <div className="compare-filters"><label className="input-with-icon"><Icon name="search" size={16}/><input aria-label="搜索版本对照内容" placeholder="查找定位或文字…" value={query} onChange={event=>{setQuery(event.target.value);setOffset(0);}}/></label><select aria-label="筛选对照片段" value={mode} onChange={event=>{setMode(event.target.value as "changed"|"all");setOffset(0);}}><option value="changed">仅显示变化与单侧</option><option value="all">全部片段</option></select></div>
        <div className="compare-rows">{rows.slice(shownOffset,shownOffset+12).map(row=><details className="compare-row" data-status={row.status} key={row.key}><summary><span className="compare-status">{statusLabel[row.status]}</span><strong>{row.left?.locator_value||row.right?.locator_value}</strong><small>{row.ambiguous?"重复定位 · 人工核对":"展开完整文本"}</small></summary><div className="compare-columns">{(["left","right"] as const).map(side=><section key={side} aria-label={side==="left"?"左侧原文":"右侧原文"}><header><span>{versionName(loaded[side])}</span>{row[side]&&<button className="text-button" disabled={opening} onClick={()=>void source(row[side]!)}>阅读{side==="left"?"左":"右"}侧原文 <Icon name="arrow" size={14}/></button>}</header>{row[side]?<pre tabIndex={0} aria-label={`${side==="left"?"左":"右"}侧完整提取文本`}>{row[side]!.text}</pre>:<p className="compare-absent">此侧没有可唯一配对的定位</p>}</section>)}</div></details>)}</div>
        {!rows.length&&<div className="reading-tool-empty"><Icon name="check" size={28}/><strong>{!result.rows.length?"没有可对照的文件提取文本":query?"没有匹配的片段":mode==="changed"?"相同定位的提取文本没有变化":"没有符合条件的片段"}</strong><p>{!result.rows.length?"扫描资料可阅读原页；人工补录文字单独保留。":"切换到全部片段，或调整搜索词继续查看。"}</p></div>}
        <nav className="catalogue-pages" aria-label="版本对照分页"><button className="secondary" disabled={opening||!shownOffset} onClick={()=>setOffset(shownOffset-12)}>上一页</button><span role="status">{Math.floor(shownOffset/12)+1} / {Math.max(1,Math.ceil(rows.length/12))} 页 · {rows.length} 组</span><button className="secondary" disabled={opening||shownOffset+12>=rows.length} onClick={()=>setOffset(shownOffset+12)}>下一页</button></nav>
      </>}
      {!result&&!busy&&!error&&<div className="reading-tool-empty"><Icon name="split" size={32}/><strong>选好版本，再开始对照</strong><p>历史引用始终指向原版本，对照不会改写资料或笔记。</p></div>}
    </WorkspaceDialog>
  </>;
}
