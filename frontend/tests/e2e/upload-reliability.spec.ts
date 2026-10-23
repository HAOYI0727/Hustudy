import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
 const auth=await(await request.post(base+"/auth/register",{data:{username:"upload_runtime_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};const course=await(await request.post(base+"/courses",{headers,data:{name:"上传处理服务"}})).json();
 await page.addInitScript(auth=>{if(window===window.top){localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);}},auth);
 return{auth,headers,course};
}
async function reveal(page:Page){const service=page.getByRole("region",{name:"资料处理服务",exact:true,includeHidden:true});await expect(service).toBeAttached();if(!await service.isVisible())await page.getByRole("button",{name:/资料库与上传/}).click();return service;}
for(const width of [390,1440])test(`服务不可用仍保存原件，刷新恢复不重传且布局不溢出 ${width}px`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});const s=await setup(page,request);let unavailable=true,uploads=0;
 await page.route("**/processing/status",route=>unavailable?route.fulfill({json:{state:"unavailable",checked_at:new Date().toISOString(),message:"资料处理服务暂不可用，原件仍可上传保存；处理恢复后继续，无需重复上传。"}}):route.continue());page.on("request",r=>{if(r.method()==="POST"&&r.url().endsWith(`/courses/${s.course.id}/documents`))uploads++;});
 await page.goto(`/materials?course=${s.course.id}`);const service=await reveal(page);await expect(service).toContainText("暂不可用");await page.getByLabel("选择课程文件",{exact:true}).setInputFiles({name:"原件保存.md",mimeType:"text/markdown",buffer:Buffer.from("# 原件保存\n服务状态提示不能导致重复上传。")});await page.getByRole("button",{name:"上传并开始整理",exact:true}).click();await expect(page.getByRole("region",{name:"资料上传队列",exact:true})).toContainText("已保存");expect(uploads).toBe(1);
 const docs=await(await request.get(base+`/courses/${s.course.id}/documents`,{headers:s.headers})).json();expect(docs).toHaveLength(1);await expect.poll(async()=>(await(await request.get(base+`/versions/${docs[0].latest_version_id}`,{headers:s.headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
 unavailable=false;await reveal(page);await service.getByRole("button",{name:"重试",exact:true}).click();await expect(service).toHaveCount(0);expect(uploads).toBe(1);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);
});

test("服务状态读取失败仅显式重试，上传选择与未保存输入保留",async({page,request})=>{
 const s=await setup(page,request);let reads=0,fail=true;await page.route("**/processing/status",route=>{reads++;return fail?route.fulfill({status:503,json:{error:{message:"isolated status failure"}}}):route.continue();});await page.goto(`/materials?course=${s.course.id}`);const service=await reveal(page);await expect(service).toContainText("暂时无法确认");await page.getByLabel("选择课程文件",{exact:true}).setInputFiles({name:"待上传.md",mimeType:"text/markdown",buffer:Buffer.from("# 队列保留\n刷新服务状态不能清除选择。")});const queue=page.getByRole("region",{name:"资料上传队列",exact:true});await expect(queue).toContainText("待上传.md");await queue.evaluate(e=>e.setAttribute("data-runtime-queue","kept"));expect(reads).toBe(1);fail=false;await service.getByRole("button",{name:"重试",exact:true}).click();await expect(service).toHaveCount(0);expect(reads).toBe(2);await expect(queue).toHaveAttribute("data-runtime-queue","kept");await expect(queue).toContainText("待上传.md");
});

test("异常重试401让出重登，正常状态安静且不自动上传",async({page,request})=>{
 const s=await setup(page,request);let unavailable=true,unauthorized=false,posts=0;
 page.on("request",r=>{if(r.method()==="POST"&&r.url().endsWith(`/courses/${s.course.id}/documents`))posts++;});
 await page.route("**/processing/status",route=>unauthorized?route.fulfill({status:401,json:{error:{message:"isolated expiry"}}}):unavailable?route.fulfill({json:{state:"unavailable",checked_at:new Date().toISOString(),message:"处理暂不可用，原件保留。"}}):route.continue());
 await page.goto(`/materials?course=${s.course.id}`);const service=await reveal(page);await expect(service).toContainText("暂不可用");
 await page.getByLabel("选择课程文件",{exact:true}).setInputFiles({name:"重登后待确认.md",mimeType:"text/markdown",buffer:Buffer.from("# 登录保护\n不自动重放上传。")});
 unauthorized=true;await service.getByRole("button",{name:"重试",exact:true}).click();const dialog=page.getByRole("dialog",{name:/登录已过期/});await expect(dialog).toBeVisible();
 unavailable=false;unauthorized=false;await dialog.getByLabel("密码",{exact:true}).fill("Test-password-2026");await dialog.getByRole("button",{name:"登录",exact:true}).click();await expect(dialog).not.toBeVisible();
 await expect(page.getByRole("region",{name:"资料上传队列",exact:true})).toContainText("重登后待确认.md");await expect(service).toHaveCount(0);await expect(page.getByRole("button",{name:"刷新处理服务",exact:true})).toHaveCount(0);expect(posts).toBe(0);
});
