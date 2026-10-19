import {useEffect, useRef, useState} from "react";
import {api, type SourceCitation} from "../../api/client";
import {EmptyInline} from "../../components/workspace";

const locators: Record<string, string> = {slide: "幻灯片", page: "页", heading: "标题", docx_block: "正文块", preview_page: "预览页"};

export function NoteCitations({noteId, token, disabled, onSource, onError, onNotice}: {
  noteId?: string; token: string; disabled: boolean;
  onSource: (versionId: string, chunkId: string) => void;
  onError: (error: unknown) => void; onNotice: (message: string) => void;
}) {
  const [rows, setRows] = useState<SourceCitation[]>([]);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [removing, setRemoving] = useState("");
  const [reload, setReload] = useState(0);
  const generation = useRef(0);
  const lock = useRef(false);
  useEffect(() => {
    const current = ++generation.current;
    setRows([]); setFailed(false);
    if (!noteId) {setLoading(false); return;}
    setLoading(true);
    void api.citations(token, noteId).then(value => {
      if (current === generation.current) setRows(value);
    }).catch(error => {
      if (current === generation.current) {setFailed(true); onError(error);}
    }).finally(() => {if (current === generation.current) setLoading(false);});
    return () => {generation.current++;};
  }, [noteId, token, reload]);
  useEffect(() => {
    const guard = (event: Event) => {if (lock.current) event.preventDefault();};
    const unload = (event: BeforeUnloadEvent) => {if (lock.current) {event.preventDefault(); event.returnValue = "";}};
    window.addEventListener("hustudy:before-navigate", guard);
    window.addEventListener("hustudy:before-material-change", guard);
    window.addEventListener("beforeunload", unload);
    return () => {
      window.removeEventListener("hustudy:before-navigate", guard);
      window.removeEventListener("hustudy:before-material-change", guard);
      window.removeEventListener("beforeunload", unload);
    };
  }, []);
  const remove = async (citation: SourceCitation) => {
    if (!noteId || !citation.id || disabled || lock.current) return;
    if (!window.confirm("从这篇笔记移除此引用？原资料和笔记正文保留，已有包含此引用的导出包需要重新生成。")) return;
    lock.current = true; setRemoving(citation.id);
    const current = generation.current;
    try {
      await api.removeCitation(token, noteId, citation.id);
      if (current === generation.current) {
        setRows(value => value.filter(row => row.id !== citation.id));
        onNotice("引用已移除，原资料与笔记正文保留。");
      }
    } catch (error) {if (current === generation.current) onError(error);}
    finally {lock.current = false; setRemoving("");}
  };
  return <section className="panel note-citations" aria-label="资料来源">
    <div className="panel-title"><h3>资料来源{!loading && !failed && rows.length > 0 ? ` · ${rows.length}` : ""}</h3>
      {noteId && <button className="text-button" disabled={loading || disabled || !!removing} onClick={() => setReload(value => value + 1)}>刷新引用</button>}
    </div>
    {loading ? <p role="status">正在加载资料引用…</p> : failed ? <div role="alert"><p>资料引用未能加载，请重试。笔记内容已保留。</p><button className="secondary" disabled={disabled || !!removing} onClick={() => setReload(value => value + 1)}>重试加载引用</button></div> : rows.map(citation => <article className="citation-card" key={citation.id}>
      <strong className="note-citation-source">{citation.document_name || "来源资料不可用"}{citation.version_no != null ? ` · v${citation.version_no}` : ""}</strong>
      <span className="locator">{citation.source_kind === "manual_transcript" ? "人工补录 · " : ""}{locators[citation.locator_type || ""] || citation.locator_type} {citation.locator_value}</span>
      <p>{citation.quote}</p>
      <div className="note-citation-actions">{citation.availability === "active" ? <button className="secondary" disabled={disabled || !!removing} onClick={() => onSource(citation.version_id, citation.chunk_id)}>回到原文 ↗</button> : <small>来源当前不可用，摘录保留供核对</small>}
        {citation.id && <button className="text-button" disabled={disabled || !!removing} onClick={() => void remove(citation)}>{removing === citation.id ? "正在移除…" : "移除此引用"}</button>}
      </div>
    </article>)}
    {!loading && !failed && !rows.length && <EmptyInline text="在资料阅读中选择这篇笔记添加引用"/>}
    {rows.length > 0 && <p className="hint">同一摘录重复添加只保留一条；每篇最多50条。引用固定在原资料版本。</p>}
  </section>;
}
