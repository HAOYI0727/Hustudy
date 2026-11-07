import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext,count=3){
 const username="scope_"+crypto.randomUUID().replaceAll("-","");const auth=await(await request.post(base+"/auth/register",{data:{username,password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"课程资料 · 按需带走"}})).json();
 for(let i=0;i<count;i++)expect((await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:`章节${String(i).padStart(2,"0")}.md`,mimeType:"text/markdown",buffer:Buffer.from(`# 原文${i}\n章节${i}的原始内容。`)}}})).status()).toBe(202);
 const rows=await(await request.get(base+`/courses/${course.id}/documents`,{headers})).json();
 await expect.poll(async()=>{const result=await(await request.get(base+`/courses/${course.id}/jobs/page?status=pending`,{headers})).json();return result.pending_count;},{timeout:25000}).toBe(0);
 await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
 return {headers,course,rows};
}
async function library(page:Page,width:number){if(width<761)await page.getByRole("button",{name:/资料库与上传/}).click();await page.getByRole("button",{name:"批量整理分类与标签",exact:true}).click();}
async function fit(page:Page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);}
for(const width of [1440,390])test(`跨页勾选资料包真实生成/下载/校验，不加入未选资料 ${width}px`,async({page,request})=>{
 test.setTimeout(90000);await page.setViewportSize({width,height:1000});const s=await setup(page,request,13);await page.goto(`/materials?course=${s.course.id}`);await library(page,width);
 const first=page.getByRole("checkbox",{name:/^选择资料：/}).first();const firstName=(await first.getAttribute("aria-label"))!.replace("选择资料：","");await first.check();
 await page.getByRole("navigation",{name:"资料分页"}).getByRole("button",{name:"下一页",exact:true}).click();const second=page.getByRole("checkbox",{name:/^选择资料：/});await expect(second).toHaveCount(1);const secondName=(await second.getAttribute("aria-label"))!.replace("选择资料：","");await second.check();
 await page.getByRole("button",{name:"导出已选",exact:true}).click();const panel=page.locator(".material-export-panel");await expect(panel).toHaveAttribute("open","");await expect(panel.getByLabel("资料包导出范围")).toHaveValue("selected");await expect(panel.getByLabel("本次导出资料").locator("li")).toHaveCount(2);
 const posted=page.waitForRequest(r=>r.method()==="POST"&&r.url().endsWith(`/courses/${s.course.id}/material-exports`));await panel.getByRole("button",{name:"生成所选资料包",exact:true}).click();const payload=(await posted).postDataJSON();const ids=[firstName,secondName].map(name=>s.rows.find((row:{name:string})=>row.name===name).id).sort();expect(payload.document_ids).toEqual(ids);
 const download=panel.getByRole("button",{name:"下载 ZIP",exact:true});await expect(download).toBeEnabled({timeout:20000});await expect(panel).toContainText("所选 2 份资料");await fit(page);await page.screenshot({path:test.info().outputPath(`material-scope-${width}.png`),fullPage:true});
 const pending=page.waitForEvent("download");await download.click();const target=test.info().outputPath("selected-materials.zip");await(await pending).saveAs(target);
 const python=fileURLToPath(new URL(process.platform==="win32"?"../../../../.venv/Scripts/python.exe":"../../../../.venv/bin/python",import.meta.url));
 const check=spawnSync(python,["-c","import json,sys,zipfile,hashlib; z=zipfile.ZipFile(sys.argv[1]); m=json.loads(z.read('manifest.json')); assert all(hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256'] for f in m['files']); print(json.dumps({'ids': sorted(d['id'] for d in m['documents']), 'versions': len(m['versions']), 'scope':m['scope']}))",target],{encoding:"utf8"});expect(check.status,check.stderr).toBe(0);expect(JSON.parse(check.stdout)).toEqual({ids,versions:2,scope:"selected_materials"});await expect(page.getByText("已选 2 份",{exact:true})).toBeVisible();
});

for(const status of [503,401])test(`提交结果不明确时冻结选择及请求，显式核对不重复创建 ${status}`,async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/materials?course=${s.course.id}`);await library(page,1440);const boxes=page.getByRole("checkbox",{name:/^选择资料：/});await boxes.nth(0).check();await page.getByRole("button",{name:"导出已选",exact:true}).click();
 const payloads:unknown[]=[];await page.route(`**/courses/${s.course.id}/material-exports`,async route=>{if(route.request().method()!=="POST"){await route.continue();return;}payloads.push(route.request().postDataJSON());if(payloads.length===1){await route.fetch();await route.fulfill({status,json:{error:{message:"隔离提交响应丢失"}}});}else await route.continue();});
 const panel=page.locator(".material-export-panel");await panel.getByRole("button",{name:"生成所选资料包",exact:true}).click();
 if(status===401){const auth=page.getByRole("dialog",{name:/登录已过期/});await expect(auth).toBeVisible();await auth.getByLabel("密码",{exact:true}).fill("Test-password-2026");await auth.getByRole("button",{name:"登录",exact:true}).click();await expect(auth).not.toBeVisible();}
 await expect(panel.getByRole("alert")).toContainText("原选择和请求标识已保留");expect(payloads).toHaveLength(1);await expect(panel.getByLabel("资料包导出范围")).toBeDisabled();await boxes.nth(1).check();
 await page.getByRole("button",{name:"展开专注阅读",exact:true}).click();await expect(panel).not.toBeVisible();await page.getByRole("button",{name:"返回完整工作台",exact:true}).click();await expect(panel.getByRole("alert")).toContainText("原选择和请求标识已保留");await expect(panel.getByLabel("本次导出资料").locator("li")).toHaveCount(1);
 await panel.getByRole("button",{name:"核对并重试原请求",exact:true}).click();await expect(panel.getByRole("alert")).toHaveCount(0);expect(payloads).toHaveLength(2);expect(payloads[1]).toEqual(payloads[0]);const records=await(await request.get(base+`/courses/${s.course.id}/material-exports`,{headers:s.headers})).json();expect(records).toHaveLength(1);expect(records[0].selected_count).toBe(1);await expect(page.getByText("已选 2 份",{exact:true})).toBeVisible();
});

test("任务类型独立过滤、迟到结果不覆盖，历史版本回跳保留整理保护",async({page,request})=>{
 const s=await setup(page,request,1);const row=s.rows[0];const latest=await(await request.post(base+`/documents/${row.id}/versions`,{headers:s.headers,multipart:{file:{name:"新版.md",mimeType:"text/markdown",buffer:Buffer.from("# 新版\n新版文字。")}}})).json();await expect.poll(async()=>(await(await request.get(base+`/versions/${latest.resource_id}`,{headers:s.headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
 await page.goto(`/materials?course=${s.course.id}&document=${row.id}&version=${latest.resource_id}`);await expect(page.locator(".reading-paper")).toContainText("新版文字");await page.locator(".material-jobs summary").click();await expect(page.locator(".material-job")).toHaveCount(4);let catalogue=0;page.on("request",r=>{if(r.url().includes(`/courses/${s.course.id}/documents/page?`))catalogue++;});
 let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});let held!:()=>void;const started=new Promise<void>(resolve=>{held=resolve;});
 await page.route(`**/courses/${s.course.id}/jobs/page?**`,async route=>{if(new URL(route.request().url()).searchParams.get("kind")==="PARSE"){const response=await route.fetch();held();await gate;await route.fulfill({response});}else await route.continue();});
 await page.getByLabel("按任务类型筛选",{exact:true}).selectOption("PARSE");await started;await page.getByLabel("按任务类型筛选",{exact:true}).selectOption("INDEX");await expect(page.locator(".material-job")).toHaveCount(2);release();await expect(page.locator(".material-job small")).toHaveText([/关键词索引/,/关键词索引/]);expect(catalogue).toBe(0);
 await page.getByRole("button",{name:"整理",exact:true}).click();const name=page.locator(".material-metadata").getByLabel("资料名称",{exact:true});await name.fill("未保存的改名");const old=page.locator(".material-job").filter({hasText:"v1"}).getByRole("button",{name:"回到资料版本",exact:true});page.once("dialog",dialog=>dialog.dismiss());await old.click();await expect(name).toHaveValue("未保存的改名");await expect(page.getByLabel("资料版本",{exact:true})).toHaveValue(latest.resource_id);
 page.once("dialog",dialog=>dialog.accept());await old.click();await expect(page.getByLabel("资料版本",{exact:true})).toHaveValue(row.latest_version_id);await expect(page.locator(".reading-paper")).toContainText("章节0的原始内容");
});
