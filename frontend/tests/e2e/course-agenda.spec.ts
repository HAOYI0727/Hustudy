import {test,expect,type Page,type APIRequestContext} from "@playwright/test";
const base="http://127.0.0.1:8056/api/v1";
const agendaRequest=(url:string)=>url.includes("/review-tasks?")&&new URL(url).searchParams.has("course_id");

async function setup(page:Page,request:APIRequestContext){
  const auth=await(await request.post(base+"/auth/register",{data:{username:"agenda_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();
  const headers={Authorization:"Bearer "+auth.access_token};
  const course=await(await request.post(base+"/courses",{headers,data:{name:"网络复习日程"}})).json();
  const other=await(await request.post(base+"/courses",{headers,data:{name:"其他课程"}})).json();
  const bank=await(await request.post(base+`/courses/${course.id}/question-bank/import`,{headers,data:{title:"日程自制题库",content:Array.from({length:10},(_,i)=>`${i+1}. 自制判断${i+1}，请选择正确项。\nA. 正确\nB. 错误一\nC. 错误二\nD. 错误三\n答案：A\n知识标签：日程练习`).join("\n\n")}})).json();
  expect((await request.post(base+`/past-papers/${bank.id}/confirm`,{headers})).status()).toBe(200);
  const paper=await(await request.post(base+`/courses/${course.id}/question-bank/draw`,{headers,data:{request_id:crypto.randomUUID(),topic_ids:[],count:10,duration_minutes:30}})).json();
  expect((await request.post(base+`/exam-papers/${paper.id}/review`,{headers})).status()).toBe(200);
  const attempt=await(await request.post(base+`/exam-papers/${paper.id}/attempts`,{headers})).json();
  for(const question of paper.questions){const answer="ABCD"[question.options.indexOf("错误一")];expect((await request.put(base+`/attempts/${attempt.id}/answers/${question.id}`,{headers,data:{answer}})).status()).toBe(200);}
  expect((await request.post(base+`/attempts/${attempt.id}/submit`,{headers})).status()).toBe(200);
  const mistakes=await(await request.get(base+"/mistakes",{headers})).json();expect(mistakes).toHaveLength(10);
  const today=(await(await request.get(base+"/review-tasks",{headers})).json()).today;
  const shift=(days:number)=>{const date=new Date(today+"T12:00:00Z");date.setUTCDate(date.getUTCDate()+days);return date.toISOString().slice(0,10);};
  const plans=[];
  for(let i=0;i<10;i++){
    const response=await request.post(base+"/review-tasks",{headers,data:{mistake_id:mistakes[i].id,title:i===0?"TCP 100%_核对原文":`回顾计划${i}`,due_date:i===8?shift(-1):i===9?shift(2):today}});
    expect(response.status()).toBe(201);plans.push(await response.json());
  }
  expect((await request.post(base+`/review-tasks/${plans[7].id}/complete`,{headers})).status()).toBe(200);
  await page.addInitScript(auth=>{localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);},auth);
  return {auth,headers,course,other,plans,mistakes,today};
}

for(const width of [1440,390,320])test(`当前课程日程：真实计数/搜索分页/统一主题/回顾不自动重做 ${width}px`,async({page,request})=>{
  test.setTimeout(120000);await page.setViewportSize({width,height:1000});const s=await setup(page,request);
  const reads:string[]=[],writes:string[]=[];page.on("request",r=>{if(agendaRequest(r.url()))reads.push(r.url());if(r.url().includes("/api/v1/")&&!['GET','OPTIONS'].includes(r.method()))writes.push(r.url());});
  await page.goto(`/overview?course=${s.course.id}`);const agenda=page.locator(".course-agenda");await expect(agenda).toContainText("网络复习日程");expect(reads).toHaveLength(0);
  await agenda.locator("summary").click();const results=agenda.getByRole("region",{name:"当前课程日程列表"});
  await expect(results).toContainText("到期回顾 · 8项");await expect(agenda.getByRole("button",{name:/^今天/})).toContainText("7");
  await expect(agenda.locator(".agenda-plan")).toHaveCount(6);await agenda.getByRole("button",{name:"下一页日程",exact:true}).click();await expect(agenda.locator(".agenda-plan")).toHaveCount(2);await expect(results).toContainText("2 / 2 页 · 8 项");
  for(const [label,count]of [["已逾期",1],["今天",7],["未来安排",1],["已完成",1],["全部待办",9]] as const){await agenda.getByRole("button",{name:new RegExp("^"+label)}).click();await expect(results).toContainText(`${label} · ${count}项`);}
  await agenda.getByLabel("搜索复习计划标题",{exact:true}).fill("100%_");await agenda.getByRole("button",{name:"查找日程",exact:true}).click();await expect(agenda.locator(".agenda-plan")).toHaveCount(1);await expect(results).toContainText("TCP 100%_核对原文");
  await agenda.getByRole("button",{name:"清除日程查找",exact:true}).click();await expect(results).toContainText("全部待办 · 9项");
  await page.getByRole("button",{name:"外观与布局",exact:true}).click();const panel=page.getByRole("dialog",{name:"外观与布局",exact:true});await panel.getByRole("button",{name:"松石青",exact:true}).click();await panel.getByRole("button",{name:"完成设置",exact:true}).click();
  const accent=await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--accent").trim());
  await expect.poll(()=>agenda.locator(".agenda-views .is-selected").evaluate(e=>getComputedStyle(e).borderTopColor)).toBe(`rgb(${[1,3,5].map(i=>parseInt(accent.slice(i,i+2),16)).join(", ")})`);
  if(width===1440){const positions=await agenda.locator(".agenda-toolbar form").evaluate(e=>{const input=e.querySelector("input")!,button=e.querySelector("button")!;return [input.getBoundingClientRect().top,button.getBoundingClientRect().top];});expect(Math.abs(positions[0]-positions[1])).toBeLessThan(8);}
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);expect(await agenda.evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBe(true);
  await agenda.screenshot({path:test.info().outputPath(`course-agenda-${width}.png`)});
  await agenda.getByLabel("搜索复习计划标题",{exact:true}).fill("100%_");await agenda.getByRole("button",{name:"查找日程",exact:true}).click();await expect(agenda.locator(".agenda-plan")).toHaveCount(1);
  await agenda.getByRole("button",{name:"回顾复习计划：TCP 100%_核对原文",exact:true}).click();await expect(page).toHaveURL(/review=plan/);await expect(page.getByRole("heading",{name:"错题回顾与复习",exact:true})).toBeVisible();
  await expect(page.getByRole("region",{name:"安排错题复习"})).toBeVisible();expect(writes).toEqual([]);
  await page.getByRole("button",{name:"← 返回错题库",exact:true}).click();const plan=page.locator(".review-plan-row").filter({hasText:"TCP 100%_核对原文"});await plan.getByRole("button",{name:"完成计划",exact:true}).click();await expect(page.locator(".review-schedule")).toContainText("本次复习计划已完成");
  await page.goto(`/overview?course=${s.course.id}`);await page.locator(".course-agenda summary").click();await expect(page.locator(".course-agenda")).toContainText("到期回顾 · 7项");await page.locator(".course-agenda").getByRole("button",{name:/^已完成/}).click();await expect(page.locator(".course-agenda")).toContainText("已完成 · 2项");
  const latest=await(await request.get(base+"/mistakes",{headers:s.headers})).json();expect(latest.every((m:{mastered:boolean})=>!m.mastered)).toBe(true);
  expect((await(await request.get(base+`/review-tasks?course_id=${s.course.id}`,{headers:s.headers})).json()).total).toBe(8);
});

test("日程失败/离线只显式重试并保留查找，关闭和切课程拒绝迟到",async({page,request})=>{
  test.setTimeout(120000);const s=await setup(page,request);let count=0;
  await page.route("**/api/v1/review-tasks?**",route=>{if(!agendaRequest(route.request().url()))return route.continue();count++;return route.fulfill({status:503,json:{error:{message:"隔离日程服务暂不可用"}}});});
  await page.goto(`/overview?course=${s.course.id}`);const agenda=page.locator(".course-agenda");await agenda.locator("summary").click();await expect(agenda.getByRole("alert")).toContainText("隔离日程服务暂不可用");expect(count).toBe(1);
  await agenda.getByLabel("搜索复习计划标题",{exact:true}).fill("TCP");await page.unroute("**/api/v1/review-tasks?**");await agenda.getByRole("button",{name:"重试课程日程",exact:true}).click();await expect(agenda).toContainText("到期回顾 · 8项");await expect(agenda.getByLabel("搜索复习计划标题",{exact:true})).toHaveValue("TCP");
  await page.context().setOffline(true);await agenda.getByRole("button",{name:"刷新日程",exact:true}).click();await expect(agenda.getByRole("alert")).toBeVisible();await page.context().setOffline(false);await expect(agenda.getByRole("alert")).toBeVisible();await agenda.getByRole("button",{name:"重试课程日程",exact:true}).click();await expect(agenda).toContainText("到期回顾 · 8项");
  await page.route("**/api/v1/review-tasks?**",route=>route.fulfill({json:{course_id:s.other.id,items:[{...s.plans[0],title:"错误课程的日程"}],total:1,counts:{due:1,overdue:0,today:1,upcoming:0,pending:1,completed:0},today:s.today,timezone:"Asia/Shanghai",offset:0,limit:6}}));await agenda.getByRole("button",{name:"刷新日程",exact:true}).click();await expect(agenda.getByRole("alert")).toContainText("无法核对当前课程日程");await expect(agenda).not.toContainText("错误课程的日程");await page.unroute("**/api/v1/review-tasks?**");await agenda.getByRole("button",{name:"重试课程日程",exact:true}).click();await expect(agenda).toContainText("到期回顾 · 8项");
  let release!:()=>void;let captured!:()=>void;const gate=new Promise<void>(r=>release=r),started=new Promise<void>(r=>captured=r);
  await page.route("**/api/v1/review-tasks?**",async route=>{if(new URL(route.request().url()).searchParams.get("course_id")!==s.course.id)return route.continue();const response=await route.fetch();captured();await gate;await route.fulfill({response}).catch(()=>{});});
  await agenda.getByRole("button",{name:"刷新日程",exact:true}).click();await started;await agenda.locator("summary").click();await expect(agenda).not.toHaveAttribute("open","");
  await page.getByLabel("当前课程",{exact:true}).selectOption(s.other.id);await expect(page.locator(".course-agenda")).toContainText("其他课程");await page.locator(".course-agenda summary").click();await expect(page.locator(".course-agenda")).toContainText("到期回顾 · 0项");release();
  await expect(page.locator(".course-agenda")).not.toContainText("TCP 100%_核对原文");await expect(page.locator(".course-agenda .agenda-plan")).toHaveCount(0);
});

test("日程401让出统一登录，重新登录后不自动重放",async({page,request})=>{
  test.setTimeout(120000);const s=await setup(page,request);let count=0;
  await page.route("**/api/v1/review-tasks?**",route=>{count++;return route.fulfill({status:401,json:{error:{message:"隔离会话过期"}}});});
  await page.goto(`/overview?course=${s.course.id}`);await page.locator(".course-agenda summary").click();const login=page.getByRole("dialog");await expect(login).toBeVisible();expect(count).toBe(1);
  await page.unroute("**/api/v1/review-tasks?**");await login.getByLabel("密码",{exact:true}).fill("Test-password-2026");await login.getByRole("button",{name:"登录",exact:true}).click();await expect(login).not.toBeVisible();expect(count).toBe(1);
  await expect(page.locator(".course-agenda")).not.toHaveAttribute("open","");
  await page.locator(".course-agenda summary").click();await expect(page.locator(".course-agenda")).toContainText("到期回顾 · 8项");
});
