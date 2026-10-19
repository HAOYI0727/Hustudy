import {describe, expect, it} from 'vitest';
import type {Note, NoteFolder} from '../../src/api/client';
import {folderPath, insideFolder, parseTags, suggestNotes} from '../../src/features/notes/organization';
import {continueList, formatMarkdown, markdownOutline} from '../../src/features/notes/markdownEditing';

const folders: NoteFolder[] = [{id: 'a', name: '编程', course_id: 'c', parent_id: null, revision: 1}, {id: 'b', name: '函数式编程', course_id: 'c', parent_id: 'a', revision: 1}];
const note = (id: string, title: string, tags: string[], folder_id: string | null = null): Note => ({id, title, tags, folder_id, course_id: 'c', content: '', revision: 1, updated_at: ''});

describe('organization', () => {
  it('has bounded ancestor lookup, breadcrumbs and deduplicated batch tags', () => {
    expect(folderPath(folders, 'b')).toBe('编程 / 函数式编程');
    expect(folderPath(folders, null)).toBe('未归档');
    expect(insideFolder(folders, 'b', 'a')).toBe(true);
    expect(insideFolder([{...folders[0], parent_id: 'a'}], 'a', 'missing')).toBe(false);
    expect(parseTags('重点，复习,重点\n定义')).toEqual(['重点','复习','定义']);
    expect(() => parseTags(Array.from({length: 13}, (_,i) => 'tag'+i).join(','))).toThrow('12');
  });
  it('explains suggestions and excludes already filed or other-course notes', () => {
    const notes = [note('seed','纯函数',['不可变'],'b'), note('x','闭包',['不可变']), note('y','函数式编程入门',[]), note('z','体育',[]), note('filed','纯函数',['不可变'],'a'), {...note('foreign','纯函数',['不可变']), course_id: 'other'}];
    const suggestions = suggestNotes(notes, folders[1], folders);
    expect(suggestions.map(s => s.note.id).sort()).toEqual(['x','y']);
    expect(suggestions.find(s => s.note.id === 'x')?.reason).toContain('共同标签：不可变');
  });
});

describe('Markdown editing', () => {
  it('formats selection without replacing surrounding content', () => {
    const edit = formatMarkdown('前重点后',1,3,'bold');
    expect(edit).toEqual({text: '前**重点**后', start: 3, end: 5});
    expect(formatMarkdown('a\nb',0,3,'task').text).toBe('- [ ] a\n- [ ] b');
    expect(formatMarkdown('  a\n  b',0,7,'outdent').text).toBe('a\nb');
    expect(formatMarkdown('说明',0,2,'link').text).toBe('[说明](https://example.com)');
  });
  it('continues ordered/tasks lists and exits empty items', () => {
    expect(continueList('2. 项目',5)?.text).toBe('2. 项目\n3. ');
    expect(continueList('- [x] 完成',8)?.text).toBe('- [x] 完成\n- [ ] ');
    expect(continueList('上文\n- ',5)?.text).toBe('上文\n');
    expect(continueList('普通段落',4)).toBeNull();
  });
  it('outline ignores fenced code and keeps source offsets', () => {
    const body = '# 总览\n```md\n## 代码里的标题\n```\n## 正文';
    const headings = markdownOutline(body);
    expect(headings.map(h => h.label)).toEqual(['总览','正文']);
    expect(body.slice(headings[1].offset)).toBe('## 正文');
  });
});
