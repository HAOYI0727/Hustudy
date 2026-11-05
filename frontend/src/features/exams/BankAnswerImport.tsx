import {AnswerImageTools} from "./BankImageTools";
import {AnswerCrop} from "./AnswerCrop";
import {useEffect,useRef,useState} from "react";
import {api,AnswerImport,BankPaperMeta,Asset} from "../../api/client";
import {BankMath} from "./BankMath";
import {BankFigure} from "./BankImages";

export function BankAnswerImport({token,courseId,papers,disabled,onApplied,onError,libraryImages}:{
  token:string;courseId:string;papers:BankPaperMeta[];disabled:boolean;libraryImages:Asset[];
  onApplied:(paperId:string)=>Promise<void>;onError:(error:unknown)=>void;
}){
  const [paper,setPaper]=useState(""),[file,setFile]=useState<File|null>(null),[data,setData]=useState<AnswerImport|null>(null);
  const [busy,setBusy]=useState(false),[overwrite,setOverwrite]=useState(false);
  const [history,setHistory]=useState<{id:string;filename:string;status:string}[]>([]);
  const epoch=useRef(0);
  const deleted=useRef(new Set<string>());
  const [notice,setNotice]=useState("");
  useEffect(()=>{
    if(!paper){setHistory([]);return;}
    let live=true;
    void api.answerImports(token,paper).then(rows=>{if(live)setHistory(rows.filter(row=>!deleted.current.has(row.id)));}).catch(error=>{if(live)onError(error);});
    return()=>{live=false;};
  },[token,paper,data?.id,data?.status]);
  useEffect(()=>()=>{epoch.current++;},[token,courseId]);
  const run=async(work:()=>Promise<AnswerImport>)=>{
    const current=epoch.current;setBusy(true);
    try{const next=await work();if(current===epoch.current&&!deleted.current.has(next.id)){setData(next);}}
    catch(error){if(current===epoch.current)onError(error);}
    finally{if(current===epoch.current)setBusy(false);}
  };
  useEffect(()=>{
    if(!data||!["QUEUED","RUNNING"].includes(data.status))return;
    let live=true;
    const timer=setTimeout(()=>{void api.answerImport(token,data.id).then(value=>{if(live&&!deleted.current.has(value.id))setData(value);}).catch(error=>{if(live)onError(error);});},2500);
    return()=>{live=false;clearTimeout(timer);};
  },[token,data]);
  const active=Boolean(data&&["QUEUED","RUNNING"].includes(data.status));
  const matched=Array.from(new Set(data?.results.flatMap(r=>r.question_id?[r.question_id]:[])||[]));
  return <section className="panel">
    <h3>录入答案文件</h3>
    <p>选择已有题库，上传仅含答案的文件。确认后发送该题库题号、题干及答案文件进行匹配。</p>
    <fieldset disabled={disabled||busy||active}>
      <label>目标题库<select value={paper} onChange={e=>{setPaper(e.target.value);setData(null);}}><option value="">请选择题库</option>{papers.map(p=><option key={p.id} value={p.id}>{p.title} · {p.question_count}题</option>)}</select></label>
      <label>答案文件<input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.md,.markdown,.txt" onChange={e=>{setFile(e.target.files?.[0]||null);setData(null);}}/></label>
      <p className="hint">支持PDF、图片、Markdown和TXT，文件最多30MiB，PDF最多20页，目标题库最多100题。</p>
      <button className="secondary" disabled={!paper||!file} onClick={()=>{if(!window.dispatchEvent(new Event("hustudy:bank-before-confirm",{cancelable:true})))return;void run(()=>api.answerPreview(token,paper,file!));}}>上传并预览发送范围</button>
    </fieldset>
    {notice&&<p role="status">{notice}</p>}
    {history.length>0&&<details><summary>已保存答案任务</summary>{history.map(row=><div className="bank-actions" key={row.id}><button className="secondary" disabled={busy||active} onClick={()=>void run(()=>api.answerImport(token,row.id))}>{row.filename} · {row.status}</button><button className="danger-button" disabled={busy} onClick={async()=>{
      if(!window.confirm("删除这条已保存答案任务？已填入题库的参考答案仍保留。"))return;
      const current=epoch.current;setBusy(true);
      try{await api.deleteAnswerImport(token,row.id);if(current===epoch.current){deleted.current.add(row.id);setNotice("答案任务已删除");setHistory(values=>values.filter(v=>v.id!==row.id));if(data?.id===row.id)setData(null);}}
      catch(error){if(current===epoch.current)onError(error);}
      finally{if(current===epoch.current)setBusy(false);}
    }}>删除任务</button></div>)}</details>}
    {data&&<><button className="secondary" disabled={busy} onClick={()=>void run(()=>api.answerImport(token,data.id))}>刷新答案任务</button><p>模型 {data.model} · {data.endpoint} · {data.status} · {data.progress}%</p>
      {data.error&&<p role="alert">{data.error}</p>}
      <details><summary>核对将发送的题目和答案原件</summary>
        {data.questions.map(q=><div key={q.id}><strong>题号 {q.number}</strong><BankMath token={token} text={q.stem}/></div>)}
        {data.sources.map((s,i)=><div key={i}>{s.asset_id?<BankFigure token={token} courseId={courseId} image={{asset_id:s.asset_id,alt:"答案原页 "+s.page}}/>:<pre>{s.text}</pre>}</div>)}
      </details>
      {data.status==="PREVIEW"&&<button className="primary" disabled={busy||disabled} onClick={()=>void run(()=>api.confirmAnswerImport(token,data.id))}>确认发送并匹配答案</button>}
      {data.status==="SUCCEEDED"&&<><p>已整理 {matched.length} 题参考答案，未找到的标为“略”。请核对匹配与图片裁剪位置。</p>
        {matched.map(id=>{const question=data.questions.find(q=>q.id===id);return <article className="panel" key={id}>
          <h4>题号 {question?.number}{question?.has_answer?" · 已有答案":""}</h4>
          <section className="answer-review-question" aria-label={`题号${question?.number}原题`}><h5>原题</h5><BankMath token={token} text={question?.stem||"原题暂不可用，请重新预览"}/>{question?.options?.map((option,index)=><div key={index}><strong>{"ABCD"[index]}. </strong><BankMath token={token} text={option}/></div>)}</section><h5>参考答案</h5>
          {data.results.map((r,index)=>r.question_id===id&&<div key={index}><p>{r.page?"第"+r.page+"页 · ":""}{r.reason}</p><BankMath token={token} text={r.answer||""}/>{Array.from((r.answer||"").matchAll(/!\[\[asset:([0-9a-fA-F-]{36})\|[^\]]*\]\]/g)).map(match=><AnswerCrop key={match[1]} token={token} courseId={courseId} sources={data.sources.flatMap(source=>source.asset_id?[{asset_id:source.asset_id,alt:"答案第"+source.page+"页"}]:[])} assetId={match[1]} originalId={r.image_origins?.[match[1]]} disabled={busy||disabled} onDelete={()=>run(()=>api.removeAnswerResultImage(token,data.id,{result_index:index,asset_id:match[1],expected_answer:r.answer||""}))} onSave={(box,sourceId)=>run(()=>api.cropAnswerResult(token,data.id,{result_index:index,asset_id:match[1],source_asset_id:sourceId,box,expected_answer:r.answer||""}))}/>)}</div>)}
          <AnswerImageTools label="添加图片" libraryImages={libraryImages} token={token} courseId={courseId} preferredAssetId={data.sources.find(source=>source.page===data.results.find(result=>result.question_id===id&&result.page)?.page)?.asset_id} sources={data.sources.flatMap(source=>source.asset_id?[{asset_id:source.asset_id,alt:"答案原页 "+source.page}]:[])} busy={busy||disabled} onWorking={setBusy} onInsert={async(_markdown,images)=>{
            const index=data.results.findIndex(result=>result.question_id===id);
            await run(()=>api.addAnswerResultImages(token,data.id,{result_index:index,images,expected_answer:data.results[index].answer||""}));
          }}/>
        </article>;})}
        <label><input type="checkbox" checked={overwrite} onChange={e=>setOverwrite(e.target.checked)}/>允许覆盖题目已有的参考答案</label>
        <button className="primary" disabled={busy||disabled||!matched.length} onClick={async()=>{
          if(!window.dispatchEvent(new Event("hustudy:bank-before-confirm",{cancelable:true})))return;
          const current=epoch.current;setBusy(true);
          try{const next=await api.applyAnswerImport(token,data.id,matched,overwrite);if(current===epoch.current){setData(next);await onApplied(paper);}}
          catch(error){if(current===epoch.current)onError(error);}
          finally{if(current===epoch.current)setBusy(false);}
        }}>填充整套答案（{matched.length}题）</button>
      </>}
      {data.status==="APPLIED"&&<p>答案已填入，请在题目校正区核对并重新核验。</p>}
    </>}
  </section>;
}
