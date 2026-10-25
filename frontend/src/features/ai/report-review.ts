import {labelSourceText} from "./ReportLabelSource";
import type {StudyReport} from "../../api/client";

export type ReviewLabel = Pick<StudyReport["topics"][number]["labels"][number], "kind" | "reason">;
export type ReportReview = {report:StudyReport; labels:ReviewLabel[][]; scope?:"topic"};
export const labelNames = {key:"重点", difficult:"难点", exam:"考点建议"};

export function beginReportReview(report:StudyReport):ReportReview {
  const snapshot = structuredClone(report);
  return {report:snapshot, labels:snapshot.topics.map(topic=>Array.from(new Map(topic.labels.map(({kind,reason})=>[kind,{kind,reason}])).values()))};
}

export function beginTopicReview(report:StudyReport, topicId:string):ReportReview {
  const matches=report.topics.filter(topic=>topic.topic_id===topicId);
  if(matches.length!==1)throw new Error("无法唯一定位这个知识点，请重新打开报告核对。");
  const topic=structuredClone(matches[0]);
  if(!topic.citations.length)throw new Error("这个知识点没有可验证引用，暂不能整理为有来源笔记。");
  if(topic.citations.some(source=>source.availability!=="active"))throw new Error("这个知识点含失效来源，请核对原文后再整理。");
  const sources=Array.from(new Map(topic.citations.map(source=>[JSON.stringify([source.version_id,source.chunk_id,source.quote]),source])).values());
  if(sources.length>50)throw new Error("这个知识点超过单篇笔记50处引用限制，不能截断来源保存。");
  topic.citations=sources;
  const review=beginReportReview({...report,summary:"",topics:[topic],citations:sources,learning_goals:[],prerequisites:[],learning_sequence:[],examples:[],self_checks:[],review_suggestions:[]});
  return {...review,scope:"topic"};
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
  const topicOnly=review.scope==="topic";
  const lines = [topicOnly?`# ${report.topics[0].name}（AI辅助知识点摘记，待核实）`:"# 章节学习报告（AI辅助草稿，待核实）",
    topicOnly?"本篇仅摘取所选知识点，不包含原报告其他知识点、例题、自测或全文学习安排。":report.summary,...(report.validation_notices||[]).map(notice=>`> ${notice}`),
    "标签由用户整理，不代表教师要求、真题统计或报告全文已核实。"];
  if(!topicOnly)for (const [items,title] of [[report.learning_goals,"学习目标"],[report.prerequisites,"前置知识"],[report.learning_sequence,"建议学习顺序"]] as const)
    lines.push(`## ${title}`, ...(items.length?items.map(item=>`- ${item}`):["资料未明确要求前置知识。"]));
  report.topics.forEach((topic,index)=>{
    lines.push(`## ${topic.name}`,topic.explanation,"### 原始AI建议及来源标签（保留供核对）",
      ...topic.labels.flatMap(label=>[`- ${labelNames[label.kind]}（${labelSourceText(label)}）：${label.reason}`,...(label.notice?[label.notice]:[]),...(label.evidence||[]).map(e=>e.quote?`本人记录原文：${e.quote}`:`真题依据：${e.paper_title} · ${e.year??"年份未知"} · 题目ID ${e.question_id}`)]),
      "### 我的标签整理（用户编辑，待核实）",
      ...(labels[index].length?labels[index].map(label=>`- ${labelNames[label.kind]}：${label.reason.trim()}`):["未保留标签。"]),
      ...topic.misconceptions.map(item=>`- 易错点：${item}`));
    if(topic.concept_group)lines.push(`学习分层（AI建议）：${topic.concept_group}`);
    for(const relation of topic.related_concepts||[])lines.push(`- 与${relation.target}的关系：${relation.relation}`);
    if(topic.breakthrough_steps?.length)lines.push("### 难点突破步骤（AI建议）",...topic.breakthrough_steps.map((step,i)=>`${i+1}. ${step}`));
    for (const citation of topic.citations)
      lines.push(`依据摘录（${citation.locator?.value||"原文"}）：`,...citation.quote.split("\n").map(line=>`> ${line}`));
  });
  if(!topicOnly)for (const [items,title] of [[report.examples,"例题"],[report.self_checks,"自测"]] as const) {
    lines.push(`## ${title}`);
    items.forEach((exercise,index)=>lines.push(`### ${index+1}. ${exercise.question}`,`答案说明：${exercise.answer}`));
  }
  if(!topicOnly&&report.review_suggestions?.length)lines.push("## 复习建议（AI建议）",...report.review_suggestions.map(item=>`- ${item}`));
  return lines.join("\n\n");
}
