import type {NoteSummary, NoteFolder} from '../../api/client';
import {addNoteTag} from './tags';

export function parseTags(input: string): string[] {
  return input.split(/[,，;；\n]/).filter(s => s.trim()).reduce((tags, value) => addNoteTag(tags, value), [] as string[]);
}

export function noteSnippet(content: string): string {
  return content.slice(0, 1000).replace(/!\[\[asset:[^\]|]+(?:\|([^\]]*))?\]\]/g, (_all, label) => `[图片：${label || '课程图片'}]`)
    .replace(/\[\[note:[^\]|]+(?:\|([^\]]*))?\]\]/g, (_all, label) => label || '关联笔记')
    .replace(/!?\[\[(?:asset|note):[^\]]*$/, '').replace(/^#{1,6}\s+/gm, '').replace(/[*`~]/g, '').replace(/\s+/g, ' ').trim().slice(0, 70);
}

export function folderPath(folders: NoteFolder[], id?: string | null): string {
  const names: string[] = [], seen = new Set<string>();
  while (id && !seen.has(id)) {
    seen.add(id); const folder = folders.find(f => f.id === id);
    if (!folder) return names.length ? names.join(' / ') : '文件夹不可用';
    names.unshift(folder.name); id = folder.parent_id;
  }
  return names.join(' / ') || '未归档';
}

export function folderOptions(folders: NoteFolder[]) {
  return folders.map(f => ({...f, path: folderPath(folders, f.id)})).sort((a, b) => a.path.localeCompare(b.path, 'zh-CN'));
}

export function insideFolder(folders: NoteFolder[], id: string | null | undefined, parent: string): boolean {
  const seen = new Set<string>();
  while (id && !seen.has(id)) {if (id === parent) return true; seen.add(id); id = folders.find(f => f.id === id)?.parent_id;}
  return false;
}

function words(text: string): string[] {
  const stop = new Set(['笔记', '复习', '学习', '总结', '课程', '第一章', '第二章']);
  const Segmenter = (Intl as unknown as {Segmenter?: new(locale: string, options: {granularity: 'word'}) => {segment: (input: string) => Iterable<{segment: string; isWordLike?: boolean}>}}).Segmenter;
  const segments = Segmenter ? [...new Segmenter('zh', {granularity: 'word'}).segment(text.toLocaleLowerCase())] : (text.toLocaleLowerCase().match(/[a-z][a-z0-9_]+|[\u4e00-\u9fff]{2,}/g) || []).map(segment => ({segment, isWordLike: true}));
  return [...new Set(segments.filter(p => p.isWordLike && Array.from(p.segment).length >= 2 && !stop.has(p.segment)).map(p => p.segment))];
}

export function suggestNotes(notes: NoteSummary[], folder: NoteFolder, folders: NoteFolder[]) {
  const examples = notes.filter(n => insideFolder(folders, n.folder_id, folder.id));
  const tags = new Set(examples.flatMap(n => n.tags));
  const terms = [...new Set(words(folder.name + ' ' + examples.map(n => n.title).join(' ')))];
  return notes.filter(n => !n.folder_id && n.course_id === folder.course_id).map(note => {
    const shared = note.tags.filter(tag => tags.has(tag));
    const matches = terms.filter(term => (note.title + ' ' + note.tags.join(' ')).toLocaleLowerCase().includes(term));
    return {note, score: shared.length * 3 + matches.length, reason: [shared.length ? `共同标签：${shared.join('、')}` : '', matches.length ? `标题或标签包含：${matches.join('、')}` : ''].filter(Boolean).join('；')};
  }).filter(item => item.score > 0).sort((a, b) => b.score - a.score || a.note.title.localeCompare(b.note.title, 'zh-CN')).slice(0, 30);
}
