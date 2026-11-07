import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {readFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
  const auth=await(await request.post(base+"/auth/register",{data:{username:"manual_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();
  await page.addInitScript(auth=>{if(window===window.top){localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);}},auth);return{auth,headers:{Authorization:"Bearer "+auth.access_token}};
}
for(const width of [390,1440])test(`完整手册：按需读取/25章/查找/键盘/真实下载 ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:1000});const s=await setup(page,request);let reads=0;const writes:string[]=[];
  page.on("request",r=>{if(r.resourceType()==="fetch"&&/\/user(?:-[\w-]+)?\.md(?:\?|$)/.test(r.url()))reads++;if(r.url().includes("/api/v1/")&&!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(r.url());});
  await page.goto("/help");const entry=page.getByRole("region",{name:"完整手册与闭环示例",exact:true}),open=entry.getByRole("button",{name:"阅读完整使用手册",exact:true});await expect(open).toBeVisible();expect(reads).toBe(0);await open.click();
  const dialog=page.getByRole("dialog",{name:"Hustudy完整使用手册",exact:true}),nav=dialog.getByRole("navigation",{name:"选择手册章节",exact:true});await expect(nav.getByRole("button")).toHaveCount(25);
  await nav.getByRole("button",{name:/^7\. 当前PPT/}).click();const article=dialog.getByRole("article",{name:"手册章节正文",exact:true});await expect(article).toBeFocused();await expect(article).toContainText("第1–3页");await expect(article).toContainText("跟随当前阅读页");
  const query=dialog.getByLabel("查找手册章节",{exact:true});await query.fill("没有这一个章节ABC999");await expect(nav.getByRole("button")).toHaveCount(0);await expect(article).toContainText("当前PPT专用AI阅读助手");await dialog.getByRole("button",{name:"清除手册查找",exact:true}).click();await expect(nav.getByRole("button")).toHaveCount(25);await nav.getByRole("button",{name:/^3\. 用示例/}).click();await expect(article).toContainText("传输层基础");expect(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth+2)).toBe(true);await page.screenshot({path:test.info().outputPath(`manual-${width}.png`)});await page.keyboard.press("Escape");await expect(dialog).not.toBeVisible();await expect(open).toBeFocused();expect(reads).toBe(1);
  for(const [label,file] of [["下载完整手册","user.md"],["下载传输层资料示例","fixtures/learning_loop_material.md"],["下载配套题库示例","fixtures/learning_loop_questions.md"],["下载固定报告演示资料","fixtures/materialhub_demo.md"]]){
    const [download]=await Promise.all([page.waitForEvent("download"),entry.getByRole("link",{name:label,exact:true}).click()]);const path=await download.path();expect(path).toBeTruthy();expect(await readFile(path!)).toEqual(await readFile(fileURLToPath(new URL("../../../../"+file,import.meta.url))));
  }
  expect(writes).toEqual([]);expect(await(await request.get(base+"/courses",{headers:s.headers})).json()).toEqual([]);
});
test("手册首次离线/格式失败可重试，关闭拒绝迟到且不加载外部图片",async({page,request})=>{
  await setup(page,request);await page.goto("/help");const open=page.getByRole("button",{name:"阅读完整使用手册",exact:true}),dialog=page.getByRole("dialog",{name:"Hustudy完整使用手册",exact:true});await expect(open).toBeVisible();await page.context().setOffline(true);await open.click();await expect(dialog.getByRole("alert")).toContainText("网络");await page.context().setOffline(false);await dialog.getByRole("button",{name:"重试读取手册",exact:true}).click();await expect(dialog.getByRole("navigation",{name:"选择手册章节"}).getByRole("button")).toHaveCount(25);await page.keyboard.press("Escape");
  let hold=false,release!:()=>void;const gate=new Promise<void>(done=>release=done);await page.route("**/user.md*",async route=>{if(route.request().resourceType()!=="fetch")return route.continue();if(hold){await gate;try{await route.fulfill({contentType:"text/markdown",body:"# Hustudy\n## 迟到旧手册\nOld"});}catch{}return;}return route.fulfill({contentType:"text/html",body:"<html>missing</html>"});});
  await open.click();await expect(dialog.getByRole("alert")).toContainText("格式不正确");await page.keyboard.press("Escape");hold=true;await open.click();await expect(dialog.getByRole("status")).toContainText("正在读取");await page.keyboard.press("Escape");release();await expect(dialog).not.toBeVisible();await expect(open).toBeFocused();await page.unroute("**/user.md*");await open.click();await expect(dialog.getByRole("navigation",{name:"选择手册章节"}).getByRole("button")).toHaveCount(25);await expect(dialog).not.toContainText("迟到旧手册");await page.keyboard.press("Escape");
  let external=0;await page.route("https://manual-images.invalid/**",route=>{external++;return route.abort();});await page.route("**/user.md*",route=>route.request().resourceType()!=="fetch"?route.continue():route.fulfill({contentType:"text/markdown",body:'# Hustudy\n## 安全显示\n<script>window.manualInjected=true</script>\n![test](https://manual-images.invalid/image.png)\n[外部链接](https://manual-images.invalid/open)'}));await open.click();await expect(dialog.getByRole("article")).toContainText("图片请在原文中核对");await expect(dialog.locator("img,a[href],script")).toHaveCount(0);expect(await page.evaluate(()=>(window as any).manualInjected)).toBeUndefined();expect(external).toBe(0);
});


test("使用指南说明全部默认收起，支持逐项展开，重新进入重置",async({page,request})=>{
 await setup(page,request);await page.goto('/help');
 const section=page.locator('.help-columns section').filter({has:page.getByRole('heading',{name:'使用前，了解这些',exact:true})});
 // Standalone topic-learning guidance was removed in main@70096a8.
 const items=section.locator('details');await expect(items).toHaveCount(8);await expect(section.locator('details[open]')).toHaveCount(0);
 for(let i=0;i<await items.count();i++){const item=items.nth(i);await item.locator('summary').click();await expect(item).toHaveAttribute('open','');await item.locator('summary').click();await expect(item).not.toHaveAttribute('open','');}
 await section.getByText('演示模型能做什么？',{exact:true}).click();await expect(section.locator('details[open]')).toHaveCount(1);
 await page.reload();await expect(section.locator('details[open]')).toHaveCount(0);
});
