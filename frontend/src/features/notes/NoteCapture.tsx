import {useEffect, useRef, useState} from 'react';
import {api, ApiError, type NoteCapture as Capture} from '../../api/client';
import {captureText} from './captureText';

type Draft = {text: string; inserted: boolean; edited: boolean};
type Upload = {file: File; id: string; done: boolean; error?: string};
export function NoteCapture({token, courseId, isOpen, disabled, onInsert, onError, onBusy}: {
  token: string; courseId: string; isOpen: boolean; disabled: boolean;
  onInsert: (text: string) => boolean; onError: (error: unknown) => void; onBusy: (busy: boolean) => void;
}) {
  const [rows, setRows] = useState<Capture[]>([]), [uploads, setUploads] = useState<Upload[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({}), [selected, setSelected] = useState('');
  const [caps, setCaps] = useState<Awaited<ReturnType<typeof api.captureCapabilities>>>();
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [recording, setRecording] = useState(false), [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null), stream = useRef<MediaStream | null>(null), timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const mounted = useRef(true), actionLock = useRef(false), generation = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const current = rows.find(row => row.id === selected), draft = drafts[selected];
  const report = (e: unknown) => {setError(e instanceof Error ? e.message : '操作失败，请重试'); if (e instanceof ApiError && e.status === 401) onError(e);};
  const merge = (items: Capture[]) => {setRows(items); setDrafts(old => {const next = {...old}; for (const row of items) {const text = captureText(row.result); if (text && !next[row.id]) next[row.id] = {text, inserted: false, edited: false};} return next;});};
  useEffect(() => {
    mounted.current = true;
    return () => {mounted.current = false; clearInterval(timer.current); if (recorder.current?.state === 'recording') recorder.current.stop(); stream.current?.getTracks().forEach(track => track.stop());};
  }, []);
  useEffect(() => {onBusy(busy || recording);}, [busy, recording, onBusy]);
  useEffect(() => {
    generation.current++; setRows([]); setDrafts({}); setUploads([]); setSelected(''); setError('');
  }, [courseId]);
  useEffect(() => {
    if (!isOpen) {if (recorder.current?.state === 'recording') recorder.current.stop(); return;}
    let live = true, handle: ReturnType<typeof setTimeout>;
    const refresh = async () => {try {const result = await api.captures(token, courseId); if (live) merge(result);} catch (e) {if (live) {report(e); if (e instanceof ApiError && e.status === 401) return;}} if (live) handle = setTimeout(refresh, 2000);};
    void api.captureCapabilities(token).then(value => {if (live) setCaps(value);}).catch(e => {if (live) report(e);});
    void refresh();
    return () => {live = false; clearTimeout(handle);};
  }, [token, courseId, isOpen]);
  const unsaved = Object.values(drafts).some(item => item.edited && !item.inserted) || uploads.some(item => !item.done);
  useEffect(() => {
    const unload = (event: BeforeUnloadEvent) => {if (unsaved || recording || busy) {event.preventDefault(); event.returnValue = '';}};
    const leave = (event: Event) => {if (recording || busy || (unsaved && !window.confirm('识别结果仍保留在任务列表，但尚未插入的手动修改将丢失。确定离开吗？'))) event.preventDefault();};
    window.addEventListener('beforeunload', unload); window.addEventListener('hustudy:before-material-change', leave); window.addEventListener('hustudy:before-navigate', leave);
    return () => {window.removeEventListener('beforeunload', unload); window.removeEventListener('hustudy:before-material-change', leave); window.removeEventListener('hustudy:before-navigate', leave);};
  }, [unsaved, recording, busy]);
  const run = async (action: () => Promise<void>) => {
    if (actionLock.current || disabled || recording) return;
    actionLock.current = true; setBusy(true); setError('');
    try {await action();} catch (e) {report(e);} finally {actionLock.current = false; if (mounted.current) setBusy(false);}
  };
  const upload = () => void run(async () => {
    const queue = uploads.map(item => ({...item}));
    for (const item of queue) {
      if (item.done) continue;
      try {if (item.file.size > 20 * 1024 * 1024) throw new Error('每份文件最多20MiB'); const row = await api.uploadCapture(token, item.file, courseId, item.id); item.done = true; item.error = ''; setSelected(row.id);}
      catch (e) {item.error = e instanceof Error ? e.message : '上传失败'; if (e instanceof ApiError && (e.status === 0 || e.status === 401 || e.status >= 500)) {setUploads([...queue]); throw e;}}
      setUploads([...queue]);
    }
    merge(await api.captures(token, courseId));
  });
  const edit = (text: string) => setDrafts(old => ({...old, [selected]: {text, edited: true, inserted: false}}));
  const insert = () => {
    if (busy || disabled || recording || !draft?.text.trim()) return;
    if (onInsert(draft.text)) setDrafts(old => ({...old, [selected]: {...old[selected], inserted: true}}));
  };
  const startRecording = async () => {
    if (actionLock.current || busy || recording || disabled) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {setError('此浏览器不支持录音，请上传音频文件；麦克风需要localhost或HTTPS'); return;}
    actionLock.current = true; setBusy(true); setError('');
    const at = generation.current;
    try {
      const media = await navigator.mediaDevices.getUserMedia({audio: true});
      if (!mounted.current || at !== generation.current) {media.getTracks().forEach(track => track.stop()); return;}
      stream.current = media;
      const mime = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'].find(value => MediaRecorder.isTypeSupported(value));
      const instance = new MediaRecorder(media, mime ? {mimeType: mime} : undefined), chunks: BlobPart[] = [];
      recorder.current = instance; setSeconds(0); setRecording(true);
      let elapsed = 0;
      instance.ondataavailable = event => {if (event.data.size) chunks.push(event.data);};
      instance.onerror = () => {setError('录音中断，请检查麦克风后重试'); instance.stop();};
      instance.onstop = () => {
        clearInterval(timer.current); media.getTracks().forEach(track => track.stop());
        if (!mounted.current || at !== generation.current) return;
        setRecording(false);
        const ext = instance.mimeType.includes('mp4') ? 'm4a' : instance.mimeType.includes('ogg') ? 'ogg' : 'webm';
        const file = new File(chunks, `录音-${new Date().toISOString().replace(/[:.]/g, '-')}.${ext}`, {type: instance.mimeType});
        if (file.size) setUploads(old => [...old, {file, id: crypto.randomUUID(), done: false}]);
      };
      instance.start(1000);
      timer.current = setInterval(() => {elapsed++; setSeconds(elapsed); if (elapsed >= 299 && instance.state === 'recording') instance.stop();}, 1000);
    } catch {stream.current?.getTracks().forEach(track => track.stop()); setRecording(false); setError('无法录音，请允许麦克风权限，或直接上传音频文件');}
    finally {actionLock.current = false; setBusy(false);}
  };
  return <section className="note-capture">
    <p>上传手写照片、扫描件、PDF 或 Word（.docx），识别后核对文字，插入当前笔记的光标处或替换选中文字。</p>
    <p className="hint">每批最多20份，每份20MiB；PDF最多40页。文字识别在本机后台进行，需要保持worker运行。音频文件转写也支持，最长5分钟；实时语音输入请使用笔记编辑器里的“语音输入”。</p>
    <p className="hint">本地OCR：{caps ? caps.ocr ? '已安装' : '未安装' : '检测中'}。识别文本可直接编辑；关闭窗口后保留，插入后随当前笔记保存。</p>
    <button disabled={busy || recording} onClick={() => void api.captureCapabilities(token).then(setCaps).catch(report)}>重新检测识别组件</button>
    <input ref={input} type="file" hidden multiple accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.wav,.mp3,.m4a,.webm,.ogg,.mp4" aria-label="选择识别文件" onChange={event => {const files = Array.from(event.target.files || []); event.target.value = ''; if (files.length > 20) {setError('每批最多20份'); return;} setUploads(files.map(file => ({file, id: crypto.randomUUID(), done: false})));}}/>
    <div className="note-folder-actions"><button className="primary" disabled={busy || recording || disabled || uploads.some(item => !item.done)} onClick={() => input.current?.click()}>选择识别文件</button><button disabled={busy || recording || disabled || !uploads.some(item => !item.done)} onClick={upload}>上传并识别 / 重试上传</button></div>
    <details><summary>本地录音转写（可选）</summary><p className="hint">需要本地Whisper模型。{caps?.speech ? '模型已就绪。' : '尚未配置模型；编辑器的实时语音输入无需安装这个模型。'}</p><button disabled={busy || disabled || !caps?.speech} onClick={() => recording ? recorder.current?.stop() : void startRecording()}>{recording ? `停止录音（${seconds}秒）` : '开始本地录音'}</button></details>
    {uploads.length > 0 && <ul>{uploads.map(item => <li key={item.id}>{item.file.name}：{item.done ? '已提交后台' : item.error || '待上传'}</li>)}</ul>}
    {uploads.some(item => !item.done) && <button disabled={busy || recording} onClick={() => {if (window.confirm('放弃未上传文件？')) setUploads([]);}}>清空上传列表</button>}
    {error && <p role="alert">{error}</p>}
    <label>识别任务<select aria-label="识别任务" value={selected} disabled={busy || recording} onChange={event => setSelected(event.target.value)}><option value="">选择识别任务</option>{rows.map(row => <option key={row.id} value={row.id}>{row.filename} · {({QUEUED: '排队中', RUNNING: '处理中', SUCCEEDED: '已完成', FAILED: '失败', CANCELLED: '已取消'} as Record<string, string>)[row.status]}</option>)}</select></label>
    {current && <><p role="status">{current.error || (current.status === 'QUEUED' ? '等待后台识别；若一直排队，请检查worker是否运行。' : current.status === 'RUNNING' ? '正在识别，可关闭窗口后回来查看。' : current.status === 'CANCELLED' ? '任务已取消，已有识别文本仍可使用。' : '识别已完成，请核对文本。')}</p>
      <button disabled={busy || recording} onClick={() => void run(async () => {const blob = await api.captureFile(token, current.id); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = current.filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 10000);})}>下载原文件核对</button>
      <button disabled={busy || recording} onClick={() => void run(async () => {if (!window.confirm('移除此识别任务及原文件？已插入的笔记正文不受影响，尚未插入的修改将丢失。')) return; await api.removeCapture(token, current.id); setRows(old => old.filter(row => row.id !== current.id)); setDrafts(old => {const next = {...old}; delete next[current.id]; return next;}); setSelected('');})}>移除任务 / 取消处理</button>
      {draft && <>
        <details><summary>查看原始识别文本与来源位置</summary>{current.result.parts?.length ? current.result.parts.map((part, index) => <section key={index}><small>{part.location}</small><pre className="capture-original">{part.text}</pre></section>) : <pre className="capture-original">{current.result.text}</pre>}</details>
        {current.result.warnings?.map((warning, index) => <p className="hint" key={index}>{warning}</p>)}
        <label>核对识别文字<textarea aria-label="识别文字" rows={12} value={draft.text} disabled={busy} onChange={event => edit(event.target.value)}/></label>
        <button className="primary" disabled={busy || recording || disabled || !draft.text.trim()} onClick={insert}>插入正文</button>
        <p className="hint">只插入上面的文本，插入后可在编辑器撤销。页号和时间仅供核对，不添加到正文。</p>
      </>}
    </>}
  </section>;
}
