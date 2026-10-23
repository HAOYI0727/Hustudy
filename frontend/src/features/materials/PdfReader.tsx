import { FormEvent, useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy, type RenderTask } from "pdfjs-dist/legacy/build/pdf.mjs";
import workerUrl from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?url";
import { Icon } from "../../components/Icon";
GlobalWorkerOptions.workerSrc = workerUrl;
const localAssets = `${import.meta.env.BASE_URL}pdfjs-assets/`;
const MAX_PIXELS = 3_000_000;

type Props = { onPageChange?: (page:number)=>void; url: string; initialPage?: number; sourceType: string; name: string; onCapture: (file: File, page: number) => Promise<void>; onDownload: () => void; onTranscribe?: (page:number) => void };
export default function PdfReader({ url, initialPage = 1, sourceType, name, onCapture, onDownload, onTranscribe, onPageChange }: Props) {
  const [loadAttempt,setLoadAttempt] = useState(0);
  const [pdf, setPdf] = useState<PDFDocumentProxy>();
  const [page, setPage] = useState(initialPage);
  const [pageInput, setPageInput] = useState(String(initialPage));
  const [zoom, setZoom] = useState(1);
  const [width, setWidth] = useState(600);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [diagnostic,setDiagnostic] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [captureNotice, setCaptureNotice] = useState("");
  const [captureFailed, setCaptureFailed] = useState(false);
  const host = useRef<HTMLDivElement>(null);
  const rendered = useRef<{canvas: HTMLCanvasElement; page: number; url: string} | undefined>(undefined);
  const generation = useRef(0);
  const mounted = useRef(true);
  const pageCallback=useRef(onPageChange);pageCallback.current=onPageChange;
  useEffect(()=>{if(ready)pageCallback.current?.(page);},[ready,page]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const pageLabel = sourceType === "slide" ? "幻灯片" : sourceType === "preview_page" ? "预览页" : "页";
  useEffect(() => {
    let active = true; let task: ReturnType<typeof getDocument> | undefined;
    setPdf(undefined); setError(""); setDiagnostic(""); setReady(false);
    const controller = new AbortController();
    void fetch(url,{signal:controller.signal}).then(r => {if(!r.ok)throw new Error("文件读取失败");return r.arrayBuffer();}).then(buffer => {
      if (!active) return;
      task = getDocument({data: new Uint8Array(buffer), cMapUrl: localAssets + "cmaps/", cMapPacked: true, standardFontDataUrl: localAssets + "standard_fonts/", wasmUrl: localAssets + "wasm/", iccUrl: localAssets + "iccs/", enableXfa: false, useSystemFonts: true});
      return task.promise;
    }).then(document => {
      if (!active || !document) return;
      setPdf(document); const chosen = Math.max(1, Math.min(initialPage, document.numPages)); setPage(chosen); setPageInput(String(chosen));
    }).catch(reason => { if (active) setError(reason?.name === "PasswordException" ? "此PDF需要密码，请先另存为不加密PDF后上传。" : "PDF 未能打开。可重试预览，或下载原件查看；正文仍可阅读。"); });
    return () => { active = false; controller.abort(); generation.current++; rendered.current = undefined; void task?.destroy().catch(() => undefined); };
  }, [url, initialPage, loadAttempt]);
  useEffect(() => {
    if (!host.current) return;
    const observer = new ResizeObserver(entries => setWidth(Math.max(240, entries[0].contentRect.width - 32)));
    observer.observe(host.current); return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!pdf) return;
    const current = ++generation.current; let task: RenderTask | undefined; let active = true;
    setReady(false); setError(""); setCaptureNotice(""); rendered.current = undefined; host.current?.replaceChildren();
    void pdf.getPage(page).then(async source => {
      if (!active) return;
      const base = source.getViewport({scale: 1});
      const displayScale = Math.min(width / base.width, 1.5) * zoom;
      const requested = displayScale * Math.min(window.devicePixelRatio || 1, 2);
      const scale = Math.min(requested, Math.sqrt(MAX_PIXELS / (base.width * base.height)), 12000 / Math.max(base.width, base.height));
      const viewport = source.getViewport({scale});
      const canvas = document.createElement("canvas"); canvas.width = Math.max(1, Math.floor(viewport.width)); canvas.height = Math.max(1, Math.floor(viewport.height));
      canvas.style.width = `${base.width * displayScale}px`; canvas.style.height = `${base.height * displayScale}px`;
      canvas.setAttribute("role", "img"); canvas.setAttribute("aria-label", `${name} · ${pageLabel} ${page}`);
      task = source.render({canvas, viewport}); await task.promise;
      if (active && current === generation.current && host.current) { host.current.replaceChildren(canvas); rendered.current = {canvas, page, url}; setReady(true); }
    }).catch(reason => { if (active && current === generation.current) {setError("这一页暂时无法渲染。可重试、切换其他页，或下载原件查看。");setDiagnostic(reason instanceof Error ? `${reason.name}: ${reason.message}`.slice(0,300) : "PDF页面渲染失败");} });
    return () => { active = false; task?.cancel(); };
  }, [pdf, page, width, zoom, name, pageLabel, url]);
  const go = (target: number) => { if (!pdf) return; const next = Math.max(1, Math.min(target, pdf.numPages)); setPageInput(String(next)); if (next === page) return; rendered.current = undefined; setReady(false); setPage(next); };
  const jump = (e: FormEvent) => { e.preventDefault(); const target = Number(pageInput); if (Number.isInteger(target) && target >= 1 && pdf && target <= pdf.numPages) go(target); else setPageInput(String(page)); };
  const capture = async () => {
    const frame = rendered.current;
    if (!ready || !frame || frame.page !== page || frame.url !== url || capturing) return;
    const current = generation.current; setCapturing(true); setCaptureNotice(""); setCaptureFailed(false);
    try {
      const blob = await new Promise<Blob>((resolve, reject) => frame.canvas.toBlob(b => b ? resolve(b) : reject(new Error("截图生成失败")), "image/png"));
      if (current !== generation.current || frame !== rendered.current) return;
      await onCapture(new File([blob], `preview-page-${page}.png`, {type: "image/png"}), page);
      if (current === generation.current) setCaptureNotice("已保存到课程图片，可在笔记工具栏插入。");
    } catch (reason) { if (current === generation.current) { setCaptureFailed(true); setCaptureNotice(reason instanceof Error ? reason.message : "截图保存失败，请重试"); } }
    finally { if (mounted.current) setCapturing(false); }
  };
  return <section className="pdf-reader" aria-label="PDF 按页阅读">
    <div className="pdf-reader-toolbar"><div className="pdf-page-controls"><button className="icon-button secondary" aria-label="上一页" disabled={!pdf || page <= 1 || capturing} onClick={() => go(page - 1)}><Icon name="arrow" className="reverse-arrow"/></button><form onSubmit={jump}><label htmlFor="pdf-page-number">{pageLabel}</label><input id="pdf-page-number" type="number" min={1} max={pdf?.numPages || 1} value={pageInput} disabled={!pdf || capturing} onChange={e => setPageInput(e.target.value)} onBlur={jump}/><span>/ {pdf?.numPages || "…"}</span></form><button className="icon-button secondary" aria-label="下一页" disabled={!pdf || page >= pdf.numPages || capturing} onClick={() => go(page + 1)}><Icon name="arrow"/></button></div><select aria-label="PDF 阅读缩放" value={zoom} disabled={capturing} onChange={e => setZoom(Number(e.target.value))}>{[.75, 1, 1.25, 1.5, 2].map(value => <option key={value} value={value}>{value === 1 ? "适合宽度" : Math.round(value * 100) + "%"}</option>)}</select><button className="secondary" disabled={!ready || capturing} onClick={() => void capture()}><Icon name={capturing ? "refresh" : "image"} size={16}/>{capturing ? "正在保存…" : "保存当前页图片"}</button></div>
    {onTranscribe && <button className="secondary transcript-page-button" disabled={!ready || capturing} onClick={() => onTranscribe(page)}><Icon name="edit" size={15}/>补录本页文字</button>}
    <p className="pdf-source-note"><Icon name="info" size={14}/>{sourceType === "preview_page" ? "DOCX 转换后的预览页，不能当作 Word 正文引用页码。" : "截图保存当前资料版本和页号；图中文字不会自动进入检索。"}</p>
    {(!ready && !error) && <p className="material-loading" role="status"><Icon name="refresh" className="is-spinning"/>正在渲染{pageLabel} {page}…</p>}
    {error && <div className="pdf-error" role="alert"><Icon name="info"/>{error}{diagnostic && <details><summary>查看错误详情</summary><code>{diagnostic}</code></details>}<button className="secondary" onClick={()=>setLoadAttempt(value=>value+1)}><Icon name="refresh" size={16}/>重试打开</button><button className="secondary" onClick={onDownload}><Icon name="download" size={16}/>下载原件</button></div>}
    <div ref={host} className={"pdf-canvas-stage" + (!ready ? " rendering" : "")}/>
    {captureNotice && <p className={"pdf-capture-notice" + (captureFailed ? " capture-failed" : "")} role={captureFailed ? "alert" : "status"}>{captureNotice}</p>}
    <p className="hint">当前为按页图像预览。需要选取正文引用时，返回文本与引用。</p>
  </section>;
}
