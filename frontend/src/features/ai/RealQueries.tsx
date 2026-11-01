import {SupplementInputs,SupplementPreview} from "./SupplementInputs";
import {useModelChange} from '../../api/modelEvents';
import type {AISupplementSelection} from "../../api/client";
import {SourceScopePicker} from "./SourceScopePicker";
import {AIActivity} from "../../components/AIActivity";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, AIAnswer, AIProvider, DocumentItem, RemoteQuery, CandidateOptions, CandidateContext } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Status } from "../../components/workspace";
import { ExecutionSummary } from "./ExecutionSummary";
import { ReusableResult } from "./ReusableResult";
import { RelatedAnswers } from "./RelatedAnswers";
import {ChunkPicker} from "./ChunkPicker";
import type {StudyTarget} from "../platform/routing";
import {resolveStudySource} from "./studySource";
import {readingSummaryGoal,belongsToReadingVersion} from "./readingSummary";

type Props = {readingName?:string;historyVersionId?:string;hidden?:boolean;skipRestore?:boolean;initialStudy?: StudyTarget; token: string; courseId: string; task?:"qa"|"study_report"|"question_drafts";onBusyChange?:(busy:boolean)=>void; onAnswer: (answer: AIAnswer) => void; onNotice: (s: string) => void; onError: (e: unknown) => void; onSource: (versionId: string, chunkId: string) => void};

export function RealQueries({readingName,historyVersionId,hidden=false,skipRestore, initialStudy, token, courseId, task="qa", onBusyChange, onAnswer, onNotice, onError, onSource}: Props) {
  const isReport = task === "study_report";
  const isCandidate = task === "question_drafts";
  const [provider, setProvider] = useState<AIProvider | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [query, setQuery] = useState(readingName?readingSummaryGoal(readingName):isReport ? "理解所选资料，梳理知识点并完成自测" : isCandidate ? "依据所选资料生成练习候选题" : "");
  const [studyMode,setStudyMode] = useState("systematic");
  const [allowRepairs,setAllowRepairs] = useState(false);
  const [supplement,setSupplement]=useState<AISupplementSelection>({note_ids:[],notes_confirmed:false});
  const [reports,setReports] = useState<AIAnswer[]>([]);
  const visibleReports=historyVersionId?reports.filter(row=>readingName?belongsToReadingVersion(row,historyVersionId):row.result.citations?.some(source=>source.version_id===historyVersionId)||row.result.coverage?.versions?.some(version=>version.version_id===historyVersionId)):reports;
  const [versions, setVersions] = useState<string[]>([]);
  const [chunkIds,setChunkIds] = useState<string[]>([]);
  const [candidateContext,setCandidateContext]=useState<CandidateContext>({topics:[],references:[]});
  const [candidateConfig,setCandidateConfig]=useState<CandidateOptions>({chapter_id:"",topic_ids:[],type:"single_choice",count:1,points:"5",difficulty_label:"basic",mode:"historical",original_past_question_ids:[]});
  const [remote, setRemote] = useState<RemoteQuery | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [initializationFailed, setInitializationFailed] = useState(false);
  const [readingSource, setReadingSource] = useState<Awaited<ReturnType<typeof resolveStudySource>> | null>(null);
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const [reload, setReload] = useState(0);
  const alive = useRef(true);
  const resultId = useRef("");
  const callbacks = useRef({onAnswer, onNotice, onError});
  callbacks.current = {onAnswer, onNotice, onError};
  const storageKey = readingName? `hustudy_reading_summary:${courseId}:${initialStudy?.versionId||""}`:isReport ? `hustudy_study_report:${courseId}` : isCandidate ? `hustudy_question_drafts:${courseId}` : `hustudy_remote_query:${courseId}`;
  const chapterId=versions.includes(candidateConfig.chapter_id)?candidateConfig.chapter_id:versions[0]||"";
  const candidateOptions={...candidateConfig,chapter_id:chapterId};
  const candidateReady=versions.length>0&&candidateConfig.topic_ids.length>0&&(candidateConfig.mode!=="variant"||candidateConfig.original_past_question_ids.length>0);
  const pending = Boolean(remote?.job && ["QUEUED", "RUNNING"].includes(remote.job.status));
  useModelChange(token,isCurrent=>{setConsent(false);if(!remote?.job)setRemote(null);void api.aiProvider(token).then(value=>{if(isCurrent())setProvider(value);}).catch(e=>{if(isCurrent())callbacks.current.onError(e);});});
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
    const signature=value.result?`${value.result.id}:${value.batch_progress?.completed||0}:${value.result.status}`:"";
    if (value.result && signature !== resultId.current) {
      resultId.current = signature; callbacks.current.onAnswer(value.result);
      callbacks.current.onNotice(value.result.result.partial ? (value.batch_progress?.kind==="qa"?`已完成${value.batch_progress.completed}/${value.batch_progress.total}步，检查全部资料后再统一回答`:`已完成${value.batch_progress?.completed||0}/${value.batch_progress?.total||0}批，可先查看已完成部分`) : value.result.status === "grounded" ? "真实AI结果已生成，请核对引用与解释" : "AI结果已返回，请查看证据或异常说明");
    }
  };
  useEffect(() => {
    alive.current = true;
    return () => {alive.current = false;};
  }, []);
  useEffect(() => {
    let active = true;
    setInitializing(true); setInitializationFailed(false); setError("");
    void Promise.all([api.aiProvider(token),isCandidate?api.candidateContext(token,courseId):Promise.resolve(null), initialStudy ? resolveStudySource(token, courseId, initialStudy) : Promise.resolve(null)]).then(async ([settings,context,source]) => {
      if (!active) return;
      if(readingName&&!source)throw new Error("当前课件来源无法核对，未改用其他资料。");
      setProvider(settings);
      // Include the exact historical version alongside the latest version, never substitute it.
      if(source)setDocuments([{...source.document,latest_version_id:source.version.id,latest_version_no:source.version.version_no}]);
      if(context)setCandidateContext(context);
      if (source) {
        setReadingSource(source); setVersions([source.version.id]); setChunkIds(readingName?[]:source.chunk ? [source.chunk.id] : []);
        // Keep earlier requests in history; entering from the reader starts with its own scope.
        setRemote(null); setConsent(false);
        return;
      }
      if(skipRestore)return;
      const previous = localStorage.getItem(storageKey);
      if (previous) {
        try {const value = await api.remoteQuery(token, previous); if (active) {setQuery(value.query);const saved=value.sources[0]?.m2_supplement;setSupplement({note_ids:saved?.notes.map(n=>n.id)||[],notes_confirmed:false});setAllowRepairs(Boolean(value.execution?.max_structure_repairs));if(value.report_scope){setVersions(value.report_scope.scope_version_ids);setChunkIds(value.report_scope.chunk_ids||[]);setStudyMode(value.report_scope.study_mode);}if(value.candidate_scope){setVersions(value.candidate_scope.request.version_ids);setChunkIds(value.candidate_scope.request.chunk_ids);setCandidateConfig(value.candidate_scope.request);} accept(value);}}
        catch {if (active) localStorage.removeItem(storageKey);}
      }
    }).catch(e => {if (active) {setInitializationFailed(true); setError(e instanceof Error ? e.message : "加载失败"); callbacks.current.onError(e);}})
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
    event.preventDefault(); if (initializing || initializationFailed || busy || pending || !query.trim()) return;
    if(readingName&&(!readingSource||versions.length!==1||versions[0]!==initialStudy?.versionId||chunkIds.length)){onError(new Error("当前课件版本或范围无法核对，请重新加载来源。"));return;}
    setBusy(true); setError(""); setConsent(false);
    try {const value = isCandidate?await api.previewQuestionDrafts(token,courseId,query,versions,chunkIds,candidateOptions):isReport ? await api.previewStudyReport(token,courseId,query,versions,studyMode,chunkIds,allowRepairs?2:0,supplement) : await api.previewRemoteQuery(token, courseId, query, versions,chunkIds,allowRepairs?2:0,{note_ids:supplement.note_ids,notes_confirmed:supplement.notes_confirmed}); if (alive.current) {accept(value); onNotice(value.reusable_result ? "找到相同设置的成功结果，可直接使用；也可确认后重新生成" : "发送预览已准备；尚未调用远程模型");}}
    catch (e) {if (alive.current) {setError(e instanceof Error ? e.message : "预览失败"); onError(e);}}
    finally {if (alive.current) setBusy(false);}
  };
  const configure=(patch:Partial<CandidateOptions>)=>{resetPreview();setCandidateConfig(current=>({...current,...patch}));};
  const demo=async()=>{if(busy||pending||(isReport?!versions.length:!candidateReady))return;resetPreview();setBusy(true);try{const result=isReport?await api.demoStudyReport(token,courseId,query,versions,studyMode,chunkIds):await api.demoQuestionDrafts(token,courseId,query,versions,chunkIds,candidateOptions);if(alive.current){onAnswer(result);setReload(n=>n+1);onNotice("固定自制演示已返回，未调用远程模型");}}catch(e){if(alive.current){setError(e instanceof Error?e.message:"演示失败");onError(e);}}finally{if(alive.current)setBusy(false);}};
  const confirm = async () => {
    if (!remote || busy || !consent || expired || remote.job) return;
    setBusy(true); setError("");
    try {const value = await api.confirmRemoteQuery(token, remote.id); if (alive.current) {accept(value); setConsent(false); onNotice("真实AI任务已排队，可继续阅读并稍后查看");}}
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
  return <section hidden={hidden} className="panel real-ai-workspace" id="ai-controls" tabIndex={0}>
    <div className="panel-title"><div><p className="eyebrow">AI · SOURCE FIRST</p><h3>{readingName?"为当前课件生成知识点总结":isCandidate?"从知识依据生成练习草稿":isReport ? "把资料整理成可学习的报告" : "先核对原文，再让 AI 解释"}</h3></div><span className="course-current">{provider?.configured ? provider.model : "待配置"}</span></div>
    {initializing ? <p role="status">正在读取后端模型与课程资料…</p> : initializationFailed ? <div className="inline-retry" role="alert">来源或配置加载未完成，请重试。<button className="secondary" onClick={() => setReload(value => value + 1)}>重新加载来源与配置</button></div> : <><p className="hint">{isCandidate?"候选生成包含预览原文、出题设置、目标知识点及所选原题，发送前仍须确认。":"仅发送预览中确认的课程原文和你主动选中的补充笔记，不会自动上传原件或图片。发送前须逐次确认。"}</p>
    {readingSource && <section className="study-source-context" aria-label="从资料阅读带入的来源"><strong>{readingSource.document.name} · v{readingSource.version.version_no}</strong><p>{readingSource.chunk ? `阅读入口：${readingSource.chunk.locator_value} · ${readingSource.chunk.text.slice(0, 120)}` : readingName?"固定当前版本的全部可提取文字，不混入其他课件。":"已预选阅读时的版本，可在下方调整本次范围。"}</p><p className="hint">{remote?.job ? "本次任务与发送状态见下方记录。" : readingName?"尚未发送；长课件按原预算分批，确认前可查看每批范围。":"尚未发送；请核对下方资料与片段选择。"}</p><button type="button" className="secondary" onClick={() => onSource(readingSource.version.id, readingSource.chunk?.id || "")}>回到阅读原文 <Icon name="arrow" size={15}/></button></section>}
    {!provider?.configured && <p className="course-conflict">当前账户尚未配置模型，请在API接入保存自己的密钥。阅读、笔记和演示检索仍可用。<button className="secondary" onClick={() => setReload(value => value + 1)}>重新检查</button></p>}
    {pending&&<AIActivity active queued={remote?.job?.status==="QUEUED"} label={isReport?"学习报告":"资料问答"}/>}
    <form onSubmit={preview}>{readingName&&<div className="reading-summary-presets" role="group" aria-label="课件总结侧重点">{["全面梳理","复习提纲","笔记写作"].map((name,i)=><button key={name} type="button" className="secondary" disabled={busy||pending} onClick={()=>{resetPreview();setStudyMode(i===1?"revision":"systematic");setQuery(readingSummaryGoal(readingName)+(i===1?"\n补充侧重点：突出概念区别、适用条件和易错点，形成复习提纲。":i===2?"\n补充侧重点：按知识点给出适合用自己的话重述的笔记层次，保留原文依据。":""));}}>{name}</button>)}</div>}<label>{readingName?"总结要求与提示词（可修改）":isCandidate?"本次出题目标":isReport ? "本次学习目标" : "向课程提问"}<textarea maxLength={isCandidate?1000:2000} rows={4} value={query} disabled={busy || pending} onChange={e => {resetPreview(); setQuery(e.target.value);}} placeholder="例如：这章如何区分流量控制与拥塞控制？" required/></label>
      {isReport && !readingName && <label>学习方式<select value={studyMode} disabled={busy||pending} onChange={e=>{resetPreview();setStudyMode(e.target.value);}}><option value="preview">快速预习</option><option value="systematic">系统自学</option><option value="revision">考前复习</option></select></label>}
      {!readingName&&<><details className="ai-scope-picker" open={isReport||isCandidate||!!initialStudy ? true : undefined}><summary>限定资料范围 · {versions.length ? `已选${versions.length}份` : isReport||isCandidate ? "请至少选择一份资料" : "自动检索最新版本"}</summary><p className="hint">{isReport ? "纳入所选资料的完整可提取正文，最多400段、24万字符，自动分批；也可精确选择章节片段。" : isCandidate ? "纳入所选范围完整正文，最多128段、32000字符；超限时请按章节选择。" : "明确选择课件时纳入完整可提取正文，最多400段/24万字符，长资料先分批检查依据再统一回答。不选课件时按问题检索相关片段。"}</p><SourceScopePicker token={token} courseId={courseId} documents={documents} onDocuments={setDocuments} versions={versions} disabled={busy||pending} onChange={ids=>{resetPreview();setChunkIds([]);setVersions(ids);}}/></details>
      <ChunkPicker limit={isReport?400:isCandidate?128:400} token={token} versions={versions} documents={documents} selected={chunkIds} disabled={busy||pending} onChange={ids=>{resetPreview();setChunkIds(ids);}} onError={onError}/></>}
      {readingName&&<p className="hint">默认纳入当前版本全部可提取正文，最多400段/24万字符并自动分批；是否完整以发送预览为准。无文字的图片页不能据此总结。</p>}
      {isCandidate&&<fieldset className="candidate-settings" disabled={busy||pending}><legend>候选题设置</legend><label>目标章节资料<select value={chapterId} onChange={e=>configure({chapter_id:e.target.value})}><option value="" disabled>请选择资料</option>{versions.map(id=><option key={id} value={id}>{documents.find(d=>d.latest_version_id===id)?.name||"已选历史版本"}</option>)}</select></label><label>生成模式<select value={candidateConfig.mode} onChange={e=>configure({mode:e.target.value as CandidateOptions["mode"]})}><option value="historical">按指定结构出题</option><option value="variant">同考点变式</option><option value="weakness">自选薄弱项练习</option></select></label><label>题型<select value={candidateConfig.type} onChange={e=>configure({type:e.target.value as CandidateOptions["type"]})}><option value="single_choice">单选题</option><option value="boolean">判断题</option><option value="short_answer">简答题</option></select></label><label>题数<input type="number" min={1} max={6} step={1} value={candidateConfig.count} onChange={e=>configure({count:Number(e.target.value)})}/></label><label>每题分值<input type="number" min="0.01" max="100" step="0.01" value={candidateConfig.points} onChange={e=>configure({points:e.target.value})}/></label><label>难度标签<select value={candidateConfig.difficulty_label} onChange={e=>configure({difficulty_label:e.target.value as CandidateOptions["difficulty_label"]})}><option value="basic">基础</option><option value="application">应用</option><option value="advanced">进阶</option></select></label><p className="hint">标签仅辅助估计；按指定结构不等于历史预测，自选弱项不代表已测得掌握度。</p><strong>目标知识点（最多4个）</strong><p className="hint">AI会分别标出每道题实际考查的知识点，不会统一附加全部所选知识点；关联准确性仍需审阅。</p><div className="ai-scope-options">{candidateContext.topics.map(t=><label key={t.id}><input type="checkbox" disabled={!candidateConfig.topic_ids.includes(t.id)&&candidateConfig.topic_ids.length>=4} checked={candidateConfig.topic_ids.includes(t.id)} onChange={e=>configure({topic_ids:e.target.checked?[...candidateConfig.topic_ids,t.id]:candidateConfig.topic_ids.filter(id=>id!==t.id)})}/><span>{t.name}</span></label>)}</div>{!candidateContext.topics.length&&<p className="hint">请先在「真题与模拟卷」创建考点，再返回此页。</p>}<details><summary>选择设计参考原题 · {candidateConfig.original_past_question_ids.length}题</summary><p className="hint">只列出已确认原题；变式模式必选，原题不作为答案知识依据。</p><div className="ai-scope-options">{candidateContext.references.map(r=><label key={r.id}><input type="checkbox" disabled={!candidateConfig.original_past_question_ids.includes(r.id)&&candidateConfig.original_past_question_ids.length>=6} checked={candidateConfig.original_past_question_ids.includes(r.id)} onChange={e=>configure({original_past_question_ids:e.target.checked?[...candidateConfig.original_past_question_ids,r.id]:candidateConfig.original_past_question_ids.filter(id=>id!==r.id)})}/><span>{r.title} · {r.stem}</span></label>)}</div></details></fieldset>}
      {!isCandidate&&<SupplementInputs token={token} courseId={courseId} value={supplement} onChange={value=>{resetPreview();setSupplement(value);}} disabled={busy||pending}/>}
      {!isCandidate&&<label className="ai-consent"><input type="checkbox" checked={allowRepairs} disabled={busy||pending} onChange={e=>{resetPreview();setAllowRepairs(e.target.checked);}}/><span>允许最多2次格式修复（可能增加AI调用费用）<small className="hint">默认关闭。仅格式错误时，将错误输出与原资料范围发回同一模型；共用本次120秒预算。限流、超时或无效引用不会自动重发。</small></span></label>}
      <button className="primary" disabled={busy || pending || !query.trim() || !provider?.configured || (isReport && !versions.length)||(isCandidate&&!candidateReady)}><Icon name="preview" size={17}/>{busy ? "处理中…" : "预览将发送的片段"}</button>
      {isCandidate&&<><button type="button" className="secondary" disabled={busy||pending||!candidateReady} onClick={()=>void demo()}>运行固定自制演示（不发送）</button><p className="hint">演示仅支持materialhub_demo.md、进程与线程考点、基础难度和最多2题。</p></>}
      {isReport&&<><button type="button" className="secondary" disabled={busy||pending||!versions.length} onClick={()=>void demo()}>运行固定报告演示（不发送）</button><p className="hint">仅支持自制materialhub_demo.md中的进程与线程片段，不根据任意目标理解未知资料。</p></>}
    </form></>}
    {error && <p className="course-conflict" role="alert">{error}</p>}
    {remote && <section className="ai-send-preview">
      <div className="panel-title"><h4>{remote.job ? "真实AI任务" : "发送前核对"}</h4>{remote.job && <Status value={remote.job.status}/>}</div>
      <SupplementPreview value={remote.sources[0]?.m2_supplement}/>
      <ExecutionSummary execution={remote.execution} pending={pending}/>
      <p><strong>{isReport ? "学习目标：" : "问题："}</strong>{remote.query}</p><p className="hint">{remote.model} · {remote.sources.length}个片段 · {remote.sources.reduce((total, s) => total + Array.from(s.text).length, 0)}字；核对后15分钟内确认。{isReport && "每批输出上限6000 tokens；格式修复以本次授权为准。"}</p>
      {(remote.report_scope||remote.candidate_scope) && <div className="ai-privacy-card"><strong>{(remote.report_scope||remote.candidate_scope)!.coverage.truncated ? "所选资料超出预算或仅选择部分片段" : "已纳入所选版本的可用文本"}</strong><p>{(remote.report_scope||remote.candidate_scope)!.coverage.notice}</p>{(remote.report_scope||remote.candidate_scope)!.coverage.warnings?.map((warning,i)=><p role="alert" key={i}>{warning}</p>)}{(remote.report_scope||remote.candidate_scope)!.coverage.versions.map(v=><p key={v.version_id}>{v.document_name}：{v.selected_chunks}/{v.total_chunks}段，{v.sent_chars}/{v.total_chars}字符{v.truncated ? " · 未完整覆盖" : ""}</p>)}</div>}
      {remote.qa_scope&&<div className="ai-privacy-card"><strong>{remote.qa_scope.mode==="retrieved"?"当前使用相关片段检索":"已纳入所选范围的完整可提取正文"}</strong><p>{remote.qa_scope.coverage.notice}</p>{remote.qa_scope.coverage.warnings?.map((warning,i)=><p role="alert" key={i}>{warning}</p>)}{remote.qa_scope.coverage.versions.map(v=><p key={v.version_id}>{v.document_name}：{v.selected_chunks}/{v.total_chunks}段，{v.sent_chars}/{v.total_chars}字符{v.truncated?" · 仅所选范围":""}</p>)}{remote.qa_scope.batched&&<p>先检查{remote.qa_scope.batch_count}批资料，再汇总一次回答；最多{remote.qa_scope.batch_count+1}次原生成调用，另计已授权修复，共用120秒处理窗口。</p>}</div>}
      {remote.candidate_scope&&<div className="ai-privacy-card"><strong>本次出题与参考范围</strong><p>{remote.candidate_scope.request.count}题 · 每题{remote.candidate_scope.request.points}分 · {remote.candidate_scope.request.type} · {remote.candidate_scope.request.difficulty_label} · {remote.candidate_scope.request.mode}</p><p>目标：{remote.candidate_scope.exam_context.topics.map(t=>t.name).join("、")}</p>{remote.candidate_scope.exam_context.references.map(r=><details key={r.id} open><summary>{r.title} · {r.year??"年份未知"}</summary><p>{r.stem}</p></details>)}<p className="hint">上述设置、知识点名称和原题正文也会发送；不包含原题答案。</p></div>}
      {!remote.job && !remote.reusable_result && !!remote.related_results?.length && <RelatedAnswers key={remote.id} token={token} queryId={remote.id} kind={isReport?"study_report":"qa"} currentQuestion={remote.query} candidates={remote.related_results} disabled={busy||expired} onBusyChange={setBusy} onAdopt={saved=>{resetPreview();onAnswer(saved);onNotice(`已使用历史原${isReport?"报告，原学习目标":"答案，原问题"}：${saved.query}。本次未调用AI，请继续核对适用性。`);}}/>}
      {!remote.job && remote.reusable_result && <ReusableResult answer={remote.reusable_result} disabled={busy||expired} onReuse={async()=>{
        if(busy||expired||!remote.reusable_result)return;
        setBusy(true);setError("");
        try{const saved=await api.reuseRemoteQuery(token,remote.id,remote.reusable_result.id);if(alive.current){resetPreview();onAnswer(saved);onNotice("已使用已有结果，未调用AI，也未新增生成费用；仍请核对内容。");}}
        catch(e){if(alive.current){setError(e instanceof Error?e.message:"复用失败");onError(e);}}
        finally{if(alive.current)setBusy(false);}
      }}/>}
      {!remote.job && <><div className="ai-context-list">{remote.sources.map((s,i) => <details key={`${s.source_id}-${i}`}><summary>{s.document_name} · v{s.version_no} · {s.locator.value}{s.source_kind === "manual_transcript" ? " · 人工补录" : ""}</summary><p>{s.text}</p><button className="secondary" onClick={() => onSource(s.version_id, s.source_id)}>对照原文 <Icon name="arrow" size={15}/></button></details>)}</div>
      <div className="ai-privacy-card"><strong>发送至{provider?.provider||"所选模型平台"}</strong><p className="hint">{remote.endpoint}</p><p>官方模型/接口文档核对日期：{provider?.checked_at}。{provider?.policy_status}</p><div><a href={provider?.documentation_url} target="_blank" rel="noopener noreferrer">官方模型文档 ↗</a> · <a href={provider?.policy_entry_url} target="_blank" rel="noopener noreferrer">平台协议入口（政策待核实）↗</a></div><p>派发后无法召回远程请求；取消或删除来源会阻止后续结果写入。额度与限流以你的模型服务账户为准。</p></div>
      <label className="ai-consent"><input type="checkbox" checked={consent} disabled={busy || expired} onChange={e => setConsent(e.target.checked)}/><span>我已核对上述问题与片段，理解政策未核实项，同意本次发送至所选模型平台。{Boolean(remote.execution?.max_structure_repairs)&&`包含最多${remote.execution!.max_structure_repairs}次格式修复，错误输出与原范围会再次发送并消耗额度。`}{remote.batch_progress&&remote.batch_progress.total>1&&`本次计划${remote.batch_progress.total}${remote.batch_progress.kind==="qa"?"步（含最终汇总）":"批"}调用，分别消耗账户额度。`}</span></label>
      {expired && <p role="alert" className="hint">预览已过期，请重新预览。</p>}
      <div className="course-editor-actions"><button className="secondary" disabled={busy} onClick={() => {resetPreview(); onNotice("已放弃预览，没有发送模型请求");}}>放弃，不发送</button><button className="primary" disabled={busy || !consent || expired} onClick={() => void confirm()}>{remote.reusable_result?"仍要重新生成（调用AI）":"确认本次发送"}</button></div></>}
      {remote.batch_progress&&<div className="ai-batch-progress" role="status"><strong>{remote.batch_progress.kind==="qa"?"分批问答":"分批报告"}：已完成{remote.batch_progress.completed}/{remote.batch_progress.total}{remote.batch_progress.kind==="qa"?"步":"批"}</strong><progress aria-label={remote.batch_progress.kind==="qa"?"问答步骤进度":"报告批次进度"} max={remote.batch_progress.total||1} value={remote.batch_progress.completed}/><p>共{remote.batch_progress.chars}字符；最多{remote.batch_progress.total-remote.batch_progress.completed}次原生成调用；另有预览授权的剩余格式修复额度，均受120秒窗口限制。{remote.batch_progress.kind==="qa"?"全部资料检查后再统一回答，已检查批次不会重发。":"每部分独立生成，成功部分不会重发。"}</p></div>}
      {remote.job && <><p className="hint">{pending ? "任务在后台生成，可离开页面继续阅读；返回后会恢复本次任务。" : remote.job.error || "结果保留在本次请求中，可重新预览新问题。"}{remote.dispatched_at ? " · 请求已派发" : " · 尚未派发"}</p><div className="course-editor-actions">{pending ? <button className="secondary" disabled={busy} onClick={() => void cancel()}>取消后续处理</button> : <button className="secondary" disabled={busy} onClick={resetPreview}>开始新问题</button>}<button className="secondary" disabled={busy} onClick={async () => {try {accept(await api.remoteQuery(token, remote.id));} catch(e) {onError(e);}}}>刷新状态</button></div></>}
      {remote.batch_progress&&remote.job&&["FAILED","CANCELLED"].includes(remote.job.status)&&<div><label className="ai-consent"><input type="checkbox" checked={consent} disabled={busy} onChange={e=>setConsent(e.target.checked)}/><span>我同意仅继续未完成批次并开启新的120秒窗口，可能产生额外模型调用费用；成功部分不重发，格式修复总额度不重置。</span></label><button className="primary" disabled={busy||!consent} onClick={async()=>{setBusy(true);try{accept(await api.resumeRemoteQuery(token,remote.id));setConsent(false);}catch(e){onError(e);}finally{setBusy(false);}}}>确认继续未完成批次</button></div>}
    </section>}
    <section className="report-history"><h4>{readingName?"当前课件的总结记录":isCandidate?"已保存的题目候选":isReport?"已保存的学习报告":"已保存的课程问答"}</h4><p className="hint">{historyVersionId?"从课程最近20条中筛选包含当前版本依据/覆盖信息的记录；不代表完整版本历史。":"最近20条，包含失败记录。"}结果自动保存，生成成功仍需人工核实。</p>{visibleReports.length ? visibleReports.map(r=><button className="relation-link" key={r.id} disabled={busy} onClick={()=>onAnswer(r)}>{r.query} · {r.status === "grounded" ? "查看结果" : "查看不足或失败原因"}</button>) : <p className="hint">还没有结果，请先预览范围。</p>}</section>
  </section>;
}
