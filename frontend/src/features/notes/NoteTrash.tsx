import {useEffect, useRef, useState} from 'react';
import {api, type NoteTrashPage, type NoteTrashPolicy} from '../../api/client';

const when = (value: string) => new Date(value).toLocaleString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false});

export function NoteTrash({token, courseId, open, disabled, perform, onChanged, onError, onNotice}: {
  token: string; courseId: string; open: boolean; disabled: boolean;
  perform: (action: () => Promise<void>) => Promise<void>; onChanged: () => Promise<void>;
  onError: (error: unknown) => void; onNotice: (message: string) => void;
}) {
  const [page, setPage] = useState<NoteTrashPage | null>(null);
  const [policy, setPolicy] = useState<NoteTrashPolicy | null>(null);
  const [days, setDays] = useState('30');
  const [automatic, setAutomatic] = useState(true);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const generation = useRef(0);
  const load = async (nextOffset = offset) => {
    const version = ++generation.current; setLoading(true); setError('');
    try {
      const [data, settings] = await Promise.all([api.noteTrash(token, nextOffset), api.noteTrashPolicy(token)]);
      if (version !== generation.current) return;
      if (!data.items.length && nextOffset > 0) {await load(Math.max(0, Math.ceil(data.total / 50) - 1) * 50); return;}
      setPage(data); setPolicy(settings); setAutomatic(settings.retention_days !== null); setDays(String(settings.retention_days ?? 30));
      setSelected([]); setOffset(nextOffset);
    } catch (e) {
      if (version === generation.current) {setError(e instanceof Error ? e.message : '回收站加载失败'); onError(e);}
    } finally {if (version === generation.current) setLoading(false);}
  };
  useEffect(() => {if (open) {setPage(null); setPolicy(null); setNotice(''); void load(0);} return () => {generation.current++;};}, [open, token]);
  const locked = disabled || loading;
  const run = (action: () => Promise<{affected: number}>, message: string) => {
    if (locked) return;
    void perform(async () => {
      setError('');
      try {
        const result = await action();
        setNotice(`${message} ${result.affected} 篇笔记。`); onNotice(`${message} ${result.affected} 篇笔记。`);
        await load(); await onChanged();
      } catch (e) {setError(e instanceof Error ? e.message : '操作失败，请刷新后重试'); throw e;}
    });
  };
  const batch = (action: 'restore' | 'purge') => {
    if (!page || !selected.length || locked) return;
    const rows = page.items.filter(n => selected.includes(n.id));
    const message = action === 'purge'
      ? `彻底删除所选 ${rows.length} 篇笔记？此操作无法撤销，原图片和资料会保留。`
      : `恢复所选 ${rows.length} 篇笔记？${rows.some(n => n.restore_requires_course) ? '原课程已不可用的笔记将恢复到当前课程的未归档目录。' : '笔记将回到原来的位置，已删除的目录将改为未归档。'}`;
    if (!window.confirm(message)) return;
    run(() => api.trashNotes(token, action, rows.map(n => ({id: n.id, revision: n.revision})), courseId), action === 'restore' ? '已恢复' : '已彻底删除');
  };
  const savePolicy = () => {
    if (!policy || locked) return;
    const value = automatic ? Number(days) : null;
    if (value !== null && (!Number.isInteger(value) || value < 1 || value > 365)) {setError('请输入 1–365 之间的整数天数'); return;}
    if (value === policy.retention_days) return;
    if (!window.confirm(value === null ? '关闭自动清理？回收站笔记将保留，直到你手动彻底删除。' : `将保留时间设为 ${value} 天？此设置影响账户回收站中所有笔记，从各自删除时间起计算；已超过期限的笔记将在下次自动清理时彻底删除。`)) return;
    void perform(async () => {
      try {await api.updateNoteTrashPolicy(token, {retention_days: value, revision: policy.revision}); setNotice('回收站设置已保存。'); await load();}
      catch (e) {setError(e instanceof Error ? e.message : '设置保存失败'); throw e;}
    });
  };
  return <section className="note-trash" aria-label="回收站管理">
    <p className="hint">账户全部课程的已删除笔记。恢复保留正文、标签和引用；彻底删除后无法从回收站找回。</p>
    <details className="note-trash-settings"><summary>自动清理设置 · {policy ? policy.retention_days === null ? '已关闭' : `保留 ${policy.retention_days} 天` : '加载中'}</summary>
      <div className="note-trash-policy"><label><input type="checkbox" checked={automatic} disabled={locked || !policy} onChange={e => setAutomatic(e.target.checked)}/>启用自动清理</label>
        <label>保留天数<input aria-label="回收站保留天数" type="number" min={1} max={365} step={1} value={days} disabled={locked || !automatic || !policy} onChange={e => setDays(e.target.value)}/></label>
        <button className="secondary" disabled={locked || !policy || (automatic ? Number(days) : null) === policy.retention_days} onClick={savePolicy}>保存清理设置</button>
      </div><p className="hint">从移入回收站时起计算，修改设置也会调整已有笔记的期限。后台服务停止时暂停清理，再次启动后继续。</p>
    </details>
    {error && <p role="alert">{error}，可点击“刷新回收站”获取最新状态。</p>}
    {notice && <p role="status">{notice}</p>}
    <div className="note-trash-toolbar"><strong>共 {page?.total ?? '…'} 篇 · 已选 {selected.length} 篇</strong><button className="text-button" disabled={locked} onClick={() => void load()}>刷新回收站</button></div>
    <div className="note-batch-bar"><label><input type="checkbox" aria-label="选择本页回收站笔记" disabled={locked || !page?.items.length} checked={!!page?.items.length && page.items.every(n => selected.includes(n.id))} onChange={e => setSelected(e.target.checked ? page?.items.map(n => n.id) ?? [] : [])}/>本页全选</label>
      <button className="secondary" disabled={locked || !selected.length} onClick={() => batch('restore')}>恢复所选</button>
      <button className="text-button note-delete" disabled={locked || !selected.length} onClick={() => batch('purge')}>彻底删除所选</button>
      <button className="text-button note-delete" disabled={locked || !page?.total} onClick={() => {if (page && window.confirm(`清空整个账户回收站中的 ${page.total} 篇笔记（包含所有课程和其他分页）？此操作无法撤销。`)) run(() => api.emptyNoteTrash(token, page.snapshot), '已彻底删除');}}>清空回收站</button>
    </div>
    {loading && <p role="status">正在加载回收站…</p>}
    <div className="note-trash-list">{page?.items.map(note => <article className="note-trash-row" key={note.id}>
      <input type="checkbox" aria-label={`选择回收站笔记 ${note.title}`} checked={selected.includes(note.id)} disabled={locked} onChange={e => setSelected(e.target.checked ? [...selected, note.id] : selected.filter(id => id !== note.id))}/>
      <div><strong>{note.title}</strong><small>{note.course_name}{note.restore_requires_course ? '（恢复到当前课程）' : ''} · 删除于 {when(note.deleted_at)}</small><small>{note.purge_after ? `计划清理：${when(note.purge_after)}` : '自动清理已关闭'}</small><div className="note-tags">{note.tags.map(tag => <span className="note-tag" key={tag}>#{tag}</span>)}</div></div>
    </article>)}</div>
    {page?.total === 0 && <p className="note-manager-empty">回收站是空的。</p>}
    {!!page?.total && <nav className="note-trash-pagination" aria-label="回收站分页"><button className="secondary" disabled={locked || !offset} onClick={() => void load(offset - 50)}>上一页</button><span>{Math.floor(offset / 50) + 1} / {Math.ceil(page.total / 50)}</span><button className="secondary" disabled={locked || offset + 50 >= page.total} onClick={() => void load(offset + 50)}>下一页</button></nav>}
    {disabled && <p className="hint">请先保存或处理编辑区的草稿，再操作回收站。</p>}
  </section>;
}
