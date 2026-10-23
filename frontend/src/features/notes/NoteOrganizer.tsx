import {useState} from 'react';
import {api, type Note, NoteSummary, type NoteFolder, type NoteBatchChange} from '../../api/client';
import {folderOptions, parseTags, suggestNotes} from './organization';

export function NoteOrganizer({token, notes, folders, selected, setSelected, disabled, perform, onChanged, suggestedFolder, mode}: {
  token: string; notes: NoteSummary[]; folders: NoteFolder[]; selected: string[]; setSelected: (ids: string[]) => void;
  disabled: boolean; perform: (action: () => Promise<void>) => Promise<void>; onChanged: (notes: Note[]) => void; suggestedFolder: string;
  mode: 'batch' | 'tags' | 'recommend';
}) {
  const [tagText, setTagText] = useState(''), [destination, setDestination] = useState(''), [oldTag, setOldTag] = useState(''), [newTag, setNewTag] = useState('');
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [recommendFolder, setRecommendFolder] = useState('');
  const chosen = notes.filter(n => selected.includes(n.id));
  const tags = [...new Set(notes.flatMap(n => n.tags))].sort((a,b) => a.localeCompare(b, 'zh-CN'));
  const options = folderOptions(folders);
  const destinationFolder = folders.find(f => f.id === (recommendFolder || suggestedFolder));
  const suggestions = destinationFolder ? suggestNotes(notes, destinationFolder, folders) : [];
  const apply = (scope: NoteSummary[], change: NoteBatchChange, message: string) => {
    setError(''); setNotice('');
    if (!scope.length || scope.length > 200) {setError('每次请选择1–200篇笔记；超过200篇时请分批整理。'); return;}
    if (!window.confirm(`${message}，共 ${scope.length} 篇笔记？`)) return;
    void perform(async () => {const updated = await api.batchNotes(token, scope.map(n => ({id: n.id, revision: n.revision})), change); onChanged(updated); setSelected([]); setNotice(`已更新 ${updated.length} 篇笔记。`);});
  };
  const tagAction = (remove: boolean) => {
    try {const parsed = parseTags(tagText); if (!parsed.length) throw new Error('请先输入标签'); apply(chosen, remove ? {remove_tags: parsed} : {add_tags: parsed}, `${remove ? '移除' : '添加'}标签“${parsed.join('、')}”`);} catch (e) {setError((e as Error).message);}
  };
  const rename = () => {
    try {const parsed = parseTags(newTag); if (parsed.length !== 1) throw new Error('请输入一个新标签名称'); apply(notes.filter(n => n.tags.includes(oldTag)), {remove_tags: [oldTag], add_tags: parsed}, `将当前课程的“${oldTag}”改名/合并为“${parsed[0]}”`);} catch (e) {setError((e as Error).message);}
  };
  return <section className="note-organizer">
    {disabled && <p className="hint">请先保存或处理当前草稿，再批量整理或导入。</p>}
    {mode === 'batch' && <><p>已选 {chosen.length} 篇（可包含筛选范围外的笔记）</p><div className="note-batch-titles">{chosen.map(n => <span key={n.id}>{n.title}</span>)}</div><div className="note-organize-fields">
      <label>批量标签<input aria-label="批量标签" disabled={disabled} value={tagText} onChange={e => setTagText(e.target.value)} placeholder="多个标签用逗号分隔"/></label>
      <div className="note-folder-actions"><button className="secondary" disabled={disabled || !chosen.length} onClick={() => tagAction(false)}>为所选添加标签</button><button className="secondary" disabled={disabled || !chosen.length} onClick={() => tagAction(true)}>从所选移除标签</button></div>
      <label>移动目标<select aria-label="批量移动目标" disabled={disabled} value={destination} onChange={e => setDestination(e.target.value)}><option value="">未归档</option>{options.map(f => <option value={f.id} key={f.id}>{f.path}</option>)}</select></label><button className="secondary" disabled={disabled || !chosen.length} onClick={() => apply(chosen, {folder_id: destination || null}, '移动所选笔记')}>移动所选笔记</button>
    </div></>}
    {mode === 'tags' && <section className="note-tag-manager"><p className="hint">改名为已存在的标签会合并；删除标签只移除标记，保留笔记。这里的操作覆盖当前课程，不受列表筛选影响。</p>
      <div className="note-organize-fields"><label>现有标签<select aria-label="管理现有标签" value={oldTag} disabled={disabled} onChange={e => setOldTag(e.target.value)}><option value="">选择标签</option>{tags.map(t => <option key={t} value={t}>{t}（{notes.filter(n => n.tags.includes(t)).length}篇）</option>)}</select></label><label>新名称<input aria-label="标签新名称" value={newTag} disabled={disabled} onChange={e => setNewTag(e.target.value)} maxLength={32}/></label></div>
      <div className="note-folder-actions"><button className="secondary" disabled={disabled || !tags.includes(oldTag) || !newTag.trim()} onClick={rename}>改名或合并标签</button><button className="text-button" disabled={disabled || !tags.includes(oldTag)} onClick={() => apply(notes.filter(n => n.tags.includes(oldTag)), {remove_tags: [oldTag]}, `从当前课程移除标签“${oldTag}”`)}>删除此标签</button></div>
    </section>}
    {mode === 'recommend' && <section className="note-recommendations"><p className="hint">依据文件夹名称、已有笔记标题与标签，推荐当前课程的未归档笔记；无需联网。先选择候选，再确认移动。</p>
      <label>推荐目标文件夹<select aria-label="推荐目标文件夹" value={destinationFolder?.id || ''} onChange={e => {setRecommendFolder(e.target.value); setSelected([]);}}><option value="">选择文件夹</option>{options.map(f => <option key={f.id} value={f.id}>{f.path}</option>)}</select></label>
      {suggestions.map(item => <label className="note-export-choice" key={item.note.id}><input type="checkbox" disabled={disabled} checked={selected.includes(item.note.id)} onChange={e => setSelected(e.target.checked ? [...new Set([...selected, item.note.id])] : selected.filter(id => id !== item.note.id))}/><span><strong>{item.note.title}</strong><small>{item.reason}</small></span></label>)}
      {destinationFolder && !suggestions.length && <p className="hint">暂无明确匹配。可先手动移入一篇代表笔记，或为笔记添加标签。</p>}
      <button className="secondary" disabled={disabled || !destinationFolder || !suggestions.some(s => selected.includes(s.note.id))} onClick={() => destinationFolder && apply(suggestions.filter(s => selected.includes(s.note.id)).map(s => s.note), {folder_id: destinationFolder.id}, `归入“${destinationFolder.name}”`)}>将勾选候选归入文件夹</button>
    </section>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
  </section>;
}
