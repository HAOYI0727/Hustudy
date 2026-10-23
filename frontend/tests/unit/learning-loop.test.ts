import {afterEach,expect,test,vi} from "vitest";
import {readingPositions,rememberReading,forgetReading} from "../../src/features/materials/readingPositions";
import {parseWorkspace,workspaceHref} from "../../src/features/platform/routing";
import {continuationItem,openWorkspaceItem,CourseWorkspace} from "../../src/features/platform/CourseWorkspace";
import {createElement,type ComponentProps} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import type {WorkspaceItem} from "../../src/api/client";

const course="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",documentId="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",versionId="cccccccc-cccc-cccc-cccc-cccccccccccc",chunkId="dddddddd-dddd-dddd-dddd-dddddddddddd";
const position={courseId:course,documentId,versionId,chunkId,page:3,view:"pdf" as const,name:"自制课程资料"};
test("历史失败不留下首页提醒，当前异常按资料份数提示",()=>{
 const props:ComponentProps<typeof CourseWorkspace>={parts:{materials:{loading:false,error:false,data:{course_id:course,domain:"materials",counts:{total:1,failed_jobs:10,attention_materials:0},recent:[],checked_at:"2026-10-23T00:00:00Z"}},notes:{loading:false,error:false},study:{loading:false,error:false},practice:{loading:false,error:false}},retry:()=>{},onOpen:()=>{},onRecords:()=>{}};
 expect(renderToStaticMarkup(createElement(CourseWorkspace,props))).not.toContain("检查资料处理");
 props.parts.materials.data!.counts.attention_materials=2;
 const html=renderToStaticMarkup(createElement(CourseWorkspace,props));expect(html).toContain("检查资料处理");expect(html).toContain("2 份资料的最新版本需要检查");
});
function storage(){const rows=new Map<string,string>();vi.stubGlobal("localStorage",{getItem:(key:string)=>rows.get(key)??null,setItem:(key:string,value:string)=>rows.set(key,value)});return rows;}
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});
test("阅读位置按账户、课程、版本隔离，不保存正文或令牌",()=>{
  const rows=storage();rememberReading("alice",position);rememberReading("bob",{...position,page:8});
  expect(readingPositions("alice",course)[0].page).toBe(3);expect(readingPositions("bob",course)[0].page).toBe(8);
  expect(readingPositions("alice",documentId)).toEqual([]);
  rememberReading("alice",{...position,page:5});expect(readingPositions("alice")).toHaveLength(1);
  expect([...rows.values()].join()).not.toContain("token");expect([...rows.values()].join()).not.toContain("content");
  forgetReading("alice",versionId);expect(readingPositions("alice")).toEqual([]);expect(readingPositions("bob")).toHaveLength(1);
});
test("阅读历史只保留最近60个版本，过期与坏数据不影响页面",()=>{
  const rows=storage();vi.useFakeTimers();vi.setSystemTime(new Date("2026-10-22T00:00:00Z"));
  for(let i=0;i<65;i++){vi.advanceTimersByTime(1000);rememberReading("alice",{...position,versionId:crypto.randomUUID()});}
  expect(readingPositions("alice")).toHaveLength(60);
  vi.advanceTimersByTime(181*86400000);expect(readingPositions("alice")).toEqual([]);
  rows.set("hustudy-reading:v1:alice",'{"broken":true}');expect(readingPositions("alice")).toEqual([]);
  rows.set("hustudy-reading:v1:alice","not JSON");expect(readingPositions("alice")).toEqual([]);
});
test("私密浏览或磁盘配额错误不阻断阅读",()=>{
  vi.stubGlobal("localStorage",{getItem:()=>{throw new Error("denied");},setItem:()=>{throw new Error("quota");}});
  expect(()=>rememberReading("alice",position)).not.toThrow();expect(readingPositions("alice")).toEqual([]);expect(()=>forgetReading("alice",versionId)).not.toThrow();
});
test.each([
  ["ai",{aiResultId:chunkId,aiMode:"report"}],
  ["exam",{examTab:"practice",attemptId:chunkId}],
  ["exam",{examTab:"analysis"}],
] as const)("学习结果/作答/分析URL支持刷新往返：%s",(section,extra)=>{
  const url=new URL(workspaceHref(section,course,extra),"http://localhost");
  expect(parseWorkspace(url.pathname,url.search)).toMatchObject({section,courseId:course,...extra,invalid:false});
});
test.each(["/ai?result=broken","/ai?mode=unknown","/exam?tab=bad",`/exam?attempt=${chunkId}&tab=bank`,`/notes?result=${chunkId}`])("拒绝错页或无效定位：%s",address=>{
  const url=new URL(address,"http://localhost");expect(parseWorkspace(url.pathname,url.search).invalid).toBe(true);
});
test("近期项目始终携带明确对象ID，不创建学习任务",()=>{
  const open=vi.fn();
  const item={id:chunkId,title:"标题",kind:"attempt",status:"IN_PROGRESS",updated_at:new Date().toISOString()} as WorkspaceItem;
  openWorkspaceItem(item,open);expect(open).toHaveBeenLastCalledWith("exam",{examTab:"practice",attemptId:chunkId});
  openWorkspaceItem({...item,kind:"report"},open);expect(open).toHaveBeenLastCalledWith("ai",{aiResultId:chunkId,aiMode:"report"});
  openWorkspaceItem({...item,id:documentId,kind:"material",document_id:documentId,version_id:versionId},open);expect(open).toHaveBeenLastCalledWith("materials",{material:{documentId,versionId,chunkId:""}});
});

test("学习卡片只从各域可继续的原对象中选择最新项，不修改摘要顺序",()=>{
  const base:WorkspaceItem={id:chunkId,title:"原记录",kind:"material",status:"SUCCEEDED",updated_at:"2026-10-23T01:00:00Z",document_id:documentId,version_id:versionId};
  const newer={...base,id:versionId,updated_at:"2026-10-23T02:00:00Z"};
  const rows=[base,{...newer,status:"FAILED"},newer];
  expect(continuationItem("materials",rows)).toBe(newer);expect(rows[0]).toBe(base);
  expect(continuationItem("materials",[{...base,version_id:undefined},{...base,status:"RUNNING"}])).toBeUndefined();
  expect(continuationItem("notes",[{...newer,kind:"note",status:"DELETED"},{...base,kind:"note",status:"SAVED"}])?.id).toBe(base.id);
  expect(continuationItem("study",[{...newer,kind:"qa",status:"provider_error"},{...base,kind:"report",status:"grounded"}])?.id).toBe(base.id);
  expect(continuationItem("study",[{...base,kind:"qa",status:"grounded"}])?.kind).toBe("qa");
});
test("练习卡片只恢复进行中作答，提交/评分/空态不当成待继续",()=>{
  const base:WorkspaceItem={id:chunkId,title:"同一张试卷",kind:"attempt",status:"IN_PROGRESS",updated_at:"2026-10-23T01:00:00Z"};
  expect(continuationItem("practice",[{...base,id:versionId,status:"SCORED",updated_at:"2026-10-23T02:00:00Z"},base])).toBe(base);
  expect(continuationItem("practice",["SUBMITTED","SCORED","READY","CANCELLED"].map(status=>({...base,status})))).toBeUndefined();
  expect(continuationItem("practice",[])).toBeUndefined();
  const tied=[{...base,id:"b"},{...base,id:"a"}];expect(continuationItem("practice",tied)?.id).toBe("a");
});
