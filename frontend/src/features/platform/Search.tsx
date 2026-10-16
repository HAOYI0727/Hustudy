import { FormEvent, useEffect, useRef, useState } from "react";
import { api, SearchPage, NoteSearchPage } from "../../api/client";
import { EmptyState } from "../../components/workspace";
import { Icon } from "../../components/Icon";
import { SearchExcerpt } from "../../components/SearchExcerpt";

export type MaterialTarget = { documentId: string; versionId: string; chunkId: string; previewPage?: number };
const pageSize = 12;
const empty = { items: [], total: 0, offset: 0, limit: pageSize };
function Pager({ page, label, busy, onPage }: { page: {total:number;offset:number;limit:number}; label:string; busy:boolean; onPage:(offset:number)=>void }) {
  if (!page.total) return null;
  return <nav className="search-pagination" aria-label={`${label}分页`}>
    <span>{page.offset >= page.total ? `当前页已无结果，共 ${page.total} 条` : `${page.offset + 1}–${Math.min(page.offset + page.limit, page.total)} / ${page.total}`}</span>
    <div><button className="secondary" disabled={busy || page.offset === 0} aria-label={`${label}上一页`} onClick={() => onPage(Math.max(0, Math.min(page.offset - page.limit, Math.floor((page.total - 1) / page.limit) * page.limit)))}>上一页</button>
    <button className="secondary" disabled={busy || page.offset + page.limit >= page.total} aria-label={`${label}下一页`} onClick={() => onPage(page.offset + page.limit)}>下一页<Icon name="arrow" size={14}/></button></div>
  </nav>;
}
export function Search({ token, courseId, onMaterial, onNote, onError }: {
  token: string; courseId: string; onMaterial: (target: MaterialTarget) => void;
  onNote: (id: string) => void; onError: (error: unknown) => void;
}) {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [materials, setMaterials] = useState<SearchPage>(empty);
  const [notebook, setNotebook] = useState<NoteSearchPage>(empty);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [filter, setFilter] = useState("all");
  const [scopes, setScopes] = useState<{categories:string[];tags:string[]}>({categories:[],tags:[]});
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [latestOnly, setLatestOnly] = useState(true);
  const [scopeFailed, setScopeFailed] = useState(false);
  const generation = useRef(0);
  useEffect(() => {
    let active = true; setScopeFailed(false);
    void api.documentPage(token, courseId, {q:"",category:"",tag:"",state:"all",sort:"recent",offset:0,limit:1})
      .then(page => { if (active) setScopes({categories:page.categories,tags:page.tags}); })
      .catch(() => { if (active) setScopeFailed(true); });
    return () => { active = false; generation.current++; };
  }, [token, courseId]);
  const clearResults = () => { generation.current++; setSubmitted(""); setMaterials(empty); setNotebook(empty); setBusy(false); setFailed(false); };
  const load = async (keyword:string, materialOffset=0, noteOffset=0) => {
    const current = ++generation.current;
    setBusy(true); setFailed(false); setSubmitted(keyword);
    try {
      const [found, notes] = await Promise.all([
        api.searchPage(token, courseId, keyword, {category,tag,latestOnly}, materialOffset, pageSize),
        api.noteSearch(token, courseId, keyword, noteOffset, pageSize),
      ]);
      if (current !== generation.current) return;
      setMaterials(found); setNotebook(notes);
    } catch (error) { if (current === generation.current) { setFailed(true); onError(error); } }
    finally { if (current === generation.current) setBusy(false); }
  };
  const search = (event:FormEvent) => { event.preventDefault(); if (query.trim()) void load(query.trim()); };
  return <div className="page search-page">
    <section className="search-hero"><p className="eyebrow">FIND YOUR KNOWLEDGE</p><h2>想找的知识，就在这门课里。</h2><p>一次查找课程原文和笔记，直接回到知识所在的位置。</p>
      <form className="workspace-search" onSubmit={search}><Icon name="search" size={21}/><input autoFocus aria-label="查找课程资料与笔记" value={query} onChange={e => setQuery(e.target.value)} placeholder="输入概念、章节或笔记关键词…" maxLength={200}/><button className="primary" disabled={busy || !query.trim()}>{busy ? "查找中…" : "查找"}<Icon name="arrow" size={16}/></button></form>
      <div className="search-scope"><select aria-label="查找资料分类" value={category} onChange={e => { setCategory(e.target.value); clearResults(); }}><option value="">全部资料分类</option>{scopes.categories.map(value => <option key={value}>{value}</option>)}</select><select aria-label="查找资料标签" value={tag} onChange={e => { setTag(e.target.value); clearResults(); }}><option value="">全部资料标签</option>{scopes.tags.map(value => <option key={value}>{value}</option>)}</select><select aria-label="查找资料版本范围" value={latestOnly ? "latest" : "all"} onChange={e => { setLatestOnly(e.target.value === "latest"); clearResults(); }}><option value="latest">只查最新版本</option><option value="all">包含历史版本</option></select></div>
      {(category || tag) && <p className="scope-notice">分类与标签筛选适用于资料；笔记仍按课程关键词查找。</p>}{scopeFailed && <p className="scope-notice" role="status">分类列表暂未加载，仍可按课程关键词查找。</p>}
      <small>当前课程范围 · 中文关键词索引 · 每页 12 条，可翻页查看全部命中</small>
    </section>
    <div className="search-filters" aria-label="结果类型">{[["all", "全部"], ["materials", "资料原文"], ["notes", "我的笔记"]].map(([value, label]) => <button key={value} className={filter === value ? "selected" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>)}</div>
    {busy ? <div className="panel" role="status">正在查找「{submitted}」…</div> : failed ? <EmptyState title="本次查找未完成" text="检查连接后重新查找，失败结果不会显示为零条命中。"/> : !submitted ? <EmptyState title="从一个关键词开始" text="试试课件里的一个术语，或你在笔记中记录的问题。"/> : <>
      <p className="hint" role="status">「{submitted}」 · {materials.total} 个资料片段 · {notebook.total} 篇笔记</p>
      {filter !== "notes" && <section className="panel search-group"><h3><Icon name="file"/>资料原文 <span className="count-pill">{materials.total}</span></h3>{materials.items.map(hit => <button className="knowledge-hit" key={hit.chunk_id} onClick={() => onMaterial({ documentId: hit.document_id, versionId: hit.version_id, chunkId: hit.chunk_id })}><span className="hit-meta">{hit.document_name} <span>v{hit.version_no} · {hit.source_kind === "manual_transcript" ? "人工补录 · " : ""}{hit.locator_type} · {hit.locator_value}</span></span><div className="metadata-chips"><span>{hit.category}</span>{hit.tags.map(t => <span key={t}>{t}</span>)}</div><p><SearchExcerpt excerpt={hit.excerpt}/></p><small>打开原文位置 <Icon name="arrow" size={13}/></small></button>)}{!materials.total && <p className="hint">所选范围没有匹配片段，试试更短的关键词或包含历史版本；最新版本仍在处理时不会退回旧内容。</p>}<Pager page={materials} label="资料结果" busy={busy} onPage={offset => void load(submitted,offset,notebook.offset)}/></section>}
      {filter !== "materials" && <section className="panel search-group"><h3><Icon name="notes"/>我的笔记 <span className="count-pill">{notebook.total}</span></h3>{notebook.items.map(note => <button className="knowledge-hit" key={note.id} onClick={() => onNote(note.id)}><strong>{note.title}</strong><p><SearchExcerpt excerpt={note.excerpt}/></p><small>打开这篇笔记 <Icon name="arrow" size={13}/></small></button>)}{!notebook.total && <p className="hint">当前课程中没有匹配的笔记。</p>}<Pager page={notebook} label="笔记结果" busy={busy} onPage={offset => void load(submitted,materials.offset,offset)}/></section>}
    </>}
  </div>;
}
