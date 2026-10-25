import type {ReportLabel} from "../../api/client";

export const labelOrigins={ai_suggestion:"AI建议",teacher_mark:"教师强调",observed_exam:"已确认真题"};
export function labelSourceText(label:ReportLabel){
  return `${labelOrigins[label.origin]}${label.availability==="unavailable"?"（依据已失效）":""}`;
}
export function ReportLabelSource({label}:{label:ReportLabel}){
  return <div className={`report-label report-label-${label.kind}`}><strong>{{key:"重点",difficult:"难点",exam:label.origin==="ai_suggestion"?"考点建议":"考点"}[label.kind]} · {labelSourceText(label)}</strong><p>{label.reason}</p>
    {label.notice&&<p className="hint">{label.notice}</p>}
    {Boolean(label.evidence?.length)&&<details><summary>查看标签依据</summary>{label.evidence!.map((e,i)=><p key={i}>{label.origin==="teacher_mark"?`本人记录：${e.reason}；原文：${e.quote}`:`${e.paper_title} · ${e.year??"年份未知"} · ${e.topic_name} · 题目ID：${e.question_id}`}</p>)}</details>}
  </div>;
}
