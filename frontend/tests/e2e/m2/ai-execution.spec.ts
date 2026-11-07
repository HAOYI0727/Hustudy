import {test,expect} from '@playwright/test';

for(const width of [390,1440])for(const report of [false,true])test(`M2修复授权与预算${report?'报告续跑':'问答计数'} ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:1000});
  const base='http://127.0.0.1:8056/api/v1';
  const username='execution_'+crypto.randomUUID().replaceAll('-','');
  const auth=await(await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await(await request.post(base+'/courses',{headers,data:{name:'M2执行预算验收'}})).json();
  const upload=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'预算资料.md',mimeType:'text/markdown',buffer:Buffer.from('# 函数\n\n高阶函数可以接收函数作为参数。')}}})).json();
  const version=upload.resource_id;
  await expect.poll(async()=>(await(await request.get(base+`/versions/${version}`,{headers})).json()).index_status).toBe('SUCCEEDED');
  const chunk=(await(await request.get(base+`/versions/${version}/chunks`,{headers})).json())[0];
  const citation={version_id:version,chunk_id:chunk.id,quote:chunk.text,availability:'active',locator:{type:'heading',value:'函数'}};
  const exercise={question:'什么是高阶函数？',answer:'可以接收函数作为参数。',citations:[citation]};
  const teaching={summary:'高阶函数',learning_goals:['理解概念'],prerequisites:[],learning_sequence:['阅读'],topics:[{topic_id:crypto.randomUUID(),name:'高阶函数',explanation:exercise.answer,misconceptions:[],labels:[],citations:[citation]}],examples:[exercise],self_checks:[exercise,exercise,exercise]};
  const execution={budget_seconds:120,max_structure_repairs:report?0:2,repairs_used:0,total_calls:0,window_number:1,window_calls:0,window_call_limit:report?2:3,window_started_at:null as string|null,deadline_at:null as string|null,remaining_seconds:120,phase:'awaiting_dispatch'};
  const remote:any={id:crypto.randomUUID(),course_id:course.id,query:report?'理解所选资料，梳理知识点并完成自测':'高阶函数是什么',request_kind:report?'study_report':'qa',model:'glm-5.3-flash',endpoint:'https://open.bigmodel.cn/api/paas/v4/chat/completions',expires_at:new Date(Date.now()+900000).toISOString(),consented_at:null,dispatched_at:null,sources:[{source_id:chunk.id,version_id:version,document_name:'预算资料.md',version_no:1,locator:citation.locator,text:chunk.text}],job:null,result:null,execution};
  const kind=report?'study-reports':'remote-queries';let previews=0,confirms=0,resumes=0;
  await page.route('**/api/v1/ai/provider',route=>route.fulfill({json:{configured:true,model:remote.model}}));
  await page.route(`**/api/v1/courses/${course.id}/${kind}/preview`,async route=>{
    previews++;expect(route.request().postDataJSON().max_structure_repairs).toBe(report?0:2);
    if(report)expect(route.request().postDataJSON().version_ids).toEqual([version]);
    await route.fulfill({status:201,json:remote});
  });
  await page.route(`**/api/v1/remote-queries/${remote.id}**`,async route=>{
    if(route.request().url().endsWith('/confirm')){
      confirms++;Object.assign(execution,{total_calls:report?1:2,window_calls:report?1:2,repairs_used:report?0:1,window_started_at:new Date().toISOString(),remaining_seconds:report?0:90,phase:report?'budget_exhausted':'generated'});
      remote.job={status:report?'FAILED':'SUCCEEDED',error:report?'本次120秒预算已用尽':null};
      remote.result={id:crypto.randomUUID(),course_id:course.id,query:remote.query,status:report?'provider_error':'grounded',model_mode:'real',result:{execution:{...execution},citations:[citation],...(report?{error_code:'TASK_BUDGET_EXCEEDED',message:'预算已用尽',partial:true,study_report_sections:[{title:'第1部分',report:teaching}]}:{answer:exercise.answer})}};
      if(report)remote.batch_progress={total:2,completed:1,max_calls:2,chars:10000};
    }
    if(route.request().url().endsWith('/resume')){
      resumes++;expect(route.request().postDataJSON()).toEqual({confirm_remote_send:true});
      Object.assign(execution,{window_number:2,window_calls:1,window_call_limit:1,total_calls:2,remaining_seconds:80,phase:'generated'});
      remote.job={status:'SUCCEEDED'};remote.batch_progress.completed=2;
      remote.result={...remote.result,id:crypto.randomUUID(),status:'grounded',result:{execution:{...execution},citations:[citation],study_report_sections:[{title:'第1部分',report:teaching},{title:'第2部分',report:teaching}]}};
    }
    await route.fulfill({json:remote});
  });
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  await page.goto(`/ai?course=${course.id}`);
  await page.getByRole('button',{name:report?'学习报告':'资料问答',exact:true}).click();
  const repair=page.getByRole('checkbox',{name:/允许最多2次格式修复/});await expect(repair).not.toBeChecked();
  if(report)await page.getByRole('checkbox',{name:/预算资料/}).check();
  else{await page.getByLabel('向课程提问',{exact:true}).fill(remote.query);await repair.check();}
  expect(confirms).toBe(0);expect(previews).toBe(0);
  await page.getByRole('button',{name:'预览将发送的片段',exact:true}).click();
  await expect(page.getByRole('button',{name:'确认本次发送',exact:true})).toBeDisabled();
  await expect(page.getByLabel('本次处理预算')).toContainText('120秒');
  await page.getByRole('checkbox',{name:/我已核对上述问题与片段/}).check();
  await page.getByRole('button',{name:'确认本次发送',exact:true}).click();
  if(report){
    await expect(page.locator('#ai-result')).toContainText('处理预算已用尽');
    const resume=page.getByRole('button',{name:'确认继续未完成批次',exact:true});await expect(resume).toBeDisabled();
    await page.getByRole('checkbox',{name:/我同意仅继续未完成批次/}).check();await resume.click();
    await expect(page.locator('#ai-result')).toContainText('第2部分');
    await expect(page.locator('#ai-result')).toContainText('第2个窗口');expect(resumes).toBe(1);
  }else await expect(page.locator('#ai-result')).toContainText('已用格式修复1/2次');
  expect(confirms).toBe(1);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
