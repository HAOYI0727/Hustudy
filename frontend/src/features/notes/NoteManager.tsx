import type {DragEvent} from 'react';
import type {Note, NoteFolder} from '../../api/client';
import {folderPath} from './organization';
import {Icon} from '../../components/Icon';

export function NoteManager({notes, folders, selected, setSelected, disabled, search, setSearch, tag, setTag, tags, path, onOpen, onTool, onRefresh, onDrag, onDragEnd, onDelete}: {
  notes: Note[]; folders: NoteFolder[]; selected: string[]; setSelected: (ids: string[]) => void; disabled: boolean;
  search: string; setSearch: (s: string) => void; tag: string; setTag: (s: string) => void; tags: string[]; path: string;
  onOpen: (note: Note) => void; onTool: (tool: 'batch' | 'export') => void; onRefresh: () => void;
  onDrag: (event: DragEvent, note: Note) => void; onDragEnd: () => void;
  onDelete: () => void;
}) {
  return <section className="panel note-manager" aria-label="笔记管理列表">
    <div className="panel-title"><div><h2>{path}</h2><p className="hint note-filter-summary">找到 {notes.length} 篇笔记 · 打开标题即可编辑</p></div><button className="text-button" disabled={disabled} onClick={onRefresh}>刷新笔记列表</button></div>
    <div className="note-manager-filters"><input aria-label="搜索笔记" placeholder="搜索标题、正文或标签…" maxLength={200} value={search} onChange={e => setSearch(e.target.value)}/><select aria-label="按标签筛选笔记" value={tag} onChange={e => setTag(e.target.value)}><option value="">全部标签</option>{[...new Set([...tags, ...(tag ? [tag] : [])])].map(t => <option key={t}>{t}</option>)}</select>{(search || tag) && <button className="text-button" onClick={() => {setSearch(''); setTag('');}}>清除筛选</button>}</div>
    <div className="note-batch-bar" aria-label="列表批量操作">
      <label><input type="checkbox" aria-label="选择当前筛选结果" disabled={disabled || !notes.length} checked={!!notes.length && notes.every(n => selected.includes(n.id))} onChange={e => setSelected(e.target.checked ? [...new Set([...selected, ...notes.map(n => n.id)])] : selected.filter(id => !notes.some(n => n.id === id)))}/>全选</label>
      <strong role="status">已选 {selected.length} 篇</strong><button className="secondary" disabled={disabled || !selected.length} onClick={() => onTool('batch')}>批量整理</button><button className="secondary" disabled={disabled || !selected.length} onClick={() => onTool('export')}>导出已选</button><button className="text-button" disabled={disabled || !selected.length} onClick={() => setSelected([])}>清空选择</button>
      <button className="text-button note-delete" disabled={disabled || !selected.length || selected.length > 200} onClick={onDelete}>批量删除</button>
      {selected.length > 200 && <small>每次最多删除 200 篇，请分批选择</small>}
      {selected.some(id => !notes.some(n => n.id === id)) && <small>含筛选范围外的笔记</small>}
    </div>
    <div className="note-manager-list">{notes.map(note => <article key={note.id} className={`note-manager-row ${selected.includes(note.id) ? 'is-selected' : ''}`} draggable={!disabled} onDragStart={e => onDrag(e, note)} onDragEnd={onDragEnd} data-note-id={note.id}>
      <input type="checkbox" aria-label={`选择笔记 ${note.title}`} checked={selected.includes(note.id)} disabled={disabled} onChange={e => setSelected(e.target.checked ? [...new Set([...selected, note.id])] : selected.filter(id => id !== note.id))}/>
      <Icon name="notes" size={18}/><div className="note-manager-info"><button className="note-title-link" onClick={() => onOpen(note)}>{note.title}</button><small>{folderPath(folders, note.folder_id)}</small><div className="note-tags">{note.tags.map(t => <span className="note-tag" key={t}>#{t}</span>)}</div></div><span className="note-drag-handle" aria-hidden="true">⠿</span>
    </article>)}</div>
    {!notes.length && <p className="note-manager-empty">这里还没有笔记，可以新建、导入，或调整筛选条件。</p>}
    <p className="hint note-drag-tip">将笔记拖到左侧文件夹可移动；勾选多篇后拖动其中一篇可一起移动。也可使用“批量整理”。</p>
  </section>;
}
