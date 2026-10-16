import { FormEvent, useEffect, useRef, useState } from "react";
import { api, AccountArchive } from "../../api/client";
import { PageTitle, Status } from "../../components/workspace";
import { Icon } from "../../components/Icon";

type Props = {token:string;onError:(e:unknown)=>void;onNotice:(s:string)=>void;onRestored:()=>Promise<void>};
const labels: Record<string,string> = {courses:"课程",documents:"资料",document_versions:"版本",document_chunks:"原文片段",assets:"图片",notes:"笔记",note_links:"双链",citations:"资料引用",exam_papers:"模拟卷",exam_attempts:"作答",mistakes:"错题",review_tasks:"复习任务"};

export function Backups({token,onError,onNotice,onRestored}:Props) {
  const [records,setRecords] = useState<AccountArchive[]>([]);
  const [loading,setLoading] = useState(true), [failed,setFailed] = useState(false), [busy,setBusy] = useState(false);
  const [file,setFile] = useState<File>(), [confirmation,setConfirmation] = useState("");
  const alive = useRef(true), sequence=useRef(0), completed=useRef(new Set<string>()), input=useRef<HTMLInputElement>(null);
  const pending=records.some(row=>["QUEUED","RUNNING"].includes(row.job.status));
  const load = async () => {
    const serial=++sequence.current;
    try {
      const rows=await api.accountArchives(token);
      if (!alive.current || serial!==sequence.current) return;
      setRecords(rows);setFailed(false);
      let refreshed=false;
      for (const row of rows) if (row.purpose==="restore" && row.job.status==="SUCCEEDED" && !completed.current.has(row.id)) {
        completed.current.add(row.id); refreshed=true;
      }
      if(refreshed) await onRestored();
    } catch (e) { if (alive.current && serial===sequence.current) {setFailed(true);onError(e);} }
    finally {if(alive.current && serial===sequence.current)setLoading(false);}
  };
  useEffect(()=>{alive.current=true;void load();return()=>{alive.current=false;sequence.current++;};},[token]);
  useEffect(()=>{if(!pending)return;const timer=window.setTimeout(()=>void load(),2000);return()=>window.clearTimeout(timer);},[records,pending]);
  const create = async () => {
    if(busy||pending)return;setBusy(true);
    try {await api.createAccountArchive(token);onNotice("完整备份已入队，可离开本页稍后下载");await load();}catch(e){onError(e);}finally{setBusy(false);}
  };
  const restore = async (event:FormEvent) => {
    event.preventDefault();if(!file||confirmation!=="恢复到空账户"||busy||pending)return;setBusy(true);
    try {await api.restoreAccountArchive(token,file);setFile(undefined);setConfirmation("");if(input.current)input.current.value="";onNotice("已提交恢复任务，校验通过后会一次性恢复到空账户");await load();}catch(e){onError(e);}finally{setBusy(false);}
  };
  const download = async (row:AccountArchive) => {
    setBusy(true);
    try {const blob=await api.downloadAccountArchive(token,row.id);const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`hustudy-account-${row.id}.zip`;link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);onNotice("备份已下载，请妥善保存在本地");}catch(e){onError(e);}finally{setBusy(false);}
  };
  const remove = async (row:AccountArchive) => {
    if(busy || !window.confirm("移除这份备份ZIP和记录？已恢复的课程和学习数据会保留。"))return;
    setBusy(true);
    try {await api.removeAccountArchive(token,row.id);onNotice("备份记录已移除，账户学习数据保留");await load();}catch(e){onError(e);}finally{setBusy(false);}
  };
  return <div className="page"><PageTitle eyebrow="ACCOUNT BACKUP" title="让每一步积累，都有备份。" text="资料、笔记、引用与学习记录一同保存，校验完整后恢复到空账户。"/>
    <div className="backup-columns"><section className="panel"><h3><Icon name="download"/>保存完整账户</h3><p className="muted">包含资料原件与版本、图片、笔记与双链、AI结果、试卷、作答、错题和复习任务。密钥与登录凭据不导出。</p><p className="hint">先等待或取消正在处理的资料/AI任务。课程资料ZIP是可重建缓存，不复制其文件；原文、来源关系和hash保留。</p><button className="primary" disabled={busy||pending} onClick={()=>void create()}><Icon name="download"/>{pending?"已有任务正在处理":"生成完整备份"}</button></section>
    <form className="panel" onSubmit={restore}><h3><Icon name="upload"/>恢复到空账户</h3><p className="muted">只恢复到没有业务数据的账户，不覆盖已有课程。为保留UUID，请在新数据库的空账户恢复；源对象仍在同一数据库时会拒绝冲突。</p><label>选择完整账户ZIP<input ref={input} type="file" accept=".zip,application/zip" disabled={busy||pending} onChange={e=>{const picked=e.target.files?.[0];if(picked && (!picked.size || picked.size>256*1024*1024)){setFile(undefined);e.target.value="";onError(new Error("请选择非空、≤256MiB的完整备份ZIP"));return;}setFile(picked);}}/></label><label>输入“恢复到空账户”确认<input value={confirmation} disabled={busy||pending} onChange={e=>setConfirmation(e.target.value)} autoComplete="off"/></label><p className="hint">损坏、版本不兼容、归属或关联校验失败时整体回滚；不会执行新的模型请求。仅支持Hustudy完整账户备份，课程资料包不能恢复。</p><button className="secondary" disabled={!file||confirmation!=="恢复到空账户"||busy||pending}><Icon name="upload"/>校验并恢复</button></form></div>
    <section className="panel"><div className="panel-title"><h3>备份与恢复记录</h3><button className="secondary" disabled={busy||loading} onClick={()=>void load()}><Icon name="refresh"/>刷新</button></div>{loading?<p role="status">正在加载…</p>:failed?<p role="alert">记录暂未加载，请刷新重试。</p>:!records.length?<p className="hint">还没有记录，从第一份完整备份开始。</p>:<div className="backup-history">{records.map(row=><article className="backup-record" key={row.id}><div className="panel-title"><h4>{row.purpose==="export"?"完整账户备份":"空账户恢复"}</h4><Status value={row.job.status}/></div><p className="hint">{new Date(row.created_at).toLocaleString("zh-CN")} · {row.size_bytes?(row.size_bytes/1024/1024).toFixed(2)+" MiB":"后台处理中"}</p>{["QUEUED","RUNNING"].includes(row.job.status)&&<progress aria-label="备份恢复进度" max={100} value={row.job.progress}/>}<div className="metadata-chips">{Object.entries(row.counts).filter(([key])=>key in labels).map(([key,value])=><span key={key}>{labels[key]} {value}</span>)}</div>{row.job.error&&<p className="form-error" role="alert">{row.job.error}</p>}{row.sha256&&<details><summary>查看文件SHA-256</summary><code className="backup-hash">{row.sha256}</code></details>}{row.purpose==="export"&&row.job.status==="SUCCEEDED"&&<button className="secondary" disabled={busy} onClick={()=>void download(row)}><Icon name="download"/>下载完整备份</button>}{!["QUEUED","RUNNING"].includes(row.job.status)&&<button className="text-button danger" disabled={busy} onClick={()=>void remove(row)}>移除这份记录</button>}</article>)}</div>}<p className="hint">最多保留50条记录，可移除不再需要的备份文件与记录。校验保证字节和关系完整，不证明AI内容正确；保留本地ZIP时也请保护其中的个人资料。</p></section>
  </div>;
}
