import { FormEvent, useEffect, useRef, useState } from "react";
import { api, AIAnswer, AIProvider, DocumentItem, RemoteQuery } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Status } from "../../components/workspace";

type Props = {token: string; courseId: string; onAnswer: (answer: AIAnswer) => void; onNotice: (s: string) => void; onError: (e: unknown) => void; onSource: (versionId: string, chunkId: string) => void};

export function RealQueries({token, courseId, onAnswer, onNotice, onError, onSource}: Props) {
  const [provider, setProvider] = useState<AIProvider | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [query, setQuery] = useState("");
  const [versions, setVersions] = useState<string[]>([]);
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
  const storageKey = `hustudy_remote_query:${courseId}`;
  const pending = Boolean(remote?.job && ["QUEUED", "RUNNING"].includes(remote.job.status));
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
    void Promise.all([api.aiProvider(token), api.documents(token, courseId)]).then(async ([settings, docs]) => {
      if (!active) return;
      setProvider(settings); setDocuments(docs);
      const previous = localStorage.getItem(storageKey);
      if (previous) {
        try {const value = await api.remoteQuery(token, previous); if (active) {setQuery(value.query); accept(value);}}
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
    try {const value = await api.previewRemoteQuery(token, courseId, query, versions); if (alive.current) {accept(value); onNotice("发送预览已准备；尚未调用远程模型");}}
    catch (e) {if (alive.current) {setError(e instanceof Error ? e.message : "预览失败"); onError(e);}}
    finally {if (alive.current) setBusy(false);}
  };
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
    <div className="panel-title"><div><p className="eyebrow">GLM · SOURCE FIRST</p><h3>先核对原文，再让 AI 解释</h3></div><span className="course-current">{provider?.configured ? provider.model : "待配置"}</span></div>
    {initializing ? <p role="status">正在读取后端模型与课程资料…</p> : <><p className="hint">使用智谱文本模型。不会上传原件、图片、笔记或整份课程；只发送下方问题和已预览片段。默认不发送。</p>
    {!provider?.configured && <p className="course-conflict">后端尚未配置模型。阅读、笔记和演示检索仍可用。<button className="secondary" onClick={() => setReload(value => value + 1)}>重新检查</button></p>}
    <form onSubmit={preview}><label>向课程提问<textarea maxLength={2000} rows={4} value={query} disabled={busy || pending} onChange={e => {resetPreview(); setQuery(e.target.value);}} placeholder="例如：这章如何区分流量控制与拥塞控制？" required/></label>
      <details className="ai-scope-picker"><summary>限定资料范围 · {versions.length ? `已选${versions.length}份` : "自动检索最新版本"}</summary><p className="hint">最多选择20份资料；系统预览匹配的片段。没有关键词证据时不会调用模型。</p><div className="ai-scope-options">{documents.filter(d => d.latest_version_id).map(d => <label key={d.id}><input type="checkbox" disabled={busy || pending || (!versions.includes(d.latest_version_id!) && versions.length >= 20)} checked={versions.includes(d.latest_version_id!)} onChange={e => {resetPreview(); setVersions(current => e.target.checked ? [...current, d.latest_version_id!] : current.filter(id => id !== d.latest_version_id));}}/><span>{d.name} <small>v{d.latest_version_no}</small></span></label>)}</div></details>
      <button className="primary" disabled={busy || pending || !query.trim() || !provider?.configured}><Icon name="preview" size={17}/>{busy ? "处理中…" : "预览将发送的片段"}</button>
    </form></>}
    {error && <p className="course-conflict" role="alert">{error}</p>}
    {remote && <section className="ai-send-preview">
      <div className="panel-title"><h4>{remote.job ? "真实AI任务" : "发送前核对"}</h4>{remote.job && <Status value={remote.job.status}/>}</div>
      <p><strong>问题：</strong>{remote.query}</p><p className="hint">{remote.model} · {remote.sources.length}个片段 · {remote.sources.reduce((total, s) => total + Array.from(s.text).length, 0)}字；核对后15分钟内确认。</p>
      {!remote.job && <><div className="ai-context-list">{remote.sources.map(s => <details open key={s.source_id}><summary>{s.document_name} · v{s.version_no} · {s.locator.value}{s.source_kind === "manual_transcript" ? " · 人工补录" : ""}</summary><p>{s.text}</p><button className="secondary" onClick={() => onSource(s.version_id, s.source_id)}>对照原文 <Icon name="arrow" size={15}/></button></details>)}</div>
      <div className="ai-privacy-card"><strong>发送至智谱开放平台</strong><p className="hint">{remote.endpoint}</p><p>官方模型/接口文档核对日期：{provider?.checked_at}。{provider?.policy_status}</p><div><a href={provider?.documentation_url} target="_blank" rel="noopener noreferrer">官方模型文档 ↗</a> · <a href={provider?.policy_entry_url} target="_blank" rel="noopener noreferrer">平台协议入口（政策待核实）↗</a></div><p>派发后无法召回远程请求；取消或删除来源会阻止后续结果写入。额度与限流以你的智谱账户为准。</p></div>
      <label className="ai-consent"><input type="checkbox" checked={consent} disabled={busy || expired} onChange={e => setConsent(e.target.checked)}/><span>我已核对上述问题与片段，理解政策未核实项，同意本次发送至智谱。</span></label>
      {expired && <p role="alert" className="hint">预览已过期，请重新预览。</p>}
      <div className="course-editor-actions"><button className="secondary" disabled={busy} onClick={() => {resetPreview(); onNotice("已放弃预览，没有发送模型请求");}}>放弃，不发送</button><button className="primary" disabled={busy || !consent || expired} onClick={() => void confirm()}>确认本次发送</button></div></>}
      {remote.job && <><p className="hint">{pending ? "任务在后台生成，可离开页面继续阅读；返回后会恢复本次任务。" : remote.job.error || "结果保留在本次请求中，可重新预览新问题。"}{remote.dispatched_at ? " · 请求已派发" : " · 尚未派发"}</p><div className="course-editor-actions">{pending ? <button className="secondary" disabled={busy} onClick={() => void cancel()}>取消后续处理</button> : <button className="secondary" disabled={busy} onClick={resetPreview}>开始新问题</button>}<button className="secondary" disabled={busy} onClick={async () => {try {accept(await api.remoteQuery(token, remote.id));} catch(e) {onError(e);}}}>刷新状态</button></div></>}
    </section>}
  </section>;
}
