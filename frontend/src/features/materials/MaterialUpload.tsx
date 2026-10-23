import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type DocumentItem, type Job } from "../../api/client";
import { Icon } from "../../components/Icon";
import { documentBatchError, documentFileError, uploadDocuments, type DocumentUpload } from "./uploadDocuments";
import "./material-flow.css";
import {ProcessingService} from "./ProcessingService";

type Props = {
  token: string; courseId: string; active: DocumentItem | null; disabled: boolean;
  pending?:boolean;
  onBeforeUpload: () => boolean; onBusy: (busy: boolean) => void;
  onComplete: (jobs: Job[]) => Promise<void>; onError: (error: unknown) => void;
};
const labels = {waiting: "待上传", uploading: "上传中", saved: "已保存", existing: "已存在", failed: "未上传成功", paused: "已暂停"};

export function MaterialUpload({token, courseId, active, disabled, pending=false, onBeforeUpload, onBusy, onComplete, onError}: Props) {
  const [mode, setMode] = useState("new");
  const [rows, setRows] = useState<DocumentUpload[]>([]);
  const [target, setTarget] = useState<{id: string; name: string} | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const running = useRef(false);
  const outstanding = rows.filter(row => !["saved", "existing"].includes(row.state));
  const saved = rows.length - outstanding.length;
  useEffect(() => {
    const navigate = (event: Event) => {
      if (running.current || (outstanding.length && !window.confirm("还有尚未上传成功的文件，放弃当前上传队列并离开？"))) event.preventDefault();
    };
    const change = (event: Event) => {if (running.current) event.preventDefault();};
    const unload = (event: BeforeUnloadEvent) => {if (running.current || outstanding.length) {event.preventDefault(); event.returnValue = "";}};
    window.addEventListener("hustudy:before-navigate", navigate);
    window.addEventListener("hustudy:before-material-change", change);
    window.addEventListener("beforeunload", unload);
    return () => {window.removeEventListener("hustudy:before-navigate", navigate); window.removeEventListener("hustudy:before-material-change", change); window.removeEventListener("beforeunload", unload);};
  }, [outstanding.length]);
  const choose = (files: File[]) => {
    setDragging(false);
    if (disabled || running.current || !files.length) return;
    const error = documentBatchError(files, mode === "version");
    if (error) {onError(new Error(error)); return;}
    if (outstanding.length && !window.confirm("替换当前尚未上传成功的文件队列？")) return;
    setTarget(mode === "version" && active ? {id: active.id, name: active.name} : null);
    setRows(files.map(file => ({id: crypto.randomUUID(), file, state: "waiting"})));
    if (input.current) input.current.value = "";
  };
  const upload = async (event: FormEvent) => {
    event.preventDefault();
    if (running.current || disabled || !outstanding.length || !onBeforeUpload()) return;
    // Freeze the destination and queue before the first asynchronous request.
    const destination = target;
    running.current = true; setUploading(true); onBusy(true);
    try {
      const completed = await uploadDocuments(rows, file => destination ? api.uploadVersion(token, destination.id, file) : api.uploadDocument(token, courseId, file), row => setRows(current => current.map(item => item.id === row.id ? row : item)));
      if (completed.length) await onComplete(completed.map(row => row.job!));
    } catch (error) {onError(error);}
    finally {running.current = false; setUploading(false); onBusy(false);}
  };
  const clear = () => {setRows([]); setTarget(null); if (input.current) input.current.value = "";};
  return <form className={`upload-zone compact-upload material-upload${dragging ? " is-dragging" : ""}`} onSubmit={upload}
    onDragOver={event => {event.preventDefault(); if (!disabled) setDragging(true);}}
    onDragLeave={event => {if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);}}
    onDrop={event => {event.preventDefault(); choose(Array.from(event.dataTransfer.files));}}>
    <select aria-label="上传方式" disabled={disabled || !!outstanding.length} value={mode} onChange={event => {setMode(event.target.value); clear();}}><option value="new">导入新资料</option><option value="version" disabled={!active}>为选中资料添加新版本</option></select>
    <span className="material-upload-symbol"><Icon name={rows.length ? "file" : "upload"} size={26}/></span>
    <strong>{rows.length === 1 ? rows[0].file.name : rows.length ? `本批 ${rows.length} 份资料` : "把课件放进知识库"}</strong>
    <small>{target ? `新版本目标：${target.name}` : mode === "version" ? "选择一份文件，保留旧版本和引用" : "支持多选与拖放，每批最多 20 份"}</small>
    <ProcessingService token={token} pending={pending||uploading}/>
    <input ref={input} className="sr-only" aria-label="选择课程文件" type="file" multiple={mode === "new"} accept=".pptx,.pdf,.docx,.md,.markdown,.txt" disabled={disabled} onChange={event => choose(Array.from(event.target.files || []))}/>
    <div className="upload-actions"><button type="button" className="secondary" disabled={disabled} onClick={() => input.current?.click()}><Icon name="folder" size={16}/>{rows.length ? "重新选择" : "选择文件"}</button>{!!rows.length && <button type="button" className="icon-button secondary" aria-label="取消所选文件" disabled={disabled} onClick={clear}><Icon name="close" size={16}/></button>}</div>
    {!!rows.length && <section className="document-upload-queue" aria-label="资料上传队列">
      <p role="status">已保存 {saved} / {rows.length} 份{uploading ? " · 正在逐份上传" : outstanding.length ? " · 等待操作" : " · 本批完成"}</p>
      <progress aria-label="资料批次进度" max={rows.length} value={saved}/>
      <ol>{rows.map(row => <li key={row.id} data-state={row.state}><div><span title={row.file.name}>{row.file.name}</span><strong>{labels[row.state]}</strong></div>{(row.message || documentFileError(row.file)) && <small>{row.message || documentFileError(row.file)}</small>}</li>)}</ol>
      {!!saved && <small>原件已入库，解析与索引进度见处理记录。</small>}
    </section>}
    <button className="primary" disabled={disabled || !outstanding.length || (mode === "version" && !target)}><Icon name={uploading ? "refresh" : "upload"} className={uploading ? "is-spinning" : ""}/>{uploading ? "正在上传…" : rows.some(row => ["failed", "paused"].includes(row.state)) ? "重试未成功文件" : mode === "version" ? "保存为新版本" : "上传并开始整理"}</button>
    <small>PPTX / PDF / DOCX / MD / TXT · 每份≤30 MiB · 每批≤100 MiB</small>
  </form>;
}
