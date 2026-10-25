import {test,expect} from '@playwright/test';

for(const width of [390,1440])test(`长课件问答覆盖范围及汇总续跑 ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:1000});
  const base='http://127.0.0.1:8056/api/v1';
  const username='qa_batches_'+crypto.randomUUID().replaceAll('-','');
  const auth=await(await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await(await request.post(base+'/courses',{headers,data:{name:'完整课件问答'}})).json();
  const job=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'指令系统课件.md',mimeType:'text/markdown',buffer:Buffer.from('# 指令\n\n常用指令分为传送、算术、逻辑和转移。')}}})).json();
  const version=job.resource_id;
  await expect.poll(async()=>(await(await request.get(base+`/versions/${version}`,{headers})).json()).index_status).toBe('SUCCEEDED');
  const chunk=(await(await request.get(base+`/versions/${version}/chunks`,{headers})).json())[0];
  const coverage={versions:[{version_id:version,document_name:'指令系统课件',total_chunks:140,selected_chunks:140,total_chars:20000,sent_chars:20000,truncated:false}],truncated:false,notice:'仅分析实际发送的可提取正文。'};
  const pending:any={id:crypto.randomUUID(),course_id:course.id,query:'常用指令有哪些类型？',request_kind:'qa',model:'glm-5.3-flash',endpoint:'https://open.bigmodel.cn/api/paas/v4/chat/completions',expires_at:new Date(Date.now()+900000).toISOString(),sources:[{source_id:chunk.id,version_id:version,document_name:'指令系统课件',version_no:1,locator:{type:'heading',value:'指令'},text:chunk.text}],qa_scope:{mode:'selected_materials',coverage,batch_count:3,batched:true},batch_progress:{kind:'qa',total:4,completed:0,max_calls:4,chars:20000,phase:'extracting'},job:null,result:null};
  let calls=0;
  await page.route('**/api/v1/ai/provider',r=>r.fulfill({json:{configured:true,model:pending.model}}));
  await page.route(`**/api/v1/courses/${course.id}/remote-queries/preview`,async r=>{expect(r.request().postDataJSON().version_ids).toEqual([version]);await r.fulfill({status:201,json:pending});});
  await page.route(`**/api/v1/remote-queries/${pending.id}**`,async r=>{
    if(r.request().url().endsWith('/confirm')){
      calls++;pending.job={status:'FAILED',error:'处理预算已用尽'};pending.batch_progress.completed=2;
      pending.result={id:crypto.randomUUID(),course_id:course.id,query:pending.query,status:'provider_error',model_mode:'real',result:{error_code:'TASK_BUDGET_EXCEEDED',message:'已检查2批，尚未完成统一回答',partial:true,coverage,citations:[]}};
    }
    if(r.request().url().endsWith('/resume')){
      expect(r.request().postDataJSON()).toEqual({confirm_remote_send:true});calls++;
      pending.job={status:'SUCCEEDED'};pending.batch_progress.completed=4;
      pending.result={...pending.result,id:crypto.randomUUID(),status:'grounded',result:{answer:'常用指令包括传送、算术、逻辑和转移。',partial:false,coverage,citations:[{version_id:version,chunk_id:chunk.id,quote:chunk.text,availability:'active',locator:{type:'heading',value:'指令'}}]}};
    }
    await r.fulfill({json:pending});
  });
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  await page.goto(`/ai?course=${course.id}`);
  await page.getByRole('button',{name:'资料问答',exact:true}).click();
  await page.locator('summary').filter({hasText:/^限定资料范围/}).click();
  await page.getByRole('checkbox',{name:/指令系统课件/}).check();
  await page.getByLabel('向课程提问',{exact:true}).fill(pending.query);
  await page.getByRole('button',{name:'预览将发送的片段',exact:true}).click();
  await expect(page.getByText(/140\/140段/)).toBeVisible();
  await expect(page.getByText(/先检查3批资料，再汇总一次回答/)).toBeVisible();
  await page.getByRole('checkbox',{name:/我已核对上述问题与片段/}).check();
  await page.getByRole('button',{name:'确认本次发送',exact:true}).click();
  const resume=page.getByRole('button',{name:'确认继续未完成批次',exact:true});
  await expect(resume).toBeDisabled();await expect(page.getByText('分批问答：已完成2/4步',{exact:true})).toBeVisible();
  await page.getByRole('checkbox',{name:/我同意仅继续未完成批次/}).check();await resume.click();
  await expect(page.locator('#ai-result')).toContainText('常用指令包括传送、算术、逻辑和转移。');
  expect(calls).toBe(2);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
