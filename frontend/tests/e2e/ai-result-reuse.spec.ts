import {test,expect} from '@playwright/test';

// Real disposable accounts and materials, synthetic AI protocol. No provider calls.
for(const width of [390,1440])test(`M2已有结果复用无需发送确认 ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:1000});
  const base='http://127.0.0.1:8056/api/v1';
  const username='reuse_'+crypto.randomUUID().replaceAll('-','');
  const auth=await(await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await(await request.post(base+'/courses',{headers,data:{name:'M2复用验收'}})).json();
  const uploaded=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'复用资料.md',mimeType:'text/markdown',buffer:Buffer.from('# 函数\n\n高阶函数可以接收函数作为参数。')}}})).json();
  const version=uploaded.resource_id;
  await expect.poll(async()=>(await(await request.get(base+`/versions/${version}`,{headers})).json()).index_status).toBe('SUCCEEDED');
  const chunk=(await(await request.get(base+`/versions/${version}/chunks`,{headers})).json())[0];
  const result={id:crypto.randomUUID(),course_id:course.id,query:'高阶函数是什么',status:'grounded',model_mode:'real',result:{answer:'高阶函数可以接收函数作为参数。',model:'glm-5.3-flash',citations:[{version_id:version,chunk_id:chunk.id,quote:chunk.text,availability:'active',locator:{type:'heading',value:'函数'}}]}};
  const remote={id:crypto.randomUUID(),course_id:course.id,query:result.query,request_kind:'qa',model:'glm-5.3-flash',endpoint:'https://open.bigmodel.cn/api/paas/v4/chat/completions',expires_at:new Date(Date.now()+900000).toISOString(),consented_at:null,dispatched_at:null,sources:[{source_id:chunk.id,version_id:version,document_name:'复用资料.md',version_no:1,locator:{type:'heading',value:'函数'},text:chunk.text}],job:null,result:null,reusable_result:result};
  let sends=0,reuses=0;
  await page.route('**/api/v1/ai/provider',route=>route.fulfill({json:{configured:true,model:remote.model}}));
  await page.route(`**/api/v1/courses/${course.id}/remote-queries/preview`,route=>route.fulfill({status:201,json:remote}));
  await page.route(`**/api/v1/remote-queries/${remote.id}/reuse`,async route=>{
    reuses++;expect(route.request().postDataJSON()).toEqual({result_id:result.id});
    await route.fulfill({json:result});
  });
  await page.route(`**/api/v1/remote-queries/${remote.id}/confirm`,async route=>{sends++;await route.fulfill({status:500,json:{}});});
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  await page.goto(`/ai?course=${course.id}`);
  await page.getByRole('button',{name:'资料问答',exact:true}).click();
  await page.getByLabel('向课程提问',{exact:true}).fill(result.query);
  await page.getByRole('button',{name:'预览将发送的片段',exact:true}).click();
  await expect(page.getByRole('button',{name:'仍要重新生成（调用AI）',exact:true})).toBeDisabled();
  await expect(page.getByRole('checkbox',{name:/我已核对上述问题与片段/})).not.toBeChecked();
  await page.getByRole('button',{name:'使用已有结果（不调用AI）',exact:true}).click();
  await expect(page.locator('#ai-result')).toContainText(result.result.answer);
  expect(reuses).toBe(1);expect(sends).toBe(0);
  expect((await(await request.get(base+`/courses/${course.id}/jobs`,{headers})).json()).filter((job:{type:string})=>job.type==='AI_ANALYSIS')).toHaveLength(0);
});
