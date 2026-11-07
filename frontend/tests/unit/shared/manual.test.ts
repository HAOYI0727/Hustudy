import {describe,it,expect,vi,afterEach} from "vitest";
import {readFileSync} from "node:fs";
import {manualChapters,readManual,MANUAL_MAX_BYTES} from "../../../src/features/platform/manual";

afterEach(()=>vi.unstubAllGlobals());
describe("complete user manual",()=>{
  it("splits chapters without treating code examples as navigation headings",()=>{
    const text="# Hustudy\r\n## One\r\n```markdown\r\n## Inside a code example\r\n```\r\n## Two ###\r\n~~~\r\n## Another example\r\n~~~\r\nDone";
    const rows=manualChapters(text);
    expect(rows.map(row=>row.title)).toEqual(["One","Two"]);
    expect(rows[0].markdown).toContain("## Inside a code example");
    expect(rows[1].markdown).toContain("## Another example");
  });
  it("uses the actual root manual and covers all current modules and the worked example",()=>{
    const text=readFileSync(new URL("../../../../user.md",import.meta.url),"utf8"),rows=manualChapters(text);
    expect(rows).toHaveLength(25);
    for(const term of ["当前版本功能总览与完整测试","学习闭环","当前PPT专用AI阅读助手","知识笔记与编辑器","导入自己的题库","错题复盘与复习计划","导出、备份与恢复","保存结果未知","从资料库导入"])expect(text).toContain(term);
    expect(new TextEncoder().encode(text).length).toBeLessThan(MANUAL_MAX_BYTES);
  });
  it("rejects a successful HTML fallback, oversized or incomplete documents",async()=>{
    const controller=new AbortController();
    for(const [body,headers] of [["<html>app</html>",{"Content-Type":"text/html"}],["# Hustudy\n## One",{"Content-Type":"text/plain","Content-Length":String(MANUAL_MAX_BYTES+1)}],["not the manual",{"Content-Type":"text/markdown"}]] as const){
      vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(body,{headers})));
      await expect(readManual("/manual",controller.signal)).rejects.toThrow();
    }
  });
  it("passes cancellation to the explicit read and accepts the text asset",async()=>{
    const controller=new AbortController(),fetcher=vi.fn().mockResolvedValue(new Response("# Hustudy\n## One\nContent",{headers:{"Content-Type":"text/markdown; charset=utf-8"}}));vi.stubGlobal("fetch",fetcher);
    expect(await readManual("/manual",controller.signal)).toContain("Content");
    expect(fetcher).toHaveBeenCalledWith("/manual",{signal:controller.signal,cache:"no-cache"});
  });
});
