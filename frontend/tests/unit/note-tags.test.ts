import { describe, expect, it } from "vitest";
import { addNoteTag, filterNotes } from "../../src/features/notes/tags";
import type { Note } from "../../src/api/client";

describe("M3 tags", () => {
  it("trims, deduplicates and counts Unicode characters", () => {
    expect(addNoteTag(["期末"], " 期末 ")).toEqual(["期末"]);
    expect(addNoteTag([], "😀".repeat(32))).toHaveLength(1);
    expect(() => addNoteTag([], "😀".repeat(33))).toThrow("32");
    expect(() => addNoteTag([], "a\u0000b")).toThrow("控制字符");
    expect(() => addNoteTag([], " ")).toThrow("请输入");
    const full = Array.from({length: 12}, (_, i) => String(i));
    expect(addNoteTag(full, "0")).toEqual(full);
    expect(() => addNoteTag(full, "新标签")).toThrow("12");
  });
  it("combines exact tags and literal text search without changing link targets", () => {
    const notes: Note[] = [
      {id:"1",title:"Scheduling",content:"进程",tags:["期末", "100%"],revision:1,updated_at:""},
      {id:"2",title:"内存",content:"分页",tags:["期末复习"],revision:1,updated_at:""},
    ];
    expect(filterNotes(notes, "  schedULING  ", "期末").map(n=>n.id)).toEqual(["1"]);
    expect(filterNotes(notes, "期末", "")).toHaveLength(2);
    expect(filterNotes(notes, "%", "").map(n=>n.id)).toEqual(["1"]);
    expect(filterNotes(notes, "分页", "期末")).toEqual([]);
    expect(notes).toHaveLength(2);
  });
});
