import {afterEach,beforeEach,expect,test,vi} from "vitest";
import {editReadingBookmark,readingBookmarks,shortReadingLabel,type BookmarkTarget} from "../../src/features/materials/readingBookmarks";
import {compareVersionText,filterComparison} from "../../src/features/materials/versionComparison";
import type {Chunk} from "../../src/api/client";
const uuid=(n:number)=>`10000000-0000-4000-8000-${String(n).padStart(12,"0")}`;
const owner=uuid(1),course=uuid(2);
const target=(n=4):BookmarkTarget=>({documentId:uuid(3),versionId:uuid(4),chunkId:uuid(n+1),versionNo:1,documentName:"操作系统",locatorType:"heading",locatorValue:`第${n}节`});
let store:Map<string,string>;
beforeEach(()=>{store=new Map();vi.stubGlobal("localStorage",{getItem:(k:string)=>store.get(k)??null,setItem:(k:string,v:string)=>store.set(k,v)});});
afterEach(()=>vi.unstubAllGlobals());
test("书签只存定位元数据，按真实账户和课程隔离",()=>{
  const saved=editReadingBookmark(owner,course,{kind:"save",target:target(),label:"  进程概念  "});
  expect(saved.error).toBe("");expect(saved.items[0].label).toBe("进程概念");expect(readingBookmarks(owner,course).items).toEqual(saved.items);
  expect(readingBookmarks(uuid(20),course).items).toEqual([]);expect(readingBookmarks(owner,uuid(20)).items).toEqual([]);
  expect(Object.keys(saved.items[0]).sort()).toEqual(["id","documentId","versionId","chunkId","versionNo","documentName","locatorType","locatorValue","label","updatedAt"].sort());
  expect(readingBookmarks("bad",course).error).not.toBe("");
});
test("同片段重复保存只改名称并保持身份，不影响另一个版本",()=>{
  const first=editReadingBookmark(owner,course,{kind:"save",target:target(),label:"重点"}).items[0];
  const changed=editReadingBookmark(owner,course,{kind:"save",target:target(),label:"易错点"});expect(changed.items).toHaveLength(1);expect(changed.items[0].id).toBe(first.id);
  const another=editReadingBookmark(owner,course,{kind:"save",target:{...target(),versionId:uuid(99),versionNo:2},label:"新版"});expect(another.items).toHaveLength(2);
  expect(editReadingBookmark(owner,course,{kind:"rename",id:first.id,label:"重读"}).items.find(r=>r.id===first.id)?.label).toBe("重读");
  expect(editReadingBookmark(owner,course,{kind:"remove",id:first.id}).items).toHaveLength(1);
});
test("重读后修改保留另一窗口新增；已被删除的名称编辑不复活",()=>{
  const a=editReadingBookmark(owner,course,{kind:"save",target:target(10),label:"A"}).items[0];
  editReadingBookmark(owner,course,{kind:"save",target:target(11),label:"B"});
  expect(editReadingBookmark(owner,course,{kind:"rename",id:a.id,label:"A新"}).items).toHaveLength(2);
  editReadingBookmark(owner,course,{kind:"remove",id:a.id});
  expect(editReadingBookmark(owner,course,{kind:"rename",id:a.id,label:"不能复活"}).error).toContain("其他窗口移除");
});
test("100条上限仍可编辑已有项，超限/非法来源/字段注入不覆盖",()=>{
  for(let i=0;i<100;i++)expect(editReadingBookmark(owner,course,{kind:"save",target:target(i+100),label:`第${i}条`}).error).toBe("");
  expect(editReadingBookmark(owner,course,{kind:"save",target:target(2000),label:"第101条"}).error).toContain("100条");
  expect(editReadingBookmark(owner,course,{kind:"save",target:target(100),label:"更新"}).error).toBe("");
  expect(editReadingBookmark(owner,course,{kind:"save",target:{...target(),token:"secret"} as BookmarkTarget,label:"不能存凭据"}).error).not.toBe("");
  expect(editReadingBookmark(owner,course,{kind:"save",target:{...target(),versionNo:0},label:"无效"}).error).not.toBe("");
  expect(readingBookmarks(owner,course).items).toHaveLength(100);
});
test.each(["", "x".repeat(81)])("非法名称不产生假成功：%s",label=>{expect(editReadingBookmark(owner,course,{kind:"save",target:target(),label}).error).not.toBe("");expect(store.size).toBe(0);});
test.each(['{"version":2,"items":[]}', '{"version":1,"items":[null]}', "bad json", "", "x".repeat(128*1024+1)])("损坏/超大/未知存储不自动覆盖",raw=>{
  store.set(`hustudy-bookmarks:v1:${owner}:${course}`,raw);expect(readingBookmarks(owner,course).error).not.toBe("");
  expect(editReadingBookmark(owner,course,{kind:"save",target:target(),label:"新书签"}).error).not.toBe("");expect([...store.values()]).toEqual([raw]);
});
test("重复UUID或同一片段的注入记录被拒绝",()=>{
  const first=editReadingBookmark(owner,course,{kind:"save",target:target(),label:"原"}).items[0];
  store.set(`hustudy-bookmarks:v1:${owner}:${course}`,JSON.stringify({version:1,items:[first,{...first,id:uuid(50)}]}));expect(readingBookmarks(owner,course).error).not.toBe("");
});
test("配额写失败保留前一版本且报告可重试错误",()=>{
  const prior=editReadingBookmark(owner,course,{kind:"save",target:target(),label:"原书签"}).items;
  vi.stubGlobal("localStorage",{getItem:(k:string)=>store.get(k)??null,setItem:()=>{throw new Error("quota");}});
  const failed=editReadingBookmark(owner,course,{kind:"rename",id:prior[0].id,label:"失败"});expect(failed.error).toContain("未能写入");expect(failed.items).toEqual(prior);expect(readingBookmarks(owner,course).items).toEqual(prior);
});
test("短名称保持完整表情，非UTC时间记录明确拒绝",()=>{
  expect(shortReadingLabel("甲".repeat(79)+"🧠",80)).toBe("甲".repeat(79));
  const saved=editReadingBookmark(owner,course,{kind:"save",target:target(),label:"表情🧠"}).items[0];
  store.set(`hustudy-bookmarks:v1:${owner}:${course}`,JSON.stringify({version:1,items:[{...saved,updatedAt:"2026/10/22"}]}));expect(readingBookmarks(owner,course).error).not.toBe("");
});
const chunk=(id:number,locator:string,text:string,other:Partial<Chunk>={}):Chunk=>({id:uuid(id),version_id:uuid(10),locator_type:"heading",locator_value:locator,text,source_kind:"extracted",...other});
test("唯一定位配对、精确文本变化和单侧定位独立保留",()=>{
  const result=compareVersionText([chunk(1,"同","same"),chunk(2,"改","a"),chunk(3,"旧","old")],[chunk(4,"同","same"),chunk(5,"改","b"),chunk(6,"新","new")]);
  expect(result.rows.map(r=>r.status)).toEqual(["same","changed","left","right"]);expect(result.rows[1].right?.text).toBe("b");
  expect(filterComparison(result.rows,"changed","")).toHaveLength(3);expect(filterComparison(result.rows,"all","SAME")).toHaveLength(1);expect(filterComparison(result.rows,"all","旧")[0].left?.text).toBe("old");
});
test("重复定位不猜测配对，保留所有原始片段",()=>{
  const result=compareVersionText([chunk(1,"重复","A"),chunk(2,"重复","B")],[chunk(3,"重复","A")]);
  expect(result.rows.map(r=>r.status)).toEqual(["left","left","right"]);expect(result.ambiguous).toBe(3);
});
test("格式/定位类型变化不冒充文本变化，人工补录不参与比较",()=>{
  const result=compareVersionText([chunk(1,"1","<script>unsafe()</script>"),chunk(2,"2","manual",{source_kind:"manual_transcript"})],[chunk(3,"1","<script>unsafe()</script>",{locator_type:"page"})]);
  expect(result.differentLocators).toBe(true);expect(result.excludedLeft).toBe(1);expect(result.rows.map(r=>r.status)).toEqual(["left","right"]);expect(result.rows[0].left?.text).toContain("<script>");
});
test("空文件、兼容旧来源字段与大小写/空白变化均如实显示",()=>{
  expect(compareVersionText([],[]).rows).toEqual([]);
  const result=compareVersionText([chunk(1,"章","A",{source_kind:undefined})],[chunk(2,"章","a ")]);expect(result.rows[0].status).toBe("changed");
});
