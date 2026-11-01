import {useEffect, useRef, useState} from "react";
import {api, type AIAnswer, type RelatedAnswer} from "../../api/client";
import {AIAnswerPreview} from "./AIAnswerPreview";

type Props = {
  token:string; queryId:string; currentQuestion:string; candidates:RelatedAnswer[];
  kind?:"qa"|"study_report";
  disabled:boolean; onBusyChange:(busy:boolean)=>void; onAdopt:(answer:AIAnswer)=>void;
};

export function RelatedAnswers(props:Props) {
  const {token,queryId,currentQuestion,candidates,disabled,onBusyChange,onAdopt}=props;
  const report=props.kind==="study_report", subject=report?"学习目标":"问题", resultName=report?"报告":"答案", historyName=report?"报告":"问答";
  const [opened,setOpened]=useState<AIAnswer|null>(null);
  const [confirmed,setConfirmed]=useState(false);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);
  const epoch=useRef(0);
  const pending=useRef<AbortController|null>(null);
  const callbacks=useRef({onBusyChange,onAdopt});
  callbacks.current={onBusyChange,onAdopt};
  useEffect(()=>{
    epoch.current++;setOpened(null);setConfirmed(false);setError("");setLoading(false);
    return()=>{epoch.current++;if(pending.current){pending.current.abort();pending.current=null;callbacks.current.onBusyChange(false);}};
  },[token,queryId]);

  const perform=async(id:string,adopt=false)=>{
    if(disabled||pending.current||(adopt&&!confirmed))return;
    const generation=epoch.current, controller=new AbortController();
    pending.current=controller;setLoading(true);setError("");callbacks.current.onBusyChange(true);
    if(!adopt){setOpened(null);setConfirmed(false);}
    try {
      const answer=adopt
        ?await api.reuseRelatedAnswer(token,queryId,id,controller.signal)
        :await api.relatedRemoteAnswer(token,queryId,id,controller.signal);
      if(epoch.current!==generation||controller.signal.aborted)return;
      if(adopt)callbacks.current.onAdopt(answer);
      else setOpened(answer);
    } catch(reason) {
      if(epoch.current===generation&&!controller.signal.aborted){
        setOpened(null);setConfirmed(false);
        setError(reason instanceof Error?reason.message:"历史结果暂时无法读取，请重新预览");
      }
    } finally {
      if(epoch.current===generation){pending.current=null;setLoading(false);callbacks.current.onBusyChange(false);}
    }
  };

  return <section className="ai-privacy-card related-answers" aria-label={`相近历史${historyName}`}>
    <strong>找到可能相关的历史{historyName}</strong>
    <p>以下按文字相近程度推荐，可能与本次{subject}要求不同。请查看原{subject}和原{resultName}后自行判断，也可继续在下方确认生成新{resultName}。</p>
    <p><strong>本次{subject}：</strong>{currentQuestion}</p>
    {candidates.map(item=><article key={item.id}>
      <p><strong>原{subject}：</strong>{item.query}</p>
      <p className="related-answer-summary">{item.answer_preview}</p>
      <p className="hint">{item.model} · {new Date(item.created_at).toLocaleString()}</p>
      <button type="button" className="secondary" disabled={disabled||loading} onClick={()=>void perform(item.id)}>查看原{resultName}</button>
      {opened?.id===item.id&&<div className="related-answer-detail">
        <p><strong>历史原{resultName}（未重新生成）</strong></p>
        <AIAnswerPreview content={opened.result.answer||""}/>
        <p className="hint">原{resultName}含{opened.result.citations?.length||0}条来源引用；使用后可在学习结果中查看并回到原文。</p>
        <label><input type="checkbox" checked={confirmed} disabled={disabled||loading} onChange={event=>setConfirmed(event.target.checked)}/>我已对照原{subject}和原{resultName}，确认适用于本次{subject}</label>
        <button type="button" className="primary" disabled={disabled||loading||!confirmed} onClick={()=>void perform(item.id,true)}>确认使用这{report?"份":"条"}历史{resultName}（不调用AI）</button>
      </div>}
    </article>)}
    {loading&&<p role="status">正在核对历史{historyName}与资料状态…</p>}
    {error&&<p role="alert" className="course-conflict">{error}</p>}
  </section>;
}
