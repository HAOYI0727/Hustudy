import {useMemo, useState} from 'react';
import type {NoteFolder} from '../../api/client';
import {NotesDialog} from './NotesDialog';
import {mergeText, mergeField, resolveText} from './noteMerge';
import type {NoteDraft} from './noteRecovery';
import {folderPath} from './organization';
import {downloadDraft} from './draftDownload';
import './note-merge.css';

type Side = 'local' | 'server';
type Field = 'title' | 'tags' | 'folder_id';
type Props = {
  base: NoteDraft | null; local: NoteDraft; server: NoteDraft & {revision: number};
  folders: NoteFolder[]; onClose: () => void; onApply: (draft: NoteDraft) => string;
};

/** A local preview only. The parent retains the original draft and controls explicit saving. */
export function NoteMergeDialog({base, local, server, folders, onClose, onApply}: Props) {
  const plan = useMemo(() => mergeText(base?.content ?? null, local.content, server.content), [base, local, server]);
  const fields = useMemo(() => base ? {
    title: mergeField(base.title, local.title, server.title),
    tags: mergeField(base.tags, local.tags, server.tags),
    folder_id: mergeField(base.folder_id ?? null, local.folder_id ?? null, server.folder_id ?? null),
  } : null, [base, local, server]);
  const [choices, setChoices] = useState<Record<string, Side>>({});
  const [metadata, setMetadata] = useState<Partial<Record<Field, Side>>>({});
  const [error, setError] = useState('');
  const content = plan.kind === 'ready' ? resolveText(plan, choices) : null;
  const fieldKeys: Field[] = ['title', 'tags', 'folder_id'];
  const fieldLabels = {title: '标题', tags: '标签', folder_id: '文件夹'};
  const fieldValue = (field: Field, draft: NoteDraft) => field === 'tags' ? draft.tags.join('、') || '无标签' : field === 'folder_id' ? folderPath(folders, draft.folder_id) : draft.title || '未填写标题';
  const remaining = (plan.kind === 'ready' ? plan.segments.filter(part => part.kind === 'conflict' && !choices[part.id]).length : 0) + fieldKeys.filter(key => fields?.[key].conflict && !metadata[key]).length;
  const selected = <T,>(key: Field, automatic: T, localValue: T, serverValue: T): T => metadata[key] ? (metadata[key] === 'local' ? localValue : serverValue) : automatic;
  const result: NoteDraft | null = content !== null && fields && !remaining ? {
    content,
    title: selected('title', fields.title.value, local.title, server.title),
    tags: selected('tags', fields.tags.value, local.tags, server.tags),
    folder_id: selected('folder_id', fields.folder_id.value, local.folder_id ?? null, server.folder_id ?? null),
  } : null;
  const choose = (id: string, side: Side) => {setChoices(value => ({...value, [id]: side})); setError('');};
  return <NotesDialog open title="合并笔记修改" onClose={onClose} className="note-merge-dialog">
    <div className="note-merge-workspace">
      <p className="hint">对照共同版本，合并两处修改。应用后仍需点击「立即保存」；此窗口不会写入服务端。</p>
      <div className="note-merge-downloads"><button className="secondary" onClick={() => downloadDraft(local, '本地草稿')}>下载本地草稿</button><button className="secondary" onClick={() => downloadDraft(server, '服务端版本')}>下载服务端版本</button></div>
      <p className="hint">下载包含完整 Markdown 正文，保留原图片和双链引用；图片附件请使用笔记导出功能。</p>
      {plan.kind === 'unavailable' ? <><p role="alert">{plan.reason} 两份完整正文仍可下载。关闭窗口后可核对并保留本地草稿，或载入服务端版本。</p><button className="primary" disabled>应用合并到草稿</button></> : <>
        <div className="note-merge-summary" role="status">{remaining ? `还有 ${remaining} 项修改需要选择` : '所有修改已核对，可以应用到草稿'}<small>不同位置的修改已合并；相同修改只保留一份。</small></div>
        {fields && fieldKeys.map(key => fields[key].conflict ? <section className="note-merge-conflict" aria-label={`${fieldLabels[key]}冲突`} key={key}>
          <h3>{fieldLabels[key]}有不同修改</h3>
          <div className="note-merge-columns">{(['local', 'server'] as const).map(side => <div key={side}><strong>{side === 'local' ? '本地' : '服务端'}</strong><p>{fieldValue(key, side === 'local' ? local : server)}</p><button className="secondary" aria-pressed={metadata[key] === side} onClick={() => {setMetadata(value => ({...value, [key]: side})); setError('');}}>采用{side === 'local' ? '本地' : '服务端'}{fieldLabels[key]}</button></div>)}</div>
          <details><summary>查看共同版本</summary><p>{fieldValue(key, base!)}</p></details>
        </section> : null)}
        {plan.segments.filter(part => part.kind === 'conflict').map((part, index) => <section className="note-merge-conflict" aria-label={`冲突段落 ${index + 1}`} key={part.id}>
          <h3>段落 {index + 1}<small>共同版本第 {part.startLine}–{part.endLine} 行</small></h3>
          <div className="note-merge-columns">{(['local', 'server'] as const).map(side => <div key={side}><strong>{side === 'local' ? '本地内容' : '服务端内容'}</strong><pre>{part[side] || '（此段已删除）'}</pre><button className="secondary" aria-pressed={choices[part.id] === side} onClick={() => choose(part.id, side)}>采用{side === 'local' ? '本地' : '服务端'}内容</button></div>)}</div>
          <details><summary>查看共同版本</summary><pre>{part.base || '（此处原无内容）'}</pre></details>
        </section>)}
        <section className="note-merge-preview"><h3>合并结果</h3>{result ? <><dl><dt>标题</dt><dd>{result.title}</dd><dt>标签</dt><dd>{result.tags.join('、') || '无标签'}</dd><dt>文件夹</dt><dd>{folderPath(folders, result.folder_id)}</dd></dl><pre aria-label="合并结果预览" tabIndex={0}>{result.content || '（正文为空）'}</pre></> : <p className="hint">先为每处冲突选择内容，再查看完整合并结果。应用后可以继续在编辑器中修改。</p>}</section>
        {error && <p role="alert">{error}</p>}
        <div className="note-merge-actions"><button className="secondary" onClick={onClose}>取消合并</button><button className="primary" disabled={!result} onClick={() => {if (result) setError(onApply(result));}}>应用合并到草稿</button></div>
      </>}
    </div>
  </NotesDialog>;
}
