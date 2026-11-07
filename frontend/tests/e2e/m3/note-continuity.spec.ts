import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext,count=1){
 const username="continuity_"+crypto.randomUUID().replaceAll("-","");
 const auth=await(await request.post(base+"/auth/register",{data:{username,password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"连续学习"}})).json();const notes=[];
 for(let i=0;i<count;i++)notes.push(await(await request.post(base+"/notes",{headers,data:{course_id:course.id,title:`学习笔记${String(i).padStart(2,"0")}`,content:`原始理解${i}。${i===0?"正文独特线索":""}`}})).json());
 await page.addInitScript(({token,username})=>{localStorage.setItem("hustudy_token",token);localStorage.setItem("hustudy_user",username);},{token:auth.access_token,username});
 return {headers,course,notes,auth};
}
async function reload(page:Page){page.once("dialog",dialog=>dialog.accept());await page.reload();}
async function copies(page:Page,userId:string){return page.evaluate(userId=>Object.keys(localStorage).filter(key=>key.startsWith(`hustudy-note-recovery:v1:${userId}:`)).map(key=>JSON.parse(localStorage.getItem(key)!)),userId);}
for(const width of [390,1440])test(`失败草稿刷新恢复、服务端冲突核对、恢复不自动保存 ${width}px`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});const s=await setup(page,request);const note=s.notes[0];let writes=0;
 await page.route(`**/api/v1/notes/${note.id}`,async route=>{if(route.request().method()==="PATCH"){writes++;await route.fulfill({status:503,json:{error:{message:"隔离保存失败"}}});}else await route.continue();});
 await page.goto(`/notes?course=${s.course.id}&note=${note.id}`);await page.getByLabel('自动保存笔记', {exact: true}).check();await page.getByLabel("Markdown 正文").fill("离线期间不能丢失的理解 $x^2$。");await expect(page.locator(".save-indicator")).toContainText("未保存");
 await expect.poll(async()=>(await copies(page,s.auth.user.id)).length).toBe(1);
 const server=await request.patch(base+`/notes/${note.id}`,{headers:s.headers,data:{revision:note.revision,content:"另一窗口的新理解。"}});expect(server.status()).toBe(200);
 await reload(page);await expect(page.getByLabel("Markdown 正文")).toHaveValue("另一窗口的新理解。");const before=writes;
 await page.getByRole("button",{name:"核对并恢复",exact:true}).click();await expect(page.getByLabel("Markdown 正文")).toHaveValue("离线期间不能丢失的理解 $x^2$。");await expect(page.locator(".conflict-panel")).toContainText("另一窗口的新理解。");
 await page.waitForTimeout(2200);expect(writes).toBe(before);
 page.once("dialog",dialog=>dialog.accept());await page.getByRole("button",{name:"核对后保留本地草稿",exact:true}).click();
 await page.waitForTimeout(2100);expect(writes).toBe(before);
 await page.unroute(`**/api/v1/notes/${note.id}`);await page.getByRole("button",{name:"立即保存",exact:true}).click();
 await expect(page.locator(".save-indicator")).toHaveText("已保存到本地服务");
 expect((await(await request.get(base+`/notes/${note.id}`,{headers:s.headers})).json()).content).toBe("离线期间不能丢失的理解 $x^2$。");
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);
});

test("新建结果未知后刷新沿原请求身份恢复，不重复创建",async({page,request})=>{
 const s=await setup(page,request,0);let createdRequest="";
 await page.route("**/api/v1/notes",async route=>{if(route.request().method()!=="POST"){await route.continue();return;}createdRequest=route.request().postDataJSON().request_id;const response=await route.fetch();expect(response.status()).toBe(201);await route.fulfill({status:503,json:{error:{message:"保存结果未确认"}}});});
 await page.goto(`/notes?course=${s.course.id}`);await page.getByRole("button",{name:"新建笔记",exact:true}).click();await page.getByLabel('自动保存笔记', {exact: true}).check();await page.getByLabel("笔记标题").fill("未知结果恢复");await page.getByLabel("Markdown 正文").fill("提交前原始理解");await expect(page.locator(".save-indicator")).toContainText("未保存");
 await expect.poll(async()=>(await copies(page,s.auth.user.id))[0]?.pending?.request_id).toBeTruthy();
 await reload(page);await page.getByRole("button",{name:"核对并恢复",exact:true}).click();await page.unroute("**/api/v1/notes");
 const saved=page.waitForResponse(response=>response.url().endsWith("/api/v1/notes")&&response.request().method()==="POST");await page.getByRole("button",{name:"立即保存",exact:true}).click();const response=await saved;expect(response.request().postDataJSON().request_id).toBe(createdRequest);
 await expect(page.locator(".save-indicator")).toHaveText("已保存到本地服务");
 const rows=await(await request.get(base+`/notes?course_id=${s.course.id}`,{headers:s.headers})).json();expect(rows).toHaveLength(1);expect(rows[0].title).toBe("未知结果恢复");
});

test("笔记目录按元数据分页，正文搜索命中且只打开所选正文",async({page,request})=>{
 const s=await setup(page,request,25);const unbounded:string[]=[];const bodies:string[]=[];
 page.on("request",r=>{if(/\/api\/v1\/notes(?:\?|$)/.test(r.url())&&r.method()==="GET")unbounded.push(r.url());if(/\/api\/v1\/notes\/[a-f0-9-]{36}$/.test(r.url()))bodies.push(r.url());});
 await page.goto(`/notes?course=${s.course.id}`);const manager=page.getByRole("region",{name:"笔记管理列表"});await expect(manager.locator(".note-manager-row")).toHaveCount(20);expect(bodies).toEqual([]);
 await page.getByRole("navigation",{name:"笔记管理分页"}).getByRole("button",{name:"下一页笔记",exact:true}).click();await expect(manager.locator(".note-manager-row")).toHaveCount(5);
 await page.getByLabel("搜索笔记",{exact:true}).fill("正文独特线索");await expect(manager.locator(".note-manager-row")).toHaveCount(1);await manager.getByRole("button",{name:"学习笔记00",exact:true}).click();await expect(page.getByLabel("Markdown 正文")).toHaveValue(/正文独特线索/);expect(bodies).toHaveLength(1);expect(unbounded).toEqual([]);
});

test("恢复副本按服务端账户隔离、原笔记删除时保留副本供复制",async({page,request,context})=>{
 const s=await setup(page,request);const note=s.notes[0];await page.route(`**/api/v1/notes/${note.id}`,async route=>{if(route.request().method()==="PATCH")await route.fulfill({status:503,json:{error:{message:"隔离失败"}}});else await route.continue();});
 await page.goto(`/notes?course=${s.course.id}&note=${note.id}`);await page.getByLabel('自动保存笔记', {exact: true}).check();await page.getByLabel("Markdown 正文").fill("只能由原账户恢复的草稿");await expect(page.locator(".save-indicator")).toContainText("未保存");
 await request.delete(base+`/notes/${note.id}`,{headers:s.headers});await reload(page);await page.getByRole("button",{name:"核对并恢复",exact:true}).click();await expect(page.getByRole("region",{name:"本机笔记恢复"})).toContainText("原笔记无法核对");
 const second=await context.newPage();const other=await setup(second,request,0);await second.goto(`/notes?course=${other.course.id}`);await expect(second.getByRole("region",{name:"本机笔记恢复"})).toBeVisible();await expect(second.getByRole("button",{name:"核对并恢复",exact:true})).toHaveCount(0);expect((await copies(second,s.auth.user.id)).length).toBeGreaterThan(0);await second.close();
});

test("恢复另一份副本前保留当前未保存草稿，切换不覆盖",async({page,request})=>{
 const s=await setup(page,request);const note=s.notes[0];
 await page.route(`**/api/v1/notes/${note.id}`,async r=>{if(r.request().method()==="PATCH")await r.fulfill({status:503,json:{error:{message:"隔离失败"}}});else await r.continue();});
 await page.goto(`/notes?course=${s.course.id}&note=${note.id}`);await page.getByLabel('自动保存笔记', {exact: true}).check();await page.getByLabel("Markdown 正文").fill("第一份未保存的理解");await expect(page.locator(".save-indicator")).toContainText("未保存");await reload(page);
 await page.getByLabel("Markdown 正文").fill("当前窗口的另一份理解");await expect(page.locator(".save-indicator")).toContainText("未保存");
 page.once("dialog",d=>d.accept());await page.getByRole("button",{name:"核对并恢复",exact:true}).click();await expect(page.getByLabel("Markdown 正文")).toHaveValue("第一份未保存的理解");
 await expect.poll(async()=>(await copies(page,s.auth.user.id)).filter(row=>row.draft.content==="当前窗口的另一份理解").length).toBe(1);
 await page.getByRole("button",{name:"检查恢复副本",exact:true}).click();await expect(page.getByRole("region",{name:"本机笔记恢复"}).getByText("当前窗口的另一份理解",{exact:true})).toHaveCount(1);
});
