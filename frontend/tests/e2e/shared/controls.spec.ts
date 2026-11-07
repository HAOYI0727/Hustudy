import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
 const username="controls_"+crypto.randomUUID().replaceAll("-","");const auth=await(await request.post(base+"/auth/register",{data:{username,password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"共享控件 · 学习工作台"}})).json();
 await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
 return {headers,course,auth};
}
async function upload(request:APIRequestContext,headers:Record<string,string>,course:string,document?:string){
 const response=await request.post(base+(document?`/documents/${document}/versions`:`/courses/${course}/documents`),{headers,multipart:{file:{name:"学习资料.md",mimeType:"text/markdown",buffer:Buffer.from("# 进程与线程\n线程共享进程资源。\n# 内存管理\n虚拟地址空间。"+(document?"\n新版增加说明。":""))}}});expect(response.status()).toBe(202);const job=await response.json();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");return (await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
}
async function fixture(page:Page){await page.locator(".content>.page").waitFor();await page.evaluate(()=>{
 const select=document.createElement("select");select.setAttribute("aria-label","隔离选项验收");select.id="isolated-select";select.setAttribute("aria-expanded","false");
 const a=new Option("Alpha 当前","a"),disabled=new Option("Beta 禁用","b");disabled.disabled=true;select.append(a,disabled);
 const group=document.createElement("optgroup");group.label="后续章节";for(let i=0;i<28;i++)group.append(new Option("章节 "+String(i).padStart(2,"0"),"chapter-"+i));select.append(group);
 const blocked=document.createElement("optgroup");blocked.label="禁用分组";blocked.disabled=true;blocked.append(new Option("组内不可选择","blocked"));select.append(blocked,new Option("Zulu 最后一个可用选项","z"));
 select.addEventListener("change",()=>select.dataset.changes=String(Number(select.dataset.changes||0)+1));document.querySelector(".content>.page")!.prepend(select);
 });return page.getByLabel("隔离选项验收",{exact:true});}
test("桌面下拉选择驱动原React筛选，程序化选择仍兼容",async({page,request})=>{
 const s=await setup(page,request);await upload(request,s.headers,s.course.id);await page.goto(`/materials?course=${s.course.id}`);const field=page.getByLabel("按处理状态筛选",{exact:true});
 await field.click();const menu=page.getByRole("listbox",{name:"按处理状态筛选的选项",exact:true});await expect(menu).toBeVisible();await expect(field).toBeFocused();
 await menu.getByRole("option",{name:"可检索",exact:true}).click();await expect(menu).not.toBeVisible();await expect(field).toHaveValue("ready");await expect(field).toBeFocused();await expect(page.locator(".material-document")).toHaveCount(1);
 await field.selectOption("failed");await expect(page.getByText("没有匹配资料，试试清除筛选",{exact:true})).toBeVisible();
 await field.click();await page.keyboard.press("Home");await page.keyboard.press("Enter");await expect(field).toHaveValue("all");await expect(page.locator(".material-document")).toHaveCount(1);
});
test("键盘/快速定位/禁用分组/滚动，取消不改值且同值不重复提交",async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/overview?course=${s.course.id}`);const field=await fixture(page);
 await field.click();const menu=page.getByRole("listbox",{name:"隔离选项验收的选项",exact:true});await expect(menu.getByRole("option",{name:"Beta 禁用",exact:true})).toBeDisabled();await expect(menu.getByRole("option",{name:"组内不可选择",exact:true})).toBeDisabled();
 await page.keyboard.press("ArrowDown");await expect(field).toHaveAttribute("aria-activedescendant",/\-2$/);await page.keyboard.press("Escape");await expect(field).toHaveValue("a");await expect(field).toHaveAttribute("aria-expanded","false");await expect(field).not.toHaveAttribute("data-changes",/./);
 await field.press("ArrowDown");await page.keyboard.press("End");await expect.poll(()=>page.locator(".select-menu-options").evaluate(e=>e.scrollTop)).toBeGreaterThan(0);await page.keyboard.press("Enter");await expect(field).toHaveValue("z");await expect(field).toHaveAttribute("data-changes","1");
 await field.click();await menu.getByRole("option",{name:"Zulu 最后一个可用选项",exact:true}).click();await expect(field).toHaveAttribute("data-changes","1");
 await field.click();await page.keyboard.press("a");await page.keyboard.press("Enter");await expect(field).toHaveValue("a");await expect(field).toHaveAttribute("data-changes","2");
 await field.click();await page.keyboard.press("Tab");await expect(menu).not.toBeVisible();await expect(field).not.toBeFocused();
});
test("弹窗内选项进入顶层，Escape先关菜单再关原弹窗",async({page,request})=>{
 const s=await setup(page,request);const old=await upload(request,s.headers,s.course.id);const latest=await upload(request,s.headers,s.course.id,old.document_id);
 await page.goto(`/materials?course=${s.course.id}&document=${old.document_id}&version=${latest.id}`);await page.getByRole("button",{name:"版本对照",exact:true}).click();const dialog=page.getByRole("dialog",{name:"版本文本对照",exact:true});const field=dialog.getByLabel("对照左侧版本",{exact:true});
 await field.click();const menu=dialog.getByRole("listbox",{name:"对照左侧版本的选项",exact:true});await expect(menu).toBeVisible();expect(await menu.evaluate(e=>e.closest("dialog")?.open)).toBe(true);
 await page.keyboard.press("Escape");await expect(menu).not.toBeVisible();await expect(dialog).toBeVisible();await expect(field).toBeFocused();
 await field.click();await menu.getByRole("option",{name:/v2/}).click();await expect(dialog.getByText("请选择两个不同版本。",{exact:true})).toBeVisible();
 await page.keyboard.press("Escape");await expect(dialog).not.toBeVisible();
});
test("选项变化/禁用/移除和外部滚动关闭旧菜单，不产生值写入",async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/overview?course=${s.course.id}`);const field=await fixture(page);const menu=page.getByRole("listbox",{name:"隔离选项验收的选项",exact:true});
 await field.click();await field.evaluate(e=>(e as HTMLSelectElement).disabled=true);await expect(menu).not.toBeVisible();
 await field.evaluate(e=>(e as HTMLSelectElement).disabled=false);await field.click();await field.evaluate(e=>(e as HTMLSelectElement).options[0].text="新的选项快照");await expect(menu).not.toBeVisible();await expect(field).not.toHaveAttribute("data-changes",/./);
 await field.click();await page.evaluate(()=>window.scrollTo(0,300));await expect(menu).not.toBeVisible();await expect(field).toHaveValue("a");
 await field.scrollIntoViewIfNeeded();await field.click();await field.evaluate(e=>e.remove());await expect(menu).not.toBeVisible();
});
test("原生降级不影响选择和表单行为",async({page,request})=>{
 await page.addInitScript(()=>{Object.defineProperty(HTMLElement.prototype,"showPopover",{configurable:true,value:undefined});});
 const s=await setup(page,request);await page.goto(`/materials?course=${s.course.id}`);const field=page.getByLabel("资料排序",{exact:true});await field.selectOption("name");await expect(field).toHaveValue("name");await field.focus();await field.press("ArrowDown");await expect(page.locator(".select-menu")).toHaveCount(0);
});
test("后台401关闭菜单且不遮住重登",async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/materials?course=${s.course.id}`);await page.getByLabel("资料排序",{exact:true}).click();await expect(page.getByRole("listbox",{name:"资料排序的选项",exact:true})).toBeVisible();
 await page.route(`**/api/v1/courses/${s.course.id}/documents/page?*`,route=>route.fulfill({status:401,json:{error:{message:"隔离认证过期"}}}));
 await page.getByRole("button",{name:"刷新资料与处理状态",exact:true}).evaluate(e=>(e as HTMLButtonElement).click());
 await expect(page.getByRole("dialog",{name:"登录已过期 · 保留当前工作",exact:true})).toBeVisible();await expect(page.locator(".select-menu")).toHaveCount(0);
});
for(const width of [320,820,1440])test(`控件/折叠/阴影与适中字级 ${width}px`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});const s=await setup(page,request);await upload(request,s.headers,s.course.id);await page.goto(`/overview?course=${s.course.id}`);const hero=page.locator(".dashboard-hero h2"),card=page.locator(".metric-card").first();
 expect(await hero.evaluate(e=>parseFloat(getComputedStyle(e).fontSize))).toBeLessThanOrEqual(31);expect(await card.evaluate(e=>getComputedStyle(e).boxShadow)).not.toBe("none");
 if(width>=820){await card.hover();await expect.poll(()=>card.evaluate(e=>getComputedStyle(e).transform)).toContain("-3");await page.emulateMedia({reducedMotion:"reduce"});await expect.poll(()=>card.evaluate(e=>getComputedStyle(e).transform)).toBe("none");}
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:test.info().outputPath(`cards-${width}.png`),fullPage:true});
 await page.goto(`/materials?course=${s.course.id}`);if(width<768)await page.getByRole("button",{name:/资料库与上传 展开/}).click();const field=page.getByLabel("按处理状态筛选",{exact:true});
 if(width>=768){await field.click();const menu=page.getByRole("listbox",{name:"按处理状态筛选的选项",exact:true});await expect(menu).toBeVisible();expect(await menu.evaluate(e=>e.getBoundingClientRect().right<=innerWidth-10)).toBe(true);expect(await menu.evaluate(e=>e.scrollHeight<=e.clientHeight+1)).toBe(true);await page.screenshot({path:test.info().outputPath(`options-${width}.png`)});await page.keyboard.press("Escape");}
 else{await field.selectOption("ready");expect(await field.evaluate(e=>e.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);await expect(page.locator(".select-menu")).toHaveCount(0);}
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
