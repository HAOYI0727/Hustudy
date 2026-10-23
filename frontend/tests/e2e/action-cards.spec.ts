import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
import {readFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext){
  const auth=await(await request.post(base+"/auth/register",{data:{username:"cards_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};
  const course=await(await request.post(base+"/courses",{headers,data:{name:"操作系统 · 学习与实践",description:"从课程原文出发，把知识连接到笔记与练习。"}})).json();
  const note=await(await request.post(base+"/notes",{headers,data:{course_id:course.id,title:"进程与线程 · 理解笔记",content:"# 我的理解\n进程拥有独立的地址空间。",tags:["进程"]}})).json();
  const content=await readFile(fileURLToPath(new URL("../../../fixtures/materialhub_demo.md",import.meta.url)));
  const upload=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:"materialhub_demo.md",mimeType:"text/markdown",buffer:content}}})).json();
  await expect.poll(async()=>(await(await request.get(base+`/versions/${upload.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
  const version=await(await request.get(base+`/versions/${upload.resource_id}`,{headers})).json();
  await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
  return {headers,course,note,version};
}
async function fit(page:Page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);}

for(const width of [1440,390])test(`四阶段快捷卡片打开原版本/笔记/报告/作答，零额外创建 ${width}px`,async({page,request})=>{
  test.setTimeout(90000);await page.setViewportSize({width,height:1000});const s=await setup(page,request);
  await page.goto(`/materials?course=${s.course.id}&document=${s.version.document_id}&version=${s.version.id}`);
  await page.getByRole("button",{name:"整理学习报告",exact:true}).click();await page.getByRole("button",{name:"运行固定报告演示（不发送）",exact:true}).click();await expect(page.getByRole("article",{name:"章节学习报告"})).toBeVisible();
  const report=(await(await request.get(base+`/courses/${s.course.id}/workspace/study`,{headers:s.headers})).json()).recent[0];
  const bank=await(await request.post(base+`/courses/${s.course.id}/question-bank/import`,{headers:s.headers,data:{title:"卡片练习",content:"1. 选择正确项。\nA. 正确\nB. 错误一\nC. 错误二\nD. 错误三\n答案：A"}})).json();expect((await request.post(base+`/past-papers/${bank.id}/confirm`,{headers:s.headers})).status()).toBe(200);
  const paper=await(await request.post(base+`/courses/${s.course.id}/question-bank/draw`,{headers:s.headers,data:{request_id:crypto.randomUUID(),topic_ids:[],count:1,duration_minutes:30}})).json();expect((await request.post(base+`/exam-papers/${paper.id}/review`,{headers:s.headers})).status()).toBe(200);
  const attempt=await(await request.post(base+`/exam-papers/${paper.id}/attempts`,{headers:s.headers})).json();const saved="ABCD"[paper.questions[0].options.indexOf("错误一")];await request.put(base+`/attempts/${attempt.id}/answers/${paper.questions[0].id}`,{headers:s.headers,data:{answer:saved}});
  const writes:string[]=[];page.on("request",r=>{if(["POST","PUT","PATCH","DELETE"].includes(r.method()))writes.push(r.method()+" "+new URL(r.url()).pathname);});
  for(const [stage,pattern] of [["materials",new RegExp(`document=${s.version.document_id}&version=${s.version.id}`)],["notes",new RegExp(`note=${s.note.id}`)],["study",new RegExp(`result=${report.id}`)],["practice",new RegExp(`attempt=${attempt.id}`)]] as const){
    await page.goto(`/overview?course=${s.course.id}`);await expect(page.locator(".stage-continue")).toHaveCount(4);await fit(page);
    if(stage==="materials")await page.screenshot({path:test.info().outputPath(`action-overview-${width}.png`),fullPage:true});
    await page.locator(`.stage-${stage} .stage-continue`).click();await expect(page).toHaveURL(pattern);
    if(stage==="materials")await expect(page.locator(".reading-paper")).toBeVisible();
    if(stage==="notes")await expect(page.getByLabel("Markdown 正文",{exact:true})).toHaveValue(s.note.content);
    if(stage==="study")await expect(page.getByRole("article",{name:"章节学习报告"})).toBeVisible();
    if(stage==="practice")await expect(page.locator(".selected-option")).toContainText("错误一");
  }
  expect(writes).toEqual([]);
  await request.post(base+`/attempts/${attempt.id}/submit`,{headers:s.headers});await page.goto(`/overview?course=${s.course.id}`);
  await expect(page.locator(".stage-practice .stage-start")).toContainText("暂无进行中的作答");await expect(page.locator(".stage-practice .stage-continue")).toHaveCount(0);await expect(page.locator(".stage-practice .stage-action")).toBeEnabled();
});

for(const width of [1440,390])test(`资料详细/精简保持三状态、选择、阅读器和未保存整理 ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:1000});const s=await setup(page,request);
  // Only presentation is stubbed: a successful parse does not imply index/preview success.
  await page.route(`**/courses/${s.course.id}/documents/page?**`,async route=>{const response=await route.fetch();const data=await response.json();data.items=data.items.map((doc:object)=>({...doc,parse_status:"SUCCEEDED",index_status:"RUNNING",preview_status:"FAILED"}));await route.fulfill({response,json:data});});
  await page.goto(`/materials?course=${s.course.id}&document=${s.version.document_id}&version=${s.version.id}`);await expect(page.locator(".reading-paper")).toBeVisible();
  if(width<761)await page.getByRole("button",{name:/资料库与上传/}).click();
  const card=page.locator(".material-cover-card");await expect(card).toHaveCount(1);await expect(card).toHaveAttribute("aria-pressed","true");
  await expect(card.getByLabel("解析状态",{exact:true})).toContainText("已完成");await expect(card.getByLabel("索引状态",{exact:true})).toContainText("处理中");await expect(card.getByLabel("预览状态",{exact:true})).toContainText("失败");
  await page.getByRole("button",{name:"批量整理分类与标签",exact:true}).click();const check=page.getByRole("checkbox",{name:/选择资料：/});await check.check();
  await page.getByRole("button",{name:"整理",exact:true}).click();const name=page.locator(".material-metadata").getByLabel("资料名称",{exact:true});await name.fill("保留在编辑中的资料名称");
  await page.locator(".reading-paper").evaluate(e=>e.setAttribute("data-card-sentinel","kept"));
  let calls=0;page.on("request",r=>{if(r.url().includes(`/courses/${s.course.id}/documents/page?`))calls++;});
  const group=page.getByRole("group",{name:"资料卡片显示方式",exact:true});await group.getByRole("button",{name:"精简",exact:true}).click();await expect(card).toHaveClass(/is-compact/);await expect(check).toBeChecked();await expect(name).toHaveValue("保留在编辑中的资料名称");await expect(page.locator(".reading-paper")).toHaveAttribute("data-card-sentinel","kept");
  await expect(card.getByLabel("预览状态",{exact:true})).toContainText("失败");await expect(group.getByRole("button",{name:"精简",exact:true})).toHaveAttribute("aria-pressed","true");
  await group.getByRole("button",{name:"详细",exact:true}).focus();await page.keyboard.press("Enter");await expect(card).toHaveClass(/is-detailed/);await expect(check).toBeChecked();expect(calls).toBe(0);await fit(page);
  if(width<761)expect(await group.getByRole("button",{name:"精简",exact:true}).evaluate(e=>e.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await page.screenshot({path:test.info().outputPath(`material-cards-${width}.png`),fullPage:true});
});

test("阶段空态与独立错误不显示可继续旧对象，重试恢复",async({page,request})=>{
  const s=await setup(page,request);let broken=true;
  await page.route(`**/courses/${s.course.id}/workspace/notes`,route=>broken?route.fulfill({status:503,json:{error:{message:"隔离摘要失败"}}}):route.continue());
  await page.goto(`/overview?course=${s.course.id}`);const stage=page.locator(".stage-notes");await expect(stage).toContainText("暂时无法读取");await expect(stage.locator(".stage-continue")).toHaveCount(0);
  await expect(page.locator(".stage-study .stage-start")).toContainText("选定资料");await expect(page.locator(".stage-materials .stage-continue")).toBeVisible();broken=false;await stage.getByRole("button",{name:"重试已保存笔记",exact:true}).click();await expect(stage.locator(".stage-continue")).toContainText(s.note.title);
});
