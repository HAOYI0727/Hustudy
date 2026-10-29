import {useEffect, useState, type DragEvent} from 'react';
import {api, type NoteSummary, type NoteFolder} from '../../api/client';
import {folderOptions, insideFolder} from './organization';
import {NotesDialog} from './NotesDialog';
import {canDropNotes, type NoteDrag} from './noteDragging';

export function FolderLibrary({token, courseId, folders, notes, selected, onSelect, disabled, perform, refresh, drag, startDrag, endDrag, drop, error, onImportPackage, onExportPackage}: {
  token: string; courseId: string; folders: NoteFolder[]; notes: NoteSummary[]; selected: string; onSelect: (id: string) => void;
  disabled: boolean; perform: (action: () => Promise<void>) => Promise<void>; refresh: () => Promise<void>;
  drag: NoteDrag | null; startDrag: (event: DragEvent, value: NoteDrag) => void; endDrag: () => void; drop: (target: string | null) => void;
  error: string;
  onImportPackage?: (folderId:string)=>void; onExportPackage?: (folderId:string)=>void;
}) {
  const [editing, setEditing] = useState<NoteFolder | null>(null);
  const [form, setForm] = useState(false), [name, setName] = useState(''), [parent, setParent] = useState('');
  const [collapsed, setCollapsed] = useState<string[]>([]);
  useEffect(() => {const close = () => setForm(false); window.addEventListener('hustudy:notes-session-expired', close); return () => window.removeEventListener('hustudy:notes-session-expired', close);}, []);
  const [over, setOver] = useState<string | null>(null);
  const dropProps = (id: string | null) => ({
    onDragOver: (event: DragEvent) => {if (!disabled && canDropNotes(drag, id, folders)) {event.preventDefault(); event.stopPropagation(); event.dataTransfer.dropEffect = 'move'; setOver(id || 'root');}},
    onDragLeave: (event: DragEvent) => {if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOver(null);},
    onDrop: (event: DragEvent) => {event.preventDefault(); event.stopPropagation(); setOver(null); if (!disabled && canDropNotes(drag, id, folders)) drop(id); else endDrag();},
  });
  const options = folderOptions(folders);
  const target = folders.find(f => f.id === selected);
  const open = (folder?: NoteFolder) => {setEditing(folder || null); setName(folder?.name || ''); setParent(folder ? folder.parent_id || '' : target?.id || ''); setForm(true);};
  const submit = () => perform(async () => {
    if (editing) await api.updateNoteFolder(token, editing.id, {name: name.trim(), parent_id: parent || null, revision: editing.revision});
    else {const created = await api.createNoteFolder(token, {course_id: courseId, name: name.trim(), parent_id: parent || null}); onSelect(created.id);}
    await refresh(); setForm(false); setEditing(null);
  });
  const branch = (parentId: string | null, depth = 0): React.ReactNode => folders.filter(f => f.parent_id === parentId).sort((a,b) => a.name.localeCompare(b.name, 'zh-CN')).map(folder => {
    const children = folders.some(f => f.parent_id === folder.id), hidden = collapsed.includes(folder.id);
    const count = notes.filter(n => insideFolder(folders, n.folder_id, folder.id)).length;
    return <li key={folder.id}><div className={`note-folder-row ${drag && over === folder.id ? 'drop-target' : ''}`} data-folder-id={folder.id} {...dropProps(folder.id)}>
      {children ? <button className="text-button folder-toggle" aria-label={`${hidden ? '展开' : '折叠'}文件夹 ${folder.name}`} aria-expanded={!hidden} onClick={() => setCollapsed(ids => hidden ? ids.filter(id => id !== folder.id) : [...ids, folder.id])}>{hidden ? '▸' : '▾'}</button> : <span className="folder-toggle"/>}
      <button draggable={!disabled} onDragStart={e => startDrag(e, {kind: 'folder', folder: {...folder}})} onDragEnd={endDrag} className={`folder-choice ${selected === folder.id ? 'active' : ''}`} aria-pressed={selected === folder.id} onClick={() => onSelect(folder.id)}><span>▱ {folder.name}</span><small>{count}</small></button>
    </div>{children && !hidden && depth < 6 && <ul>{branch(folder.id, depth + 1)}</ul>}</li>;
  });
  return <section className="note-folder-library" aria-label="笔记文件夹">
    <div className="note-tag-heading"><strong>文件夹</strong><button className="text-button" disabled={disabled} onClick={() => open()}>＋ 新建文件夹</button></div>
    <button className={`folder-choice ${selected === '*' ? 'active' : ''}`} onClick={() => onSelect('*')}>全部笔记 <small>{notes.length}</small></button>
    <button className={`folder-choice ${selected === '' ? 'active' : ''} ${drag?.kind === 'folder' ? 'folder-root-drop' : ''} ${drag && over === 'root' ? 'drop-target' : ''}`} {...dropProps(null)} onClick={() => onSelect('')}>{drag?.kind === 'folder' ? '移到根目录' : '未归档'} <small>{notes.filter(n => !n.folder_id).length}</small></button>
    <ul className="note-folder-tree">{branch(null)}</ul>
    {target && <div className="note-folder-actions"><button className="text-button" disabled={disabled} onClick={() => open(target)}>编辑文件夹</button><button className="text-button" disabled={disabled} onClick={() => {if (window.confirm(`删除空文件夹“${target.name}”？含有笔记或子文件夹时不会删除。`)) void perform(async () => {await api.deleteNoteFolder(token, target.id, target.revision); onSelect('*'); await refresh();});}}>删除空文件夹</button></div>}
    <button className="text-button" disabled={disabled} onClick={() => void perform(refresh)}>刷新文件夹</button>
    {target&&(onImportPackage||onExportPackage)&&<div className="note-folder-actions">{onImportPackage&&<button className="text-button" onClick={()=>onImportPackage(target.id)}>导入到此文件夹</button>}{onExportPackage&&<button className="text-button" onClick={()=>onExportPackage(target.id)}>导出此文件夹</button>}</div>}
    <NotesDialog open={form} title={editing ? '编辑文件夹' : '新建文件夹'} onClose={() => setForm(false)} busy={disabled}>
    {error && <p role="alert">{error}</p>}
    <form className="note-folder-form" onSubmit={e => {e.preventDefault(); void submit();}}>
      <label>{editing ? '文件夹新名称' : '文件夹名称'}<input aria-label="文件夹名称" maxLength={64} value={name} disabled={disabled} onChange={e => setName(e.target.value)}/></label>
      <label>上级文件夹<select aria-label="上级文件夹" value={parent} disabled={disabled} onChange={e => setParent(e.target.value)}><option value="">根目录</option>{options.filter(f => !editing || !insideFolder(folders, f.id, editing.id)).map(f => <option key={f.id} value={f.id}>{f.path}</option>)}</select></label>
      <div className="note-folder-actions"><button className="secondary" disabled={disabled || !name.trim()} type="submit">{editing ? '保存文件夹' : '创建文件夹'}</button><button className="text-button" disabled={disabled} type="button" onClick={() => setForm(false)}>取消</button></div>
    </form></NotesDialog>
  </section>;
}
