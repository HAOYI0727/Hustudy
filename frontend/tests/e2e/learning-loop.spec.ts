import {test,expect,type APIRequestContext,type Page} from "@playwright/test";
import {readFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
  const auth=await(await request.post(base+"/auth/register",{data:{username:"loop_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();
  const headers={Authorization:"Bearer "+auth.access_token};
  const course=await(await request.post(base+"/courses",{headers,data:{name:"完整学习闭环"}})).json();
  await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
  return {auth,headers,course};
}
async function imported(request:APIRequestContext,headers:Record<string,string>,course:string,name:string,buffer:Buffer){
  const response=await request.post(base+`/courses/${course}/documents`,{headers,multipart:{file:{name,mimeType:"text/markdown",buffer}}});expect(response.status()).toBe(202);
  const job=await response.json();
  await expect.poll(async()=>(await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
  return(await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
}
async function navigate(page:Page,label:string){
  const mobile=page.getByRole("button",{name:"打开导航菜单",exact:true});
  if(await mobile.isVisible()){await mobile.click();await page.getByRole("dialog",{name:"导航菜单",exact:true}).getByRole("button",{name:label,exact:true}).click();}
  else await page.locator(".sidebar").getByRole("button",{name:label,exact:true}).click();
}

test("课程摘要独立失败/重试，首页只读取有界元数据",async({page,request})=>{
  const s=await setup(page,request);const bodyRequests:string[]=[];
  page.on("request",r=>{if(/\/notes\?course_id=|\/courses\/[^/]+\/documents\?$/.test(r.url()))bodyRequests.push(r.url());});
  await page.route(`**/api/v1/courses/${s.course.id}/workspace/study`,route=>route.fulfill({status:503,json:{error:{code:"TEST_ONLY",message:"模拟摘要故障"}}}));
  await page.goto(`/overview?course=${s.course.id}`);
  await expect(page.getByRole("article",{name:"理清知识脉络"})).toContainText("暂时无法读取");
  await expect(page.getByRole("article",{name:"读懂课程资料"}).locator(".stage-count strong")).toHaveText("0");
  await expect(page.getByRole("article",{name:"写成自己的理解"}).locator(".stage-count strong")).toHaveText("0");
  await page.unroute(`**/api/v1/courses/${s.course.id}/workspace/study`);
  await page.getByRole("button",{name:"重试有来源结果",exact:true}).click();
  await expect(page.getByRole("article",{name:"理清知识脉络"}).locator(".stage-count strong")).toHaveText("0");
  expect(bodyRequests).toEqual([]);
});

test("切换课程时迟到摘要不覆盖当前课程",async({page,request})=>{
  const s=await setup(page,request);
  const second=await(await request.post(base+"/courses",{headers:s.headers,data:{name:"另一门课程"}})).json();
  await imported(request,s.headers,s.course.id,"one.md",Buffer.from("# 一\n自制文字甲"));
  await imported(request,s.headers,second.id,"two.md",Buffer.from("# 二\n自制文字乙"));
  await imported(request,s.headers,second.id,"three.md",Buffer.from("# 三\n自制文字丙"));
  let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
  await page.route(`**/api/v1/courses/${s.course.id}/workspace/materials`,async route=>{const result=await route.fetch();await gate;await route.fulfill({response:result});});
  await page.goto(`/overview?course=${s.course.id}`);
  await page.getByLabel("当前课程",{exact:true}).selectOption(second.id);
  await expect(page.getByRole("article",{name:"读懂课程资料"}).locator(".stage-count strong")).toHaveText("2");
  release();
  await expect(page.getByRole("article",{name:"读懂课程资料"}).locator(".stage-count strong")).toHaveText("2");
  await expect(page.getByRole("region",{name:"当前课程近期活动"})).not.toContainText("one");
});

test("阅读位置：显式继续、片段优先、刷新保留及清除",async({page,request})=>{
  const s=await setup(page,request);
  const buffer=Buffer.from(Array.from({length:4},(_,i)=>`# 章节${i+1}\n${"自制背景原文。".repeat(200)}\n章节${i+1}结尾。`).join("\n"));
  const version=await imported(request,s.headers,s.course.id,"long.md",buffer);
  const chunks=await(await request.get(base+`/versions/${version.id}/chunks`,{headers:s.headers})).json();
  await page.goto(`/materials?course=${s.course.id}&document=${version.document_id}&version=${version.id}`);
  await page.getByLabel("资料目录").getByRole("button",{name:"3. 章节3",exact:true}).click();
  await expect.poll(async()=>page.evaluate(()=>JSON.parse(localStorage.getItem(`hustudy-reading:v1:${encodeURIComponent(localStorage.getItem("hustudy_user")||"")}`)||"[]")[0]?.chunkId)).toBe(chunks[2].id);
  await page.goto(`/materials?course=${s.course.id}`);
  const resume=page.getByRole("region",{name:"继续上次阅读"});await expect(resume).toContainText("long");
  await resume.getByRole("button",{name:"继续上次阅读",exact:true}).click();
  await expect(page.locator("#chunk-"+chunks[2].id)).toBeInViewport();
  await page.goto(`/materials?course=${s.course.id}&document=${version.document_id}&version=${version.id}&chunk=${chunks[0].id}`);
  await expect(page.locator(".chunk-highlight")).toHaveAttribute("id","chunk-"+chunks[0].id);
  await page.getByRole("button",{name:"清除这条阅读位置",exact:true}).click();
  await expect(page.getByRole("region",{name:"继续上次阅读"})).toHaveCount(0);
});

for(const width of [1440,390])test(`完整学习闭环：资料/摘录/报告/笔记/练习恢复/错题回源 ${width}px`,async({page,request})=>{
  test.setTimeout(120000);await page.setViewportSize({width,height:1000});
  const renderErrors:string[]=[];page.on("console",message=>{if(message.type()==="error"&&message.text().includes("same key"))renderErrors.push(message.text());});
  const s=await setup(page,request);
  const buffer=await readFile(fileURLToPath(new URL("../../../fixtures/materialhub_demo.md",import.meta.url)));
  const version=await imported(request,s.headers,s.course.id,"materialhub_demo.md",buffer);
  let remoteSends=0;page.on("request",r=>{if(r.method()==="POST"&&/remote-queries.*(confirm|resume)|study-reports\/preview/.test(r.url()))remoteSends++;});
  await page.goto(`/materials?course=${s.course.id}&document=${version.document_id}&version=${version.id}`);
  await page.getByRole("button",{name:"摘录为新笔记",exact:true}).first().click();
  await expect(page.getByLabel("Markdown 正文")).toHaveValue(/阅读摘录/);
  await page.getByRole("button",{name:/^引用与关联/}).click();
  await expect(page.getByRole("region",{name:"资料来源",exact:true})).toContainText("materialhub_demo");
  await page.getByRole("button",{name:"回到原文 ↗",exact:true}).click();
  await page.getByRole("button",{name:"整理学习报告",exact:true}).click();
  await page.getByRole("button",{name:"运行固定报告演示（不发送）",exact:true}).click();
  await expect(page.getByRole("article",{name:"章节学习报告"})).toBeVisible();
  await page.getByRole("button",{name:"整理为可编辑笔记草稿",exact:true}).click();
  await page.getByRole("button",{name:"继续编辑笔记正文",exact:true}).click();
  await page.getByRole("button",{name:"确认保存为笔记草稿",exact:true}).click();
  await page.getByRole("button",{name:"打开刚保存的笔记",exact:false}).click();
  await expect(page.getByLabel("笔记标题")).toHaveValue("AI 学习草稿（待核实）");
  const bankText="# 自制练习\n1. 哪个是资源分配的基本单位？\nA. 进程\nB. 调度\nC. 管道\nD. 线程\n答案：A\n知识标签：进程";
  const bankVersion=await imported(request,s.headers,s.course.id,"bank-source.md",Buffer.from(bankText));
  const bank=await(await request.post(base+`/courses/${s.course.id}/question-bank/import`,{headers:s.headers,data:{title:"原文来源题库",version_id:bankVersion.id}})).json();
  expect((await request.post(base+`/past-papers/${bank.id}/confirm`,{headers:s.headers})).status()).toBe(200);
  await navigate(page,"课程总览");
  await expect(page.getByRole("article",{name:"写成自己的理解"}).locator(".stage-count strong")).toHaveText("2");
  await expect(page.getByRole("article",{name:"理清知识脉络"}).locator(".stage-count strong")).toHaveText("1");
  await page.getByRole("region",{name:"当前课程近期活动"}).locator("button").filter({hasText:"学习报告"}).first().click();
  await expect(page).toHaveURL(/result=.*mode=report/);await page.reload();
  await expect(page.getByRole("article",{name:"章节学习报告"})).toBeVisible();
  await navigate(page,"课程总览");
  await expect(page.getByRole("article",{name:"读懂课程资料"}).locator(".stage-count strong")).toHaveText("2");
  await expect(page.getByRole("article",{name:"写成自己的理解"}).locator(".stage-count strong")).toHaveText("2");
  await expect(page.getByRole("article",{name:"理清知识脉络"}).locator(".stage-count strong")).toHaveText("1");
  await expect(page.getByRole("article",{name:"在练习中巩固"}).locator(".stage-count strong")).toHaveText("1");
  await page.mouse.move(width-5,5);
  await page.screenshot({path:test.info().outputPath(`workspace-${width}.png`),fullPage:true});
  await page.getByRole("button",{name:"进入题库练习",exact:true}).click();
  await expect(page).toHaveURL(/tab=practice/);
  await page.getByLabel("题数",{exact:true}).fill("1");
  await page.getByRole("button",{name:"随机抽取题库练习",exact:true}).click();
  await page.getByRole("button",{name:"已核对题干，确认练习",exact:true}).click();
  await page.getByRole("button",{name:"开始作答",exact:true}).click();
  await page.locator(".option").filter({hasText:"调度"}).click();
  await expect(page.locator(".toast.success")).toContainText("答案已保存到服务器");
  await navigate(page,"课程总览");
  await page.getByRole("button",{name:/继续未完成作答/}).click();
  await expect(page).toHaveURL(/tab=practice&attempt=/);await page.reload();
  await expect(page.locator(".selected-option")).toContainText("调度");
  await page.getByRole("button",{name:"交卷并查看答案",exact:true}).click();
  await page.getByRole("button",{name:"去错题复盘 →",exact:true}).click();
  await page.getByRole("button",{name:"重做错题",exact:true}).click();
  const sources=page.getByRole("region",{name:"错题回源"});
  await expect(sources).toContainText("bank-source");
  await sources.getByRole("button",{name:/bank-source/}).click();
  await expect(page.locator(".reading-paper")).toContainText("资源分配的基本单位");
  expect(renderErrors).toEqual([]);expect(remoteSends).toBe(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
