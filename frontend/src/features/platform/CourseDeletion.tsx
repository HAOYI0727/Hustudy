import { FormEvent, useEffect, useRef, useState } from "react";
import { api, ApiError, CourseDeletionPreview } from "../../api/client";

const labels: Record<string, string> = {documents: "资料", versions: "资料版本", assets: "有效图片", material_exports: "资料包", notes: "笔记", ai_results: "AI结果", remote_queries: "AI发送预览/任务", past_papers: "真题", exam_papers: "模拟卷", attempts: "作答记录", review_tasks: "关联复习任务"};
type Props = {token: string; courseId: string; onCancel: () => void; onDeleted: () => Promise<void>; onBusy: (busy: boolean) => void; onError: (e: unknown) => void};

export function CourseDeletion({token, courseId, onCancel, onDeleted, onBusy, onError}: Props) {
  const [preview, setPreview] = useState<CourseDeletionPreview | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const live = useRef(true);
  useEffect(() => {live.current = true; return () => {live.current = false;};}, []);
  useEffect(() => {
    let active = true;
    setLoading(true); setPreview(null); setConfirmation(""); setError("");
    void api.courseDeletionPreview(token, courseId).then(value => {if (active) setPreview(value);})
      .catch(async e => {if (active) {
        if (e instanceof ApiError && e.status === 404) {try {await onDeleted();} catch (reason) {onError(reason);} return;}
        setError(e instanceof Error ? e.message : "无法加载删除范围"); if (e instanceof ApiError && e.status === 401) onError(e);
      }})
      .finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [token, courseId, reload]);
  const remove = async (event: FormEvent) => {
    event.preventDefault();
    if (!preview || busy || loading || confirmation !== preview.course.name) return;
    setBusy(true); onBusy(true); setError("");
    try {
      await api.deleteCourse(token, courseId, preview.course.revision);
      if (live.current) {
        try {await onDeleted();} catch (e) {onError(e);}
      }
    } catch (e) {
      if (!live.current) return;
      if (e instanceof ApiError && e.status === 404) {try {await onDeleted();} catch (reason) {onError(reason);} return;}
      setError(e instanceof ApiError && e.status === 409 ? "课程已被其他窗口修改。请重新加载影响范围，再核对课程名称。" : e instanceof Error ? e.message : "删除失败，请重试");
      if (e instanceof ApiError && e.status === 409) setPreview(null);
      if (e instanceof ApiError && e.status === 401) onError(e);
    } finally {if (live.current) {setBusy(false); onBusy(false);}}
  };
  return <form className="course-delete-panel" onSubmit={remove}>
    <h2 id="course-editor-title">确认删除课程</h2><p>将移除课程及相关学习记录，停止资料读取、检索与后台处理。其他课程、独立复习任务与外部笔记正文保留；引用此课程的来源会显示失效。</p>
    <p className="course-conflict"><strong>当前没有恢复入口。</strong>请先保存需要保留的数据；课程资料包只含资料，不能替代全部学习记录备份。</p>
    {loading ? <p role="status">正在核对影响范围…</p> : preview && <><strong>{preview.course.name}</strong><dl className="course-delete-counts">{Object.entries(preview.counts).map(([key, value]) => <div key={key}><dt>{labels[key] || key}</dt><dd>{value}</dd></div>)}</dl><p className="hint">数量为当前预览，删除时针对整门课程。</p><label>输入课程名称确认<input autoComplete="off" value={confirmation} disabled={busy} onChange={e => setConfirmation(e.target.value)} placeholder={preview.course.name}/></label></>}
    {error && <p className="course-conflict" role="alert">{error}</p>}
    <div className="course-editor-actions"><button type="button" className="secondary" disabled={busy || loading} onClick={() => setReload(value => value + 1)}>重新核对范围</button><button type="button" className="secondary" disabled={busy} onClick={onCancel}>返回整理</button><button className="danger" disabled={busy || loading || !preview || confirmation !== preview.course.name}>{busy ? "删除中…" : "确认删除课程"}</button></div>
  </form>;
}
