import {test,expect,type APIRequestContext,type Page} from "@playwright/test";
const base="http://127.0.0.1:8056/api/v1";
async function setup(page:Page,request:APIRequestContext,count=1){
  const username="organize_"+crypto.randomUUID().replaceAll("-","");
  const auth=await(await request.post(base+"/auth/register",{data:{username,password:"Test-password-2026"}})).json();
  const headers={Authorization:"Bearer "+auth.access_token};
  const course=await(await request.post(base+"/courses",{headers,data:{name:"资料整理验收"}})).json();
  for(let i=0;i<count;i++)expect((await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:`课件${String(i).padStart(2,"0")}.md`,mimeType:"text/markdown",buffer:Buffer.from(`# 原文${i}\n\n整理资料保留引用${i}。`)}}})).status()).toBe(202);
  const rows=await(await request.get(base+`/courses/${course.id}/documents`,{headers})).json();
  await expect.poll(async()=>(await(await request.get(base+`/versions/${rows[0].latest_version_id}`,{headers})).json()).index_status,{timeout:20000}).toBe("SUCCEEDED");
  await page.addInitScript(({token,username})=>{localStorage.setItem("hustudy_token",token);localStorage.setItem("hustudy_user",username);},{token:auth.access_token,username});
  return {headers,course,rows};
}
async function getDoc(request:APIRequestContext,headers:Record<string,string>,id:string){return(await request.get(base+`/documents/${id}`,{headers})).json();}
async function fit(page:Page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);}
for(const width of [1440,390])test(`跨页资料选择/原子冲突/刷新后显式保存 ${width}px`,async({page,request})=>{
  test.setTimeout(90000);await page.setViewportSize({width,height:1000});const s=await setup(page,request,13);
  await page.goto(`/materials?course=${s.course.id}`);
  if(width<761)await page.getByRole("button",{name:/资料库与上传/}).click();
  await page.getByRole("button",{name:"批量整理分类与标签",exact:true}).click();
  const box=page.getByRole("checkbox",{name:/^选择资料：/}).first();
  const firstName=(await box.getAttribute("aria-label"))!.replace("选择资料：","");const first=s.rows.find((row:{name:string})=>row.name===firstName);
  await box.check();
  await page.getByRole("navigation",{name:"资料分页"}).getByRole("button",{name:"下一页",exact:true}).click();
  await expect(page.getByRole("checkbox",{name:/^选择资料：/})).toHaveCount(1);
  const secondBox=page.getByRole("checkbox",{name:/^选择资料：/});const secondName=(await secondBox.getAttribute("aria-label"))!.replace("选择资料：","");const second=s.rows.find((row:{name:string})=>row.name===secondName);
  await secondBox.check();await expect(page.getByText("已选 2 份",{exact:true})).toBeVisible();
  await page.getByLabel("筛选资料名称或标签").fill("完全不匹配的筛选");
  await expect(page.getByRole("checkbox",{name:/^选择资料：/})).toHaveCount(0);
  await page.getByRole("button",{name:"整理已选",exact:true}).click();
  const dialog=page.getByRole("dialog",{name:"整理所选资料",exact:true});
  await dialog.getByRole("checkbox",{name:"统一设置分类"}).check();await page.getByLabel("批量目标分类").fill("期末资料");
  await page.getByLabel("批量标签操作").selectOption("add");await page.getByLabel("批量资料标签").fill("重点，复习");
  expect((await request.patch(base+`/documents/${first.id}`,{headers:s.headers,data:{name:"另一个窗口的课件名称"}})).status()).toBe(200);
  await dialog.getByRole("button",{name:"确认整理 2 份资料",exact:true}).click();
  await expect(dialog.getByRole("button",{name:"重新读取所选资料",exact:true})).toBeVisible();
  expect((await getDoc(request,s.headers,second.id)).category).toBe(second.category);
  await expect(page.getByLabel("批量资料标签")).toHaveValue("重点，复习");
  await dialog.getByRole("button",{name:"重新读取所选资料",exact:true}).click();
  await expect(dialog.getByText(/已读取全部所选资料的最新信息/)).toBeVisible();
  await expect(dialog).toContainText("另一个窗口的课件名称");await fit(page);
  await page.screenshot({path:test.info().outputPath(`organize-${width}.png`),fullPage:false});
  await dialog.getByRole("button",{name:"确认整理 2 份资料",exact:true}).click();await expect(dialog).not.toBeVisible();
  for(const row of [first,second]){const current=await getDoc(request,s.headers,row.id);expect(current.category).toBe("期末资料");expect(current.tags).toEqual(["重点","复习"]);expect(current.latest_version_id).toBe(row.latest_version_id);}
  const untouched=s.rows.find((row:{id:string})=>![first.id,second.id].includes(row.id));expect((await getDoc(request,s.headers,untouched.id)).category).toBe(untouched.category);
  await fit(page);
});

test("资料/任务/引用目标独立失败恢复、分页标题查找、正文不拉取",async({page,request})=>{
  const s=await setup(page,request);const doc=s.rows[0];
  let chosen:any;for(let i=0;i<23;i++){const note=await(await request.post(base+"/notes",{headers:s.headers,data:{course_id:s.course.id,title:`笔记${String(i).padStart(2,"0")}`,content:"不应在资料列表读取的正文"}})).json();if(i===0)chosen=note;}
  let jobsBroken=true,notesBroken=true;let jobsCalls=0;const unbounded:string[]=[];
  page.on("request",r=>{if(/\/notes\?course_id=/.test(r.url()))unbounded.push(r.url());});
  await page.route("**/courses/*/jobs/page?**",async route=>{jobsCalls++;if(jobsBroken)await route.fulfill({status:503,json:{error:{message:"隔离任务失败"}}});else await route.continue();});
  await page.route("**/courses/*/note-options?**",async route=>{if(notesBroken)await route.fulfill({status:503,json:{error:{message:"隔离候选失败"}}});else await route.continue();});
  await page.goto(`/materials?course=${s.course.id}&document=${doc.id}&version=${doc.latest_version_id}`);
  await expect(page.locator(".reading-paper")).toContainText("整理资料保留引用");
  await expect(page.getByRole("button",{name:"批量整理分类与标签",exact:true})).toBeEnabled();
  await expect(page.getByRole("button",{name:"重试引用笔记列表",exact:true})).toBeVisible();
  await page.locator(".material-jobs summary").click();await expect(page.getByRole("button",{name:"重试处理记录",exact:true})).toBeVisible();
  const calls=jobsCalls;await page.waitForTimeout(2300);expect(jobsCalls).toBe(calls);
  jobsBroken=false;notesBroken=false;await page.getByRole("button",{name:"重试处理记录",exact:true}).click();await expect(page.getByRole("button",{name:"重试处理记录",exact:true})).toHaveCount(0);
  await page.getByRole("button",{name:"重试引用笔记列表",exact:true}).click();await expect(page.getByLabel("引用到笔记",{exact:true}).locator("option")).toHaveCount(21);
  await page.locator(".citation-target-search summary").click();await page.getByRole("button",{name:"后一页笔记",exact:true}).click();
  await expect(page.getByLabel("引用到笔记",{exact:true}).locator("option")).toHaveCount(4);
  await page.getByLabel("引用到笔记",{exact:true}).selectOption(chosen.id);
  await page.getByLabel("按标题查找引用目标").fill("笔记22");
  await expect(page.getByLabel("引用到笔记",{exact:true}).locator("option")).toHaveCount(3); // placeholder, selected target, matching result
  await expect(page.getByLabel("引用到笔记",{exact:true})).toHaveValue(chosen.id);
  await page.getByRole("button",{name:"引用到所选笔记",exact:true}).first().click();
  await expect.poll(async()=>(await(await request.get(base+`/notes/${chosen.id}/citations`,{headers:s.headers})).json()).length).toBe(1);
  expect(unbounded).toEqual([]);
});

test("单份整理冲突保留输入，合并时保留其他窗口的未编辑字段",async({page,request})=>{
  const s=await setup(page,request);const doc=s.rows[0];await page.goto(`/materials?course=${s.course.id}&document=${doc.id}&version=${doc.latest_version_id}`);
  await page.getByRole("button",{name:"整理",exact:true}).click();const form=page.locator(".material-metadata");
  await form.getByLabel("分类",{exact:true}).fill("我的分类");
  await request.patch(base+`/documents/${doc.id}`,{headers:s.headers,data:{name:"其他窗口的新名称",tags:["另一标签"]}});
  await form.getByRole("button",{name:"保存整理",exact:true}).click();
  await expect(page.getByRole("button",{name:"核对后保留本地修改",exact:true})).toBeVisible();
  await expect(form.getByLabel("分类",{exact:true})).toHaveValue("我的分类");
  await page.getByRole("button",{name:"核对后保留本地修改",exact:true}).click();
  await expect(form.getByLabel("资料名称",{exact:true})).toHaveValue("其他窗口的新名称");await expect(form.getByLabel("标签",{exact:true})).toHaveValue("另一标签");
  await form.getByRole("button",{name:"保存整理",exact:true}).click();
  await expect.poll(async()=>(await getDoc(request,s.headers,doc.id)).category).toBe("我的分类");
  expect((await getDoc(request,s.headers,doc.id)).name).toBe("其他窗口的新名称");
});

test("批量整理401让出重登窗口、保留输入、恢复后不自动重放",async({page,request})=>{
  const s=await setup(page,request);const doc=s.rows[0];await page.goto(`/materials?course=${s.course.id}`);
  await page.getByRole("button",{name:"批量整理分类与标签",exact:true}).click();await page.getByRole("checkbox",{name:/^选择资料：/}).check();await page.getByRole("button",{name:"整理已选",exact:true}).click();
  let calls=0,release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
  await page.route("**/courses/*/documents/organize",async route=>{calls++;await gate;await route.fulfill({status:401,json:{error:{message:"隔离登录过期"}}});});
  const dialog=page.getByRole("dialog",{name:"整理所选资料",exact:true});await page.getByLabel("批量标签操作").selectOption("add");await page.getByLabel("批量资料标签").fill("恢复后核对");
  await dialog.getByRole("button",{name:"确认整理 1 份资料",exact:true}).click();
  await expect(dialog.getByRole("button",{name:"关闭整理所选资料",exact:true})).toBeDisabled();await page.keyboard.press("Escape");await expect(dialog).toBeVisible();
  release();const auth=page.getByRole("dialog",{name:/登录已过期/});await expect(auth).toBeVisible();await expect(page.locator("dialog[open]")).toHaveCount(0);
  await auth.getByLabel("密码",{exact:true}).fill("Test-password-2026");await auth.getByRole("button",{name:"登录",exact:true}).click();await expect(auth).not.toBeVisible();expect(calls).toBe(1);
  await page.unroute("**/courses/*/documents/organize");await page.getByRole("button",{name:"整理已选",exact:true}).click();await expect(page.getByLabel("批量资料标签")).toHaveValue("恢复后核对");
  await expect(dialog.getByRole("button",{name:"确认整理 1 份资料",exact:true})).toBeDisabled();
  await dialog.getByRole("button",{name:"重新读取所选资料",exact:true}).click();await expect(dialog.getByText(/已读取全部所选资料的最新信息/)).toBeVisible();
  await dialog.getByRole("button",{name:"确认整理 1 份资料",exact:true}).click();await expect(dialog).not.toBeVisible();
  expect((await getDoc(request,s.headers,doc.id)).tags).toEqual(["恢复后核对"]);
});
