import {test,expect} from '@playwright/test';

// Real temporary API for accounts/materials/notes; AI HTTP responses are synthetic.
for (const width of [390,1440]) test(`M2报告：确认、报告、自测、草稿与恢复 ${width}px`,async({page,request})=>{
  await page.setViewportSize({width,height:1000});
  const base='http://127.0.0.1:8056/api/v1';
  const username='report_'+crypto.randomUUID().replaceAll('-','');
  const auth=await (await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await (await request.post(base+'/courses',{headers,data:{name:'M2自制验收课程'}})).json();
  const uploaded=await (await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'报告样例.md',mimeType:'text/markdown',buffer:Buffer.from('# 进程\n\n进程是资源分配的基本单位，线程是调度和执行的基本单位。')}}})).json();
  const version=uploaded.resource_id;
  await expect.poll(async()=> (await (await request.get(base+`/versions/${version}`,{headers})).json()).index_status).toBe('SUCCEEDED');
  const chunk=(await (await request.get(base+`/versions/${version}/chunks`,{headers})).json())[0];
  const citation={version_id:version,chunk_id:chunk.id,locator:{type:chunk.locator_type,value:chunk.locator_value},quote:chunk.text,availability:'active'};
  const exercise={question:'线程主要承担什么作用？',answer:'线程是调度和执行的基本单位。',citations:[citation]};
  const report={summary:'理解进程与线程的分工。',learning_goals:['区分资源分配与执行'],prerequisites:[],learning_sequence:['阅读概念','核对区别','完成自测'],topics:[{topic_id:crypto.randomUUID(),name:'进程与线程',explanation:'进程负责资源分配，线程承担调度和执行。',misconceptions:['不要将两种基本单位混淆'],labels:[{kind:'key',origin:'ai_suggestion',reason:'原文直接给出了两者区别'}],citations:[citation]}],examples:[exercise],self_checks:[exercise,exercise,exercise]};
  const coverage={truncated:false,notice:'报告仅依据实际发送片段。',versions:[{version_id:version,document_name:'报告样例.md',total_chunks:1,selected_chunks:1,total_chars:chunk.text.length,sent_chars:chunk.text.length,truncated:false}]};
  const result={id:crypto.randomUUID(),course_id:course.id,query:'理解所选资料，梳理知识点并完成自测',status:'grounded',model_mode:'real',result:{study_report:report,coverage,citations:[citation],answer:'# 报告草稿\n进程与线程的分工。',model:'glm-5.3-flash',model_notice:'测试响应 · 非真实模型调用'}};
  const remote={id:crypto.randomUUID(),course_id:course.id,query:result.query,request_kind:'study_report',report_scope:{goal:result.query,scope_version_ids:[version],study_mode:'systematic',coverage},model:'glm-5.3-flash',endpoint:'https://open.bigmodel.cn/api/paas/v4/chat/completions',expires_at:new Date(Date.now()+900000).toISOString(),consented_at:null as string|null,dispatched_at:null as string|null,sources:[{source_id:chunk.id,version_id:version,document_name:'报告样例.md',version_no:1,locator:citation.locator,text:chunk.text}],job:null as object|null,result:null as typeof result|null};
  let confirms=0,resumes=0;
  await page.route('**/api/v1/ai/provider',route=>route.fulfill({json:{configured:true,model:remote.model,checked_at:'2026-10-16',policy_status:'政策细项未核实',documentation_url:'https://docs.bigmodel.cn',policy_entry_url:'https://open.bigmodel.cn/console'}}));
  await page.route(`**/api/v1/courses/${course.id}/study-reports/preview`,async route=>{
    expect(route.request().postDataJSON().version_ids).toEqual([version]);
    await route.fulfill({status:201,json:remote});
  });
  await page.route(`**/api/v1/courses/${course.id}/study-reports`,route=>route.fulfill({json:confirms ? [result] : []}));
  await page.route(`**/api/v1/remote-queries/${remote.id}**`,async route=>{
    if(route.request().url().endsWith('/resume')){
      resumes++;expect(route.request().postDataJSON()).toEqual({confirm_remote_send:true});
      Object.assign(remote,{job:{status:'SUCCEEDED',progress:100},batch_progress:{total:2,completed:2,max_calls:2,chars:10000}});
      Object.assign(result,{id:crypto.randomUUID(),status:'grounded'});
      Object.assign(result.result,{partial:false,study_report_sections:[{title:'第1部分',report},{title:'第2部分',report}]});
    }
    if(route.request().url().endsWith('/confirm')){
      confirms++;expect(route.request().postDataJSON()).toEqual({confirm_remote_send:true});
      remote.consented_at=new Date().toISOString();remote.dispatched_at=remote.consented_at;remote.job={status:'SUCCEEDED',progress:100};remote.result=result;
    }
    await route.fulfill({json:remote});
  });
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  await page.goto(`/ai?course=${course.id}`);
  await page.getByRole('button',{name:'学习报告',exact:true}).click();
  await page.getByRole('checkbox',{name:/报告样例/}).check();
  await page.getByRole('button',{name:'预览将发送的片段',exact:true}).click();
  await expect(page.getByText('已纳入所选版本的可用文本')).toBeVisible();
  const send=page.getByRole('button',{name:'确认本次发送',exact:true});
  await expect(send).toBeDisabled();expect(confirms).toBe(0);
  await page.getByRole('checkbox',{name:/我已核对上述问题与片段/}).check();await send.click();
  const article=page.getByRole('article',{name:'章节学习报告'});
  await expect(article).toBeVisible();await expect(article).toContainText('AI建议');
  await article.getByText('查看答案与依据',{exact:true}).first().click();await expect(article).toContainText(exercise.answer);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:test.info().outputPath(`study-report-${width}.png`),fullPage:true});
  await page.getByRole('button',{name:'整理为可编辑笔记草稿',exact:true}).click();
  const reason=page.getByLabel('进程与线程 标签1理由',{exact:true});
  const next=page.getByRole('button',{name:'继续编辑笔记正文',exact:true});
  await reason.fill('   ');await expect(next).toBeDisabled();
  await page.getByLabel('进程与线程 标签1类型',{exact:true}).selectOption('difficult');
  await reason.fill('我还需要练习区分资源与调度');
  await page.getByRole('button',{name:'新增标签',exact:true}).click();
  await page.getByLabel('进程与线程 标签2类型',{exact:true}).selectOption('exam');
  await page.getByLabel('进程与线程 标签2理由',{exact:true}).fill('仅作为我的复习方向');
  await page.getByRole('button',{name:'删除进程与线程标签2',exact:true}).click();
  await page.getByRole('button',{name:'资料原文检索',exact:true}).click();
  await expect(reason).toHaveValue('我还需要练习区分资源与调度');
  // Navigation cancellation preserves the independent review snapshot.
  page.once('dialog',dialog=>dialog.dismiss());
  await page.evaluate(()=>window.dispatchEvent(new Event('hustudy:before-navigate',{cancelable:true})));
  await expect(reason).toHaveValue('我还需要练习区分资源与调度');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:test.info().outputPath(`label-review-${width}.png`),fullPage:true});
  await next.click();
  const draft=page.getByLabel('AI 笔记草稿');
  await expect(draft).toHaveValue(/难点：我还需要练习区分资源与调度/);
  await expect(draft).toHaveValue(/重点（AI建议）：原文直接给出了两者区别/);
  await draft.fill((await draft.inputValue())+'\n\n人工正文修改');
  page.once('dialog',dialog=>dialog.dismiss());
  await page.getByRole('button',{name:'返回标签审阅',exact:true}).click();
  await expect(draft).toHaveValue(/人工正文修改/);
  let saves=0;
  await page.route('**/api/v1/notes',async route=>{
    if(route.request().method()!=='POST')return route.continue();
    if(++saves===1)return route.fulfill({status:503,json:{error:{code:'TEST_SAVE_FAILURE',message:'模拟保存失败'}}});
    return route.continue();
  });
  await page.getByRole('button',{name:'确认保存为笔记草稿',exact:true}).click();
  await expect(page.getByText('模拟保存失败',{exact:true})).toBeVisible();
  await expect(draft).toHaveValue(/人工正文修改/);
  await expect(draft).toBeDisabled();
  await page.getByRole('button',{name:'重试保存原笔记',exact:true}).click();
  await expect.poll(async()=> (await (await request.get(base+`/notes?course_id=${course.id}`,{headers})).json()).length).toBe(1);
  const notes=await(await request.get(base+`/notes?course_id=${course.id}`,{headers})).json();
  expect(notes[0].content).toContain('难点：我还需要练习区分资源与调度');
  expect(notes[0].content).toContain('人工正文修改');
  const citations=await(await request.get(base+`/notes/${notes[0].id}/citations`,{headers})).json();
  expect(citations[0].chunk_id).toBe(chunk.id);
  await expect(page.getByLabel('AI 笔记草稿')).toHaveCount(0);
  await page.reload();await page.getByRole('button',{name:'学习报告',exact:true}).click();
  await expect(page.getByRole('article',{name:'章节学习报告'})).toBeVisible();expect(confirms).toBe(1);
  Object.assign(remote,{job:{status:'FAILED',progress:50,error:'第2批请求超时'},batch_progress:{total:2,completed:1,max_calls:2,chars:10000}});
  Object.assign(result,{id:crypto.randomUUID(),status:'provider_error'});
  Object.assign(result.result,{partial:true,message:'第2批请求超时',error_code:'TIMEOUT',study_report_sections:[{title:'第1部分',report}]});
  await page.reload();await page.getByRole('button',{name:'学习报告',exact:true}).click();
  await expect(page.getByText('当前不是完整报告。',{exact:false})).toBeVisible();
  const resume=page.getByRole('button',{name:'确认继续未完成批次',exact:true});
  await expect(resume).toBeDisabled();expect(resumes).toBe(0);
  await page.getByRole('checkbox',{name:/我同意仅继续未完成批次/}).check();await resume.click();
  await expect(page.getByText('第2部分',{exact:true})).toBeVisible();expect(resumes).toBe(1);
  if(width>1100){
    const panels=await page.locator('.ai-workspace-grid > section').evaluateAll(nodes=>nodes.map(node=>({height:node.getBoundingClientRect().height,overflow:getComputedStyle(node).overflowY})));
    expect(panels).toHaveLength(2);expect(panels[0].overflow).toBe('auto');expect(panels[1].overflow).toBe('auto');
    expect(Math.abs(panels[0].height-panels[1].height)).toBeLessThan(2);
  }
  await page.locator('.ai-workspace-grid > section').evaluateAll(nodes=>nodes.forEach(node=>node.scrollTop=0));
  await page.locator('.ai-workspace-grid').scrollIntoViewIfNeeded();
  if(width<=1100)await expect(page.getByRole('link',{name:'设置与发送',exact:true})).toBeInViewport();
  await page.screenshot({path:test.info().outputPath(`ai-layout-${width}.png`),fullPage:false});
});
