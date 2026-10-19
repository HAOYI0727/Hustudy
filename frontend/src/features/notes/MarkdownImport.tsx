import {useRef, useState} from 'react';
import {api, ApiError, type Note, type NoteFolder} from '../../api/client';
import {folderOptions, parseTags} from './organization';

type Options = {request_id: string; course_id: string; folder_id: string | null; tags: string[]};
type Entry = {file: File; id: string; state: 'pending' | 'success' | 'failed'; error?: string; options?: Options};
export function MarkdownImport({token, courseId, folders, disabled, perform, onImported}: {
  token: string; courseId: string; folders: NoteFolder[]; disabled: boolean;
  perform: (action: () => Promise<void>) => Promise<void>; onImported: (notes: Note[]) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [entries, setEntries] = useState<Entry[]>([]), [folder, setFolder] = useState(''), [tags, setTags] = useState(''), [error, setError] = useState('');
  const [progress, setProgress] = useState('');
  const started = entries.some(e => e.options);
  const choose = (files: File[]) => {
    if (files.length > 20) {setError('每批最多20份，请分批选择。'); return;}
    setError(''); setProgress(''); setEntries(files.map(file => ({file, id: crypto.randomUUID(), state: 'pending'})));
  };
  const run = () => {
    let common: string[];
    try {common = parseTags(tags);} catch (e) {setError((e as Error).message); return;}
    setError('');
    void perform(async () => {
      const queue = entries.map(e => ({...e, options: e.options || {request_id: e.id, course_id: courseId, folder_id: folder || null, tags: common}}));
      setEntries([...queue]);
      for (let index = 0; index < queue.length; index++) {
        const entry = queue[index]; if (entry.state === 'success') continue;
        setProgress(`正在导入 ${index + 1}/${queue.length}：${entry.file.name}`);
        try {
          if (!/\.(md|markdown)$/i.test(entry.file.name)) throw new Error('只支持.md或.markdown文件');
          if (entry.file.size > 2 * 1024 * 1024) throw new Error('文件超过2MiB');
          const note = await api.importMarkdown(token, entry.file, entry.options!);
          entry.state = 'success'; entry.error = ''; onImported([note]);
        } catch (e) {
          entry.state = 'failed'; entry.error = e instanceof Error ? e.message : '导入失败';
          if (e instanceof ApiError && (e.status === 0 || e.status === 401 || e.status === 403 || e.status === 429 || e.status >= 500)) {
            setEntries(queue.map(item => ({...item})));
            if (e.status === 401) {setProgress('登录已过期，本次列表保留；登录后可重试未完成文件。'); throw e;}
            break;
          }
        }
        setEntries(queue.map(item => ({...item})));
      }
      setProgress(`已导入 ${queue.filter(e => e.state === 'success').length}/${queue.length} 份。失败或未完成项可以单独重试，已成功的不会重复导入。`);
    });
  };
  return <section className="note-import-panel">
    <p className="hint">每批最多20份，每份不超过2MiB，UTF-8编码。标题使用文件名（去除扩展名），同名文件分别保存。这里只导入文本，图片需另行上传。</p>
    <div className="note-organize-fields">
      <label>导入到文件夹<select aria-label="导入到文件夹" value={folder} disabled={disabled || started} onChange={e => setFolder(e.target.value)}><option value="">未归档</option>{folderOptions(folders).map(f => <option value={f.id} key={f.id}>{f.path}</option>)}</select></label>
      <label>统一标签<input aria-label="导入统一标签" value={tags} disabled={disabled || started} onChange={e => setTags(e.target.value)} placeholder="用逗号分隔，例如：复习，重点"/></label>
    </div>
    <input ref={input} type="file" hidden multiple accept=".md,.markdown,text/markdown" aria-label="选择Markdown文件" disabled={disabled} onChange={e => {choose(Array.from(e.target.files || [])); e.target.value = '';}}/>
    <div className="note-folder-actions"><button className="secondary" disabled={disabled || entries.length > 0} onClick={() => input.current?.click()}>选择 Markdown 文件</button>
      <button className="primary" disabled={disabled || !entries.some(e => e.state !== 'success')} onClick={run}>{started ? '重试未完成文件' : `开始导入（${entries.length}）`}</button>
      {!!entries.length && <button className="text-button" disabled={disabled} onClick={() => {setEntries([]); setProgress(''); setError('');}}>清空本次列表</button>}
    </div>
    {error && <p role="alert">{error}</p>}{progress && <p role="status">{progress}</p>}
    <ul className="note-import-results">{entries.map(e => <li key={e.id}><strong>{e.file.name}</strong><span>{e.state === 'success' ? '已导入' : e.state === 'failed' ? e.error : '待导入'}</span></li>)}</ul>
    {started && <p className="hint">重试沿用首次导入的文件和统一设置；需要更改设置时，请清空本次列表。</p>}
  </section>;
}
