import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {readFile,mkdir,writeFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";
import {resolve} from "node:path";
import {spawnSync} from "node:child_process";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
 const auth=await(await request.post(base+"/auth/register",{data:{username:"layout_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"阅读排版隔离复验"}})).json();let buffer:Buffer,name:string;
 if(process.env.HUSTUDY_LAYOUT_REAL_SAMPLE){const samples=JSON.parse(await readFile(fileURLToPath(new URL("../../../../../../../.artifacts/inputs/layout-real-materials.json",import.meta.url)),"utf8"));name=samples[0].filename;buffer=await readFile(resolve(fileURLToPath(new URL("../../../../",import.meta.url)),samples[0].source_path));}
 else{const python=fileURLToPath(new URL(process.platform==="win32"?"../../../../.venv/Scripts/python.exe":"../../../../.venv/bin/python",import.meta.url));const result=spawnSync(python,["-c","from pptx import Presentation; from io import BytesIO; import sys; p=Presentation(); [(lambda s,i: (setattr(s.shapes.title,'text',f'Slide {i+1}'),setattr(s.placeholders[1],'text',f'Local sample {i+1}: bounded reading and source navigation.')))(p.slides.add_slide(p.slide_layouts[1]),i) for i in range(80)]; b=BytesIO(); p.save(b); sys.stdout.buffer.write(b.getvalue())"],{maxBuffer:12*1024*1024});expect(result.status,result.stderr.toString()).toBe(0);buffer=result.stdout;name="selfmade-long-deck.pptx";}
 const upload=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name,mimeType:"application/vnd.openxmlformats-officedocument.presentationml.presentation",buffer}}})).json();
 await expect.poll(async()=>(await(await request.get(base+`/jobs/${upload.id}`,{headers})).json()).status,{timeout:90000}).toBe("SUCCEEDED");
 const version=await(await request.get(base+`/versions/${upload.resource_id}`,{headers})).json();const chunks=await(await request.get(base+`/versions/${version.id}/chunks`,{headers})).json();
 await page.addInitScript(auth=>{if(window===window.top){localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);}},auth);
 return {headers,course,version,chunks,name};
}
test("现有PPT长资料的阅读排版核对",async({page,request})=>{
 const pageErrors:string[]=[];page.on("pageerror",error=>pageErrors.push(error.message));
 test.setTimeout(240000);await page.setViewportSize({width:1440,height:1000});const s=await setup(page,request);expect(s.chunks.length).toBeGreaterThan(50);
 const url=`/materials?course=${s.course.id}&document=${s.version.document_id}&version=${s.version.id}`;await page.goto(url);
 if(process.env.HUSTUDY_LAYOUT_BASELINE){await expect(page.locator(".reading-paper .chunk")).toHaveCount(s.chunks.length);}
 else{await expect(page.getByRole("region",{name:"PPT 原格式阅读",exact:true})).toBeVisible();await expect(page.getByLabel("PPT幻灯片序号",{exact:true})).toBeEnabled({timeout:45000});await expect(page.locator(".reading-paper .chunk")).toHaveCount(0);}
 const metrics=await page.evaluate(()=>({height:document.documentElement.scrollHeight,viewport:innerHeight,chunks:document.querySelectorAll(".reading-paper .chunk").length,readerHeight:document.querySelector(".reader-workspace")?.getBoundingClientRect().height}));
 const output=fileURLToPath(new URL(process.env.HUSTUDY_LAYOUT_REAL_SAMPLE?"../../../../.artifacts/e2e/reading-layout-20261023/":"../../../../.artifacts/e2e/reading-layout-20261023/selfmade/",import.meta.url));await mkdir(output,{recursive:true});const phase=process.env.HUSTUDY_LAYOUT_BASELINE?"before":"after";await writeFile(output+`${phase}-${test.info().project.name}.json`,JSON.stringify({sample:s.name,slideCount:s.chunks.length,...metrics},null,2));await page.screenshot({animations:"disabled",path:output+`${phase}-${test.info().project.name}.png`});
 if(process.env.HUSTUDY_LAYOUT_BASELINE)return;
 expect(metrics.height).toBeLessThan(4200);expect(metrics.readerHeight).toBeLessThan(1500);
 await page.getByRole("button",{name:"文本与引用",exact:true}).click();await expect(page.locator(".reading-paper .chunk")).toHaveCount(1);await expect(page.getByRole("navigation",{name:"原文分页"})).toContainText(String(s.chunks.length));await page.getByLabel("跳到原文页",{exact:true}).selectOption(String(s.chunks.length-1));await expect(page.locator(".reading-paper .chunk")).toHaveAttribute("id","chunk-"+s.chunks.at(-1).id);
 await page.goto(url+`&chunk=${s.chunks.at(-1).id}`);await expect(page.locator(".chunk-highlight")).toHaveAttribute("id","chunk-"+s.chunks.at(-1).id);await expect(page.locator(".reading-paper .chunk")).toHaveCount(1);
 for(const chunk of s.chunks.slice(0,8)){const citation={version_id:s.version.id,chunk_id:chunk.id,quote:Array.from(chunk.text as string).slice(0,450).join("")};await request.post(base+"/notes",{headers:s.headers,data:{course_id:s.course.id,title:`已有理解笔记 ${chunk.ordinal}`,content:"隔离样例理解正文。",citations:[citation]}});}
 await page.setViewportSize({width:390,height:900});await page.goto(url);await expect(page.getByLabel("PPT幻灯片序号",{exact:true})).toBeEnabled({timeout:45000});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);await page.screenshot({animations:"disabled",path:output+`after-mobile-${test.info().project.name}.png`});
 await page.getByRole("button",{name:"文本与引用",exact:true}).click();await expect(page.locator(".reading-paper .chunk")).toHaveCount(1);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);await page.screenshot({animations:"disabled",path:output+`text-after-mobile-${test.info().project.name}.png`});
 expect(pageErrors).toEqual([]);
 const sourceCard=page.locator(".source-note-card").first();await expect(sourceCard).toHaveCSS("display","block");expect(await sourceCard.evaluate(e=>e.querySelector("p")!.getBoundingClientRect().width/e.getBoundingClientRect().width)).toBeGreaterThan(.75);
});

test("长文本目录/末页/全版本查找保持引用身份与阅读笔记草稿",async({page,request})=>{
 test.setTimeout(180000);
 const auth=await(await request.post(base+"/auth/register",{data:{username:"text_layout_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};const course=await(await request.post(base+"/courses",{headers,data:{name:"长正文分页"}})).json();const body=Array.from({length:19},(_,i)=>`# 章节${i}\n${("完整保留的原文😀。".repeat(100))}${i===18?"末页独有关键词":""}`).join("\n\n");
 const job=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:"长正文.md",mimeType:"text/markdown",buffer:Buffer.from(body)}}})).json();await expect.poll(async()=>(await(await request.get(base+`/jobs/${job.id}`,{headers})).json()).status,{timeout:150000}).toBe("SUCCEEDED");const version=await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json();const chunks=await(await request.get(base+`/versions/${version.id}/chunks`,{headers})).json();
 await page.addInitScript(auth=>{if(window===window.top){localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);}},auth);await page.goto(`/materials?course=${course.id}&document=${version.document_id}&version=${version.id}`);await expect(page.locator(".reading-paper .chunk")).toHaveCount(6);expect(await page.locator(".reading-paper").evaluate((e:HTMLElement)=>e.scrollHeight>e.clientHeight)).toBe(true);
 await page.getByRole("button",{name:"阅读笔记",exact:true}).click();const draft=page.getByLabel("阅读时记录理解",{exact:true});await draft.fill("保留跨页阅读的理解草稿。");await draft.evaluate(e=>e.setAttribute("data-paged-draft","kept"));await page.locator(".reader-outline button").last().click();await expect(page.locator(".reading-paper .chunk")).toHaveCount(1);await expect(page.locator(".reading-paper .chunk")).toHaveAttribute("id","chunk-"+chunks.at(-1).id);await expect(draft).toHaveValue("保留跨页阅读的理解草稿。");await expect(draft).toHaveAttribute("data-paged-draft","kept");
 await page.getByLabel("在当前版本原文中查找",{exact:true}).fill("末页独有关键词");await expect(page.locator(".reading-paper .chunk")).toHaveCount(1);await expect(page.locator(".reading-paper mark")).toHaveText("末页独有关键词");await expect(page.getByRole("navigation",{name:"原文分页",exact:true})).toContainText("1–1 / 1");await expect(draft).toHaveAttribute("data-paged-draft","kept");
});
