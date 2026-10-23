import {expect,test} from "vitest";
import {matchingText,textWindow,pageForChunk} from "../../src/features/materials/textWindow";
import type {Chunk} from "../../src/api/client";
const rows=Array.from({length:145},(_,i)=>({id:String(i),text:`原文 ${i}：完整资料😀`,locator_value:`幻灯片 ${i+1}`} as Chunk));
test("长PPT单页与正文成组分页均能到最后片段，不改原数组或文字",()=>{
 expect(textWindow(rows.length,144,1)).toEqual({page:144,pages:145,start:144,end:145});
 expect(textWindow(rows.length,24,6)).toEqual({page:24,pages:25,start:144,end:145});
 expect(pageForChunk(rows,"144",1)).toBe(144);expect(pageForChunk(rows,"144",6)).toBe(24);expect(rows[144].text).toBe("原文 144：完整资料😀");
});
test("查找覆盖整份资料及定位，返回原对象，保留Unicode文本",()=>{
 expect(matchingText(rows,"  原文 144 ")[0]).toBe(rows[144]);expect(matchingText(rows,"幻灯片 145")).toEqual([rows[144]]);expect(matchingText(rows,"😀")).toHaveLength(145);expect(matchingText(rows,"不存在")).toEqual([]);expect(matchingText(rows,"")).toBe(rows);
});
test("范围缩小或过期页码有界，缺失目标不伪造片段",()=>{
 expect(textWindow(2,100,6)).toEqual({page:0,pages:1,start:0,end:2});expect(textWindow(0,NaN,6)).toEqual({page:0,pages:1,start:0,end:0});expect(textWindow(145,-1,1).page).toBe(0);expect(pageForChunk([],"missing",6)).toBe(0);
});
