import {useEffect, useState} from 'react';
import {api, type Course, type NoteFolder, type NoteSummary} from '../../api/client';
import {folderOptions, folderPath, insideFolder} from './organization';

export function NoteReaderLibrary({token, courseId, noteId, notes, disabled, onNote}: {
  token:string; courseId:string; noteId?:string; notes:NoteSummary[]; disabled:boolean; onNote:(note:NoteSummary)=>void;
}) {
  const [courses,setCourses]=useState<Course[]>([]),[course,setCourse]=useState(courseId);
  const [folders,setFolders]=useState<NoteFolder[]>([]),[folder,setFolder]=useState('*');
  const [query,setQuery]=useState(''),[page,setPage]=useState(0),[error,setError]=useState(''),[reload,setReload]=useState(0),[loading,setLoading]=useState(false);
  useEffect(()=>{let live=true;void api.courses(token).then(rows=>{if(live)setCourses(rows);}).catch(()=>{if(live)setError('课程目录未能加载，请重试。');});return()=>{live=false;};},[token,reload]);
  useEffect(()=>{let live=true;setFolders([]);setFolder('*');setPage(0);setError('');setLoading(!!course&&course!=='none');
    if(course&&course!=='none')void api.noteFolders(token,course).then(rows=>{if(live)setFolders(rows);}).catch(()=>{if(live)setError('文件夹目录未能加载，请重试。');}).finally(()=>{if(live)setLoading(false);});
    return()=>{live=false;};},[token,course,reload]);
  const filtered=notes.filter(note=>(!course||(course==='none'?!note.course_id:note.course_id===course))
    &&(folder==='*'||(folder==='none'?!note.folder_id:insideFolder(folders,note.folder_id,folder)))
    &&note.title.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
    .sort((a,b)=>a.title.localeCompare(b.title,'zh-CN')||a.id.localeCompare(b.id));
  const pages=Math.max(1,Math.ceil(filtered.length/30)),current=Math.min(page,pages-1);
  return <section className="note-reader-library" aria-label="专注笔记列表">
    <label>课程<select aria-label="阅读课程范围" value={course} disabled={disabled} onChange={e=>setCourse(e.target.value)}><option value="">全部课程</option>{courses.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}{course&&course!=='none'&&!courses.some(c=>c.id===course)&&<option value={course}>当前课程</option>}<option value="none">未分类笔记</option></select></label>
    {course&&course!=='none'&&<label>文件夹<select aria-label="阅读文件夹范围" disabled={disabled||loading} value={folder} onChange={e=>{setFolder(e.target.value);setPage(0);}}><option value="*">全部文件夹</option><option value="none">未归档</option>{folderOptions(folders).map(f=><option key={f.id} value={f.id}>{f.path}</option>)}</select></label>}
    <label>查找笔记<input aria-label="查找阅读笔记" placeholder="输入标题关键词" maxLength={240} value={query} onChange={e=>{setQuery(e.target.value);setPage(0);}}/></label>
    {error&&<p role="alert">{error}<button className="text-button" onClick={()=>setReload(v=>v+1)}>重试目录</button></p>}
    <p className="hint">{filtered.length} 篇 · 第 {current+1} / {pages} 页{loading?' · 正在读取文件夹…':''}</p>
    <nav aria-label="阅读笔记导航"><ol>{filtered.slice(current*30,(current+1)*30).map(note=><li key={note.id}><button type="button" disabled={disabled} aria-current={note.id===noteId?'page':undefined} onClick={()=>onNote(note)}><strong>{note.title}</strong><small>{course?folderPath(folders,note.folder_id):courses.find(c=>c.id===note.course_id)?.name||'未分类'}</small></button></li>)}</ol></nav>
    {!filtered.length&&<p className="hint">没有匹配的笔记。</p>}
    <div className="note-reader-paging"><button className="secondary" disabled={disabled||current===0} onClick={()=>setPage(current-1)}>上一页笔记</button><button className="secondary" disabled={disabled||current+1>=pages} onClick={()=>setPage(current+1)}>下一页笔记</button></div>
  </section>;
}
