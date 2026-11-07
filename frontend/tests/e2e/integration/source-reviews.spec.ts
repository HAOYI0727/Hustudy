import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {readFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";
const base="http://127.0.0.1:8056/api/v1";

async function setup(page:Page,request:APIRequestContext){
 const auth=await(await request.post(base+"/auth/register",{data:{username:"source_review_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();
 const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"原文与复习闭环"}})).json();
 const content=await readFile(fileURLToPath(new URL("../../../../fixtures/source_connections_demo.md",import.meta.url)));
 const upload=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:"原文与自制题.md",mimeType:"text/markdown",buffer:content}}})).json();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${upload.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
 const version=await(await request.get(base+`/versions/${upload.resource_id}`,{headers})).json();
 const chunks=await(await request.get(base+`/versions/${version.id}/chunks`,{headers})).json();
 const bank=await(await request.post(base+`/courses/${course.id}/question-bank/import`,{headers,data:{title:"自制来源题库",version_id:version.id}})).json();
 expect((await request.post(base+`/past-papers/${bank.id}/confirm`,{headers})).status()).toBe(200);
 const paper=await(await request.post(base+`/courses/${course.id}/question-bank/draw`,{headers,data:{request_id:crypto.randomUUID(),topic_ids:[],count:1,duration_minutes:30}})).json();
 expect((await request.post(base+`/exam-papers/${paper.id}/review`,{headers})).status()).toBe(200);
 const attempt=await(await request.post(base+`/exam-papers/${paper.id}/attempts`,{headers})).json();
 const q=paper.questions[0],wrong="ABCD"[q.options.findIndex((text:string)=>text==="错误选项一")];
 expect((await request.put(base+`/attempts/${attempt.id}/answers/${q.id}`,{headers,data:{answer:wrong}})).status()).toBe(200);
 expect((await request.post(base+`/attempts/${attempt.id}/submit`,{headers})).status()).toBe(200);
 const mistake=(await(await request.get(base+"/mistakes",{headers})).json())[0];
 const plan=await(await request.post(base+"/review-tasks",{headers,data:{mistake_id:mistake.id,title:"原文复习计划",due_date:"2000-01-01"}})).json();
 await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
 return {headers,course,version,chunks,mistake,plan};
}
type Setup=Awaited<ReturnType<typeof setup>>;
async function read(page:Page,s:Setup){await page.goto(`/materials?course=${s.course.id}&document=${s.version.document_id}&version=${s.version.id}`);await expect(page.locator(".reading-paper")).toBeVisible();}
async function open(page:Page){await page.getByRole("button",{name:"学习关联",exact:true}).click();const d=page.getByRole("dialog",{name:"原文学习关联",exact:true});await d.getByLabel("筛选原文关联类型").selectOption("mistake");await expect(d.locator(".source-link-card")).toHaveCount(1);return d;}

for(const width of [320,390,1440])test(`原文相关错题、只读回顾/刷新、显式重做与计划完成各自独立 ${width}px`,async({page,request})=>{
 test.setTimeout(90000);await page.setViewportSize({width,height:1000});const s=await setup(page,request);
 let writes=0,redoes=0;page.on("request",r=>{if(["POST","PUT","PATCH","DELETE"].includes(r.method()))writes++;if(r.method()==="POST"&&/\/mistakes\/[^/]+\/redoes$/.test(new URL(r.url()).pathname))redoes++;});
 await read(page,s);let dialog=await open(page);const summary=()=>dialog.getByRole("region",{name:"关联错题复习摘要",exact:true});
 await expect(summary()).toContainText("待掌握");await expect(summary()).toContainText("今日或逾期 1 项");await expect(summary()).toContainText("2000-01-01");await expect(dialog).not.toContainText("进程是什么？");
 expect(await dialog.evaluate((e:HTMLElement)=>e.scrollWidth<=e.clientWidth+2)).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);
 await page.screenshot({path:test.info().outputPath(`source-review-${width}.png`),fullPage:true});
 await summary().getByRole("button",{name:/打开错题与复习/}).click();await expect(page).toHaveURL(new RegExp(`mistake=${s.mistake.id}&review=plan`));await expect(page.getByRole("heading",{name:"错题回顾与复习",exact:true})).toBeVisible();await expect(page.getByRole("button",{name:"重做错题",exact:true})).toBeVisible();expect(writes).toBe(0);expect(redoes).toBe(0);
 await page.reload();await expect(page.getByRole("button",{name:"重做错题",exact:true})).toBeVisible();expect(writes).toBe(0);
 await page.getByRole("button",{name:"← 返回错题库",exact:true}).click();await page.getByLabel("调整复习日期：原文复习计划",{exact:true}).fill("2099-12-31");await page.getByRole("button",{name:"保存改期",exact:true}).click();await expect(page.locator(".review-schedule")).toContainText("复习日期已更新");
 await read(page,s);dialog=await open(page);await expect(summary()).toContainText("2099-12-31");await expect(summary()).not.toContainText("今日或逾期");await expect(summary()).toContainText("待掌握");expect(redoes).toBe(0);
 await summary().getByRole("button",{name:/打开错题与复习/}).click();await page.getByRole("button",{name:"重做错题",exact:true}).click();await expect(page.getByRole("region",{name:"错题重做",exact:true})).toBeVisible();expect(redoes).toBe(1);
 await page.locator(".option").filter({hasText:"资源分配单位"}).click();await page.getByRole("button",{name:"提交重做答案",exact:true}).click();await expect(page.getByRole("button",{name:"继续保留",exact:true})).toBeVisible();await page.getByRole("button",{name:"继续保留",exact:true}).click();
 const actions=page.getByRole("group",{name:"错题后续操作",exact:true});
 await expect(actions.getByRole("button",{name:"继续保留",exact:true})).toBeDisabled();
 await expect(actions.getByRole("button",{name:"移出错题库",exact:true})).toBeDisabled();
 const nextAction=actions.getByRole("button",{name:"下一道错题 →",exact:true});
 await expect(nextAction).toBeVisible();await expect(nextAction).toBeDisabled();
 await expect(nextAction).toHaveCSS("background-color","rgb(237, 240, 243)");
 await expect(actions.getByRole("button",{name:"继续保留",exact:true})).toHaveCSS("color","rgb(122, 128, 138)");
 if(width===1440){const left=await actions.getByRole("button",{name:"再做一次",exact:true}).boundingBox();const right=await nextAction.boundingBox();const row=await actions.boundingBox();expect(Math.abs(left!.y-right!.y)).toBeLessThan(2);expect(Math.abs(right!.x+right!.width-row!.x-row!.width)).toBeLessThan(2);}
 await page.screenshot({path:test.info().outputPath(`review-action-row-${width}.png`),fullPage:true});

 await page.getByRole("button",{name:"← 返回错题库",exact:true}).click();await page.getByRole("button",{name:"完成计划",exact:true}).click();await expect(page.locator(".review-schedule")).toContainText("计划已完成");
 await read(page,s);dialog=await open(page);await expect(summary()).toContainText("已掌握 · 保留复习");await expect(summary()).toContainText("尚无待复习计划");
 const latest=(await(await request.get(base+"/mistakes",{headers:s.headers})).json()).find((m:{id:string})=>m.id===s.mistake.id);expect(latest.mastered).toBe(true);expect(redoes).toBe(1);
});

test("关联错题断网、未保存离开保护、移出后刷新与错误地址零重做",async({page,request})=>{
 const s=await setup(page,request);let redoes=0;page.on("request",r=>{if(r.method()==="POST"&&r.url().includes("/redoes"))redoes++;});await read(page,s);
 await page.getByRole("button",{name:"阅读笔记",exact:true}).click();const draft=page.getByLabel("阅读时记录理解",{exact:true});await draft.fill("仍在整理的错因与理解。");await draft.evaluate(e=>e.setAttribute("data-source-review-draft","kept"));
 await page.context().setOffline(true);await page.getByRole("button",{name:"学习关联",exact:true}).click();let dialog=page.getByRole("dialog",{name:"原文学习关联",exact:true});await expect(dialog.getByRole("alert")).toContainText("暂时无法连接");await page.context().setOffline(false);await dialog.getByRole("button",{name:"重新读取学习关联",exact:true}).click();await dialog.getByLabel("筛选原文关联类型").selectOption("mistake");await expect(dialog.locator(".source-link-card")).toHaveCount(1);
 page.once("dialog",d=>d.dismiss());await dialog.getByRole("button",{name:/打开错题与复习/}).click();await expect(draft).toHaveValue("仍在整理的错因与理解。");await expect(draft).toHaveAttribute("data-source-review-draft","kept");expect(redoes).toBe(0);
 await draft.fill("");await page.getByRole("button",{name:"学习关联",exact:true}).click();await dialog.getByLabel("筛选原文关联类型").selectOption("mistake");await expect(dialog.locator(".source-link-card")).toHaveCount(1);
 const redo=await(await request.post(base+`/mistakes/${s.mistake.id}/redoes`,{headers:s.headers,data:{request_id:crypto.randomUUID()}})).json();const correct="ABCD"[redo.question.options.findIndex((text:string)=>text==="资源分配单位")];
 expect((await request.post(base+`/mistakes/${s.mistake.id}/redoes/${redo.id}/submit`,{headers:s.headers,data:{answer:correct}})).status()).toBe(200);
 expect((await request.delete(base+`/mistakes/${s.mistake.id}`,{headers:s.headers})).status()).toBe(200);await dialog.getByRole("button",{name:"刷新关联",exact:true}).click();await expect(dialog.locator(".source-link-card")).toHaveCount(0);
 await page.goto(`/review?course=${s.course.id}&mistake=${s.mistake.id}&review=wrong`);await expect(page.getByRole("heading",{name:"错题地址无效",exact:true})).toBeVisible();expect(redoes).toBe(0);
});
