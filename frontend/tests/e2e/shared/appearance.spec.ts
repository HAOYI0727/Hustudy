import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {appearanceKey,appearanceTokens,defaultAppearance,accentPresets,contrastRatio} from "../../../src/features/appearance/preferences";
const base="http://127.0.0.1:8056/api/v1";
const rgb=(hex:string)=>`rgb(${[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)).join(", ")})`;
async function setup(page:Page,request:APIRequestContext){
 const username="visual_"+crypto.randomUUID().replaceAll("-","");const auth=await(await request.post(base+"/auth/register",{data:{username,password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
 const course=await(await request.post(base+"/courses",{headers,data:{name:"操作系统 · 学习空间",description:"从进程、线程到内存管理，把每一个概念写成自己的理解。",category:"专业必修",tags:["本学期","重点课程"]}})).json();
 const note=await(await request.post(base+"/notes",{headers,data:{course_id:course.id,title:"进程与线程 · 我的理解",content:"## 核心概念\n进程分配资源，线程参与调度。\n\n## 继续思考\n用一个具体例子，解释它们如何协作。",tags:["操作系统"]}})).json();
 const topic=await(await request.post(base+`/courses/${course.id}/topics`,{headers,data:{name:"进程与线程"}})).json();
 const uploaded=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:"第一章-进程与线程.md",mimeType:"text/markdown",buffer:Buffer.from("# 进程与线程\n进程拥有地址空间。线程共享进程资源。\n# 内存管理\n虚拟内存提供独立地址空间。")}}})).json();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${uploaded.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");const version=await(await request.get(base+`/versions/${uploaded.resource_id}`,{headers})).json();
 await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
 return {headers,course,note,topic,version,auth};
}
async function openAppearance(page:Page){await page.getByRole("button",{name:"外观与布局",exact:true}).click();const panel=page.getByRole("dialog",{name:"外观与布局",exact:true});await expect(panel).toBeVisible();return panel;}
test("六预设即时联动真实导航/按钮，刷新和四模块保持外观",async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/overview?course=${s.course.id}`);let modelWrites=0;page.on("request",r=>{if(r.method()==="POST"&&/remote-queries|study-reports/.test(r.url()))modelWrites++;});
 for(const preset of accentPresets){const panel=await openAppearance(page);await panel.getByRole("button",{name:preset.name,exact:true}).click();await expect(panel.getByRole("button",{name:preset.name,exact:true})).toHaveAttribute("aria-pressed","true");const tokens=appearanceTokens({...defaultAppearance,accent:preset.id});
  await expect.poll(()=>page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--accent").trim())).toBe(tokens["--accent"]);
  const roles=await page.evaluate(()=>{const s=getComputedStyle(document.documentElement);return ["material","ai","notes","exam","review"].map(name=>s.getPropertyValue(`--${name}-color`).trim());});expect(roles).toEqual(Array(5).fill(tokens["--accent"]));
  await expect.poll(()=>page.locator(".sidebar .nav-item.active").evaluate(e=>getComputedStyle(e).color)).toBe(rgb(tokens["--nav-selected-ink"]));
  expect(await page.locator(".sidebar .nav-item.active>span:not(.navigation-active-dot)").evaluate(e=>getComputedStyle(e).textAlign)).toBe("left");
  await panel.getByRole("button",{name:"完成设置",exact:true}).click();await expect(page.getByRole("button",{name:"外观与布局",exact:true})).toBeFocused();
 }
 const saved=await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),appearanceKey);expect(saved.value.accent).toBe("amber");await page.reload();
 for(const destination of ["materials","notes","ai","exam","topics","search"]){await page.goto(`/${destination}?course=${s.course.id}`);await expect(page.getByRole("button",{name:"外观与布局",exact:true})).toBeVisible();await expect.poll(()=>page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--accent").trim())).toBe(appearanceTokens({...defaultAppearance,accent:"amber"})["--accent"]);await expect.poll(()=>page.locator(".sidebar .nav-item.active").evaluate(e=>getComputedStyle(e).color)).toBe(rgb(appearanceTokens({...defaultAppearance,accent:"amber"})["--accent-ink"]));}
 expect(modelWrites).toBe(0);
});
test.describe("触控设备",()=>{
 test.use({hasTouch:true});
 test("紧凑模式仍保留触控目标与自选阅读字号",async({page,request})=>{
  await page.setViewportSize({width:1280,height:960});const s=await setup(page,request);await page.goto(`/materials?course=${s.course.id}&document=${s.version.document_id}&version=${s.version.id}`);
  await page.getByRole("button",{name:"增大阅读字号",exact:true}).click();const paper=page.locator(".reading-paper");await expect.poll(()=>paper.evaluate(e=>getComputedStyle(e).fontSize)).toBe("17px");await paper.evaluate(e=>e.setAttribute("data-reader-sentinel","kept"));
  const panel=await openAppearance(page);await panel.getByLabel("紧凑排列",{exact:false}).check();await panel.getByLabel("暖纸",{exact:false}).check();await panel.getByLabel("深色导航",{exact:false}).check();await panel.getByRole("button",{name:"完成设置",exact:true}).click();
  expect(await page.locator(".sidebar .nav-item").first().evaluate(e=>e.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await expect(paper).toHaveAttribute("data-reader-sentinel","kept");await expect.poll(()=>paper.evaluate(e=>getComputedStyle(e).fontSize)).toBe("17px");
  await page.setViewportSize({width:390,height:844});expect(await page.getByRole("button",{name:"外观与布局",exact:true}).evaluate(e=>e.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:test.info().outputPath("compact-touch.png"),fullPage:true});
 });
});
test("自定极浅色自动保留可读按钮，非法颜色不应用，默认可恢复",async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/overview?course=${s.course.id}`);const panel=await openAppearance(page);
 await panel.getByLabel("自定主题色值",{exact:true}).fill("#ffffff");await panel.getByRole("button",{name:"应用自定色",exact:true}).click();
 const color=await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--accent").trim());expect(contrastRatio(color,"#ffffff")).toBeGreaterThanOrEqual(4.5);
 await expect.poll(()=>panel.getByRole("button",{name:"完成设置",exact:true}).evaluate(e=>getComputedStyle(e).backgroundColor)).toBe(rgb(color));
 await panel.getByLabel("自定主题色值",{exact:true}).fill("red");await panel.getByRole("button",{name:"应用自定色",exact:true}).click();await expect(panel.getByRole("alert")).toContainText("完整的颜色值");
 expect(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--accent").trim())).toBe(color);
 await panel.getByRole("button",{name:"恢复默认外观",exact:true}).click();await expect(panel.getByRole("button",{name:"鸢尾紫",exact:true})).toHaveAttribute("aria-pressed","true");
});
test("页面基调、深浅导航、密度/宽度改变真实样式，保留编辑节点和草稿",async({page,request})=>{
 await page.setViewportSize({width:1920,height:1080});const s=await setup(page,request);await page.route(`**/api/v1/notes/${s.note.id}`,route=>route.request().method()==="PATCH"?route.fulfill({status:503,json:{error:{message:"隔离草稿保护"}}}):route.continue());
 await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);const editor=page.getByLabel("Markdown 正文",{exact:true});await editor.fill("切换主题时这段理解必须保留。 $x^2$");await editor.evaluate(e=>e.setAttribute("data-editor-sentinel","kept"));
 const panel=await openAppearance(page);await panel.getByLabel("暖纸",{exact:false}).check();await panel.getByLabel("深色导航",{exact:false}).check();await panel.getByLabel("紧凑排列",{exact:false}).check();await panel.getByLabel("聚焦布局",{exact:false}).check();
 await expect.poll(()=>page.evaluate(()=>document.documentElement.dataset.surface)).toBe("paper");await expect.poll(()=>page.locator(".sidebar").evaluate(e=>getComputedStyle(e).backgroundColor)).toBe("rgb(30, 41, 59)");
 const prefs={...defaultAppearance,surface:"paper" as const,navigation:"dark" as const,density:"compact" as const,width:"focused" as const};const tokens=appearanceTokens(prefs);
 await expect.poll(()=>page.locator(".notes-workspace .panel").first().evaluate(e=>getComputedStyle(e).backgroundColor)).toBe(rgb(tokens["--surface"]));
 await expect.poll(()=>page.locator(".content>.page").evaluate(e=>Math.round(e.getBoundingClientRect().width))).toBeLessThanOrEqual(1240);
 await panel.getByRole("button",{name:"完成设置",exact:true}).click();await expect(editor).toHaveValue("切换主题时这段理解必须保留。 $x^2$");await expect(editor).toHaveAttribute("data-editor-sentinel","kept");
});
test("存储写失败保持本次样式并提示未保存，显式重试与窗口同步",async({page,request})=>{
 const s=await setup(page,request);await page.goto(`/overview?course=${s.course.id}`);const panel=await openAppearance(page);
 await page.evaluate(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==="hustudy-appearance:v1")throw new Error("isolated quota");return original.call(this,k,v);};});
 await panel.getByRole("button",{name:"森林绿",exact:true}).click();await expect(panel.getByRole("alert")).toContainText("未能保存");await expect(panel.getByRole("button",{name:"森林绿",exact:true})).toHaveAttribute("aria-pressed","true");
 await page.reload();const fresh=await openAppearance(page);await fresh.getByRole("button",{name:"远山蓝",exact:true}).click();await expect(fresh.getByRole("alert")).toHaveCount(0);
 const other=await page.context().newPage();await other.goto(`/overview?course=${s.course.id}`);const second=await openAppearance(other);await second.getByRole("button",{name:"莓果粉",exact:true}).click();await expect(fresh.getByRole("button",{name:"莓果粉",exact:true})).toHaveAttribute("aria-pressed","true");await other.close();
});
test("未知/恶意本机偏好安全回退，手机也可恢复默认",async({page,request})=>{
 const s=await setup(page,request);await page.addInitScript(key=>localStorage.setItem(key,JSON.stringify({version:1,value:{accent:"url(https://unsafe)"}})),appearanceKey);await page.setViewportSize({width:320,height:820});await page.goto(`/overview?course=${s.course.id}`);const panel=await openAppearance(page);
 await expect(panel.getByRole("alert")).toContainText("默认样式");await panel.getByRole("button",{name:"恢复默认外观",exact:true}).click();await expect(panel.getByRole("alert")).toHaveCount(0);expect((await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),appearanceKey)).value).toEqual(defaultAppearance);
 await page.keyboard.press("Escape");await expect(panel).not.toBeVisible();await expect(page.getByRole("button",{name:"外观与布局",exact:true})).toBeFocused();
});
for(const width of [320,390,820,1440])test(`主题面板与工作台布局/焦点 ${width}px`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});const s=await setup(page,request);await page.goto(`/overview?course=${s.course.id}`);await expect(page.getByRole("region",{name:"当前课程学习工作台"})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:test.info().outputPath(`workspace-${width}.png`),fullPage:true});
  const panel=await openAppearance(page);await panel.getByRole("button",{name:"松石青",exact:true}).click();await panel.getByLabel("柔雾",{exact:false}).check();
 expect(await panel.evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.keyboard.press("Tab");expect(await panel.evaluate(e=>e.contains(document.activeElement))).toBe(true);await panel.evaluate(e=>e.scrollTop=0);await page.screenshot({path:test.info().outputPath(`appearance-${width}.png`)});
 await page.keyboard.press("Escape");await expect(panel).not.toBeVisible();
  await page.goto(`/materials?course=${s.course.id}&document=${s.version.document_id}&version=${s.version.id}`);await expect(page.locator(".reading-paper")).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  const tokens=appearanceTokens({...defaultAppearance,accent:"teal",surface:"mist"});
  const selected=page.locator(".material-document.selected-document");
  await expect.poll(()=>selected.evaluate(e=>getComputedStyle(e).backgroundImage)).toContain("linear-gradient");
  const background=await selected.evaluate(e=>getComputedStyle(e).backgroundImage);
  expect(background).toContain(rgb(tokens["--material-wash"]));
  expect(background).toContain(rgb(tokens["--material-tint"]));
  await expect.poll(()=>selected.evaluate(e=>getComputedStyle(e).borderColor)).toBe(rgb(tokens["--material-color"]));
  await expect.poll(()=>page.locator(".reading-paper .locator").first().evaluate(e=>getComputedStyle(e).color)).toBe(rgb(tokens["--accent-ink"]));
  await page.screenshot({path:test.info().outputPath(`materials-${width}.png`),fullPage:true});
});
