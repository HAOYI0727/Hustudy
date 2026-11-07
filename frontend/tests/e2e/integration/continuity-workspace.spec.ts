import {test,expect,type Page,type APIRequestContext} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:Page,request:APIRequestContext){
 const username='workspace_'+crypto.randomUUID().replaceAll('-','');
 const auth=await(await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};const course=await(await request.post(base+'/courses',{headers,data:{name:'连续学习工作区'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 return {headers,course,auth};
}
async function upload(request:APIRequestContext,headers:Record<string,string>,course:string,name:string){
 const r=await request.post(base+`/courses/${course}/documents`,{headers,multipart:{file:{name:name+'.md',mimeType:'text/markdown',buffer:Buffer.from('# '+name+'\n线程共享进程资源。')}}});expect(r.status()).toBe(202);const job=await r.json();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe('SUCCEEDED');
 return (await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
}
for(const width of [390,1440])test(`边读边记保留引用、预览关联笔记并打开完整编辑器 ${width}px`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});const {course,headers}=await setup(page,request);const v=await upload(request,headers,course.id,'并发学习');
 let modelWrites=0;page.on('request',r=>{if(r.method()==='POST'&&/remote-queries|study-reports/.test(r.url()))modelWrites++;});
 await page.goto(`/materials?course=${course.id}&document=${v.document_id}&version=${v.id}`);await page.getByRole('button',{name:'阅读笔记',exact:true}).click();const panel=page.getByRole('complementary',{name:'阅读笔记侧栏'});
 await panel.getByLabel('阅读笔记标题',{exact:true}).fill('线程学习理解');await panel.getByLabel('阅读时记录理解').fill('线程共享地址空间，可以减少资源开销。');const select=panel.getByLabel('阅读笔记来源片段');await expect(select.locator('option')).toHaveCount(2);await select.selectOption({index:1});
 await panel.getByRole('button',{name:'保存阅读笔记',exact:true}).click();await expect(panel.getByText('理解与所选原文引用已保存，可继续在完整编辑器整理。',{exact:true})).toBeVisible();
 const notes=await(await request.get(base+`/notes?course_id=${course.id}`,{headers})).json();expect(notes).toHaveLength(1);const citations=await(await request.get(base+`/notes/${notes[0].id}/citations`,{headers})).json();expect(citations).toHaveLength(1);expect(citations[0].version_id).toBe(v.id);
 await panel.getByRole('button',{name:'关联笔记 · 1',exact:true}).click();await panel.getByRole('button',{name:'线程学习理解',exact:true}).click();await expect(panel.locator('.markdown-preview')).toContainText('线程共享地址空间');expect(modelWrites).toBe(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);await page.screenshot({path:test.info().outputPath(`reader-notebook-${width}.png`),fullPage:true});
 await panel.getByRole('button',{name:'在完整编辑器打开',exact:true}).click();await expect(page).toHaveURL(new RegExp('note='+notes[0].id));await expect(page.getByLabel('Markdown 正文')).toHaveValue('线程共享地址空间，可以减少资源开销。');
});
test('阅读草稿离开保护与刷新后恢复保留原文引用',async({page,request})=>{
 const {course,headers,auth}=await setup(page,request);const v=await upload(request,headers,course.id,'恢复阅读');await page.goto(`/materials?course=${course.id}&document=${v.document_id}&version=${v.id}`);await page.getByRole('button',{name:'阅读笔记',exact:true}).click();
 await page.getByLabel('阅读时记录理解').fill('还未保存的阅读理解');await page.getByLabel('阅读笔记来源片段').selectOption({index:1});
 await expect.poll(()=>page.evaluate(id=>Object.keys(localStorage).filter(k=>k.startsWith(`hustudy-note-recovery:v1:${id}:`)).length,auth.user.id)).toBe(1);
 page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'关闭阅读笔记',exact:true}).click();await expect(page.getByLabel('阅读时记录理解')).toHaveValue('还未保存的阅读理解');
 page.once('dialog',d=>d.accept());await page.reload();await page.goto(`/notes?course=${course.id}`);await page.getByRole('button',{name:'核对并恢复',exact:true}).click();await expect(page.getByLabel('Markdown 正文')).toHaveValue('还未保存的阅读理解');
 await page.getByRole('button',{name:'立即保存',exact:true}).click();await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
 const notes=await(await request.get(base+`/notes?course_id=${course.id}`,{headers})).json();expect(notes).toHaveLength(1);expect((await(await request.get(base+`/notes/${notes[0].id}/citations`,{headers})).json())[0].version_id).toBe(v.id);
});
test('阅读笔记未知结果只重试原请求且不会重复创建',async({page,request})=>{
 const {course,headers}=await setup(page,request);const v=await upload(request,headers,course.id,'未知阅读');const ids:string[]=[];
 await page.route('**/api/v1/notes',async r=>{if(r.request().method()!=='POST')return r.continue();ids.push(r.request().postDataJSON().request_id);const response=await r.fetch();if(ids.length===1)await r.fulfill({status:503,json:{error:{message:'隔离未知结果'}}});else await r.fulfill({response});});
 await page.goto(`/materials?course=${course.id}&document=${v.document_id}&version=${v.id}`);await page.getByRole('button',{name:'阅读笔记',exact:true}).click();await page.getByLabel('阅读时记录理解').fill('不能重复新建的学习理解');await page.getByRole('button',{name:'保存阅读笔记',exact:true}).click();await expect(page.getByLabel('阅读时记录理解')).toBeDisabled();await expect(page.getByRole('button',{name:'重试保存原笔记',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'重试保存原笔记',exact:true}).click();await expect(page.getByRole('button',{name:'打开刚保存的阅读笔记',exact:true})).toBeVisible();expect(ids).toHaveLength(2);expect(ids[0]).toBe(ids[1]);expect((await(await request.get(base+`/notes?course_id=${course.id}`,{headers})).json())).toHaveLength(1);
});
test('阅读引用按Unicode字符截取，表情位于边界仍能逐字核验',async({page,request})=>{
 const {course,headers}=await setup(page,request);const text='甲'.repeat(499)+'🧠'+'乙'.repeat(80);const job=await(await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'unicode.md',mimeType:'text/markdown',buffer:Buffer.from(text)}}})).json();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json()).index_status,{timeout:20000}).toBe('SUCCEEDED');const v=await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
 await page.goto(`/materials?course=${course.id}&document=${v.document_id}&version=${v.id}`);await page.getByRole('button',{name:'阅读笔记',exact:true}).click();await page.getByLabel('阅读时记录理解').fill('字符边界的学习理解');await page.getByLabel('阅读笔记来源片段').selectOption({index:1});await page.getByRole('button',{name:'保存阅读笔记',exact:true}).click();await expect(page.getByRole('button',{name:'打开刚保存的阅读笔记',exact:true})).toBeVisible();
 const notes=await(await request.get(base+`/notes?course_id=${course.id}`,{headers})).json();const citations=await(await request.get(base+`/notes/${notes[0].id}/citations`,{headers})).json();expect(citations[0].quote).toBe('甲'.repeat(499)+'🧠');
});
test('AI资料分页与名称搜索保持已选范围且不自动发送',async({page,request})=>{
 const {course,headers}=await setup(page,request);for(let i=0;i<13;i++)await upload(request,headers,course.id,'资料'+String(i).padStart(2,'0'));
 await page.route('**/api/v1/ai/provider',r=>r.fulfill({json:{configured:true,model:'test-model'}}));let allReads=0,writes=0;page.on('request',r=>{if(r.url().endsWith(`/courses/${course.id}/documents`))allReads++;if(r.method()==='POST'&&/remote-queries|study-reports/.test(r.url()))writes++;});
 await page.goto(`/ai?course=${course.id}&mode=qa`);await page.locator('.ai-scope-picker > summary').first().click();const picker=page.getByRole('region',{name:'分页选择AI资料'}).first();await expect(picker.locator('input[type=checkbox]')).toHaveCount(12);await picker.getByText('资料00',{exact:false}).click();
 await picker.getByRole('button',{name:'下一页资料',exact:true}).click();await expect(picker).toContainText('2 / 2 页');await expect(picker.locator('input:checked')).toHaveCount(1);await picker.getByText('资料12',{exact:false}).click();
 await picker.getByLabel('查找AI资料范围').fill('资料05');await expect(picker).toContainText('1份');await expect(picker.locator('input:checked')).toHaveCount(2);await expect(picker.locator('input[type=checkbox]')).toHaveCount(3);
 await picker.getByLabel('查找AI资料范围').fill('没有匹配');await expect(picker).toContainText('没有匹配的资料');await expect(picker.locator('input:checked')).toHaveCount(2);expect(allReads).toBe(0);expect(writes).toBe(0);
});
test('考点目录只载摘要，翻页展开才读取题干，失败可显式重试',async({page,request})=>{
 const {course,headers}=await setup(page,request);const topic=await(await request.post(base+`/courses/${course.id}/topics`,{headers,data:{name:'并发考点'}})).json();
 const imported=await request.post(base+`/courses/${course.id}/question-bank/import`,{headers,data:{title:'考点题目',content:Array.from({length:25},(_,i)=>`${i+1}. 第${i+1}道题。${'需要展开才读取的正文。'.repeat(12)}\n知识标签：并发考点`).join('\n')}});expect(imported.ok()).toBe(true);
 let details=0;page.on('request',r=>{if(/\/past-questions\/[^/?]+$/.test(r.url())&&r.method()==='GET')details++;});await page.goto(`/exam?course=${course.id}&tab=analysis`);await page.getByRole('button',{name:'并发考点 · 25题',exact:true}).click();expect(topic.id).toBeTruthy();await expect(page.locator('.bank-directory-question')).toHaveCount(20);expect(details).toBe(0);
 await page.getByRole('button',{name:'下一页题目',exact:true}).click();await expect(page.locator('.bank-directory-question')).toHaveCount(5);const item=page.locator('.bank-directory-question').first();
 await page.route('**/api/v1/past-questions/*',r=>r.fulfill({status:503,json:{error:{message:'隔离详情失败'}}}));await item.locator('summary').click();await expect(item.getByRole('button',{name:'重试题目详情',exact:true})).toBeVisible();await page.unroute('**/api/v1/past-questions/*');await item.getByRole('button',{name:'重试题目详情',exact:true}).click();await expect(item.locator('.bank-math')).toContainText('需要展开才读取的正文');expect(details).toBe(2);
});
test('错误地址按需显示告警并可返回资料阅读',async({page,request})=>{
 const {course}=await setup(page,request);await page.goto(`/ai?course=${course.id}&mode=invalid`);await expect(page.getByText('地址中的页面或定位无效，请从导航重新选择。',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'资料学习地址无效',exact:true})).toBeVisible();await page.getByRole('button',{name:'返回资料阅读',exact:true}).click();await expect(page).toHaveURL(/\/materials/);
});
