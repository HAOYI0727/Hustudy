import {useEffect,useRef,useState} from "react";
import {SourceCitation, StudyReport} from "../../api/client";
import {AIAnswerPreview} from "./AIAnswerPreview";
import "./study-reports.css";
import {ReadingTopicMap} from "./ReadingTopicMap";

type Props = {report:StudyReport;onSource:(versionId:string,chunkId:string)=>void;onTopicDraft?:(topicId:string)=>void;draftDisabled?:boolean;readingVersionId?:string;currentReadingPage?:number|null};

export function StudyReportView({report,onSource,onTopicDraft,draftDisabled=false,readingVersionId,currentReadingPage}:Props) {
  const [topicId,setTopicId]=useState(report.topics[0]?.topic_id||""),[focusSerial,setFocusSerial]=useState(0);
  const detailRef=useRef<HTMLElement>(null),focusRequested=useRef(false);
  const selectedIndex=Math.max(0,report.topics.findIndex(topic=>topic.topic_id===topicId));
  const selected=report.topics[selectedIndex];
  const showTopic=(id:string)=>{if(!report.topics.some(topic=>topic.topic_id===id))return;focusRequested.current=true;setTopicId(id);setFocusSerial(value=>value+1);};
  useEffect(()=>{if(!focusRequested.current||!detailRef.current)return;focusRequested.current=false;detailRef.current.focus({preventScroll:true});detailRef.current.scrollIntoView({block:"nearest"});},[selected?.topic_id,focusSerial,readingVersionId]);
  const topics=readingVersionId?(selected?[selected]:[]):report.topics;
  const directoryKey=readingVersionId+"|"+report.topics.map(topic=>topic.topic_id).join("|");
  const citations = (sources:SourceCitation[]) => <div className="report-sources">{sources.map((c,i)=><button className="secondary" key={`${c.chunk_id}-${i}`} disabled={c.availability !== "active"} title={c.quote} onClick={()=>onSource(c.version_id,c.chunk_id)}>{c.availability === "active" ? `依据 ${i+1} · ${c.locator?.value}` : "来源已失效"}</button>)}</div>;
  return <article className="study-report" aria-label={readingVersionId?"课件知识点总结":"章节学习报告"}>
    <p className="eyebrow">LEARN · EXPLAIN · CHECK</p><h3>{readingVersionId?"课件知识点总结":"章节学习报告"}</h3>
    <AIAnswerPreview content={report.summary}/>
    {readingVersionId&&<ReadingTopicMap key={directoryKey} report={report} versionId={readingVersionId} currentPage={currentReadingPage} onRead={showTopic} onSource={onSource} onDraft={onTopicDraft} disabled={draftDisabled}/>}
    {report.validation_notices?.map((notice,i)=><p className="hint" role="status" key={i}>{notice}</p>)}
    <section className="report-section"><h4>本次学习目标</h4><ul>{report.learning_goals.map((v,i)=><li key={i}>{v}</li>)}</ul></section>
    <section className="report-section"><h4>前置知识</h4>{report.prerequisites.length ? <ul>{report.prerequisites.map((v,i)=><li key={i}>{v}</li>)}</ul> : <p className="hint">资料未明确要求前置知识。</p>}<h4>建议学习顺序</h4><ol>{report.learning_sequence.map((v,i)=><li key={i}>{v}</li>)}</ol></section>
    {!readingVersionId&&report.topics.some(topic=>topic.concept_group)&&<section className="report-section"><h4>知识点分层目录 · AI建议</h4>
      {[...new Set(report.topics.map(topic=>topic.concept_group||"未分层"))].map(group=><div key={group}><h5>{group}</h5><ul>{report.topics.filter(topic=>(topic.concept_group||"未分层")===group).map(topic=><li key={topic.topic_id}>{topic.name}</li>)}</ul></div>)}
    </section>}
    {topics.map(topic=><section className="report-section" key={topic.topic_id} ref={readingVersionId?detailRef:undefined} tabIndex={readingVersionId?-1:undefined} aria-label={readingVersionId?`知识点讲解：${topic.name}`:undefined}>{readingVersionId&&<nav className="reading-topic-detail-nav" aria-label="知识点讲解切换"><button className="secondary" disabled={selectedIndex===0} onClick={()=>showTopic(report.topics[selectedIndex-1].topic_id)}>上一个知识点</button><span>{selectedIndex+1} / {report.topics.length}</span><button className="secondary" disabled={selectedIndex+1>=report.topics.length} onClick={()=>showTopic(report.topics[selectedIndex+1].topic_id)}>下一个知识点</button></nav>}<h4>{topic.name}</h4><AIAnswerPreview content={topic.explanation}/>{topic.labels.map((label,i)=><p className={`report-label report-label-${label.kind}`} key={i}><strong>{{key:"重点",difficult:"难点",exam:"考点建议"}[label.kind]} · AI建议</strong><br/>{label.reason}</p>)}{topic.misconceptions.length > 0 && <><h5>容易混淆的地方</h5><ul>{topic.misconceptions.map((v,i)=><li key={i}>{v}</li>)}</ul></>}{citations(topic.citations)}{onTopicDraft&&<button className="secondary report-topic-note" aria-label={`将${topic.name}整理为笔记`} disabled={draftDisabled} onClick={()=>onTopicDraft(topic.topic_id)}>整理此知识点为笔记</button>}</section>)}
    {topics.some(topic=>topic.related_concepts?.length||topic.breakthrough_steps?.length)&&<section className="report-section"><h4>概念关系与难点突破 · AI建议</h4>{topics.filter(topic=>topic.related_concepts?.length||topic.breakthrough_steps?.length).map(topic=><div key={topic.topic_id}><h5>{topic.name}</h5>
      {topic.related_concepts?.map((relation,i)=><p key={i}>{topic.name} → {relation.target}：{relation.relation}</p>)}
      {Boolean(topic.breakthrough_steps?.length)&&<ol>{topic.breakthrough_steps!.map((step,i)=><li key={i}>{step}</li>)}</ol>}{citations(topic.citations)}
    </div>)}</section>}
    <section className="report-section"><h4>用例题理解</h4>{report.examples.map((exercise,i)=><div key={i}><AIAnswerPreview content={exercise.question}/><AIAnswerPreview content={exercise.answer}/>{citations(exercise.citations)}</div>)}</section>
    <section className="report-section"><h4>先自测，再展开答案</h4>{report.self_checks.map((exercise,i)=><div className="report-exercise" key={i}>{exercise.generation_origin==="rule_generated"&&<p className="hint">基础自测 · 根据已校验知识点或例题生成</p>}<AIAnswerPreview content={`${i+1}. ${exercise.question}`}/><details><summary>查看答案与依据</summary><AIAnswerPreview content={exercise.answer}/>{citations(exercise.citations)}</details></div>)}</section>
    {Boolean(report.review_suggestions?.length)&&<section className="report-section"><h4>复习建议 · AI建议</h4><ul>{report.review_suggestions!.map((item,i)=><li key={i}>{item}</li>)}</ul></section>}
  </article>;
}
