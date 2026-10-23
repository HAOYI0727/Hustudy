import {describe,it,expect} from "vitest";
import type {DocumentMetadata,DocumentOrganizeChange} from "../../src/api/client";
import {materialTags,organizedTags,organizeError} from "../../src/features/materials/organizeMetadata";
const items:DocumentMetadata[]=[{id:"a",course_id:"course",name:"课件A",tags:["A","B"],category:"课件",updated_at:"2026-10-22T08:00:00Z"}];
const change=(mode:DocumentOrganizeChange["tags_mode"],tags:string[]=[]):DocumentOrganizeChange=>({tags_mode:mode,tags});
describe("批量资料整理预览",()=>{
  it("去空白/中文逗号精确去重并保持原顺序",()=>{expect(materialTags(" A，B,A , b")).toEqual(["A","B","b"]);expect(organizedTags(items[0].tags,change("add",["B","C"]))).toEqual(["A","B","C"]);expect(items[0].tags).toEqual(["A","B"]);});
  it("预览移除/替换/清空而不改变来源选择",()=>{expect(organizedTags(items[0].tags,change("remove",["A"]))).toEqual(["B"]);expect(organizedTags(items[0].tags,change("replace",["C"]))).toEqual(["C"]);expect(organizedTags(items[0].tags,change("clear"))).toEqual([]);expect(items[0].id).toBe("a");});
  it("每份最终预算而不是仅新增标签数决定可保存",()=>{const full=[{...items[0],tags:Array.from({length:12},(_,i)=>String(i))}];expect(organizeError(full,change("add",["新标签"]))).toContain("超过12");expect(organizeError(full,change("add",["0"]))).toBe("");expect(organizeError(full,change("replace",["新标签"]))).toBe("");expect(organizeError(items,change("replace"))).toContain("填写");expect(organizeError(items,change("keep"))).toContain("操作");expect(organizeError([],change("clear"))).toContain("1–100");});
});
