import type {StudyReport} from "../../api/client";

export type ReviewLabel = Pick<StudyReport["topics"][number]["labels"][number], "kind" | "reason">;
export type ReportReview = {report:StudyReport; labels:ReviewLabel[][]};
export const labelNames = {key:"重点", difficult:"难点", exam:"考点建议"};

export function beginReportReview(report:StudyReport):ReportReview {
  const snapshot = structuredClone(report);
  return {report:snapshot, labels:snapshot.topics.map(topic=>topic.labels.map(({kind,reason})=>({kind,reason})))};
}

export function reviewError(review:ReportReview):string {
  for (const [index, labels] of review.labels.entries()) {
    if (labels.length>3 || new Set(labels.map(label=>label.kind)).size!==labels.length)
      return `「${review.report.topics[index].name}」的标签类型不能重复，最多保留三项。`;
    if (labels.some(label=>!label.reason.trim() || label.reason.trim().length>1000))
      return `请为「${review.report.topics[index].name}」的每个标签填写1–1000字的理由。`;
  }
  return "";
}

export function reviewedReportMarkdown(review:ReportReview):string {
  if (reviewError(review)) throw new Error(reviewError(review));
  const {report,labels} = review;
  const lines = ["# 章节学习报告（AI辅助草稿，待核实）",report.summary,...(report.validation_notices||[]).map(notice=>`> ${notice}`),
    "标签由用户整理，不代表教师要求、真题统计或报告全文已核实。"];
  for (const [items,title] of [[report.learning_goals,"学习目标"],[report.prerequisites,"前置知识"],[report.learning_sequence,"建议学习顺序"]] as const)
    lines.push(`## ${title}`, ...(items.length?items.map(item=>`- ${item}`):["资料未明确要求前置知识。"]));
  report.topics.forEach((topic,index)=>{
    lines.push(`## ${topic.name}`,topic.explanation,"### 原始AI建议（保留供核对）",
      ...topic.labels.map(label=>`- ${labelNames[label.kind]}（AI建议）：${label.reason}`),
      "### 我的标签整理（用户编辑，待核实）",
      ...(labels[index].length?labels[index].map(label=>`- ${labelNames[label.kind]}：${label.reason.trim()}`):["未保留标签。"]),
      ...topic.misconceptions.map(item=>`- 易错点：${item}`));
    if(topic.concept_group)lines.push(`学习分层（AI建议）：${topic.concept_group}`);
    for(const relation of topic.related_concepts||[])lines.push(`- 与${relation.target}的关系：${relation.relation}`);
    if(topic.breakthrough_steps?.length)lines.push("### 难点突破步骤（AI建议）",...topic.breakthrough_steps.map((step,i)=>`${i+1}. ${step}`));
    for (const citation of topic.citations)
      lines.push(`依据摘录（${citation.locator?.value||"原文"}）：`,...citation.quote.split("\n").map(line=>`> ${line}`));
  });
  for (const [items,title] of [[report.examples,"例题"],[report.self_checks,"自测"]] as const) {
    lines.push(`## ${title}`);
    items.forEach((exercise,index)=>lines.push(`### ${index+1}. ${exercise.question}`,`答案说明：${exercise.answer}`));
  }
  if(report.review_suggestions?.length)lines.push("## 复习建议（AI建议）",...report.review_suggestions.map(item=>`- ${item}`));
  return lines.join("\n\n");
}
