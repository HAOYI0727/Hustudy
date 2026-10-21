import {AIActivity} from "../../components/AIActivity";
import {useEffect,useRef,useState} from "react";
import {api,BankTopicJob} from "../../api/client";

export function BankAPISetup({configured}:{configured:boolean}){
 return <div className="bank-api-setup"><p className="hint">{configured?"API已配置，可使用AI辅助。":"尚未配置API，可继续使用本地功能。"} <a href="/api-connect">打开左侧“API接入”按图设置 →</a></p></div>;
}

export function BankTopicAI({token,paperId,ids,busy,onImported,onNotice}:{token:string;paperId:string;ids:string[];busy:boolean;onImported:()=>Promise<void>;onNotice:(s:string)=>void}){
 const [job,setJob]=useState<BankTopicJob|null>(null),[working,setWorking]=useState(false),[configured,setConfigured]=useState(false),[error,setError]=useState("");
 const callback=useRef(onImported);callback.current=onImported;
 const finished=useRef("");
 useEffect(()=>{let alive=true;void api.bankAICapabilities(token).then(v=>{if(alive)setConfigured(v.configured);}).catch(()=>{});void api.bankTopicStatus(token,paperId).then(v=>{if(alive)setJob(v);}).catch(()=>{});return()=>{alive=false;};},[token,paperId]);
 const pending=job?.status==="QUEUED"||job?.status==="RUNNING";
 useEffect(()=>{let active=true;const poll=async()=>{try{const v=await api.bankTopicStatus(token,paperId);if(!active)return;setJob(v);if(v.status==="SUCCEEDED"&&finished.current!==v.expires_at){finished.current=v.expires_at!;const guard=new Event("hustudy:bank-before-confirm",{cancelable:true});if(window.dispatchEvent(guard)){await callback.current();}onNotice("AI知识点建议已更新，请核对蓝色推荐并选用保存");}}catch(e){if(active)setError(e instanceof Error?e.message:"读取AI任务失败");}};const timer=window.setInterval(()=>void poll(),1500);return()=>{active=false;window.clearInterval(timer);};},[pending,token,paperId]);
 useEffect(()=>{const guard=(e:Event)=>{if(working)e.preventDefault();};window.addEventListener("hustudy:before-navigate",guard);return()=>window.removeEventListener("hustudy:before-navigate",guard);},[working]);
 const run=async(fn:()=>Promise<void>)=>{setWorking(true);setError("");try{const guard=new Event("hustudy:bank-before-confirm",{cancelable:true});if(!window.dispatchEvent(guard)){setError("请先保存尚未保存的题目校正，再使用AI归类");return;}await fn();}catch(e){setError(e instanceof Error?e.message:"AI归类失败");}finally{setWorking(false);}};
 return <div className="bank-topic-ai"><AIActivity active={pending} queued={job?.status==="QUEUED"} label="知识点归类"/><button type="button" className="secondary" disabled={busy||working||pending||!configured||!ids.length} onClick={()=>void run(async()=>setJob(await api.bankTopicPreview(token,paperId,ids)))}>AI归类这{ids.length}题</button><span className="hint">{pending?"AI正在按语义匹配知识点，可离开后回来查看。":"优先处理勾选题目，否则处理本页尚未归类的题目，每批最多32题。先预览，确认后发送。"}</span>
 <BankAPISetup configured={configured}/>
 {job?.status==="PREVIEW"&&job.input&&<section className="bank-ai-consent"><h4>AI知识点归类 · 确认发送范围</h4><p>模型：{job.model} · 目的地：{job.endpoint}。发送下列题干、选项和已有标签，不发送答案；已有标签优先，新标签仅作为备选。</p><details open><summary>本批{job.input.questions.length}道题及全部标签词表</summary>{job.input.questions.map(q=><pre key={q.question_id}>{q.stem}{q.options.length?"\n"+q.options.map((o,i)=>"ABCD"[i]+". "+o).join("\n"):""}</pre>)}<pre>{job.input.topics.map(t=>t.name+(t.aliases.length?"（别名："+t.aliases.join("、")+"）":"")).join("\n")||"词表为空，AI将提出新标签备选"}</pre></details><button type="button" className="primary" disabled={busy||working} onClick={()=>void run(async()=>setJob(await api.bankTopicConfirm(token,paperId,job.preview_id!)))}>确认发送并AI归类</button><button type="button" className="secondary" disabled={working} onClick={()=>setJob(null)}>暂不发送</button></section>}
 {job&&["FAILED","STALE","EXPIRED"].includes(job.status)&&<p role="alert">{job.error||"题目/标签已变化或预览已过期，请重新预览"}；不会自动重发。</p>}{job?.status==="SUCCEEDED"&&<div><p role="status">AI归类完成，请在每题中选用推荐并保存。</p><button type="button" className="secondary" disabled={busy||working} onClick={()=>void run(async()=>callback.current())}>载入AI建议（请先保存草稿）</button></div>}{error&&<p role="alert" className="course-conflict">{error}</p>}
 </div>;
}
