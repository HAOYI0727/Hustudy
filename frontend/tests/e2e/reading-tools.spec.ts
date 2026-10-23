import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
  const username="reading_"+crypto.randomUUID().replaceAll("-","");
  const auth=await(await request.post(base+"/auth/register",{data:{username,password:"Test-password-2026"}})).json();
  const headers={Authorization:"Bearer "+auth.access_token};
  const course=await(await request.post(base+"/courses",{headers,data:{name:"阅读工具验收"}})).json();
  const other=await(await request.post(base+"/courses",{headers,data:{name:"另一门课程"}})).json();
  await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
  return {auth,headers,course,other};
}
async function upload(request:APIRequestContext,headers:Record<string,string>,course:string,text:string,document?:string){
  const response=await request.post(base+(document?`/documents/${document}/versions`:`/courses/${course}/documents`),{headers,multipart:{file:{name:"阅读资料.md",mimeType:"text/markdown",buffer:Buffer.from(text)}}});
  expect(response.status()).toBe(202);const job=await response.json();
  await expect.poll(async()=>(await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
  return (await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
}
const sourceUrl=(course:string,version:{id:string;document_id:string})=>`/materials?course=${course}&document=${version.document_id}&version=${version.id}`;
async function addBookmark(page:Page,label:string){
  await page.getByRole("button",{name:"添加书签",exact:true}).first().click();const dialog=page.getByRole("dialog",{name:"阅读书签",exact:true});
  await dialog.getByLabel("书签名称",{exact:true}).fill(label);await dialog.getByRole("button",{name:"保存书签",exact:true}).click();
  await expect(dialog.getByRole("status").filter({hasText:"书签已保存"})).toBeVisible();return dialog;
}
test("书签去重、改名、历史定位、刷新和课程隔离",async({page,request})=>{
  const {course,headers,other}=await setup(page,request);
  const old=await upload(request,headers,course.id,"# 进程概念\n旧版本的准确解释。\n# 线程\n共享进程资源。");
  const latest=await upload(request,headers,course.id,"# 进程概念\n新版本补充说明。",old.document_id);
  let writes=0;page.on("request",r=>{if(r.method()==="POST"&&/\/notes$|remote-queries|study-reports/.test(r.url()))writes++;});
  await page.goto(sourceUrl(course.id,old));let dialog=await addBookmark(page,"期末重读");await expect(dialog.locator(".reading-bookmark-list article")).toHaveCount(1);
  await dialog.getByRole("button",{name:"关闭阅读书签",exact:true}).click();dialog=await addBookmark(page,"进程重点");await expect(dialog.locator(".reading-bookmark-list article")).toHaveCount(1);
  await dialog.getByRole("button",{name:"改名",exact:true}).click();await dialog.getByLabel("修改书签名称").fill("我的重读清单");await dialog.getByRole("button",{name:"保存名称",exact:true}).click();
  await dialog.getByRole("button",{name:"关闭阅读书签",exact:true}).click();await page.getByLabel("资料版本",{exact:true}).selectOption(latest.id);
  await expect(page.locator(".reading-paper")).toContainText("新版本补充说明");await page.getByRole("button",{name:"阅读书签 · 1",exact:true}).click();
  await dialog.getByRole("button",{name:"回到原文",exact:true}).click();await expect(dialog).not.toBeVisible();await expect(page.getByLabel("资料版本",{exact:true})).toHaveValue(old.id);
  await expect(page.locator(".chunk-highlight")).toContainText("旧版本的准确解释");await expect(page.locator(".chunk-highlight")).toBeFocused();
  await page.reload();await page.getByRole("button",{name:"阅读书签 · 1",exact:true}).click();await expect(dialog).toContainText("我的重读清单");
  await dialog.getByRole("button",{name:"关闭阅读书签",exact:true}).click();await page.getByLabel("当前课程",{exact:true}).selectOption(other.id);
  await page.getByRole("button",{name:"阅读书签",exact:true}).click();await expect(dialog).toContainText("从一个值得重读的片段开始");expect(writes).toBe(0);
});
test("书签撤权、存储写失败及损坏数据不会假成功或静默清除",async({page,request})=>{
  const {course,headers,auth}=await setup(page,request);const v=await upload(request,headers,course.id,"# 不应缓存\n正文只从服务器读取。");
  await page.goto(sourceUrl(course.id,v));let dialog=await addBookmark(page,"来源可能失效");await dialog.getByRole("button",{name:"关闭阅读书签",exact:true}).click();
  await page.evaluate(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key.startsWith("hustudy-bookmarks:"))throw new Error("isolated quota");return original.call(this,key,value);};});
  await page.getByRole("button",{name:"添加书签",exact:true}).first().click();await dialog.getByLabel("书签名称",{exact:true}).fill("不应保存");await dialog.getByRole("button",{name:"保存书签",exact:true}).click();await expect(dialog.getByRole("alert")).toContainText("未能写入");
  await page.reload();expect((await request.delete(base+`/documents/${v.document_id}`,{headers})).status()).toBe(204);
  await page.getByRole("button",{name:"阅读书签 · 1",exact:true}).click();await dialog.getByRole("button",{name:"回到原文",exact:true}).click();await expect(dialog.getByRole("alert")).toBeVisible();await expect(dialog.locator(".reading-bookmark-list article")).toHaveCount(1);
  page.once("dialog",d=>d.accept());await dialog.getByRole("button",{name:"移除",exact:true}).click();await expect(dialog.locator(".reading-bookmark-list article")).toHaveCount(0);
  await page.evaluate(({owner,course})=>{localStorage.setItem(`hustudy-bookmarks:v1:${owner}:${course}`,"unreadable");window.dispatchEvent(new StorageEvent("storage"));},{owner:auth.user.id,course:course.id});
  await expect(dialog.getByRole("alert")).toContainText("已保留原存储");expect(await page.evaluate(({owner,course})=>localStorage.getItem(`hustudy-bookmarks:v1:${owner}:${course}`),{owner:auth.user.id,course:course.id})).toBe("unreadable");
});
test("回书签前保护未保存阅读笔记，拒绝后保持当前版本和草稿",async({page,request})=>{
  const {course,headers}=await setup(page,request);const old=await upload(request,headers,course.id,"# 旧资料\n历史正文");const latest=await upload(request,headers,course.id,"# 新资料\n新正文",old.document_id);
  await page.goto(sourceUrl(course.id,old));const dialog=await addBookmark(page,"返回旧版");await dialog.getByRole("button",{name:"关闭阅读书签",exact:true}).click();
  await page.getByLabel("资料版本",{exact:true}).selectOption(latest.id);await page.getByRole("button",{name:"阅读笔记",exact:true}).click();await page.getByLabel("阅读时记录理解").fill("正在编辑的理解不能丢失");
  await page.getByRole("button",{name:"阅读书签 · 1",exact:true}).click();page.once("dialog",d=>d.dismiss());await dialog.getByRole("button",{name:"回到原文",exact:true}).click();
  await expect(dialog).toBeVisible();await expect(page.getByLabel("资料版本",{exact:true})).toHaveValue(latest.id);
  await dialog.getByRole("button",{name:"关闭阅读书签",exact:true}).click();await expect(page.getByLabel("阅读时记录理解")).toHaveValue("正在编辑的理解不能丢失");
});
test("版本完整对照与分页，原文回跳不改变已有笔记引用",async({page,request})=>{
  const {course,headers}=await setup(page,request);
  const old=await upload(request,headers,course.id,Array.from({length:14},(_,i)=>`# 知识点${i}\n${i?"旧解释"+i:"同一段文字"}`).join("\n"));
  const latest=await upload(request,headers,course.id,Array.from({length:14},(_,i)=>`# 知识点${i}\n${i?"新解释"+i:"同一段文字"}`).join("\n")+"\n# 新章节\n新增说明",old.document_id);
  const chunks=await(await request.get(base+`/versions/${old.id}/chunks`,{headers})).json();
  const note=await(await request.post(base+"/notes",{headers,data:{request_id:crypto.randomUUID(),course_id:course.id,title:"历史引用保留",content:"原来的理解",citations:[{version_id:old.id,chunk_id:chunks[0].id,quote:chunks[0].text}]}})).json();
  await page.goto(sourceUrl(course.id,latest));await page.getByRole("button",{name:"版本对照",exact:true}).click();const dialog=page.getByRole("dialog",{name:"版本文本对照",exact:true});
  await dialog.getByRole("button",{name:"加载对照",exact:true}).click();await expect(dialog.locator('.compare-stats [data-status="same"] strong')).toHaveText("1");await expect(dialog.locator('.compare-stats [data-status="changed"] strong')).toHaveText("13");
  await expect(dialog.locator(".compare-row")).toHaveCount(12);const pager=dialog.getByRole("navigation",{name:"版本对照分页"});await pager.getByRole("button",{name:"下一页",exact:true}).click();await expect(dialog.locator(".compare-row")).toHaveCount(2);
  await dialog.getByLabel("搜索版本对照内容").fill("新解释13");await expect(dialog.locator(".compare-row")).toHaveCount(1);await dialog.locator(".compare-row summary").click();await expect(dialog.getByRole("region",{name:"左侧原文"})).toContainText("旧解释13");
  await dialog.getByRole("button",{name:"阅读左侧原文",exact:true}).click();await expect(dialog).not.toBeVisible();await expect(page.getByLabel("资料版本",{exact:true})).toHaveValue(old.id);await expect(page.locator(".chunk-highlight")).toContainText("旧解释13");
  const citations=await(await request.get(base+`/notes/${note.id}/citations`,{headers})).json();expect(citations).toHaveLength(1);expect(citations[0].version_id).toBe(old.id);
});
test("版本选择和关闭拒绝迟到结果，失败后只显式重试",async({page,request})=>{
  const {course,headers}=await setup(page,request);const old=await upload(request,headers,course.id,"# 相同定位\n旧内容");const latest=await upload(request,headers,course.id,"# 相同定位\n新内容",old.document_id);
  await page.goto(sourceUrl(course.id,latest));await expect(page.locator(".reading-paper")).toBeVisible();
  let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);let started=false;
  await page.route(`**/api/v1/versions/${old.id}/chunks`,async route=>{started=true;await gate;await route.continue();});
  await page.getByRole("button",{name:"版本对照",exact:true}).click();const dialog=page.getByRole("dialog",{name:"版本文本对照",exact:true});await dialog.getByRole("button",{name:"加载对照",exact:true}).click();await expect.poll(()=>started).toBe(true);
  await dialog.getByLabel("对照左侧版本").selectOption(latest.id);const delayed=page.waitForResponse(r=>r.url().endsWith(`/versions/${old.id}/chunks`));release();await(await delayed).finished();await expect(dialog).toContainText("请选择两个不同版本");
  await expect.poll(async()=>await page.evaluate(()=>performance.getEntriesByType("resource").filter(r=>r.name.includes("/chunks")).length)).toBeGreaterThan(1);await expect(dialog.locator(".compare-stats")).toHaveCount(0);
  await page.unroute(`**/api/v1/versions/${old.id}/chunks`);await dialog.getByLabel("对照左侧版本").selectOption(old.id);
  let calls=0;await page.route(`**/api/v1/versions/${old.id}/chunks`,route=>{calls++;return route.fulfill({status:503,json:{error:{code:"TEST",message:"隔离对照失败"}}});});
  await dialog.getByRole("button",{name:"加载对照",exact:true}).click();await expect(dialog.getByRole("alert")).toContainText("隔离对照失败");expect(calls).toBe(1);await expect(dialog.locator(".compare-stats")).toHaveCount(0);
  await page.unroute(`**/api/v1/versions/${old.id}/chunks`);await dialog.getByRole("button",{name:"加载对照",exact:true}).click();await expect(dialog.locator(".compare-stats")).toBeVisible();
  await page.keyboard.press("Escape");await expect(dialog).not.toBeVisible();await expect(page.getByRole("button",{name:"版本对照",exact:true})).toBeFocused();
  let releaseClosed!:()=>void;const closedGate=new Promise<void>(resolve=>releaseClosed=resolve);let closedStarted=false;
  await page.route(`**/api/v1/versions/${old.id}/chunks`,async route=>{closedStarted=true;await closedGate;await route.continue();});
  await page.getByRole("button",{name:"版本对照",exact:true}).click();await dialog.getByRole("button",{name:"加载对照",exact:true}).click();await expect.poll(()=>closedStarted).toBe(true);
  await page.keyboard.press("Escape");await expect(dialog).not.toBeVisible();const closedResponse=page.waitForResponse(r=>r.url().endsWith(`/versions/${old.id}/chunks`));releaseClosed();await(await closedResponse).finished();
  await page.getByRole("button",{name:"版本对照",exact:true}).click();await expect(dialog.locator(".compare-stats")).toHaveCount(0);await expect(dialog).toContainText("选好版本，再开始对照");
});
test("书签片段缺失不能静默回退整份资料",async({page,request})=>{
  const {course,headers}=await setup(page,request);const v=await upload(request,headers,course.id,"# 固定片段\n不应丢失定位");
  await page.goto(sourceUrl(course.id,v));const dialog=await addBookmark(page,"固定原文");await dialog.getByRole("button",{name:"关闭阅读书签",exact:true}).click();
  await page.route(`**/api/v1/versions/${v.id}/chunks`,route=>route.fulfill({json:[]}));
  await page.getByRole("button",{name:"阅读书签 · 1",exact:true}).click();await dialog.getByRole("button",{name:"回到原文",exact:true}).click();
  await expect(dialog).toBeVisible();await expect(dialog.getByRole("alert")).toContainText("原文片段已不可用");await expect(dialog.locator(".reading-bookmark-list article")).toHaveCount(1);
});
for(const tool of ["书签","对照"])test(`${tool}遇401让出弹窗，恢复登录后显式继续`,async({page,request})=>{
  const {course,headers}=await setup(page,request);const old=await upload(request,headers,course.id,"# 历史来源\n第一版");const latest=await upload(request,headers,course.id,"# 历史来源\n第二版",old.document_id);
  await page.goto(sourceUrl(course.id,latest));const bookmarks=await addBookmark(page,"登录过期仍保留");await bookmarks.getByRole("button",{name:"关闭阅读书签",exact:true}).click();
  const denied=tool==="书签"?`**/api/v1/documents/${old.document_id}`:`**/api/v1/versions/${old.id}/chunks`;
  let calls=0;await page.route(denied,route=>{calls++;return route.fulfill({status:401,json:{error:{code:"UNAUTHORIZED",message:"隔离登录过期"}}});});
  if(tool==="书签"){await page.getByRole("button",{name:"阅读书签 · 1",exact:true}).click();await bookmarks.getByRole("button",{name:"回到原文",exact:true}).click();}
  else{await page.getByRole("button",{name:"版本对照",exact:true}).click();await page.getByRole("dialog",{name:"版本文本对照",exact:true}).getByRole("button",{name:"加载对照",exact:true}).click();}
  const login=page.getByRole("dialog",{name:"登录已过期 · 保留当前工作",exact:true});await expect(login).toBeVisible();await expect(page.locator("dialog[open]")).toHaveCount(0);expect(calls).toBe(1);
  await page.unroute(denied);await login.getByLabel("密码",{exact:true}).fill("Test-password-2026");await login.getByRole("button",{name:"登录",exact:true}).click();await expect(login).not.toBeVisible();
  await page.getByRole("button",{name:"阅读书签 · 1",exact:true}).click();await expect(bookmarks.locator(".reading-bookmark-list article")).toHaveCount(1);await bookmarks.getByRole("button",{name:"关闭阅读书签",exact:true}).click();
  await expect(page.locator(".compare-stats")).not.toBeVisible();
});
for(const width of [320,820,1440])test(`阅读工具布局、完整纯文本与键盘 ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:960});const {course,headers}=await setup(page,request);
  const old=await upload(request,headers,course.id,"# 布局对照\n<script>window.injectedReading=true</script>\n"+"长文本".repeat(240));const latest=await upload(request,headers,course.id,"# 布局对照\n改进后的自制示例。",old.document_id);
  await page.goto(sourceUrl(course.id,latest));const bookmarks=await addBookmark(page,"小屏也能轻松重读");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);expect(await bookmarks.evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBe(true);
  await bookmarks.evaluate(e=>e.scrollTop=0);await page.screenshot({path:test.info().outputPath(`bookmarks-${width}.png`)});await page.keyboard.press("Escape");await expect(bookmarks).not.toBeVisible();
  await page.getByRole("button",{name:"版本对照",exact:true}).click();const compare=page.getByRole("dialog",{name:"版本文本对照",exact:true});await compare.getByRole("button",{name:"加载对照",exact:true}).click();await compare.locator(".compare-row summary").click();
  await expect(compare.locator("pre").first()).toContainText("<script>window.injectedReading=true</script>");expect(await page.evaluate(()=>(window as unknown as {injectedReading?:boolean}).injectedReading)).toBeUndefined();
  expect(await compare.evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  if(width===1440)expect((await compare.boundingBox())!.width).toBeGreaterThan(1050);
  await compare.evaluate(e=>e.scrollTop=0);await page.screenshot({path:test.info().outputPath(`compare-${width}.png`)});await page.keyboard.press("Tab");expect(await compare.evaluate(e=>e.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");await expect(compare).not.toBeVisible();await expect(page.getByRole("button",{name:"版本对照",exact:true})).toBeFocused();
});
