import {useEffect, useRef, useState} from "react";
import {api, ApiError, MaterialExport,type DocumentMetadata} from "../../api/client";
import {Icon} from "../../components/Icon";
import {Status} from "../../components/workspace";

export function MaterialExports({token, courseId, onError, onNotice, refreshKey = 0,selected=[],openSelection=0,disabled=false,hidden=false}: {token:string; courseId:string; onError:(e:unknown)=>void; onNotice:(s:string)=>void; refreshKey?:number;selected?:DocumentMetadata[];openSelection?:number;disabled?:boolean;hidden?:boolean}) {
  const [rows,setRows] = useState<MaterialExport[]>([]);
  const [loading,setLoading] = useState(true);
  const [failed,setFailed] = useState(false);
  const [busy,setBusy] = useState("");
  const [revision,setRevision] = useState(0);
  const [scope,setScope]=useState("course"),[expanded,setExpanded]=useState(false),[uncertain,setUncertain]=useState(false);
  const panel=useRef<HTMLDetailsElement>(null),running=useRef(false);
  const requestId = useRef<{id:string;ids?:string[];names:string[]} | null>(null);
  const live = useRef(true);
  const pending = rows.some(row=>["QUEUED","RUNNING"].includes(row.job.status));
  const refresh = () => setRevision(value=>value+1);
  useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
  useEffect(()=>{
    if(!openSelection)return;
    setExpanded(true);if(!requestId.current)setScope("selected");
    const frame=requestAnimationFrame(()=>{panel.current?.scrollIntoView({block:"start",behavior:"auto"});panel.current?.querySelector("select")?.focus({preventScroll:true});});
    return()=>cancelAnimationFrame(frame);
  },[openSelection]);
  useEffect(()=>{
    const guard=(event:Event)=>{if(event.defaultPrevented)return;if(running.current||(requestId.current&&!window.confirm("资料包提交结果尚未确认，建议先核对原请求。仍离开？原任务可能已在后台创建，可稍后查看导出记录。")))event.preventDefault();};
    const unload=(event:BeforeUnloadEvent)=>{if(running.current||requestId.current){event.preventDefault();event.returnValue="";}};
    window.addEventListener("hustudy:before-navigate",guard);window.addEventListener("beforeunload",unload);
    return()=>{window.removeEventListener("hustudy:before-navigate",guard);window.removeEventListener("beforeunload",unload);};
  },[]);
  useEffect(()=>{
    let active=true;
    setLoading(true);
    void api.materialExports(token,courseId).then(result=>{if(active){setRows(result);setFailed(false);}})
      .catch(error=>{if(active){setFailed(true);onError(error);}}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[token,courseId,revision,refreshKey]);
  useEffect(()=>{if(!pending)return;const timer=window.setTimeout(refresh,2000);return()=>window.clearTimeout(timer);},[rows,pending]);
  const create = async () => {
    if(running.current||busy||disabled||(pending&&!requestId.current)||(!requestId.current&&scope==="selected"&&!selected.length))return;
    requestId.current ||= {id:crypto.randomUUID(),...(scope==="selected"?{ids:selected.map(item=>item.id).sort()}:{}),names:scope==="selected"?selected.map(item=>item.name):[]};
    const frozen=requestId.current;running.current=true;setBusy("create");
    try {
      const result=await api.createMaterialExport(token,courseId,frozen.id,frozen.ids);
      if(live.current){setRows(current=>[result,...current.filter(row=>row.id!==result.id)]);refresh();requestId.current=null;setUncertain(false);onNotice(result.job.status==="SUCCEEDED" ? "资料包已生成" : "导出已进入后台队列，可继续阅读资料");}
    } catch(error){if(live.current){const unknown=!(error instanceof ApiError)||(error.status===0||error.status===401||error.status>=500);if(!unknown)requestId.current=null;setUncertain(unknown);onError(error);}}
    finally{running.current=false;if(live.current)setBusy("");}
  };
  const download = async (row:MaterialExport) => {
    setBusy(row.id);
    try {
      const blob=await api.downloadMaterialExport(token,row.id);
      if(!live.current)return;
      const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`hustudy-materials-${row.id}.zip`;
      document.body.append(link);link.click();link.remove();window.setTimeout(()=>URL.revokeObjectURL(url),60000);
      onNotice("已发起资料包下载；可对照清单校验原件和图片");
    } catch(error){onError(error);refresh();} finally{if(live.current)setBusy("");}
  };
  const retry = async (row:MaterialExport) => {
    setBusy(row.id);
    try{await api.retryMaterialExport(token,row.id);refresh();onNotice("导出任务已恢复，已用尝试次数保留");}
    catch(error){onError(error);}finally{if(live.current)setBusy("");}
  };
  const remove = async (row:MaterialExport) => {
    if(!window.confirm("移除这条导出记录和生成的ZIP？课程原件与图片保留，可重新生成资料包。"))return;
    setBusy(row.id);
    try{await api.removeMaterialExport(token,row.id);refresh();onNotice("导出记录已移除，课程资料保留");}
    catch(error){onError(error);}finally{if(live.current)setBusy("");}
  };
  const names=uncertain?requestId.current?.names||[]:scope==="selected"?selected.map(item=>item.name):[];
  return <details ref={panel} hidden={hidden} className="panel material-export-panel" open={expanded} onToggle={event=>setExpanded(event.currentTarget.open)}>
    <summary className="jobs-summary"><span><Icon name="download"/>课程资料包</span><span className="hint">{pending?"后台生成中":`${rows.length} 条导出记录`}<Icon name="arrow" size={16}/></span></summary>
    <div className="material-export-intro"><div><h4>把需要的课件，连同来源一起带走</h4><p>原件、可用预览、解析文本、已确认补录与来源清单一并保留，包含版本、定位和文件校验值。</p><p className="hint">资料包不含笔记、AI结果、考试和作答，不用于账户恢复。内容上限256 MiB，元数据16 MiB；每课程保留20条记录。</p></div><button className="icon-button secondary" disabled={Boolean(busy)||loading} aria-label="刷新导出记录" onClick={refresh}><Icon name="refresh" size={16}/></button></div>
    <div className="material-export-scope"><label>导出范围<select aria-label="资料包导出范围" value={scope} disabled={!!busy||uncertain} onChange={event=>setScope(event.target.value)}><option value="course">整门课程 · 全部资料与有效图片</option><option value="selected">已选资料 · {selected.length} 份</option></select></label><div><strong>{uncertain?"保留原请求范围":scope==="selected"?`仅导出已选 ${selected.length} 份资料`:"导出当前课程资料"}</strong><p>{scope==="selected"?"固定提交时这些资料的全部版本，附带对应版本截图；不含未选课件、后来新增版本或无来源图库图片。":"包含当前课程未删除资料的全部版本与有效图片；独立题库原件不在范围内。"}</p>{!!names.length&&<ul aria-label="本次导出资料">{names.map((name,index)=><li key={index}>{name}</li>)}</ul>}{scope==="selected"&&!names.length&&<p className="hint">请先在资料库「批量整理分类与标签」中勾选资料，再点击「导出已选」。支持跨页选择。</p>}</div><button className="primary" disabled={disabled||Boolean(busy)||(pending&&!uncertain)||loading||failed||(!uncertain&&scope==="selected"&&!selected.length)} onClick={()=>void create()}><Icon name="download" size={16}/>{busy==="create"?"正在提交…":uncertain?"核对并重试原请求":pending?"正在生成…":scope==="selected"?"生成所选资料包":"生成资料包"}</button></div>
    {uncertain&&<p className="material-export-uncertain" role="alert">上次提交结果尚未确认，原选择和请求标识已保留。恢复连接或登录后，点击「核对并重试原请求」；不会随当前勾选变化扩大导出范围，也不会自动重放。</p>}
    {loading ? <p className="hint" role="status">正在读取导出记录…</p> : failed ? <div className="inline-retry" role="alert">导出记录暂未加载<button className="secondary" onClick={refresh}>重试</button></div> : rows.length ? <div className="material-export-list">{rows.map(row=><article key={row.id}>
      <div className="material-export-heading"><span><Icon name="file" size={17}/>{row.scope==="selected"?`所选 ${row.selected_count} 份资料` : "整门课程资料包"} · {new Date(row.created_at).toLocaleString("zh-CN")}</span><Status value={row.job.status}/></div>
      {row.job.status==="SUCCEEDED" ? <><p>{row.counts.documents || 0} 份资料 · {row.counts.versions || 0} 个版本 · {row.counts.assets || 0} 张图片 · {(row.size_bytes/1024/1024).toFixed(2)} MiB</p><small>快照：{row.snapshot_at?new Date(row.snapshot_at).toLocaleString("zh-CN"):"待生成"}</small><details className="export-hash"><summary>查看文件校验值</summary><code>{row.sha256}</code></details>{row.availability==="unavailable"&&<p className="export-unavailable">包内来源已删除或人工文字被撤回，请生成新的资料包。</p>}</> : <><progress value={row.job.progress} max={100} aria-label="资料包导出进度"/><p className="hint">{row.job.error || (row.job.status==="QUEUED"?"等待后台worker生成":"正在打包资料与校验文件…")} · 已用 {row.job.attempt_count}/{row.job.max_attempts} 次尝试</p></>}
      <div className="material-export-actions">{row.job.status==="SUCCEEDED"&&<button className="secondary" disabled={Boolean(busy)||row.availability!=="active"} onClick={()=>void download(row)}><Icon name="download" size={15}/>下载 ZIP</button>}{row.job.status==="FAILED"&&<button className="secondary" disabled={Boolean(busy)||pending||row.job.attempt_count>=row.job.max_attempts} onClick={()=>void retry(row)}><Icon name="refresh" size={15}/>重试</button>}<button className="secondary danger" disabled={Boolean(busy)} onClick={()=>void remove(row)}><Icon name="trash" size={14}/>移除记录</button></div>
    </article>)}</div> : <p className="hint">还没有导出记录。生成在后台进行，课程资料与笔记不受影响。</p>}
    <p className="hint export-verify-hint">下载后解压查看原件与文本；README 和 manifest.json 说明具体范围与来源。账户迁移请使用「备份与恢复」。</p>
  </details>;
}
