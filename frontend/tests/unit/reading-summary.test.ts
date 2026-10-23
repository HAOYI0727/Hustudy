import {describe,it,expect} from "vitest";
import type {AIAnswer,SourceCitation,StudyReport} from "../../src/api/client";
import {readingSummaryGoal,readingPages,readingPageLabel,belongsToReadingVersion,matchingReadingTopics} from "../../src/features/ai/readingSummary";

const citation=(value:string,extra:Partial<SourceCitation>={}):SourceCitation=>({version_id:"v1",chunk_id:"c"+value,quote:"原文",availability:"active",locator:{type:"slide",value},...extra});
describe("current PPT summary",()=>{
  it("searches the actual topic content and intersects with exact active cited pages",()=>{
    const topics:StudyReport["topics"]=[{topic_id:"a",name:"Queue",explanation:"调度概念",concept_group:"基础层",misconceptions:["易混条件"],labels:[{kind:"key",origin:"ai_suggestion",reason:"关键用途"}],citations:[citation("1"),citation("3")]},{topic_id:"b",name:"Other",explanation:"其他讲解",misconceptions:[],labels:[],citations:[citation("2",{availability:"unavailable"}),citation("1",{version_id:"v2"})]}];
    const before=structuredClone(topics);
    for(const query of [" queue ","调度","基础层","易混条件","关键用途"])expect(matchingReadingTopics(topics,"v1",query).map(t=>t.topic_id)).toEqual(["a"]);
    expect(matchingReadingTopics(topics,"v1","",3).map(t=>t.topic_id)).toEqual(["a"]);
    expect(matchingReadingTopics(topics,"v1","",2)).toEqual([]);
    expect(matchingReadingTopics(topics,"v1","Other",1)).toEqual([]);
    expect(matchingReadingTopics(topics,"v1","不存在")).toEqual([]);
    expect(topics).toEqual(before);
  });
  it("groups only real consecutive citation pages and never fills gaps",()=>{
    const rows=readingPages([citation("3"),citation("1"),citation("2"),citation("2"),citation("5"),citation("7")],"v1");
    expect(rows.map(row=>row.page)).toEqual([1,2,3,5,7]);
    expect(readingPageLabel(rows.map(row=>row.page))).toBe("第1–3、5、7页");
    expect(readingPageLabel([1,3])).toBe("第1、3页");
    expect(readingPageLabel([])).toBe("暂无可核对页码");
  });
  it("excludes other versions, inactive evidence, headings and malformed page locators",()=>{
    const bad=[citation("1",{version_id:"v2"}),citation("2",{availability:"unavailable"}),citation("3",{locator:{type:"heading",value:"3"}}),...['0','-1','1–3','1.5','01','9007199254740992'].map(value=>citation(value))];
    expect(readingPages(bad,"v1")).toEqual([]);
    expect(readingPages([citation("6",{locator:{type:"page",value:"6"}})],"v1")[0].page).toBe(6);
  });
  it("excludes mixed-version history while keeping exact-version coverage and legacy citations",()=>{
    const answer={result:{citations:[citation("1")]}} as AIAnswer;
    expect(belongsToReadingVersion(answer,"v1")).toBe(true);
    expect(belongsToReadingVersion(answer,"v2")).toBe(false);
    expect(belongsToReadingVersion({...answer,result:{citations:[citation("1"),citation("2",{version_id:"v2"})]}},"v1")).toBe(false);
    expect(belongsToReadingVersion({...answer,result:{coverage:{versions:[{version_id:"v1"},{version_id:"v2"}]} as any}},"v1")).toBe(false);
    expect(belongsToReadingVersion({...answer,result:{}},"v1")).toBe(false);
  });
  it("prepares an editable bounded goal for topic organization, truthful page mapping and note writing",()=>{
    const goal=readingSummaryGoal("PPT".repeat(1000));
    expect(goal.length).toBeLessThan(2000);
    for(const requirement of ["全部正文","知识点","evidence","不要自行编造页号","学习笔记","跨批融合"])expect(goal).toContain(requirement);
  });
});
