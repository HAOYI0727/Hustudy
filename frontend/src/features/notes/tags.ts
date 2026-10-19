import type { Note } from "../../api/client";

export function addNoteTag(tags: string[], input: string): string[] {
  const tag = input.trim();
  if (!tag) throw new Error("请输入标签名称");
  if (Array.from(tag).length > 32) throw new Error("每个标签最多 32 个字符");
  if (/[\u0000-\u001f\u007f]/.test(tag)) throw new Error("标签不能包含控制字符");
  if (tags.includes(tag)) return tags;
  if (tags.length >= 12) throw new Error("每篇笔记最多 12 个标签");
  return [...tags, tag];
}

export function filterNotes(notes: Note[], search: string, tag: string): Note[] {
  const query = search.trim().toLowerCase();
  return notes.filter(note => (!tag || (note.tags ?? []).includes(tag)) &&
    [note.title, note.content, ...(note.tags ?? [])].some(text => text.toLowerCase().includes(query)));
}
