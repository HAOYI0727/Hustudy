import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
 const auth=await(await request.post(base+"/auth/register",{data:{username:"workspace_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"操作系统 · 全工作区",category:"专业必修"}})).json();const note=await(await request.post(base+"/notes",{headers,data:{course_id:course.id,title:"已保存的学习笔记",content:"## 进程与线程\n进程拥有资源，线程共享进程资源。"}})).json();
 const upload=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:"课程原文.md",mimeType:"text/markdown",buffer:Buffer.from("# 进程\n进程分配资源。\n# 线程\n线程共享进程资源。")}}})).json();await expect.poll(async()=>(await(await request.get(base+`/versions/${upload.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
 await request.post(base+`/courses/${course.id}/question-bank/import`,{headers,data:{title:"自制待核对题库",content:"1. 选择资源分配的基本单位。\nA. 进程\nB. 线程\nC. 调度\nD. 管道\n答案：A\n知识标签：进程"}});
 await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);return {course,note,headers};
}
async function navigate(page:Page,label:string){const toggle=page.getByRole("button",{name:"打开导航菜单",exact:true});if(await toggle.isVisible()){await toggle.click();await page.getByRole("dialog",{name:"导航菜单",exact:true}).getByRole("button",{name:label,exact:true}).click();}else await page.locator(".sidebar").getByRole("button",{name:label,exact:true}).click();await expect(page.locator(".content>.page")).toBeVisible();}
async function fit(page:Page,width:number){
 // Mode changes can replace nodes between visibility selection and measurement.
 // Re-query until settled; keep the same overflow and 44px target requirements.
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 if(width<768)await expect.poll(()=>page.locator(".content button:visible").evaluateAll(nodes=>nodes.filter(e=>e.getBoundingClientRect().height<43.5).map(e=>({text:e.textContent,height:e.getBoundingClientRect().height,connected:e.isConnected})))).toEqual([]);
}
for(const width of [1440,390])test(`所有分界面与子模式、共享记录和字体排布 ${width}px`,async({page,request})=>{
 test.setTimeout(150000);await page.setViewportSize({width,height:1000});await setup(page,request);await page.goto("/overview");let modelCalls=0;page.on("request",r=>{if(r.method()==="POST"&&/remote-queries|study-reports|\/draw/.test(r.url()))modelCalls++;});
 for(const [route,label] of [["materials","资料阅读"],["notes","知识笔记"],["ai","AI 学习"],["exam","真题与模拟卷"],["review","错题复习"],["topics","知识点学习"],["search","课程查找"],["backup","备份与恢复"],["api-connect","API接入"],["help","使用指南"],["feedback","使用反馈"]]){
  await navigate(page,label);await expect(page.locator(".app-shell")).toHaveAttribute("data-workspace",route);const before=page.url();const entry=page.getByRole("button",{name:"学习记录",exact:true});await expect(entry).toBeVisible();await entry.click();const dialog=page.getByRole("dialog",{name:"课程学习记录",exact:true});await expect(dialog.locator(".record-card")).toHaveCount(2);await page.keyboard.press("Escape");await expect(dialog).not.toBeVisible();await expect(entry).toBeFocused();expect(page.url()).toBe(before);
  if(route==="materials"){const toggle=page.getByRole("button",{name:/资料库与上传/});if(await toggle.isVisible())await toggle.click();await page.locator(".material-document").click();await expect(page.locator(".reading-paper")).toBeVisible();}
  if(route==="ai"){for(const name of ["资料原文检索","资料问答","学习报告"]){await page.getByRole("button",{name,exact:true}).click();await fit(page,width);}}
  if(route==="exam"){for(const name of ["考点、统计与蓝图","题库练习与作答","上传与校正题库"]){await page.getByRole("button",{name,exact:true}).click();await fit(page,width);}}
  if(route==="notes"){await page.locator(".note-manager .note-title-link").click();await expect(page.getByLabel("Markdown 正文",{exact:true})).toBeVisible();await page.getByRole("button",{name:"分屏预览",exact:true}).click();}
  if(route==="help")expect(new Set(await page.locator(".learning-guide>button").evaluateAll(nodes=>nodes.map(e=>getComputedStyle(e).backgroundColor))).size).toBe(1);
  expect(await page.locator(".app-shell").evaluate(e=>{const s=getComputedStyle(e);return s.getPropertyValue("--module-color").trim()===s.getPropertyValue("--accent").trim();})).toBe(true);
  await fit(page,width);expect(await page.locator(".topbar h1").evaluate(e=>parseFloat(getComputedStyle(e).fontSize))).toBeLessThanOrEqual(24);await page.screenshot({path:test.info().outputPath(`subpage-${route}-${width}.png`),fullPage:true});
 }
 expect(modelCalls).toBe(0);
});
test("首次断网记录入口保留编辑，重试与拒绝跳转保留草稿DOM",async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/notes?course=${s.course.id}`);await page.getByRole("button",{name:"新建笔记",exact:true}).click();const text=page.getByLabel("Markdown 正文",{exact:true});await text.fill("没有标题的未保存草稿，保留在原编辑器。");await text.evaluate(e=>e.setAttribute("data-record-draft","kept"));let writes=0;page.on("request",r=>{if(r.method()==="POST"&&/\/notes$|remote-queries/.test(r.url()))writes++;});
 await page.context().setOffline(true);await page.getByRole("button",{name:"学习记录",exact:true}).click();const dialog=page.getByRole("dialog",{name:"课程学习记录",exact:true});await expect(dialog.getByRole("alert")).toContainText("学习记录暂时无法读取");await expect(dialog.locator(".records-course")).toContainText(s.course.name);await page.context().setOffline(false);await dialog.getByRole("button",{name:"重新读取记录",exact:true}).click();await dialog.getByLabel("筛选学习记录类型",{exact:true}).selectOption("note");await expect(dialog.locator(".record-card")).toHaveCount(1);page.once("dialog",prompt=>prompt.dismiss());await dialog.locator(".record-card").click();await expect(dialog).not.toBeVisible();await expect(page).toHaveURL(new RegExp(`/notes\\?course=${s.course.id}$`));await expect(text).toHaveValue("没有标题的未保存草稿，保留在原编辑器。");await expect(text).toHaveAttribute("data-record-draft","kept");expect(writes).toBe(0);
});
