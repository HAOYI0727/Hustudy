import { FormEvent, useEffect, useRef, useState } from "react";
import { api, AIAnswer, SourceCitation } from "../../api/client";
import { PageTitle, EmptyInline, EmptyState, ModuleStats } from "../../components/workspace";
import { AIResultStatus } from "./AIResultStatus";
import { AIAnswerPreview } from "./AIAnswerPreview";
import { RealQueries } from "./RealQueries";
import { StudyReportView } from "./StudyReportView";
import {QuestionDraftView} from "./QuestionDraftView";
import {ReportLabelEditor} from "./ReportLabelEditor";
import {beginReportReview, reviewedReportMarkdown, ReportReview} from "./report-review";
import "./ai-workspace.css";
import {AIActivity} from "../../components/AIActivity";

type Props = {onSource: (versionId: string, chunkId: string) => void; token: string; courseId: string; onNotice: (s: string) => void; onError: (e: unknown) => void};

const modes = {
  demo: {name:"资料原文检索", description:"按关键词查找资料中的相关原文，不调用 AI。"},
  real: {name:"资料问答", description:"结合课程资料，向 AI 提问并查看来源。"},
  report: {name:"学习报告", description:"将所选资料整理为知识讲解、例题与自测。"},
};

export function AIStudy({token, courseId, onNotice, onError, onSource}: Props) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<AIAnswer | null>(null);
  useEffect(()=>{if(answer&&window.innerWidth<=1100)document.getElementById("ai-result")?.scrollIntoView({block:"start"});},[answer?.id]);
  const [mode, setMode] = useState<"demo" | "real" | "report">("demo");
  const [remoteBusy,setRemoteBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [draftText, setDraftText] = useState("");
  const [draftOpen,setDraftOpen] = useState(false);
  const [draftAttribution,setDraftAttribution] = useState("");
  const [draftSources, setDraftSources] = useState<SourceCitation[]>([]);
  const [draftReview, setDraftReview] = useState<ReportReview|null>(null);
  const [reviewingLabels,setReviewingLabels] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const draftPanel=useRef<HTMLElement>(null);
  useEffect(()=>{
    if(draftOpen){draftPanel.current?.focus({preventScroll:true});draftPanel.current?.scrollIntoView({block:"start"});}
  },[draftOpen,reviewingLabels]);
  useEffect(() => {
    const guard = (event: Event) => {if (savingDraft || loading || (draftOpen && !window.confirm("AI草稿尚未保存，放弃修改并离开？"))) event.preventDefault();};
    const unload = (event: BeforeUnloadEvent) => {if (draftOpen || savingDraft) {event.preventDefault(); event.returnValue = "";}};
    window.addEventListener("hustudy:before-navigate", guard); window.addEventListener("beforeunload", unload);
    return () => {window.removeEventListener("hustudy:before-navigate", guard); window.removeEventListener("beforeunload", unload);};
  }, [draftOpen, savingDraft, loading]);
  const discardDraft = () => {setDraftText("");setDraftSources([]);setDraftReview(null);setReviewingLabels(false);setDraftOpen(false);setDraftAttribution("");};
  const reportText = (review:ReportReview) => draftAttribution + "\n\n" + reviewedReportMarkdown(review);
  const saveDraft = async () => {
    if (savingDraft || reviewingLabels || !draftText.trim()) return;
    setSavingDraft(true);
    try {
      await api.createNote(token, {title: "AI 学习草稿（待核实）", content: draftText, course_id: courseId,
        citations: draftSources.map(c => ({version_id: c.version_id, chunk_id: c.chunk_id, quote: c.quote}))});
      discardDraft(); onNotice("已保存为待核实笔记，请继续核对内容与来源");
    } catch (error) {onError(error);} finally {setSavingDraft(false);}
  };
  const makeDraft = (section?:{title:string;report:NonNullable<AIAnswer["result"]["study_report"]>}) => {
    if (!answer || savingDraft || (draftOpen && !window.confirm("已有未保存草稿，替换为这条AI结果？"))) return;
    const selectedReport=section?.report||answer.result.study_report;
    const selectedSources=section?.report.citations||answer.result.citations||[];
    if(selectedSources.length>50){onNotice("这份报告超过单篇笔记的50处引用限制，请按报告部分分别整理笔记");return;}
    if (selectedSources.some(c=>c.availability !== "active")) {onNotice("报告含失效来源，请重新生成后再创建笔记草稿");return;}
    setDraftSources(structuredClone(selectedSources));
    setDraftOpen(true);
    setDraftAttribution(`AI辅助草稿 · 待核实\n\n原始结果：${answer.id}\n\n生成方式：${answer.model_mode === "real" ? answer.result.model || "真实AI" : "固定自制演示"}${answer.result.prompt_version ? `\n\n提示词版本：${answer.result.prompt_version}` : ""}`);
    if(selectedReport){
      const review=beginReportReview(selectedReport);
      setDraftReview(review);setReviewingLabels(true);setDraftText("");return;
    }
    setDraftReview(null);setReviewingLabels(false);
    setDraftText(`## AI 辅助内容 · 待核实\n\n模型：${answer.model_mode === "real" ? answer.result.model || "真实AI" : answer.result.study_report ? "固定自制报告演示" : "演示检索"}\n\n${answer.result.answer || ""}\n\n## 待核对摘录\n${answer.result.citations?.map(c => "> " + c.quote).join("\n\n") || ""}`);
  };
  const ask = async (event: FormEvent) => {
    event.preventDefault(); if (loading || !query.trim()) return;
    setLoading(true);
    try {setAnswer(await api.aiQuery(token, courseId, query.trim())); setHistory(rows => [query, ...rows.filter(row => row !== query)].slice(0, 6)); onNotice("已展示演示检索原文，不是大模型讲解");}
    catch (error) {onError(error);} finally {setLoading(false);}
  };
  return <div className="page">
    <PageTitle eyebrow="AI STUDY" title="带着问题学习，带着证据理解" text="查找课程原文，结合资料提问或整理学习报告。"/>
    <AIActivity/>
    <ModuleStats items={[{label: "本页模式", value: modes[mode].name, hint: mode !== "demo" ? "真实调用每次确认" : "不发送远程资料"},
      {label: "本地提问", value: history.length, hint: "最近提问，仅当前页面保留"}, {label: "当前结果引用", value: answer?.result.citations?.length || 0, hint: "原文校验不等于解释正确"}]}/>
    <div className="ai-mode-tabs" role="group" aria-label="AI模式">
      {(Object.keys(modes) as (keyof typeof modes)[]).map(key=><button key={key} className={mode === key ? "primary" : "secondary"} aria-pressed={mode === key} disabled={loading||remoteBusy} onClick={()=>{setMode(key);setAnswer(null);}}>{modes[key].name}</button>)}
    </div>
    <p className="hint" role="status">{modes[mode].description}</p>
    <div className="ai-workspace-nav"><a href="#ai-controls">设置与发送</a><a href="#ai-result">查看学习结果</a></div><div className="ai-grid ai-workspace-grid">
      {mode !== "demo" ? <RealQueries key={mode} task={mode === "report" ? "study_report" : "qa"} token={token} courseId={courseId} onBusyChange={setRemoteBusy} onAnswer={setAnswer} onNotice={onNotice} onError={onError} onSource={onSource}/> :
        <section className="panel ai-prompt">
          <div className="mode-card"><span className="sparkle">✦</span><div><strong>资料原文检索</strong><p>展示匹配原文，不执行真实模型推理。</p></div></div>
          <div className="prompt-presets"><p className="hint">选择方向，再补充课程概念</p>{["请解释这个概念：", "这两个概念有什么区别：", "请从原文查找以下知识点："].map(text => <button className="secondary" key={text} onClick={() => setQuery(text)}>{text.replace(/：$/, "")}</button>)}</div>
          <form onSubmit={ask}><label>向这门课程提问<textarea maxLength={2000} rows={6} value={query} disabled={loading} onChange={e => setQuery(e.target.value)} placeholder="例如：拥塞控制和流量控制有什么区别？" required/></label><button className="primary full" disabled={loading || !query.trim()}>{loading ? "正在检索…" : "查看匹配原文"}</button></form>
          {history.length > 0 && <div className="session-history"><h4>最近提问</h4>{history.map(text => <button className="relation-link" key={text} onClick={() => setQuery(text)}>↺ {text}</button>)}</div>}
        </section>}
      <section className="panel ai-result" id="ai-result" tabIndex={-1}>
        <div className="panel-title"><h3>学习结果</h3>{answer && <AIResultStatus status={answer.status} errorCode={answer.result.error_code}/>}</div>
        {answer ? <>
          <div className="answer-box"><small>{answer.model_mode === "real" ? "真实AI · 待核实" : answer.result.question_drafts||answer.result.study_report ? "固定自制演示 · 待审阅" : "演示检索 · 原文展示"}</small>
            {answer.status !== "grounded" && answer.result.study_report_sections?.length ? <p role="alert">{answer.result.message} 已完成部分保留如下；当前不是完整报告。</p> : null}
            {answer.result.study_report_sections?.length ? <div><p className="hint">按资料顺序分为{answer.result.study_report_sections.length}部分，各部分独立生成。</p>{answer.result.study_report_sections.map((section,i)=><details className="report-part" open={i===0} key={i}><summary>{section.title}</summary><StudyReportView report={section.report} onSource={onSource}/><button className="secondary" disabled={savingDraft} onClick={()=>makeDraft(section)}>将{section.title}整理为笔记</button></details>)}</div> : answer.result.question_drafts?.length ? <QuestionDraftView answer={answer} onSource={onSource}/> : answer.result.study_report ? <StudyReportView report={answer.result.study_report} onSource={onSource}/> : <AIAnswerPreview content={answer.result.answer || answer.result.message || ""}/>}
            {answer.status === "provider_error" && <p className="hint">{answer.result.provider_code&&`服务错误码：${answer.result.provider_code}。`}{answer.result.retry_after_seconds!=null&&`服务建议至少等待${answer.result.retry_after_seconds}秒。`}不会自动重发；请检查原因后重新预览并确认。</p>}
            {answer.result.coverage && <p className="hint">{answer.result.coverage.truncated ? "本结果仅覆盖部分所选原文。" : "本结果依据所选版本可用文本。"}{answer.result.coverage.notice}</p>}
            <small>{answer.status === "provider_error" && ["INVALID_CITATION", "INVALID_OUTPUT", "INVALID_JSON"].includes(answer.result.error_code||"") ? "模型已返回内容，但未通过结果校验；本次未生成可用结果" : answer.result.model_notice || "结果需人工审阅"}</small>
          </div>
          {answer.status === "grounded" && !answer.result.question_drafts && <button className="secondary" disabled={savingDraft} onClick={()=>makeDraft()}>整理为可编辑笔记草稿</button>}
          <h4>来源引用</h4>
          {answer.result.citations?.map((c, index) => <details className="citation-card" open key={`${c.chunk_id}-${index}`}><summary className="locator">{c.source_kind === "manual_transcript" ? "人工补录 · " : ""}定位 {c.locator?.value} · 展开/收起证据</summary><p>{c.quote}</p><button className="secondary" disabled={c.availability === "unavailable"} onClick={() => onSource(c.version_id, c.chunk_id)}>{c.availability === "unavailable" ? "来源已失效" : "回到原文 ↗"}</button></details>)}
          {!answer.result.citations?.length && <EmptyInline text="暂无可验证来源，请补充资料或查看异常原因"/>}
        </> : <EmptyState icon="ai" title="从一个问题开始" text="结果区分有来源回答、证据不足和模型异常，不会把失败伪装成成功。"/>}
      </section>
    </div>
    {draftOpen && <section className="panel ai-draft" ref={draftPanel} tabIndex={-1} aria-label="AI笔记草稿审阅">
      {draftReview&&reviewingLabels?<ReportLabelEditor value={draftReview} onChange={setDraftReview} onCancel={discardDraft} onContinue={()=>{setDraftText(reportText(draftReview));setReviewingLabels(false);}}/>:<>
        {draftReview&&<p className="eyebrow">2 / 2 · 编辑笔记正文</p>}<h3>审阅笔记草稿</h3><p className="hint">可修改后保存；引用固定为创建这份草稿时的来源，不随新问题替换。</p>
        <textarea aria-label="AI 笔记草稿" rows={10} value={draftText} disabled={savingDraft} onChange={e => setDraftText(e.target.value)}/>
        <div className="editor-footer">
          {draftReview&&<button className="secondary" disabled={savingDraft} onClick={()=>{if(draftText===reportText(draftReview)||window.confirm("返回标签审阅后会重新生成正文，放弃当前正文修改？"))setReviewingLabels(true);}}>返回标签审阅</button>}
          <button className="secondary" disabled={savingDraft} onClick={discardDraft}>取消</button><button className="primary" disabled={savingDraft || !draftText.trim()} onClick={() => void saveDraft()}>{savingDraft ? "保存中…" : "确认保存为笔记草稿"}</button>
        </div>
      </>}
    </section>}
  </div>;
}
