import { FormEvent, useEffect, useRef, useState } from "react";
import { api, AIAnswer, AIProvider, DocumentItem, RemoteQuery, CandidateOptions, CandidateContext } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Status } from "../../components/workspace";
import {ChunkPicker} from "./ChunkPicker";

type Props = {token: string; courseId: string; task?:"qa"|"study_report"|"question_drafts";onBusyChange?:(busy:boolean)=>void; onAnswer: (answer: AIAnswer) => void; onNotice: (s: string) => void; onError: (e: unknown) => void; onSource: (versionId: string, chunkId: string) => void};

export function RealQueries({token, courseId, task="qa", onBusyChange, onAnswer, onNotice, onError, onSource}: Props) {
  const isReport = task === "study_report";
  const isCandidate = task === "question_drafts";
  const [provider, setProvider] = useState<AIProvider | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [query, setQuery] = useState(isReport ? "理解所选资料，梳理知识点并完成自测" : isCandidate ? "依据所选资料生成练习候选题" : "");
  const [studyMode,setStudyMode] = useState("systematic");
  const [reports,setReports] = useState<AIAnswer[]>([]);
  const [versions, setVersions] = useState<string[]>([]);
  const [chunkIds,setChunkIds] = useState<string[]>([]);
  const [candidateContext,setCandidateContext]=useState<CandidateContext>({topics:[],references:[]});
  const [candidateConfig,setCandidateConfig]=useState<CandidateOptions>({chapter_id:"",topic_ids:[],type:"single_choice",count:1,points:"5",difficulty_label:"basic",mode:"historical",original_past_question_ids:[]});
  const [remote, setRemote] = useState<RemoteQuery | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const [reload, setReload] = useState(0);
  const alive = useRef(true);
  const resultId = useRef("");
  const callbacks = useRef({onAnswer, onNotice, onError});
  callbacks.current = {onAnswer, onNotice, onError};
  const storageKey = isReport ? `hustudy_study_report:${courseId}` : isCandidate ? `hustudy_question_drafts:${courseId}` : `hustudy_remote_query:${courseId}`;
  const chapterId=versions.includes(candidateConfig.chapter_id)?candidateConfig.chapter_id:versions[0]||"";
  const candidateOptions={...candidateConfig,chapter_id:chapterId};
  const candidateReady=versions.length>0&&candidateConfig.topic_ids.length>0&&(candidateConfig.mode!=="variant"||candidateConfig.original_past_question_ids.length>0);
  const pending = Boolean(remote?.job && ["QUEUED", "RUNNING"].includes(remote.job.status));
  useEffect(() => {onBusyChange?.(busy);return () => onBusyChange?.(false);},[busy,onBusyChange]);
  useEffect(() => {
    let active=true;
    const load=isReport?api.studyReports:isCandidate?api.questionDrafts:api.aiResults;
    void load(token,courseId).then(rows=>{if(active)setReports(rows);}).catch(e=>{if(active)callbacks.current.onError(e);});
    return ()=>{active=false;};
  },[token,courseId,isReport,isCandidate,remote?.result?.id,reload]);
  const accept = (value: RemoteQuery) => {
    setRemote(value);
    localStorage.setItem(storageKey, value.id);
    if (value.result && value.result.id !== resultId.current) {
      resultId.current = value.result.id; callbacks.current.onAnswer(value.result);
      callbacks.current.onNotice(value.result.status === "grounded" ? "真实AI结果已生成，请核对引用与解释" : "AI结果已返回，请查看证据或异常说明");
    }
  };
  useEffect(() => {
    alive.current = true;
    return () => {alive.current = false;};
  }, []);
  useEffect(() => {
    let active = true;
    setInitializing(true); setError("");
    void Promise.all([api.aiProvider(token), api.documents(token, courseId),isCandidate?api.candidateContext(token,courseId):Promise.resolve(null)]).then(async ([settings, docs,context]) => {
      if (!active) return;
      setProvider(settings); setDocuments(docs);
      if(context)setCandidateContext(context);
      const previous = localStorage.getItem(storageKey);
      if (previous) {
        try {const value = await api.remoteQuery(token, previous); if (active) {setQuery(value.query);if(value.report_scope){setVersions(value.report_scope.scope_version_ids);setChunkIds(value.report_scope.chunk_ids||[]);setStudyMode(value.report_scope.study_mode);}if(value.candidate_scope){setVersions(value.candidate_scope.request.version_ids);setChunkIds(value.candidate_scope.request.chunk_ids);setCandidateConfig(value.candidate_scope.request);} accept(value);}}
        catch {if (active) localStorage.removeItem(storageKey);}
      }
    }).catch(e => {if (active) {setError(e instanceof Error ? e.message : "加载失败"); callbacks.current.onError(e);}})
      .finally(() => {if (active) setInitializing(false);});
    return () => {active = false;};
  }, [token, courseId, reload]);
  useEffect(() => {
    if (!remote || remote.job) {setExpired(false); return;}
    const remaining = new Date(remote.expires_at).getTime() - Date.now();
    setExpired(remaining <= 0);
    const timer = window.setTimeout(() => setExpired(true), Math.max(0, remaining));
    return () => window.clearTimeout(timer);
  }, [remote]);
  useEffect(() => {
    if (!pending || !remote) return;
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      try {const value = await api.remoteQuery(token, remote.id); if (active) {accept(value); setError("");}}
      catch (e) {if (active) setError(e instanceof Error ? e.message : "暂时无法读取后台状态");}
      finally {if (active) timer = window.setTimeout(() => void poll(), 2000);}
    };
    timer = window.setTimeout(() => void poll(), 1000);
    return () => {active = false; window.clearTimeout(timer);};
  }, [token, remote?.id, pending]);
  useEffect(() => {
    const guard = (event: Event) => {if (busy) {event.preventDefault(); callbacks.current.onNotice("正在提交操作，请稍后再切换");}};
    window.addEventListener("hustudy:before-navigate", guard);
    return () => window.removeEventListener("hustudy:before-navigate", guard);
  }, [busy]);
  const resetPreview = () => {if (!pending) {setRemote(null); setConsent(false); setError(""); localStorage.removeItem(storageKey);}};
  const preview = async (event: FormEvent) => {
    event.preventDefault(); if (busy || pending || !query.trim()) return;
    setBusy(true); setError(""); setConsent(false);
    try {const value = isCandidate?await api.previewQuestionDrafts(token,courseId,query,versions,chunkIds,candidateOptions):isReport ? await api.previewStudyReport(token,courseId,query,versions,studyMode,chunkIds) : await api.previewRemoteQuery(token, courseId, query, versions,chunkIds); if (alive.current) {accept(value); onNotice("发送预览已准备；尚未调用远程模型");}}
    catch (e) {if (alive.current) {setError(e instanceof Error ? e.message : "预览失败"); onError(e);}}
    finally {if (alive.current) setBusy(false);}
  };
  const configure=(patch:Partial<CandidateOptions>)=>{resetPreview();setCandidateConfig(current=>({...current,...patch}));};
  const demo=async()=>{if(busy||pending||(isReport?!versions.length:!candidateReady))return;resetPreview();setBusy(true);try{const result=isReport?await api.demoStudyReport(token,courseId,query,versions,studyMode,chunkIds):await api.demoQuestionDrafts(token,courseId,query,versions,chunkIds,candidateOptions);if(alive.current){onAnswer(result);setReload(n=>n+1);onNotice("固定自制演示已返回，未调用远程模型");}}catch(e){if(alive.current){setError(e instanceof Error?e.message:"演示失败");onError(e);}}finally{if(alive.current)setBusy(false);}};
  const confirm = async () => {
    if (!remote || busy || !consent || expired || remote.job) return;
    setBusy(true); setError("");
    try {const value = await api.confirmRemoteQuery(token, remote.id); if (alive.current) {accept(value); onNotice("真实AI任务已排队，可继续阅读并稍后查看");}}
    catch (e) {if (alive.current) {setError(e instanceof Error ? e.message : "确认失败"); onError(e);}}
    finally {if (alive.current) setBusy(false);}
  };
  const cancel = async () => {
    if (!remote || busy) return;
    setBusy(true);
    try {const value = await api.cancelRemoteQuery(token, remote.id); if (alive.current) {accept(value); setConsent(false); onNotice("已取消后续AI处理；派发后的请求无法召回");}}
    catch (e) {if (alive.current) setError(e instanceof Error ? e.message : "取消失败");}
    finally {if (alive.current) setBusy(false);}
  };
  return <section className="panel real-ai-workspace">
    <div className="panel-title"><div><p className="eyebrow">GLM · SOURCE FIRST</p><h3>{isCandidate?"从知识依据生成练习草稿":isReport ? "把资料整理成可学习的报告" : "先核对原文，再让 AI 解释"}</h3></div><span className="course-current">{provider?.configured ? provider.model : "待配置"}</span></div>
    {initializing ? <p role="status">正在读取后端模型与课程资料…</p> : <><p className="hint">使用智谱文本模型。不会上传原件、图片、笔记或整份课程；只发送预览中列出的内容；候选生成还包含出题设置、目标知识点及所选原题。默认不发送。</p>
    {!provider?.configured && <p className="course-conflict">后端尚未配置模型。阅读、笔记和演示检索仍可用。<button className="secondary" onClick={() => setReload(value => value + 1)}>重新检查</button></p>}
    <form onSubmit={preview}><label>{isCandidate?"本次出题目标":isReport ? "本次学习目标" : "向课程提问"}<textarea maxLength={isCandidate?1000:2000} rows={4} value={query} disabled={busy || pending} onChange={e => {resetPreview(); setQuery(e.target.value);}} placeholder="例如：这章如何区分流量控制与拥塞控制？" required/></label>
      {isReport && <label>学习方式<select value={studyMode} disabled={busy||pending} onChange={e=>{resetPreview();setStudyMode(e.target.value);}}><option value="preview">快速预习</option><option value="systematic">系统自学</option><option value="revision">考前复习</option></select></label>}
      <details className="ai-scope-picker" open={isReport||isCandidate ? true : undefined}><summary>限定资料范围 · {versions.length ? `已选${versions.length}份` : isReport||isCandidate ? "请至少选择一份资料" : "自动检索最新版本"}</summary><p className="hint">{isReport||isCandidate ? "按所选资料正文顺序预览，最多6段、8000字符；也可在下方精确选择片段。" : "最多选择20份资料；系统预览匹配的片段。没有关键词证据时不会调用模型。"}</p><div className="ai-scope-options">{documents.filter(d => d.latest_version_id).map(d => <label key={d.id}><input type="checkbox" disabled={busy || pending || (!versions.includes(d.latest_version_id!) && versions.length >= 20)} checked={versions.includes(d.latest_version_id!)} onChange={e => {resetPreview();setChunkIds([]); setVersions(current => e.target.checked ? [...current, d.latest_version_id!] : current.filter(id => id !== d.latest_version_id));}}/><span>{d.name} <small>v{d.latest_version_no}</small></span></label>)}</div></details>
      <ChunkPicker token={token} versions={versions} documents={documents} selected={chunkIds} disabled={busy||pending} onChange={ids=>{resetPreview();setChunkIds(ids);}} onError={onError}/>
      {isCandidate&&<fieldset className="candidate-settings" disabled={busy||pending}><legend>候选题设置</legend><label>目标章节资料<select value={chapterId} onChange={e=>configure({chapter_id:e.target.value})}><option value="" disabled>请选择资料</option>{versions.map(id=><option key={id} value={id}>{documents.find(d=>d.latest_version_id===id)?.name||"已选历史版本"}</option>)}</select></label><label>生成模式<select value={candidateConfig.mode} onChange={e=>configure({mode:e.target.value as CandidateOptions["mode"]})}><option value="historical">按指定结构出题</option><option value="variant">同考点变式</option><option value="weakness">自选薄弱项练习</option></select></label><label>题型<select value={candidateConfig.type} onChange={e=>configure({type:e.target.value as CandidateOptions["type"]})}><option value="single_choice">单选题</option><option value="boolean">判断题</option><option value="short_answer">简答题</option></select></label><label>题数<input type="number" min={1} max={6} step={1} value={candidateConfig.count} onChange={e=>configure({count:Number(e.target.value)})}/></label><label>每题分值<input type="number" min="0.01" max="100" step="0.01" value={candidateConfig.points} onChange={e=>configure({points:e.target.value})}/></label><label>难度标签<select value={candidateConfig.difficulty_label} onChange={e=>configure({difficulty_label:e.target.value as CandidateOptions["difficulty_label"]})}><option value="basic">基础</option><option value="application">应用</option><option value="advanced">进阶</option></select></label><p className="hint">标签仅辅助估计；按指定结构不等于历史预测，自选弱项不代表已测得掌握度。</p><strong>目标知识点（最多4个）</strong><div className="ai-scope-options">{candidateContext.topics.map(t=><label key={t.id}><input type="checkbox" disabled={!candidateConfig.topic_ids.includes(t.id)&&candidateConfig.topic_ids.length>=4} checked={candidateConfig.topic_ids.includes(t.id)} onChange={e=>configure({topic_ids:e.target.checked?[...candidateConfig.topic_ids,t.id]:candidateConfig.topic_ids.filter(id=>id!==t.id)})}/><span>{t.name}</span></label>)}</div>{!candidateContext.topics.length&&<p className="hint">请先在「真题与模拟卷」创建考点，再返回此页。</p>}<details><summary>选择设计参考原题 · {candidateConfig.original_past_question_ids.length}题</summary><p className="hint">只列出已确认原题；变式模式必选，原题不作为答案知识依据。</p><div className="ai-scope-options">{candidateContext.references.map(r=><label key={r.id}><input type="checkbox" disabled={!candidateConfig.original_past_question_ids.includes(r.id)&&candidateConfig.original_past_question_ids.length>=6} checked={candidateConfig.original_past_question_ids.includes(r.id)} onChange={e=>configure({original_past_question_ids:e.target.checked?[...candidateConfig.original_past_question_ids,r.id]:candidateConfig.original_past_question_ids.filter(id=>id!==r.id)})}/><span>{r.title} · {r.stem}</span></label>)}</div></details></fieldset>}
      <button className="primary" disabled={busy || pending || !query.trim() || !provider?.configured || (isReport && !versions.length)||(isCandidate&&!candidateReady)}><Icon name="preview" size={17}/>{busy ? "处理中…" : "预览将发送的片段"}</button>
      {isCandidate&&<><button type="button" className="secondary" disabled={busy||pending||!candidateReady} onClick={()=>void demo()}>运行固定自制演示（不发送）</button><p className="hint">演示仅支持materialhub_demo.md、进程与线程考点、基础难度和最多2题。</p></>}
      {isReport&&<><button type="button" className="secondary" disabled={busy||pending||!versions.length} onClick={()=>void demo()}>运行固定报告演示（不发送）</button><p className="hint">仅支持自制materialhub_demo.md中的进程与线程片段，不根据任意目标理解未知资料。</p></>}
    </form></>}
    {error && <p className="course-conflict" role="alert">{error}</p>}
    {remote && <section className="ai-send-preview">
      <div className="panel-title"><h4>{remote.job ? "真实AI任务" : "发送前核对"}</h4>{remote.job && <Status value={remote.job.status}/>}</div>
      <p><strong>{isReport ? "学习目标：" : "问题："}</strong>{remote.query}</p><p className="hint">{remote.model} · {remote.sources.length}个片段 · {remote.sources.reduce((total, s) => total + Array.from(s.text).length, 0)}字；核对后15分钟内确认。{isReport && "本次输出上限6000 tokens，不自动重发。"}</p>
      {(remote.report_scope||remote.candidate_scope) && <div className="ai-privacy-card"><strong>{(remote.report_scope||remote.candidate_scope)!.coverage.truncated ? "所选资料超出预算或仅选择部分片段" : "已纳入所选版本的可用文本"}</strong><p>{(remote.report_scope||remote.candidate_scope)!.coverage.notice}</p>{(remote.report_scope||remote.candidate_scope)!.coverage.versions.map(v=><p key={v.version_id}>{v.document_name}：{v.selected_chunks}/{v.total_chunks}段，{v.sent_chars}/{v.total_chars}字符{v.truncated ? " · 未完整覆盖" : ""}</p>)}</div>}
      {remote.candidate_scope&&<div className="ai-privacy-card"><strong>本次出题与参考范围</strong><p>{remote.candidate_scope.request.count}题 · 每题{remote.candidate_scope.request.points}分 · {remote.candidate_scope.request.type} · {remote.candidate_scope.request.difficulty_label} · {remote.candidate_scope.request.mode}</p><p>目标：{remote.candidate_scope.exam_context.topics.map(t=>t.name).join("、")}</p>{remote.candidate_scope.exam_context.references.map(r=><details key={r.id} open><summary>{r.title} · {r.year??"年份未知"}</summary><p>{r.stem}</p></details>)}<p className="hint">上述设置、知识点名称和原题正文也会发送；不包含原题答案。</p></div>}
      {!remote.job && <><div className="ai-context-list">{remote.sources.map(s => <details open key={s.source_id}><summary>{s.document_name} · v{s.version_no} · {s.locator.value}{s.source_kind === "manual_transcript" ? " · 人工补录" : ""}</summary><p>{s.text}</p><button className="secondary" onClick={() => onSource(s.version_id, s.source_id)}>对照原文 <Icon name="arrow" size={15}/></button></details>)}</div>
      <div className="ai-privacy-card"><strong>发送至智谱开放平台</strong><p className="hint">{remote.endpoint}</p><p>官方模型/接口文档核对日期：{provider?.checked_at}。{provider?.policy_status}</p><div><a href={provider?.documentation_url} target="_blank" rel="noopener noreferrer">官方模型文档 ↗</a> · <a href={provider?.policy_entry_url} target="_blank" rel="noopener noreferrer">平台协议入口（政策待核实）↗</a></div><p>派发后无法召回远程请求；取消或删除来源会阻止后续结果写入。额度与限流以你的智谱账户为准。</p></div>
      <label className="ai-consent"><input type="checkbox" checked={consent} disabled={busy || expired} onChange={e => setConsent(e.target.checked)}/><span>我已核对上述问题与片段，理解政策未核实项，同意本次发送至智谱。</span></label>
      {expired && <p role="alert" className="hint">预览已过期，请重新预览。</p>}
      <div className="course-editor-actions"><button className="secondary" disabled={busy} onClick={() => {resetPreview(); onNotice("已放弃预览，没有发送模型请求");}}>放弃，不发送</button><button className="primary" disabled={busy || !consent || expired} onClick={() => void confirm()}>确认本次发送</button></div></>}
      {remote.job && <><p className="hint">{pending ? "任务在后台生成，可离开页面继续阅读；返回后会恢复本次任务。" : remote.job.error || "结果保留在本次请求中，可重新预览新问题。"}{remote.dispatched_at ? " · 请求已派发" : " · 尚未派发"}</p><div className="course-editor-actions">{pending ? <button className="secondary" disabled={busy} onClick={() => void cancel()}>取消后续处理</button> : <button className="secondary" disabled={busy} onClick={resetPreview}>开始新问题</button>}<button className="secondary" disabled={busy} onClick={async () => {try {accept(await api.remoteQuery(token, remote.id));} catch(e) {onError(e);}}}>刷新状态</button></div></>}
    </section>}
    <section className="report-history"><h4>{isCandidate?"已保存的题目候选":isReport?"已保存的学习报告":"已保存的课程问答"}</h4><p className="hint">最近20条，包含失败记录。结果自动保存，生成成功仍需人工核实。</p>{reports.length ? reports.map(r=><button className="relation-link" key={r.id} disabled={busy} onClick={()=>onAnswer(r)}>{r.query} · {r.status === "grounded" ? "查看结果" : "查看不足或失败原因"}</button>) : <p className="hint">还没有结果，请先预览范围。</p>}</section>
  </section>;
}
