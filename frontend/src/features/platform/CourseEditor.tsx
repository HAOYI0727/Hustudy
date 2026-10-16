import { FormEvent, useEffect, useRef, useState } from "react";
import { api, ApiError, Course, CourseMetadata } from "../../api/client";
import { Icon } from "../../components/Icon";
import { CourseDeletion } from "./CourseDeletion";

export const courseTags = (text: string) => [...new Set(text.split(/[,，、\n]/).map(tag => tag.trim()).filter(Boolean))];
export const validCourseTags = (tags: string[]) => tags.length <= 12 && tags.every(tag => Array.from(tag).length <= 32);
type Props = {course: Course; token: string; onClose: () => void; onSaved: () => Promise<void>; onDeleted: () => Promise<void>; onRefresh: () => Promise<void>; onError: (e: unknown) => void};
const fields = (course: Course) => ({name: course.name, description: course.description || "", category: course.category, tags: course.tags.join("、")});

export function CourseEditor({course, token, onClose, onSaved, onDeleted, onRefresh, onError}: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [base, setBase] = useState(course);
  const [draft, setDraft] = useState(() => fields(course));
  const [conflict, setConflict] = useState<Course | null>(null);
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [deleting, setDeleting] = useState(false);
  const alive = useRef(true);
  const dirty = JSON.stringify(draft) !== JSON.stringify(fields(base));
  const close = () => {if (!busy && (!dirty || window.confirm("课程整理尚未保存，放弃这些修改？"))) onClose();};
  useEffect(() => {
    alive.current = true;
    dialog.current?.showModal();
    return () => {alive.current = false; dialog.current?.close();};
  }, []);
  useEffect(() => {
    const guard = (event: Event) => {if (busy || (dirty && !window.confirm("课程整理尚未保存，放弃修改并离开？"))) event.preventDefault();};
    const unload = (event: BeforeUnloadEvent) => {if (busy || dirty) {event.preventDefault(); event.returnValue = "";}};
    window.addEventListener("hustudy:before-navigate", guard);
    window.addEventListener("beforeunload", unload);
    return () => {window.removeEventListener("hustudy:before-navigate", guard); window.removeEventListener("beforeunload", unload);};
  }, [busy, dirty]);
  const save = async (event: FormEvent) => {
    event.preventDefault(); if (busy || conflict || !dirty) return;
    const tags = courseTags(draft.tags);
    if (!draft.name.trim() || !validCourseTags(tags)) {setErrorMessage("名称不能为空，标签最多12个，每个不超过32字"); return;}
    const next: CourseMetadata = {name: draft.name.trim(), description: draft.description.trim() || null, category: draft.category.trim() || "未分类", tags};
    const changes: Partial<CourseMetadata> = {};
    if (next.name !== base.name) changes.name = next.name;
    if (next.description !== (base.description || null)) changes.description = next.description;
    if (next.category !== base.category) changes.category = next.category;
    if (JSON.stringify(next.tags) !== JSON.stringify(base.tags)) changes.tags = next.tags;
    if (!Object.keys(changes).length) {onClose(); return;}
    setBusy(true);
    setErrorMessage("");
    try {
      await api.updateCourse(token, base.id, {revision: base.revision, ...changes});
      if (!alive.current) return;
      // The update is persisted even if the following list refresh fails.
      onClose();
      try {await onSaved();} catch (error) {onError(error);}
    } catch (error) {
      if (!alive.current) return;
      if (error instanceof ApiError && error.status === 409 && error.details?.server_course) {
        setConflict(error.details.server_course as Course);
        // Refresh the cards without changing the draft or emitting a stale global error.
        void onRefresh().catch(onError);
      } else {
        setErrorMessage(error instanceof Error ? error.message : "保存失败，请稍后重试");
        onError(error);
      }
    } finally {if (alive.current) setBusy(false);}
  };
  return <dialog ref={dialog} className="course-editor" aria-labelledby="course-editor-title" onCancel={event => {event.preventDefault(); close();}}>
    {deleting ? <CourseDeletion token={token} courseId={base.id} onBusy={setBusy} onError={onError} onCancel={() => setDeleting(false)} onDeleted={async () => {onClose(); await onDeleted();}}/> : <form onSubmit={save}>
      <div className="panel-title"><div><p className="eyebrow">COURSE DETAILS</p><h2 id="course-editor-title">整理课程空间</h2></div><button type="button" className="secondary" aria-label="关闭课程整理" disabled={busy} onClick={close}>×</button></div>
      <p className="hint">名称和标签帮助你找到课程；已有资料与笔记仍属于同一个课程。</p>
      {errorMessage && <p className="course-conflict" role="alert">{errorMessage}</p>}
      <label>课程名称<input autoFocus required maxLength={200} value={draft.name} disabled={busy} onChange={e => setDraft({...draft, name: e.target.value})}/></label>
      <label>课程描述<textarea rows={3} maxLength={5000} value={draft.description} disabled={busy} onChange={e => setDraft({...draft, description: e.target.value})}/></label>
      <label>课程分类<input maxLength={64} placeholder="例如：专业必修" value={draft.category} disabled={busy} onChange={e => setDraft({...draft, category: e.target.value})}/></label>
      <label>课程标签<input maxLength={1000} placeholder="例如：大二、期末复习" value={draft.tags} disabled={busy} onChange={e => setDraft({...draft, tags: e.target.value})}/><small className="hint">用逗号或顿号分隔，最多12个，每个32字。</small></label>
      {conflict && <section className="course-conflict" role="alert"><strong>另一个窗口已保存这门课程</strong><p>当前名称：{conflict.name} · 分类：{conflict.category}</p><p>描述：{conflict.description || "无"}</p><p>标签：{conflict.tags.join("、") || "无"}</p><p>本地输入已保留。请核对后选择：</p><div className="course-editor-actions"><button type="button" className="secondary" onClick={() => {setBase(conflict); setDraft(fields(conflict)); setConflict(null);}}>加载服务器内容</button><button type="button" className="secondary" onClick={() => {if (window.confirm("保留当前本地输入，并以服务器最新版为基础再次保存？")) {setBase(conflict); setConflict(null);}}}>保留本地输入再保存</button></div></section>}
      <div className="course-editor-actions"><button type="button" className="secondary course-remove-link" disabled={busy} onClick={() => {if (!dirty || window.confirm("课程整理尚未保存，放弃这些修改并核对删除范围？")) {setDraft(fields(base)); setConflict(null); setErrorMessage(""); setDeleting(true);}}}>删除课程…</button><span className="hint">{dirty ? "有尚未保存的修改" : "内容已与当前版本一致"}</span><button type="button" className="secondary" disabled={busy} onClick={close}>取消</button><button className="primary" disabled={busy || !dirty || !!conflict || !draft.name.trim()}><Icon name="check" size={16}/>{busy ? "保存中…" : "保存整理"}</button></div>
    </form>}
  </dialog>;
}
