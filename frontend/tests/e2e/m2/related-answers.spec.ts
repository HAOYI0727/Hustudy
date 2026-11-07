import {test,expect} from '@playwright/test';

for(const width of [390,1440])test(`相近历史问答查看后明确采用且不发送模型 ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:1000});
  const base='http://127.0.0.1:8056/api/v1',username='related_'+crypto.randomUUID().replaceAll('-','');
  const auth=await(await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await(await request.post(base+'/courses',{headers,data:{name:'相近问答自制验收'}})).json();
  const uploaded=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'事务.md',mimeType:'text/markdown',buffer:Buffer.from('# 事务\n\n事务ACID包含原子性、一致性、隔离性和持久性。')}}})).json();
  const version=uploaded.resource_id;
  await expect.poll(async()=>(await(await request.get(base+`/versions/${version}`,{headers})).json()).index_status).toBe('SUCCEEDED');
  const chunk=(await(await request.get(base+`/versions/${version}/chunks`,{headers})).json())[0];
  const oldQuestion='依据资料解释事务ACID',newQuestion='仅依据资料解释事务ACID';
  const result={id:crypto.randomUUID(),course_id:course.id,query:oldQuestion,status:'grounded',model_mode:'real',result:{answer:'历史原答案：事务ACID包含原子性、一致性、隔离性和持久性。',model:'glm-5.3-flash',citations:[{version_id:version,chunk_id:chunk.id,quote:chunk.text,availability:'active',locator:{type:'heading',value:'事务'}}]}};
  const remote={id:crypto.randomUUID(),course_id:course.id,query:newQuestion,request_kind:'qa',model:'glm-5.3-flash',endpoint:'https://open.bigmodel.cn/api/paas/v4/chat/completions',expires_at:new Date(Date.now()+900000).toISOString(),sources:[{source_id:chunk.id,version_id:version,text:chunk.text,document_name:'事务.md',version_no:1,locator:{type:'heading',value:'事务'}}],job:null,result:null,reusable_result:null,related_results:[{id:result.id,query:oldQuestion,answer_preview:result.result.answer,model:'glm-5.3-flash',created_at:'2026-11-01T00:00:00Z'}]};
  let views=0,adoptions=0,sends=0;
  await page.route('**/api/v1/ai/provider',route=>route.fulfill({json:{configured:true,model:remote.model}}));
  await page.route(`**/api/v1/courses/${course.id}/remote-queries/preview`,route=>route.fulfill({status:201,json:remote}));
  await page.route(`**/api/v1/remote-queries/${remote.id}/related-results/${result.id}`,async route=>{views++;await route.fulfill({json:result});});
  await page.route(`**/api/v1/remote-queries/${remote.id}/related-results/${result.id}/reuse`,async route=>{
    adoptions++;expect(route.request().postDataJSON()).toEqual({confirm_related_reuse:true});await route.fulfill({json:result});
  });
  await page.route(`**/api/v1/remote-queries/${remote.id}/confirm`,async route=>{sends++;await route.fulfill({status:500,json:{}});});
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  await page.goto(`/ai?course=${course.id}`);await page.getByRole('button',{name:'资料问答',exact:true}).click();
  await page.getByLabel('向课程提问',{exact:true}).fill(newQuestion);
  await page.getByRole('button',{name:'预览将发送的片段',exact:true}).click();
  const panel=page.getByRole('region',{name:'相近历史问答',exact:true});
  await expect(panel).toContainText(oldQuestion);await expect(panel).toContainText('可能与本次问题要求不同');
  await expect(panel.getByRole('button',{name:'确认使用这条历史答案（不调用AI）',exact:true})).toHaveCount(0);
  await panel.getByRole('button',{name:'查看原答案',exact:true}).click();
  await expect(panel.getByRole('button',{name:'确认使用这条历史答案（不调用AI）',exact:true})).toBeDisabled();
  await panel.getByRole('checkbox',{name:'我已对照原问题和原答案，确认适用于本次问题',exact:true}).check();
  await panel.getByRole('button',{name:'确认使用这条历史答案（不调用AI）',exact:true}).click();
  await expect(page.locator('#ai-result')).toContainText(result.result.answer);
  expect(views).toBe(1);expect(adoptions).toBe(1);expect(sends).toBe(0);
  expect((await(await request.get(base+`/courses/${course.id}/jobs`,{headers})).json()).filter((j:{type:string})=>j.type==='AI_ANALYSIS')).toHaveLength(0);
});
