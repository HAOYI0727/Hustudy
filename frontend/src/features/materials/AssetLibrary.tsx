import { useEffect, useRef, useState } from "react";
import { api, ApiError, Asset, AssetFilters, AssetPage, Note } from "../../api/client";
import { AssetImage } from "../../components/knowledge";
import { Icon } from "../../components/Icon";
import {uploadImages, imageLabel, MAX_IMAGE_BATCH, type ImageFailure, type ImageProgress} from "./uploadImages";
import {ImageUploadStatus} from "./ImageUploadStatus";

const defaults: AssetFilters = {q: "", tag: "", origin: "all", sort: "newest", offset: 0, limit: 12};
type Props = {
  token: string; courseId: string; onError: (e: unknown) => void; onNotice: (s: string) => void;
  refreshKey?: number; onChanged?: () => void; onNote?: (id: string) => void;
  onSource?: (target: {documentId: string; versionId: string; chunkId: string; previewPage?: number}) => void;
};

export function AssetLibrary({token, courseId, onError, onNotice, refreshKey = 0, onSource, onNote, onChanged}: Props) {
  const [page, setPage] = useState<AssetPage>({items: [], total: 0, offset: 0, limit: 12, tags: []});
  const [filters, setFilters] = useState(defaults);
  const [query, setQuery] = useState("");
  const [reload, setReload] = useState(0);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadFailures, setUploadFailures] = useState<ImageFailure[]>([]);
  const [uploadProgress, setUploadProgress] = useState<ImageProgress | null>(null);
  const [uploadSummary, setUploadSummary] = useState("");
  const uploadLock = useRef(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const editor = useRef<HTMLDivElement>(null);
  const [alt, setAlt] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [references, setReferences] = useState<Note[]>([]);
  const [focused, setFocused] = useState<Asset | null>(null);
  const [editing, setEditing] = useState<Asset | null>(null);
  const [draft, setDraft] = useState({name: "", alt: "", tags: ""});
  const [conflict, setConflict] = useState<Asset | null>(null);
  const dirty = Boolean(editing && (draft.name !== editing.name || draft.alt !== editing.alt || draft.tags !== editing.tags.join("、")));
  const refresh = () => setReload(value => value + 1);
  const discard = () => !dirty || window.confirm("图片整理还未保存，放弃这些修改？");

  useEffect(() => {
    let live = true;
    setLoading(true); setFailed(false);
    void api.assetPage(token, courseId, filters).then(result => {
      if (!live) return;
      // Deleting the last item on a page returns to the last remaining page.
      if (filters.offset && filters.offset >= result.total) {
        setFilters(current => ({...current, offset: Math.max(0, Math.floor((result.total - 1) / current.limit) * current.limit)}));
      } else setPage(result);
    }).catch(error => { if (live) {setFailed(true); onError(error);} })
      .finally(() => {if (live) setLoading(false);});
    return () => { live = false; };
  }, [token, courseId, filters, refreshKey, reload]);

  useEffect(() => {
    const guard = (event: Event) => {
      if (busy) {event.preventDefault(); onNotice("图片操作正在处理，请稍后再切换"); return;}
      if (dirty && !window.confirm("图片整理还未保存，放弃修改并离开？")) event.preventDefault();
    };
    const unload = (event: BeforeUnloadEvent) => {if (dirty || busy) {event.preventDefault(); event.returnValue = "";}};
    window.addEventListener("hustudy:before-navigate", guard);
    window.addEventListener("hustudy:before-material-change", guard);
    window.addEventListener("beforeunload", unload);
    return () => {
      window.removeEventListener("hustudy:before-navigate", guard);
      window.removeEventListener("hustudy:before-material-change", guard);
      window.removeEventListener("beforeunload", unload);
    };
  }, [dirty, busy]);

  const filter = (patch: Partial<AssetFilters>) => setFilters(current => ({...current, ...patch, offset: 0}));
  const reset = () => {setQuery(""); setFilters({...defaults, limit: filters.limit});};
  const startEdit = (asset: Asset) => {
    if (!discard()) return;
    setEditing(asset); setDraft({name: asset.name, alt: asset.alt, tags: asset.tags.join("、")}); setConflict(null);
    requestAnimationFrame(() => editor.current?.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "center"}));
  };
  const save = async () => {
    if (!editing || busy || conflict) return;
    const tags = [...new Set(draft.tags.split(/[,，、\n]/).map(tag => tag.trim()).filter(Boolean))];
    if (!draft.name.trim() || tags.length > 12 || tags.some(tag => Array.from(tag).length > 32)) {
      onError(new Error("图片名称不能为空，标签最多12个，每个不超过32字")); return;
    }
    setBusy(true);
    try {
      await api.updateAsset(token, editing.id, {revision: editing.revision, name: draft.name, alt: draft.alt, tags});
      setEditing(null); refresh(); onChanged?.(); onNotice("图片整理已保存，原页与笔记引用保持有效");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409 && error.details?.server_asset) setConflict(error.details.server_asset as Asset);
      onError(error);
    } finally {setBusy(false);}
  };
  const upload = async (batch = files) => {
    if (!batch.length || busy || uploadLock.current) return;
    if (batch.length > MAX_IMAGE_BATCH) {onError(new Error(`每批最多选择 ${MAX_IMAGE_BATCH} 张图片，请分批上传。`)); return;}
    uploadLock.current = true; setBusy(true); setUploadFailures([]); setUploadSummary("");
    try {
      const result = await uploadImages(batch, file => api.uploadAsset(token, courseId, file, alt.trim() || imageLabel(file)), setUploadProgress);
      setFiles([]); if (fileInput.current) fileInput.current.value = "";
      setUploadFailures(result.failures);
      const summary = `已导入 ${result.assets.length} 张图片${result.failures.length ? `，${result.failures.length} 张未完成` : ""}。`;
      setUploadSummary(summary);
      if (!result.failures.length) setAlt("");
      if (result.assets.length) {
        setFilters({...defaults, limit: filters.limit}); setQuery(""); refresh(); onChanged?.();
        onNotice(summary + "可整理标签或从笔记工具栏插入。");
      }
    } catch (error) {onError(error);} finally {setBusy(false); uploadLock.current = false; setUploadProgress(null);}
  };
  const openSource = async (asset: Asset) => {
    if (!onSource || busy || !discard()) return;
    setBusy(true);
    let target: Parameters<NonNullable<Props["onSource"]>>[0] | undefined;
    try {
      const source = await api.assetMetadata(token, asset.id);
      if (source.source_availability !== "active" || !source.source_document_id || !source.source_version_id || !source.source_page) throw new Error("来源资料已不可用");
      target = {documentId: source.source_document_id, versionId: source.source_version_id, chunkId: "", previewPage: source.source_page};
    } catch (error) {onError(error);} finally {setBusy(false);}
    // The parent navigation dispatches the shared guard; don't block our own navigation with busy.
    if (target) {setEditing(null); requestAnimationFrame(() => onSource(target!));}
  };
  const showReferences = async (asset: Asset) => {
    setBusy(true); setFocused(null);
    try {setReferences(await api.assetReferences(token, asset.id)); setFocused(asset);}
    catch (error) {onError(error);} finally {setBusy(false);}
  };
  const remove = async (asset: Asset) => {
    if (!window.confirm(`删除“${asset.name}”？笔记正文保留，图片引用将显示失效。`)) return;
    if (editing?.id === asset.id && !discard()) return;
    setBusy(true);
    try {
      await api.deleteAsset(token, asset.id);
      if (editing?.id === asset.id) setEditing(null);
      if (focused?.id === asset.id) setFocused(null);
      refresh(); onChanged?.(); onNotice("图片已删除，笔记引用将显示失效");
    } catch (error) {onError(error);} finally {setBusy(false);}
  };

  return <section className="panel asset-library">
    <div className="panel-title"><h3><Icon name="image"/>课程图片 <span className="count-pill">{page.total}</span></h3><span className="hint">整理图表，让每一张图都能找到出处</span></div>
    <form className="asset-upload" onSubmit={event => {event.preventDefault(); void upload();}}>
      <label>选择图片<input ref={fileInput} disabled={busy} type="file" multiple accept="image/png,image/jpeg,image/webp" onChange={event => {setFiles(Array.from(event.target.files ?? [])); setUploadFailures([]); setUploadSummary("");}}/></label>
      <label>图片说明<input disabled={busy} maxLength={500} value={alt} onChange={event => setAlt(event.target.value)} placeholder="选填；多张共用说明，留空使用文件名"/></label>
      <button className="primary" disabled={!files.length || busy}><Icon name="upload" size={16}/>导入图片</button>
    </form>
    <p className="asset-search-hint"><Icon name="info" size={14}/>可多选 PNG / JPEG / WebP，每批最多20张、每张≤10 MiB{files.length ? ` · 已选 ${files.length} 张` : ""}。查找仅匹配名称、说明与标签，图片内文字不会自动被识别。</p>
    <ImageUploadStatus progress={uploadProgress} failures={uploadFailures} summary={uploadSummary} busy={busy} retry={() => void upload(uploadFailures.map(item => item.file))} clear={() => {setUploadFailures([]); setUploadSummary("");}}/>
    <form className="asset-filters" aria-label="图片查找与筛选" onSubmit={event => {event.preventDefault(); filter({q: query});}}>
      <label className="asset-search"><span>查找图片</span><div><input maxLength={200} value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索名称、说明、标签…"/><button className="secondary" disabled={busy}><Icon name="search" size={16}/>查找</button></div></label>
      <label>标签<select value={filters.tag} disabled={busy} onChange={event => filter({tag: event.target.value})}><option value="">全部标签</option>{[...new Set([...page.tags, ...(filters.tag ? [filters.tag] : [])])].map(tag => <option key={tag} value={tag}>{tag}</option>)}</select></label>
      <label>图片来源<select value={filters.origin} disabled={busy} onChange={event => filter({origin: event.target.value as AssetFilters["origin"]})}><option value="all">全部来源</option><option value="captured">资料截图</option><option value="external">外部图片</option></select></label>
      <label>排序<select value={filters.sort} disabled={busy} onChange={event => filter({sort: event.target.value as AssetFilters["sort"]})}><option value="newest">最近导入</option><option value="updated">最近整理</option><option value="oldest">最早导入</option><option value="name">按名称</option></select></label>
      <button type="button" className="icon-button secondary" disabled={busy || loading} aria-label="刷新图片列表" onClick={refresh}><Icon name="refresh" size={16}/></button>
    </form>
    {(filters.q || filters.tag || filters.origin !== "all") && <div className="asset-filter-summary"><span>{filters.q && `“${filters.q}” · `}{filters.tag && `${filters.tag} · `}{loading ? "查找中…" : `找到 ${page.total} 张图片`}</span><button className="link-button" disabled={busy} onClick={reset}>清除筛选</button></div>}
    {editing && <div className="asset-editor" ref={editor}>
      <div className="panel-title"><h4><Icon name="edit" size={17}/>整理图片</h4><span className="hint">{dirty ? "有未保存修改" : "修改名称、说明或标签"}</span></div>
      <form onSubmit={event => {event.preventDefault(); void save();}}>
        <label>图片名称<input autoFocus maxLength={255} disabled={busy} value={draft.name} onChange={event => setDraft({...draft, name: event.target.value})}/></label>
        <label>图片说明<textarea maxLength={500} rows={3} disabled={busy} value={draft.alt} onChange={event => setDraft({...draft, alt: event.target.value})}/></label>
        <label>标签 <span className="hint">用逗号或顿号分隔，最多12个</span><input maxLength={500} disabled={busy} value={draft.tags} onChange={event => setDraft({...draft, tags: event.target.value})} placeholder="例如：重点、图表、第二章"/></label>
        {conflict && <div className="asset-conflict" role="alert"><strong>其他窗口已保存新的内容，本地输入已保留</strong><p>服务端名称：{conflict.name}</p><p>说明：{conflict.alt || "无"}</p><p>标签：{conflict.tags.join("、") || "无"}</p><span>可以先复制本地输入，再载入最新内容继续整理。</span><button type="button" className="secondary" onClick={() => startEdit(conflict)}>载入服务端内容</button></div>}
        <div className="asset-editor-actions"><button className="primary" disabled={busy || !dirty || Boolean(conflict)}><Icon name="check" size={15}/>{busy ? "处理中…" : "保存整理"}</button><button type="button" className="secondary" disabled={busy} onClick={() => {if (discard()) {setEditing(null); setConflict(null);}}}>关闭</button><small>原始文件：{editing.original_filename} · 来源和笔记链接保持有效</small></div>
      </form>
    </div>}
    {loading ? <p className="hint" role="status">正在读取课程图片…</p> : failed ? <div className="inline-retry" role="alert">图片列表暂未加载<button className="secondary" onClick={refresh}>重试</button></div> : page.items.length ? <div className="asset-grid">{page.items.map(asset => <article key={asset.id} className={editing?.id === asset.id ? "asset-editing" : ""}>
      <AssetImage token={token} id={asset.id} alt={asset.alt || asset.name}/>
      <strong>{asset.name}</strong>{asset.alt && <p className="asset-description">{asset.alt}</p>}
      <div className="asset-tags">{asset.tags.map(tag => <button className="asset-tag" key={tag} disabled={busy} onClick={() => filter({tag})}><Icon name="tag" size={11}/>{tag}</button>)}</div>
      <small>{(asset.size_bytes / 1024).toFixed(1)} KiB · {new Date(asset.created_at).toLocaleDateString("zh-CN")}</small>
      <span className="asset-source-label">{asset.source_version_id ? <><Icon name="link" size={13}/>{asset.source_locator_type === "slide" ? "幻灯片" : asset.source_locator_type === "preview_page" ? "预览页" : "来源页"} {asset.source_page} · 固定版本</> : <><Icon name="image" size={13}/>外部图片 · 未关联资料</>}</span>
      <div className="asset-card-actions"><button className="secondary" disabled={busy} onClick={() => startEdit(asset)}><Icon name="edit" size={14}/>整理</button>{asset.source_version_id && onSource && <button className="secondary" disabled={busy} onClick={() => void openSource(asset)}><Icon name="preview" size={14}/>回到原页</button>}<button className="secondary" disabled={busy} onClick={() => void showReferences(asset)}><Icon name="notes" size={14}/>引用位置</button><button className="secondary danger" disabled={busy} onClick={() => void remove(asset)} aria-label={`删除图片 ${asset.name}`}><Icon name="trash" size={14}/></button></div>
    </article>)}</div> : <div className="asset-empty"><Icon name={filters.q || filters.tag || filters.origin !== "all" ? "search" : "image"} size={28}/><strong>{filters.q || filters.tag || filters.origin !== "all" ? "没有匹配的图片" : "把重要图表收进课程图片库"}</strong><p>{filters.q || filters.tag || filters.origin !== "all" ? "试试其他关键词，或清除筛选。" : "导入图片，或在 PDF 阅读中保存当前页，再从笔记工具栏插入。"}</p></div>}
    {!loading && !failed && page.total > 0 && <div className="asset-pagination"><span>第 {Math.floor(filters.offset / filters.limit) + 1} / {Math.ceil(page.total / filters.limit)} 页 · 共 {page.total} 张</span><label>每页<select aria-label="每页图片数量" value={filters.limit} disabled={busy} onChange={event => filter({limit: Number(event.target.value)})}><option value={12}>12张</option><option value={24}>24张</option></select></label><button className="secondary" disabled={busy || !filters.offset} onClick={() => setFilters({...filters, offset: Math.max(0, filters.offset - filters.limit)})}>上一页</button><button className="secondary" disabled={busy || filters.offset + filters.limit >= page.total} onClick={() => setFilters({...filters, offset: filters.offset + filters.limit})}>下一页</button></div>}
    {focused && <div className="asset-reference-panel"><div className="panel-title"><h4><Icon name="notes" size={16}/>引用“{focused.name}”的笔记</h4><button className="icon-button secondary" aria-label="关闭图片引用列表" onClick={() => setFocused(null)}><Icon name="close" size={14}/></button></div>{references.length ? <div>{references.map(note => <button className="source-note-card" key={note.id} disabled={busy || !onNote} onClick={() => {if (discard() && onNote) {setEditing(null); requestAnimationFrame(() => onNote(note.id));}}}><Icon name="notes" size={15}/>{note.title}<Icon name="arrow" size={14}/></button>)}</div> : <p className="hint">暂无引用。可以从笔记工具栏插入这张图片。</p>}</div>}
  </section>;
}
