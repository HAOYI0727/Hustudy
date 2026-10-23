import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {contrastRatio} from "../../src/features/appearance/preferences";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
 const username="colors_"+crypto.randomUUID().replaceAll("-","");
 const auth=await(await request.post(base+"/auth/register",{data:{username,password:"Test-password-2026"}})).json();
 const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"操作系统 · 概念与实践",description:"阅读课程原文，写成自己的理解，再通过练习回顾。",category:"专业必修",tags:["本学期","期末复习"]}})).json();
 await request.post(base+"/notes",{headers,data:{course_id:course.id,title:"进程与线程 · 我的理解",content:"# 概念之间的联系\n\n进程是资源分配的单位。线程共享进程资源。",tags:["进程"]}});
 const upload=await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:"进程与线程.md",mimeType:"text/markdown",buffer:Buffer.from("# 进程与线程\n进程拥有独立地址空间。\n# 内存管理\n虚拟内存为进程提供独立地址空间。")}}});expect(upload.status()).toBe(202);
 const job=await upload.json();await expect.poll(async()=>(await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
 await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
 return course;
}
const hex=(rgb:string)=>"#"+rgb.match(/[\d.]+/g)!.slice(0,3).map(v=>Math.round(Number(v)).toString(16).padStart(2,"0")).join("");
test("四模块统一主色与卡片层次，实际跳转延续同一主题",async({page,request})=>{
 await page.setViewportSize({width:1440,height:1000});const course=await setup(page,request);await page.goto(`/overview?course=${course.id}`);
 await expect(page.locator(".learning-stage")).toHaveCount(4);
 const backgrounds=await page.locator(".learning-stage").evaluateAll(nodes=>nodes.map(e=>getComputedStyle(e).backgroundImage));expect(new Set(backgrounds).size).toBe(1);expect(backgrounds.every(v=>v.includes("gradient"))).toBe(true);
 const colors=await page.locator(".stage-action").evaluateAll(nodes=>nodes.map(e=>({ink:getComputedStyle(e).color,bg:getComputedStyle(e).backgroundColor})));
 expect(new Set(colors.map(c=>c.bg)).size).toBe(1);const accent=await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--accent").trim());for(const c of colors){expect(hex(c.bg)).toBe(accent);expect(contrastRatio(hex(c.ink),hex(c.bg))).toBeGreaterThanOrEqual(4.5);}
 await expect(page.locator(".workspace-activity-list>button")).toHaveCount(2);
 expect(new Set(await page.locator(".activity-icon").evaluateAll(nodes=>nodes.map(e=>getComputedStyle(e).backgroundColor))).size).toBe(1);
 const tint=await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--material-tint").trim());expect(hex(await page.locator(".evidence-tip").evaluate(e=>getComputedStyle(e).backgroundColor))).toBe(tint);
 expect(hex(await page.locator(".workspace-activity-list .status-succeeded").evaluate(e=>getComputedStyle(e).color))).not.toBe(accent);
 await page.screenshot({path:test.info().outputPath("color-dashboard.png"),fullPage:true});
 for(const [stage,route] of [["materials","materials"],["study","ai"],["notes","notes"],["practice","exam"]]){
  await page.locator(`.stage-${stage} .stage-action`).click();await expect(page).toHaveURL(new RegExp(`/${route}\\?`));await expect(page.locator(".app-shell")).toHaveAttribute("data-workspace",route);
  const heading=page.locator(route==="notes"?".notes-workspace-heading":".page-title");await expect(heading).toBeVisible();expect(await heading.evaluate(e=>getComputedStyle(e).backgroundImage)).toContain("gradient");
  expect(await page.locator(".app-shell").evaluate(e=>getComputedStyle(e).getPropertyValue("--module-color").trim())).toBe(accent);
  await page.screenshot({path:test.info().outputPath(`color-${route}.png`),fullPage:true});await page.goto(`/overview?course=${course.id}`);
 }
});
test("主题和基调切换联动所有模块，保留笔记正文节点与草稿",async({page,request})=>{
 const course=await setup(page,request);await page.goto(`/notes?course=${course.id}`);await page.getByRole("button",{name:"新建笔记",exact:true}).click();
 const text=page.getByLabel("Markdown 正文",{exact:true});await text.fill("彩色界面下仍保留当前草稿。");await text.evaluate(e=>e.setAttribute("data-color-sentinel","kept"));
 const original=await page.locator(".notes-workspace-heading").evaluate(e=>getComputedStyle(e).getPropertyValue("--notes-color").trim());
 await page.getByRole("button",{name:"外观与布局",exact:true}).click();const dialog=page.getByRole("dialog",{name:"外观与布局",exact:true});
 await dialog.getByRole("button",{name:"远山蓝",exact:true}).click();await dialog.getByLabel("暖纸",{exact:false}).check();await dialog.getByRole("button",{name:"完成设置",exact:true}).click();
 await expect(text).toHaveAttribute("data-color-sentinel","kept");await expect(text).toHaveValue("彩色界面下仍保留当前草稿。");
 const palette=await page.evaluate(()=>{const s=getComputedStyle(document.documentElement);return ["accent","material-color","ai-color","notes-color","exam-color","review-color"].map(key=>s.getPropertyValue("--"+key).trim());});expect(new Set(palette).size).toBe(1);expect(palette[0]).not.toBe(original);
 await page.screenshot({path:test.info().outputPath("color-paper-draft.png"),fullPage:true});
});
test("Times英文/黑体界面/宋体阅读/楷体提示，保留阅读字号和代码数学字体",async({page,request})=>{
 const course=await setup(page,request);await page.goto(`/overview?course=${course.id}`);await expect(page.locator(".learning-stage")).toHaveCount(4);await expect(page.locator(".dashboard-metrics")).not.toContainText("…");
 expect(await page.locator(".dashboard-hero h2").evaluate(e=>getComputedStyle(e).fontFamily)).toMatch(/^"?Times New Roman/);expect(await page.locator(".stage-action").first().evaluate(e=>getComputedStyle(e).fontFamily)).toContain("Heiti SC");
 expect(await page.locator(".dashboard-hero p").evaluate(e=>getComputedStyle(e).fontFamily)).toContain("Songti SC");expect(await page.locator(".evidence-tip p").evaluate(e=>getComputedStyle(e).fontFamily)).toContain("Kaiti SC");
 expect(await page.locator(".dashboard-hero h2").evaluate(e=>parseFloat(getComputedStyle(e).fontSize))).toBeLessThanOrEqual(31);await page.screenshot({path:test.info().outputPath("type-dashboard.png"),fullPage:true});
 await page.goto(`/materials?course=${course.id}`);await page.locator(".material-document").click();await expect(page.locator(".reading-paper")).toBeVisible();await page.getByRole("button",{name:"增大阅读字号",exact:true}).click();expect(await page.locator(".reading-paper").evaluate(e=>getComputedStyle(e).fontSize)).toBe("17px");expect(await page.locator(".reading-paper .chunk>p").first().evaluate(e=>getComputedStyle(e).fontFamily)).toContain("Songti SC");
 await page.goto(`/notes?course=${course.id}`);await page.getByRole("button",{name:"新建笔记",exact:true}).click();const text=page.getByLabel("Markdown 正文",{exact:true});
 const content="English and 中文段落。\n\n```text\nconst sample = 1;\n```\n\n$x^2 + y^2$";await text.fill(content);expect(await text.evaluate(e=>getComputedStyle(e).fontFamily)).toMatch(/Consolas|monospace/);await page.getByRole("button",{name:"分屏预览",exact:true}).click();await expect(page.locator(".markdown-preview .katex")).toBeVisible();
 expect(await page.locator(".markdown-preview p").first().evaluate(e=>getComputedStyle(e).fontFamily)).toContain("Songti SC");expect(await page.locator(".markdown-preview pre code").evaluate(e=>getComputedStyle(e).fontFamily)).toMatch(/mono|Consolas|Courier/i);expect(await page.locator(".markdown-preview .katex").evaluate(e=>getComputedStyle(e).fontFamily)).toContain("KaTeX");await expect(text).toHaveValue(content);await page.screenshot({path:test.info().outputPath("type-note-math.png"),fullPage:true});
});
test.describe("彩色触控工作台",()=>{
 test.use({hasTouch:true,isMobile:true});
 test("320px卡片/模式按钮可触达，820px侧栏选项文字有空间",async({page,request})=>{
  const course=await setup(page,request);await page.setViewportSize({width:320,height:900});await page.goto(`/overview?course=${course.id}`);await expect(page.locator(".learning-stage")).toHaveCount(4);await expect(page.locator(".dashboard-metrics")).not.toContainText("…");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);for(const button of await page.locator(".stage-action").all())expect(await button.evaluate(e=>e.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await page.screenshot({path:test.info().outputPath("color-mobile.png"),fullPage:true});await page.goto(`/ai?course=${course.id}`);await expect(page.locator(".ai-mode-tabs>button")).toHaveCount(3);for(const button of await page.locator(".ai-mode-tabs>button").all())expect(await button.evaluate(e=>e.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await page.setViewportSize({width:820,height:1180});await page.goto(`/materials?course=${course.id}`);const field=page.getByLabel("按处理状态筛选",{exact:true});await expect(field).toBeVisible();expect(await field.evaluate(e=>e.getBoundingClientRect().width)).toBeGreaterThanOrEqual(132);
  await field.selectOption("ready");await expect(page.locator(".material-document")).toHaveCount(1);await page.screenshot({path:test.info().outputPath("color-tablet.png"),fullPage:true});
 });
});
