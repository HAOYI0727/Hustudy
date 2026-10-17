import {SourceCitation, StudyReport} from "../../api/client";
import {AIAnswerPreview} from "./AIAnswerPreview";
import "./study-reports.css";

type Props = {report:StudyReport;onSource:(versionId:string,chunkId:string)=>void};

export function StudyReportView({report,onSource}:Props) {
  const citations = (sources:SourceCitation[]) => <div className="report-sources">{sources.map((c,i)=><button className="secondary" key={`${c.chunk_id}-${i}`} disabled={c.availability !== "active"} title={c.quote} onClick={()=>onSource(c.version_id,c.chunk_id)}>{c.availability === "active" ? `依据 ${i+1} · ${c.locator?.value}` : "来源已失效"}</button>)}</div>;
  return <article className="study-report" aria-label="章节学习报告">
    <p className="eyebrow">LEARN · EXPLAIN · CHECK</p><h3>章节学习报告</h3>
    <AIAnswerPreview content={report.summary}/>
    {report.validation_notices?.map((notice,i)=><p className="hint" role="status" key={i}>{notice}</p>)}
    <section className="report-section"><h4>本次学习目标</h4><ul>{report.learning_goals.map((v,i)=><li key={i}>{v}</li>)}</ul></section>
    <section className="report-section"><h4>前置知识</h4>{report.prerequisites.length ? <ul>{report.prerequisites.map((v,i)=><li key={i}>{v}</li>)}</ul> : <p className="hint">资料未明确要求前置知识。</p>}<h4>建议学习顺序</h4><ol>{report.learning_sequence.map((v,i)=><li key={i}>{v}</li>)}</ol></section>
    {report.topics.some(topic=>topic.concept_group)&&<section className="report-section"><h4>知识点分层目录 · AI建议</h4>
      {[...new Set(report.topics.map(topic=>topic.concept_group||"未分层"))].map(group=><div key={group}><h5>{group}</h5><ul>{report.topics.filter(topic=>(topic.concept_group||"未分层")===group).map(topic=><li key={topic.topic_id}>{topic.name}</li>)}</ul></div>)}
    </section>}
    {report.topics.map(topic=><section className="report-section" key={topic.topic_id}><h4>{topic.name}</h4><AIAnswerPreview content={topic.explanation}/>{topic.labels.map((label,i)=><p className={`report-label report-label-${label.kind}`} key={i}><strong>{{key:"重点",difficult:"难点",exam:"考点建议"}[label.kind]} · AI建议</strong><br/>{label.reason}</p>)}{topic.misconceptions.length > 0 && <><h5>容易混淆的地方</h5><ul>{topic.misconceptions.map((v,i)=><li key={i}>{v}</li>)}</ul></>}{citations(topic.citations)}</section>)}
    {report.topics.some(topic=>topic.related_concepts?.length||topic.breakthrough_steps?.length)&&<section className="report-section"><h4>概念关系与难点突破 · AI建议</h4>{report.topics.filter(topic=>topic.related_concepts?.length||topic.breakthrough_steps?.length).map(topic=><div key={topic.topic_id}><h5>{topic.name}</h5>
      {topic.related_concepts?.map((relation,i)=><p key={i}>{topic.name} → {relation.target}：{relation.relation}</p>)}
      {Boolean(topic.breakthrough_steps?.length)&&<ol>{topic.breakthrough_steps!.map((step,i)=><li key={i}>{step}</li>)}</ol>}{citations(topic.citations)}
    </div>)}</section>}
    <section className="report-section"><h4>用例题理解</h4>{report.examples.map((exercise,i)=><div key={i}><AIAnswerPreview content={exercise.question}/><AIAnswerPreview content={exercise.answer}/>{citations(exercise.citations)}</div>)}</section>
    <section className="report-section"><h4>先自测，再展开答案</h4>{report.self_checks.map((exercise,i)=><div className="report-exercise" key={i}>{exercise.generation_origin==="rule_generated"&&<p className="hint">基础自测 · 根据已校验知识点或例题生成</p>}<AIAnswerPreview content={`${i+1}. ${exercise.question}`}/><details><summary>查看答案与依据</summary><AIAnswerPreview content={exercise.answer}/>{citations(exercise.citations)}</details></div>)}</section>
    {Boolean(report.review_suggestions?.length)&&<section className="report-section"><h4>复习建议 · AI建议</h4><ul>{report.review_suggestions!.map((item,i)=><li key={i}>{item}</li>)}</ul></section>}
  </article>;
}
