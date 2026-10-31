import { FormEvent, useEffect, useRef, useState } from "react";
import { api, ApiError, ManualTranscript } from "../../api/client";
import { Icon } from "../../components/Icon";
const labels: Record<string,string> = {DRAFT:"待核对草稿",CONFIRMED:"当前确认",SUPERSEDED:"历史确认",WITHDRAWN:"已撤回"};
type Props = {token: string; versionId: string; request?: {page: number; serial: number}; onPreview: (page: number) => void; onChanged: () => Promise<void>; onError: (e:unknown) => void};
export function Transcripts({token,versionId,request,onPreview,onChanged,onError}: Props) {
  const [rows,setRows]=useState<ManualTranscript[]>([]);
  const [loading,setLoading]=useState(true);
  const [failed,setFailed]=useState(false);
  const [busy,setBusy]=useState(false);
  const [selected,setSelected]=useState<ManualTranscript>();
  const [parent,setParent]=useState<string>();
  const [page,setPage]=useState(1);
  const [body,setBody]=useState("");
  const [saved,setSaved]=useState("");
  const [conflict,setConflict]=useState<{text:string;revision:number;status:string}>();
  const live=useRef(true), sequence=useRef(0);
  const dirty=body!==saved;
  const guard=() => !dirty || window.confirm("补录文字尚未保存为草稿，确定放弃本地修改吗？");
  const load=async()=>{
    const generation=++sequence.current;
    try { const result=await api.transcripts(token,versionId); if(live.current && generation===sequence.current){setRows(result);setFailed(false);} return result; }
    catch(reason){if(live.current)setFailed(true);throw reason;}
    finally{if(live.current)setLoading(false);}
  };
  useEffect(()=>{live.current=true;void load().catch(onError);return()=>{live.current=false;sequence.current++;};},[token,versionId]);
  useEffect(()=>{
    const leave=(event:Event)=>{if(!guard())event.preventDefault();};
    const unload=(event:BeforeUnloadEvent)=>{if(dirty){event.preventDefault();event.returnValue="";}};
    window.addEventListener("hustudy:before-navigate",leave);window.addEventListener("hustudy:before-material-change",leave);window.addEventListener("beforeunload",unload);
    return()=>{window.removeEventListener("hustudy:before-navigate",leave);window.removeEventListener("hustudy:before-material-change",leave);window.removeEventListener("beforeunload",unload);};
  },[dirty]);
  const reset=(targetPage=1)=>{setSelected(undefined);setParent(undefined);setPage(targetPage);setBody("");setSaved("");setConflict(undefined);};
  useEffect(()=>{if(request && guard()){reset(request.page);document.getElementById("transcript-panel")?.scrollIntoView({block:"start",behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"});}},[request?.serial]);
  const choose=(row:ManualTranscript)=>{if(!guard())return;setSelected(row);setParent(undefined);setPage(row.page);setBody(row.text);setSaved(row.text);setConflict(undefined);};
  const failure=(reason:unknown)=>{
    if(reason instanceof ApiError && reason.status===409 && reason.details?.server_text!==undefined){setConflict({text:String(reason.details.server_text),revision:Number(reason.details.server_revision),status:String(reason.details.server_status)});}
    onError(reason);
  };
  const accept=(row:ManualTranscript)=>{setSelected(row);setParent(undefined);setBody(row.text);setSaved(row.text);setPage(row.page);setConflict(undefined);};
  const save=async(e:FormEvent)=>{
    e.preventDefault();if(busy||!body.trim())return;setBusy(true);
    try {
      const result=selected?.status==="DRAFT"?await api.updateTranscript(token,selected.id,{text:body,revision:selected.revision}):await api.createTranscript(token,versionId,{page,text:body,supersedes_id:parent});
      if(!live.current)return;accept(result);await load();
    }catch(reason){if(live.current)failure(reason);}finally{if(live.current)setBusy(false);}
  };
  const confirm=async()=>{
    if(!selected||selected.status!=="DRAFT"||dirty||busy)return;
    if(!window.confirm("已对照原始 PDF 核对这一页文字？确认后会进入检索并允许引用；确认内容的修改需另建修订。"))return;
    setBusy(true);
    try{const result=await api.confirmTranscript(token,selected.id,selected.revision);if(!live.current)return;accept(result);await load();await onChanged();}
    catch(reason){if(live.current)failure(reason);}finally{if(live.current)setBusy(false);}
  };
  const withdraw=async()=>{
    if(!selected||busy||!guard()||!window.confirm("撤回这条补录？它将停止检索，相关引用显示不可用；历史文字会保留，不自动改用旧修订。"))return;
    setBusy(true);
    try{const result=await api.withdrawTranscript(token,selected.id,selected.revision);if(!live.current)return;accept(result);await load();await onChanged();}
    catch(reason){if(live.current)failure(reason);}finally{if(live.current)setBusy(false);}
  };
  const editable=!selected||selected.status==="DRAFT";
  return <section className="manual-transcripts" id="transcript-panel">
    <div className="panel-title"><div><h4><Icon name="edit" size={17}/>原页文字补录</h4><p className="hint">人工核对后可检索与引用 · 不自动识别扫描图片</p></div><button className="secondary" disabled={busy} onClick={()=>{if(guard())reset(page);}}><Icon name="file" size={15}/>新草稿</button></div>
    <div className="transcript-layout"><aside className="transcript-list">{loading?<p className="hint" role="status">正在读取补录…</p>:failed?<button className="secondary" onClick={()=>void load().catch(onError)}>重新加载</button>:rows.map((row,index)=><button key={`${row.id}:${index}`} className={"transcript-record"+(selected?.id===row.id?" selected":"")} disabled={busy} onClick={()=>choose(row)}><strong>原 PDF 第 {row.page} 页</strong><span className={"status status-"+row.status.toLowerCase()}>{labels[row.status]}</span><small>{row.text.slice(0,55)}</small></button>)}{!loading&&!failed&&!rows.length&&<p className="hint">还没有补录。可在 PDF 阅读中点击“补录本页文字”。</p>}</aside>
    <form className="transcript-editor" onSubmit={save}><div className="transcript-controls"><label>原 PDF 页号<input aria-label="补录原 PDF 页号" type="number" min={1} step={1} value={page} onChange={e=>setPage(Number(e.target.value))} disabled={busy||!!selected||!!parent}/></label><button type="button" className="secondary" disabled={!Number.isInteger(page)||page<1||busy} onClick={()=>onPreview(page)}><Icon name="preview" size={15}/>对照原页</button>{selected&&<span className="hint">{labels[selected.status]} · 记录版本 {selected.revision}</span>}</div>
      {parent&&<p className="transcript-notice">正在创建独立修订，旧引用将保留旧文字。</p>}
      <label>人工录入正文<textarea aria-label="人工补录正文" value={body} maxLength={20000} disabled={busy} readOnly={!editable} onChange={e=>setBody(e.target.value)} rows={7} placeholder="请对照原页输入题干、公式或说明，核对后再确认。"/></label>
      <div className="transcript-save-state"><span>{body.length} / 20000 字</span><span>{dirty?"本地修改未保存":selected?.status==="DRAFT"?"草稿已保存，尚未进入检索":selected?labels[selected.status]:"确认前不会进入检索"}</span></div>
      {selected?.confirmed_at&&<p className="hint">本人确认于 {new Date(selected.confirmed_at).toLocaleString("zh-CN")} · 引用校验针对补录文字，原文件保持原样。</p>}
      <div className="transcript-actions">{editable?<><button className="primary" disabled={busy||!body.trim()||(!dirty&&!!selected)||!Number.isInteger(page)||page<1}><Icon name="check" size={15}/>保存草稿</button><button type="button" className="secondary" disabled={busy||dirty||selected?.status!=="DRAFT"} onClick={()=>void confirm()}>核对并确认</button></>:selected?.status==="CONFIRMED"?<button type="button" className="primary" disabled={busy} onClick={()=>{setParent(selected.id);setSelected(undefined);setSaved("");setConflict(undefined);}}>创建文字修订</button>:null}{selected&&selected.status!=="WITHDRAWN"&&<button type="button" className="text-button danger" disabled={busy} onClick={()=>void withdraw()}>撤回补录</button>}</div>
      {conflict&&<div className="conflict-panel" role="alert"><strong>服务器记录已变化，本地文字已保留</strong><p className="hint">服务器版本 {conflict.revision} · {labels[conflict.status]}</p><pre>{conflict.text}</pre><button type="button" className="secondary" onClick={()=>void load().then(list=>{const row=list.find(r=>r.id===selected?.id);if(row)accept(row);}).catch(onError)}>放弃本地修改，载入服务器记录</button></div>}
    </form></div>
  </section>;
}
