import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {readFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext,count=1,scan=false){
 const auth=await(await request.post(base+"/auth/register",{data:{username:"health_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"资料最新版本检查"}})).json();const versions:any[]=[];
 for(let i=0;i<count;i++){
  const buffer=scan?await readFile(fileURLToPath(new URL("../../../fixtures/no_text_demo.pdf",import.meta.url))):Buffer.from(`# 章节${i}\n当前课程章节${i}的原文，不在检查接口返回。`);
  const upload=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:scan?"扫描课件.pdf":`章节${String(i).padStart(2,"0")}.md`,mimeType:scan?"application/pdf":"text/markdown",buffer}}})).json();
  await expect.poll(async()=>(await(await request.get(base+`/jobs/${upload.id}`,{headers})).json()).status,{timeout:20000}).toMatch(/SUCCEEDED|FAILED/);
  await expect.poll(async()=>(await(await request.get(base+`/courses/${course.id}/jobs/page?status=pending`,{headers})).json()).pending_count,{timeout:20000}).toBe(0);
  versions.push(await(await request.get(base+`/versions/${upload.resource_id}`,{headers})).json());
 }
 await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
 return {headers,course,versions};
}
type Setup=Awaited<ReturnType<typeof setup>>;
async function read(page:Page,s:Setup,index=0){const v=s.versions[index];await page.goto(`/materials?course=${s.course.id}&document=${v.document_id}&version=${v.id}`);await expect(page.getByRole("button",{name:"资料检查",exact:true})).toBeEnabled();}
async function open(page:Page){await page.getByRole("button",{name:"资料检查",exact:true}).click();const d=page.getByRole("dialog",{name:"资料检查",exact:true});await expect(d).toBeVisible();return d;}
async function cancelledIndex(request:APIRequestContext,s:Setup){
 const version=s.versions[0];let id="";
 for(let i=0;i<4;i++){
  const response=await request.post(base+`/versions/${version.id}/reindex`,{headers:s.headers,data:{request_id:crypto.randomUUID()}});expect(response.status()).toBe(202);id=(await response.json()).id;
  if((await request.post(base+`/jobs/${id}/cancel`,{headers:s.headers})).status()===200)return id;
  await expect.poll(async()=>(await(await request.get(base+`/jobs/${id}`,{headers:s.headers})).json()).status).toBe("SUCCEEDED");
 }
 throw new Error("隔离样例未能及时取消索引任务");
}

for(const width of [320,390,1440])test(`当前版本检查→明确恢复→原任务完成，阅读与引用保持 ${width}px`,async({page,request})=>{
 test.setTimeout(90000);await page.setViewportSize({width,height:1000});const s=await setup(page,request);const jobId=await cancelledIndex(request,s);const version=s.versions[0];
 const chunks=await(await request.get(base+`/versions/${version.id}/chunks`,{headers:s.headers})).json();const note=await(await request.post(base+"/notes",{headers:s.headers,data:{course_id:s.course.id,title:"原文理解",content:"保留我的理解。",citations:[{version_id:version.id,chunk_id:chunks[0].id,quote:chunks[0].text}]}})).json();
 await read(page,s);const paper=page.locator(".reading-paper");await expect(paper).toBeVisible();await paper.evaluate(e=>e.setAttribute("data-health-reader","kept"));let writes=0;page.on("request",r=>{if(["POST","PUT","PATCH","DELETE"].includes(r.method()))writes++;});
 const d=await open(page);await expect(d.locator(".material-health-card")).toHaveCount(1);await expect(d.getByRole("region",{name:"索引检查：章节00",exact:true})).toContainText("已取消");expect(writes).toBe(0);expect(await d.evaluate((e:HTMLElement)=>e.scrollWidth<=e.clientWidth+2)).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);if(width<768)expect(await d.locator("button:visible").evaluateAll(es=>es.every(e=>e.getBoundingClientRect().height>=43.5))).toBe(true);
 await page.screenshot({path:test.info().outputPath(`material-health-${width}.png`),fullPage:true});
 let release!:()=>void;const gate=new Promise<void>(r=>{release=r;});let held!:()=>void;const started=new Promise<void>(r=>{held=r;});await page.route(`**/jobs/${jobId}/retry`,async route=>{const response=await route.fetch();held();await gate;await route.fulfill({response});});
 await d.getByRole("button",{name:"恢复索引",exact:true}).click();await started;await page.keyboard.press("Escape");await expect(d).toBeVisible();expect(await page.evaluate(()=>window.dispatchEvent(new Event("hustudy:before-navigate",{cancelable:true})))).toBe(false);release();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${version.id}`,{headers:s.headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");await expect(d.getByRole("button",{name:"刷新资料检查",exact:true})).toBeEnabled();await d.getByRole("button",{name:"刷新资料检查",exact:true}).click();await expect(d.locator(".material-health-card")).toHaveCount(0);expect(writes).toBe(1);
 await page.keyboard.press("Escape");await expect(page.getByRole("button",{name:"资料检查",exact:true})).toBeFocused();await expect(paper).toHaveAttribute("data-health-reader","kept");const citations=await(await request.get(base+`/notes/${note.id}/citations`,{headers:s.headers})).json();expect(citations[0].chunk_id).toBe(chunks[0].id);expect(citations[0].availability).toBe("active");
});

for(const status of [503,401])test(`恢复结果不明确 ${status}：先核对再操作，同任务预算保持`,async({page,request})=>{
 const s=await setup(page,request,1,true);await read(page,s);let d=await open(page);await expect(d.getByRole("button",{name:"恢复解析",exact:true})).toBeVisible();let posts=0;
 await page.route("**/jobs/*/retry",async route=>{posts++;const response=await route.fetch();if(posts===1)await route.fulfill({status,json:{error:{message:"隔离恢复响应未确认"}}});else await route.fulfill({response});});await d.getByRole("button",{name:"恢复解析",exact:true}).click();
 if(status===401){const auth=page.getByRole("dialog",{name:/登录已过期/});await expect(auth).toBeVisible();await expect(d).not.toBeVisible();await auth.getByLabel("密码",{exact:true}).fill("Test-password-2026");await auth.getByRole("button",{name:"登录",exact:true}).click();await expect(auth).not.toBeVisible();expect(posts).toBe(1);await expect(d).not.toBeVisible();}
 else{await expect(d.getByRole("alert")).toContainText("先重新核对任务状态");await expect(d.getByRole("button",{name:"恢复解析",exact:true})).toBeDisabled();expect(posts).toBe(1);}
 await expect.poll(async()=>(await(await request.get(base+`/versions/${s.versions[0].id}`,{headers:s.headers})).json()).parse_status,{timeout:20000}).toBe("FAILED");
 if(status===401)d=await open(page);else await d.getByRole("button",{name:"重新核对任务状态",exact:true}).click();await expect(d.getByRole("button",{name:"恢复解析",exact:true})).toBeEnabled();expect(posts).toBe(1);await d.getByRole("button",{name:"恢复解析",exact:true}).click();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${s.versions[0].id}`,{headers:s.headers})).json()).parse_status,{timeout:20000}).toBe("FAILED");await expect(d.getByRole("button",{name:"刷新资料检查",exact:true})).toBeEnabled();await d.getByRole("button",{name:"刷新资料检查",exact:true}).click();await expect(d).toContainText("已达尝试上限");await expect(d.getByRole("button",{name:"恢复解析",exact:true})).toHaveCount(0);expect(posts).toBe(2);
 const jobs=await(await request.get(base+`/courses/${s.course.id}/jobs/page?kind=PARSE`,{headers:s.headers})).json();expect(jobs.total).toBe(1);expect(jobs.items[0].attempt_count).toBe(3);
});

test("真实分页/标题筛选与新版本成功清除旧失败首页提醒",async({page,request})=>{
 test.setTimeout(90000);const s=await setup(page,request,15);await read(page,s);let d=await open(page);await d.getByLabel("资料检查范围").selectOption("all");await expect(d.locator(".material-health-card")).toHaveCount(12);await d.getByRole("button",{name:"下一页检查",exact:true}).click();await expect(d.locator(".material-health-card")).toHaveCount(3);await d.getByLabel("查找检查资料名称").fill("章节13");await d.getByRole("button",{name:"查找资料检查",exact:true}).click();await expect(d.locator(".material-health-card")).toHaveCount(1);
 const uploaded=await(await request.post(base+`/courses/${s.course.id}/documents`,{headers:s.headers,multipart:{file:{name:"扫描课件.pdf",mimeType:"application/pdf",buffer:await readFile(fileURLToPath(new URL("../../../fixtures/no_text_demo.pdf",import.meta.url)))}}})).json();await expect.poll(async()=>(await(await request.get(base+`/jobs/${uploaded.id}`,{headers:s.headers})).json()).status,{timeout:20000}).toBe("FAILED");const scan={...s,versions:[await(await request.get(base+`/versions/${uploaded.resource_id}`,{headers:s.headers})).json()]};await page.goto(`/overview?course=${scan.course.id}`);await expect(page.getByRole("button",{name:/检查资料处理/})).toBeVisible();
 const next=await(await request.post(base+`/documents/${scan.versions[0].document_id}/versions`,{headers:scan.headers,multipart:{file:{name:"已补全.md",mimeType:"text/markdown",buffer:Buffer.from("# 新版\n已补全的可用原文。")}}})).json();await expect.poll(async()=>(await(await request.get(base+`/versions/${next.resource_id}`,{headers:scan.headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");await page.reload();await expect(page.getByRole("article",{name:"读懂课程资料",exact:true}).locator(".stage-count strong")).toHaveText("16");await expect(page.getByRole("button",{name:/检查资料处理/})).toHaveCount(0);
 const old=await(await request.get(base+`/courses/${scan.course.id}/jobs/page?status=failed`,{headers:scan.headers})).json();expect(old.total).toBeGreaterThan(0);
});

test("首次断网保留阅读笔记、拒绝打开其他版本不卸载草稿",async({page,request})=>{
 const s=await setup(page,request);const scan=await(await request.post(base+`/courses/${s.course.id}/documents`,{headers:s.headers,multipart:{file:{name:"扫描课件.pdf",mimeType:"application/pdf",buffer:await readFile(fileURLToPath(new URL("../../../fixtures/no_text_demo.pdf",import.meta.url)))}}})).json();await expect.poll(async()=>(await(await request.get(base+`/jobs/${scan.id}`,{headers:s.headers})).json()).status,{timeout:20000}).toBe("FAILED");await read(page,s);await expect(page.locator(".reading-paper")).toBeVisible();await page.getByRole("button",{name:"阅读笔记",exact:true}).click();const text=page.getByLabel("阅读时记录理解",{exact:true});await text.fill("尚未保存的原文理解。");await text.evaluate(e=>e.setAttribute("data-health-draft","kept"));await page.context().setOffline(true);const d=await open(page);await expect(d.getByRole("alert")).toContainText("暂时无法连接");await page.context().setOffline(false);await d.getByRole("button",{name:"重试资料检查",exact:true}).click();await expect(d.locator(".material-health-card")).toHaveCount(1);page.once("dialog",dialog=>dialog.dismiss());await d.getByRole("button",{name:"打开检查资料：扫描课件",exact:true}).click();await expect(text).toHaveValue("尚未保存的原文理解。");await expect(text).toHaveAttribute("data-health-draft","kept");await expect(page.getByLabel("资料版本",{exact:true})).toHaveValue(s.versions[0].id);
});

test("检查失败只显式重试，关闭和范围切换拒绝迟到响应",async({page,request})=>{
 const s=await setup(page,request);await read(page,s);const url=`**/courses/${s.course.id}/material-health?**`;let reads=0;await page.route(url,route=>{reads++;return reads===1?route.fulfill({status:503,json:{error:{message:"隔离检查暂不可用"}}}):route.continue();});let d=await open(page);await expect(d.getByRole("alert")).toContainText("隔离检查暂不可用");expect(reads).toBe(1);await d.getByRole("button",{name:"重试资料检查",exact:true}).click();await expect(d).toContainText("当前匹配的最新版本没有这类检查项");await page.keyboard.press("Escape");await page.unroute(url);
 let release!:()=>void;const gate=new Promise<void>(r=>{release=r;});let held!:()=>void;const started=new Promise<void>(r=>{held=r;});let first=true;await page.route(url,async route=>{if(first){first=false;const response=await route.fetch();held();await gate;await route.fulfill({response}).catch(()=>{});}else await route.continue();});d=await open(page);await started;await page.keyboard.press("Escape");d=await open(page);await d.getByLabel("资料检查范围").selectOption("all");await expect(d.locator(".material-health-card")).toHaveCount(1);release();await expect(d.getByLabel("资料检查范围")).toHaveValue("all");await expect(d.locator(".material-health-card")).toHaveCount(1);
});

test("翻页后资料名称变化使当前页过期，可回第一页且不显示倒置页码",async({page,request})=>{
 test.setTimeout(90000);const s=await setup(page,request,15);await read(page,s);const d=await open(page);await d.getByLabel("资料检查范围").selectOption("all");await d.getByLabel("查找检查资料名称").fill("章节");await d.getByRole("button",{name:"查找资料检查",exact:true}).click();await expect(d.locator(".material-health-card")).toHaveCount(12);await d.getByRole("button",{name:"下一页检查",exact:true}).click();await expect(d.locator(".material-health-card")).toHaveCount(3);
 const last=await(await request.get(base+`/courses/${s.course.id}/material-health?issue=all&q=${encodeURIComponent("章节")}&offset=12&limit=12`,{headers:s.headers})).json();for(const [index,item]of last.items.entries())expect((await request.patch(base+`/documents/${item.document_id}`,{headers:s.headers,data:{name:`已整理${index}`}})).status()).toBe(200);
 await d.getByRole("button",{name:"刷新资料检查",exact:true}).click();await expect(d.getByRole("navigation",{name:"资料检查分页"})).toContainText("当前页已变化");await expect(d).not.toContainText("2 / 1");await d.getByRole("button",{name:"回第一页检查",exact:true}).click();await expect(d.locator(".material-health-card")).toHaveCount(12);await expect(d.getByRole("navigation",{name:"资料检查分页"})).toContainText("1 / 1 页");
});
