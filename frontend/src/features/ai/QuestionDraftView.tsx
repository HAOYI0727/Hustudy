import {AIAnswer} from "../../api/client";
import {AIAnswerPreview} from "./AIAnswerPreview";

export function QuestionDraftView({answer,onSource}:{answer:AIAnswer;onSource:(version:string,chunk:string)=>void}){
  const result=answer.result;
  const stale=result.dependency_status==="stale"||result.citations?.some(c=>c.availability!=="active");
  const download=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(answer,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`question-drafts-${answer.id}.json`;a.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);};
  return <article className="study-report" aria-label="题目候选草稿"><p className="eyebrow">QUESTION DRAFTS · REVIEW REQUIRED</p><h3>题目候选 · 待人工审阅</h3><p className="hint">{result.mode_notice}</p><p className="hint">候选尚未进入正式试卷，请先审阅题目、参考答案和知识依据。</p>{stale&&<p role="alert" className="course-conflict">材料、Topic或参考原题已失效/变化，请重新生成后再使用。</p>}
    {result.question_drafts?.map((q,i)=><section className="report-section" key={q.question_id}><h4>第{i+1}题 · {{single_choice:"单选",boolean:"判断",short_answer:"简答"}[q.type]} · {q.points}分</h4><AIAnswerPreview content={q.stem}/>{q.options.map(o=><p key={o.id}><strong>{o.id}.</strong> {o.text}</p>)}<details><summary>查看参考答案与评分细则</summary><AIAnswerPreview content={q.answer===null?"按评分细则审阅":typeof q.answer==="boolean"?(q.answer?"正确":"错误"):q.answer}/>{q.rubric.map((r,j)=><p key={j}>{r.criterion} · {r.points}分</p>)}<AIAnswerPreview content={q.explanation}/></details><div className="report-sources">{q.material_citations.map((c,j)=><button className="secondary" key={j} disabled={c.availability!=="active"} title={c.quote} onClick={()=>onSource(c.version_id,c.chunk_id)}>知识依据 {j+1} · {c.locator?.value}</button>)}</div><p className="hint">设计参考：{q.original_past_question_ids.length?q.original_past_question_ids.map(id=>result.exam_context?.references.find(r=>r.id===id)?.title||id).join("、"):"无真题参考"}</p></section>)}
    <button className="secondary" disabled={stale} onClick={download}>导出题目草稿（JSON）</button><p className="hint">此文件包含参考答案，适合审阅与导入，不用于模拟作答。</p>
  </article>;
}
