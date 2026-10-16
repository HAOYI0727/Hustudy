import {useEffect, useRef, useState} from "react";
import {api, ApiError, MaterialExport} from "../../api/client";
import {Icon} from "../../components/Icon";
import {Status} from "../../components/workspace";

export function MaterialExports({token, courseId, onError, onNotice, refreshKey = 0}: {token:string; courseId:string; onError:(e:unknown)=>void; onNotice:(s:string)=>void; refreshKey?:number}) {
  const [rows,setRows] = useState<MaterialExport[]>([]);
  const [loading,setLoading] = useState(true);
  const [failed,setFailed] = useState(false);
  const [busy,setBusy] = useState("");
  const [revision,setRevision] = useState(0);
  const requestId = useRef<string | undefined>(undefined);
  const live = useRef(true);
  const pending = rows.some(row=>["QUEUED","RUNNING"].includes(row.job.status));
  const refresh = () => setRevision(value=>value+1);
  useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
  useEffect(()=>{
    let active=true;
    void api.materialExports(token,courseId).then(result=>{if(active){setRows(result);setFailed(false);}})
      .catch(error=>{if(active){setFailed(true);onError(error);}}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[token,courseId,revision,refreshKey]);
  useEffect(()=>{if(!pending)return;const timer=window.setTimeout(refresh,2000);return()=>window.clearTimeout(timer);},[rows,pending]);
  const create = async () => {
    if(busy || pending)return;
    requestId.current ||= crypto.randomUUID(); setBusy("create");
    try {
      const result=await api.createMaterialExport(token,courseId,requestId.current);
      if(live.current){setRows(current=>[result,...current.filter(row=>row.id!==result.id)]);refresh();requestId.current=undefined;onNotice(result.job.status==="SUCCEEDED" ? "资料包已生成" : "导出已进入后台队列，可继续阅读资料");}
    } catch(error){if(error instanceof ApiError && error.status>0 && error.status<500) requestId.current=undefined;onError(error);}
    finally{if(live.current)setBusy("");}
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
  return <details className="panel material-export-panel">
    <summary className="jobs-summary"><span><Icon name="download"/>课程资料包</span><span className="hint">{pending?"后台生成中":`${rows.length} 条导出记录`}<Icon name="arrow" size={16}/></span></summary>
    <div className="material-export-intro"><div><h4>把原件、图表和来源一起带走</h4><p>包含未删除资料的全部版本原件、可用预览、解析文本、已确认补录、有效图片与来源清单。保留 UUID、版本、定位及每个文件的 SHA-256。</p><p className="hint">这是课程资料包，不含笔记、AI结果、考试和作答记录，当前不能恢复导入。内容上限256 MiB，元数据16 MiB；每课程保留20条记录。</p></div><button className="icon-button secondary" disabled={Boolean(busy)||loading} aria-label="刷新导出记录" onClick={refresh}><Icon name="refresh" size={16}/></button><button className="primary" disabled={Boolean(busy)||pending||loading||failed} onClick={()=>void create()}><Icon name="download" size={16}/>{busy==="create"?"正在提交…":pending?"正在生成…":"生成资料包"}</button></div>
    {loading ? <p className="hint" role="status">正在读取导出记录…</p> : failed ? <div className="inline-retry" role="alert">导出记录暂未加载<button className="secondary" onClick={refresh}>重试</button></div> : rows.length ? <div className="material-export-list">{rows.map(row=><article key={row.id}>
      <div className="material-export-heading"><span><Icon name="file" size={17}/>资料包 · {new Date(row.created_at).toLocaleString("zh-CN")}</span><Status value={row.job.status}/></div>
      {row.job.status==="SUCCEEDED" ? <><p>{row.counts.documents || 0} 份资料 · {row.counts.versions || 0} 个版本 · {row.counts.assets || 0} 张图片 · {(row.size_bytes/1024/1024).toFixed(2)} MiB</p><small>快照：{row.snapshot_at?new Date(row.snapshot_at).toLocaleString("zh-CN"):"待生成"}</small><details className="export-hash"><summary>查看文件校验值</summary><code>{row.sha256}</code></details>{row.availability==="unavailable"&&<p className="export-unavailable">包内来源已删除或人工文字被撤回，请生成新的资料包。</p>}</> : <><progress value={row.job.progress} max={100} aria-label="资料包导出进度"/><p className="hint">{row.job.error || (row.job.status==="QUEUED"?"等待后台worker生成":"正在打包资料与校验文件…")} · 已用 {row.job.attempt_count}/{row.job.max_attempts} 次尝试</p></>}
      <div className="material-export-actions">{row.job.status==="SUCCEEDED"&&<button className="secondary" disabled={Boolean(busy)||row.availability!=="active"} onClick={()=>void download(row)}><Icon name="download" size={15}/>下载 ZIP</button>}{row.job.status==="FAILED"&&<button className="secondary" disabled={Boolean(busy)||pending||row.job.attempt_count>=row.job.max_attempts} onClick={()=>void retry(row)}><Icon name="refresh" size={15}/>重试</button>}<button className="secondary danger" disabled={Boolean(busy)} onClick={()=>void remove(row)}><Icon name="trash" size={14}/>移除记录</button></div>
    </article>)}</div> : <p className="hint">还没有导出记录。生成在后台进行，课程资料与笔记不受影响。</p>}
    <p className="hint export-verify-hint">ZIP 中的 README 和 manifest.json 说明范围与来源；可用项目的 scripts/verify_material_package.py 检查版本、成员、字节及 hash。</p>
  </details>;
}
