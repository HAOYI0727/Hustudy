import { FormEvent, useEffect, useState } from "react";
import { api, AIAnswer, SourceCitation } from "../../api/client";
import { PageTitle, Status, EmptyInline, EmptyState, ModuleStats } from "../../components/workspace";
import { AIAnswerPreview } from "./AIAnswerPreview";
import { RealQueries } from "./RealQueries";

type Props = {onSource: (versionId: string, chunkId: string) => void; token: string; courseId: string; onNotice: (s: string) => void; onError: (e: unknown) => void};

export function AIStudy({token, courseId, onNotice, onError, onSource}: Props) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<AIAnswer | null>(null);
  const [mode, setMode] = useState<"demo" | "real">("demo");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [draftText, setDraftText] = useState("");
  const [draftSources, setDraftSources] = useState<SourceCitation[]>([]);
  const [savingDraft, setSavingDraft] = useState(false);
  useEffect(() => {
    const guard = (event: Event) => {if (savingDraft || loading || (draftText && !window.confirm("AI草稿尚未保存，放弃修改并离开？"))) event.preventDefault();};
    const unload = (event: BeforeUnloadEvent) => {if (draftText || savingDraft) {event.preventDefault(); event.returnValue = "";}};
    window.addEventListener("hustudy:before-navigate", guard); window.addEventListener("beforeunload", unload);
    return () => {window.removeEventListener("hustudy:before-navigate", guard); window.removeEventListener("beforeunload", unload);};
  }, [draftText, savingDraft, loading]);
  const saveDraft = async () => {
    if (savingDraft || !draftText.trim()) return;
    setSavingDraft(true);
    try {
      await api.createNote(token, {title: "AI 学习草稿（待核实）", content: draftText, course_id: courseId,
        citations: draftSources.map(c => ({version_id: c.version_id, chunk_id: c.chunk_id, quote: c.quote}))});
      setDraftText(""); setDraftSources([]); onNotice("已保存为待核实笔记，请继续核对内容与来源");
    } catch (error) {onError(error);} finally {setSavingDraft(false);}
  };
  const makeDraft = () => {
    if (!answer || (draftText && !window.confirm("已有未保存草稿，替换为这条AI结果？"))) return;
    setDraftSources(answer.result.citations || []);
    setDraftText(`## AI 辅助内容 · 待核实\n\n模型：${answer.model_mode === "real" ? answer.result.model || "真实AI" : "演示检索"}\n\n${answer.result.answer || ""}\n\n## 待核对摘录\n${answer.result.citations?.map(c => "> " + c.quote).join("\n\n") || ""}`);
  };
  const ask = async (event: FormEvent) => {
    event.preventDefault(); if (loading || !query.trim()) return;
    setLoading(true);
    try {setAnswer(await api.aiQuery(token, courseId, query.trim())); setHistory(rows => [query, ...rows.filter(row => row !== query)].slice(0, 6)); onNotice("已展示演示检索原文，不是大模型讲解");}
    catch (error) {onError(error);} finally {setLoading(false);}
  };
  return <div className="page">
    <PageTitle eyebrow="AI STUDY" title="带着问题学习，带着证据理解" text="演示检索留在本地；真实AI先核对发送范围，结果带引用并由你审阅。"/>
    <ModuleStats items={[{label: "本页模式", value: mode === "real" ? "真实AI" : "演示", hint: mode === "real" ? "每次预览并确认" : "不发送远程资料"},
      {label: "演示会话", value: history.length, hint: "最近提问，仅当前页面保留"}, {label: "当前结果引用", value: answer?.result.citations?.length || 0, hint: "原文校验不等于解释正确"}]}/>
    <div className="ai-mode-tabs" role="group" aria-label="AI模式">
      <button className={mode === "demo" ? "primary" : "secondary"} aria-pressed={mode === "demo"} disabled={loading} onClick={() => setMode("demo")}>本地演示检索</button>
      <button className={mode === "real" ? "primary" : "secondary"} aria-pressed={mode === "real"} disabled={loading} onClick={() => setMode("real")}>智谱真实AI · 需确认</button>
    </div>
    <div className="ai-grid">
      {mode === "real" ? <RealQueries token={token} courseId={courseId} onAnswer={setAnswer} onNotice={onNotice} onError={onError} onSource={onSource}/> :
        <section className="panel ai-prompt">
          <div className="mode-card"><span className="sparkle">✦</span><div><strong>演示检索</strong><p>展示匹配原文，不执行真实模型推理。</p></div></div>
          <div className="prompt-presets"><p className="hint">选择方向，再补充课程概念</p>{["请解释这个概念：", "这两个概念有什么区别：", "请从原文查找以下知识点："].map(text => <button className="secondary" key={text} onClick={() => setQuery(text)}>{text.replace(/：$/, "")}</button>)}</div>
          <form onSubmit={ask}><label>向这门课程提问<textarea maxLength={2000} rows={6} value={query} disabled={loading} onChange={e => setQuery(e.target.value)} placeholder="例如：拥塞控制和流量控制有什么区别？" required/></label><button className="primary full" disabled={loading || !query.trim()}>{loading ? "正在检索…" : "查看匹配原文"}</button></form>
          {history.length > 0 && <div className="session-history"><h4>最近提问</h4>{history.map(text => <button className="relation-link" key={text} onClick={() => setQuery(text)}>↺ {text}</button>)}</div>}
        </section>}
      <section className="panel ai-result">
        <div className="panel-title"><h3>学习结果</h3>{answer && <Status value={answer.status}/>}</div>
        {answer ? <>
          <div className="answer-box"><small>{answer.model_mode === "real" ? "真实AI · 待核实" : "演示检索 · 原文展示"}</small>
            <AIAnswerPreview content={answer.result.answer || answer.result.message || ""}/>
            <small>{answer.result.model_notice || "结果需人工审阅"}</small>
          </div>
          {answer.status === "grounded" && <button className="secondary" onClick={makeDraft}>整理为可编辑笔记草稿</button>}
          <h4>来源引用</h4>
          {answer.result.citations?.map((c, index) => <details className="citation-card" open key={`${c.chunk_id}-${index}`}><summary className="locator">{c.source_kind === "manual_transcript" ? "人工补录 · " : ""}定位 {c.locator?.value} · 展开/收起证据</summary><p>{c.quote}</p><button className="secondary" disabled={c.availability === "unavailable"} onClick={() => onSource(c.version_id, c.chunk_id)}>{c.availability === "unavailable" ? "来源已失效" : "回到原文 ↗"}</button></details>)}
          {!answer.result.citations?.length && <EmptyInline text="暂无可验证来源，请补充资料或查看异常原因"/>}
        </> : <EmptyState icon="ai" title="从一个问题开始" text="结果区分有来源回答、证据不足和模型异常，不会把失败伪装成成功。"/>}
      </section>
    </div>
    {draftText && <section className="panel ai-draft"><h3>审阅笔记草稿</h3><p className="hint">可修改后保存；引用固定为创建这份草稿时的来源，不随新问题替换。</p><textarea aria-label="AI 笔记草稿" rows={10} value={draftText} disabled={savingDraft} onChange={e => setDraftText(e.target.value)}/><div className="editor-footer"><button className="secondary" disabled={savingDraft} onClick={() => {setDraftText(""); setDraftSources([]);}}>取消</button><button className="primary" disabled={savingDraft || !draftText.trim()} onClick={() => void saveDraft()}>{savingDraft ? "保存中…" : "确认保存为笔记草稿"}</button></div></section>}
  </div>;
}
