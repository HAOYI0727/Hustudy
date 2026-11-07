import {describe,it,expect} from "vitest";
import {sourceReadingPage,type ReadingCursor} from "../../../src/features/materials/readingPage";

const cursor:ReadingCursor={versionId:"v1",view:"native",page:3};
describe("verified displayed source page",()=>{
  it("accepts ready native slides and original PDF/PPT previews, rejects Word layout pages",()=>{
    const value={versionId:"v1",view:"native",kind:"pptx" as const,cursor,chunks:[]};
    expect(sourceReadingPage(value)).toBe(3);
    expect(sourceReadingPage({...value,kind:"docx"})).toBeNull();
    expect(sourceReadingPage({...value,view:"pdf",cursor:{...cursor,view:"pdf"},kind:"pdf"})).toBe(3);
    expect(sourceReadingPage({...value,view:"pdf",cursor:{...cursor,view:"pdf"},kind:"pptx"})).toBe(3);
    expect(sourceReadingPage({...value,view:"pdf",cursor:{...cursor,view:"pdf"},kind:"docx"})).toBeNull();
  });
  it("does not reuse a cursor from another version, old view, failed load or invalid page",()=>{
    const value={versionId:"v1",view:"native",kind:"pptx" as const,cursor,chunks:[]};
    expect(sourceReadingPage({...value,versionId:"v2"})).toBeNull();
    expect(sourceReadingPage({...value,view:"pdf"})).toBeNull();
    expect(sourceReadingPage({...value,cursor:null})).toBeNull();
    for(const page of [0,-1,1.5,NaN,Infinity])expect(sourceReadingPage({...value,cursor:{...cursor,page}})).toBeNull();
  });
  it("uses the unique actual text locator, including sparse page numbers, without guessing from list index",()=>{
    const value={versionId:"v1",view:"text",kind:"pptx" as const,cursor:null,chunks:[{locator_type:"slide",locator_value:"59"}]};
    expect(sourceReadingPage(value)).toBe(59);
    expect(sourceReadingPage({...value,chunks:[...value.chunks,...value.chunks]})).toBeNull();
    expect(sourceReadingPage({...value,chunks:[]})).toBeNull();
    expect(sourceReadingPage({...value,kind:"docx"})).toBeNull();
    expect(sourceReadingPage({...value,kind:"pdf",chunks:[{locator_type:"page",locator_value:"17"}]})).toBe(17);
    for(const locator_value of ["0","01","1–3","chapter 1","9007199254740992"])expect(sourceReadingPage({...value,chunks:[{locator_type:"slide",locator_value}]})).toBeNull();
  });
});
