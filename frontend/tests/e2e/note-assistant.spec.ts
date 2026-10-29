import {test,expect,type Page,type APIRequestContext} from '@playwright/test';
import {resolve} from 'node:path';
const base='http://127.0.0.1:8056/api/v1';
const password='Test-password-2026';
async function setup(page:Page,request:APIRequestContext,models=true){
  const username='assistant_'+crypto.randomUUID().replaceAll('-','');
  const auth=await(await request.post(base+'/auth/register',{data:{username,password}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await(await request.post(base+'/courses',{headers,data:{name:'笔记AI与专注目录验收'}})).json();
  const content='# 事务隔离\n\n事务隔离使并发操作互不干扰。\n\n## 自测\n\n解释隔离和原子性的差别。';
  const note=await(await request.post(base+'/notes',{headers,data:{course_id:course.id,title:'原始笔记',content}})).json();
  let profile:any;
  if(models){const saved=await(await request.put(base+'/model-connections',{headers,data:{revision:0,name:'DeepSeek验收',vendor:'deepseek',endpoint:'https://api.deepseek.com/chat/completions',model:'deepseek-flash',key:'synthetic-browser-model-key',vision:false,thinking:false,json_mode:true}})).json();profile=saved.profiles[0];
    expect((await request.post(base+'/model-connections/active',{headers,data:{revision:saved.revision,profile_id:profile.id}})).ok()).toBe(true);}
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  return {headers,course,note,content,profile};
}
async function shot(page:Page,name:string){if(process.env.HUSTUDY_NOTE_READING_EVIDENCE)await page.screenshot({path:resolve('../.tools/'+name+'.png'),animations:'disabled'});}

for(const width of [390,1440])test(`专注目录跨笔记/文件夹/课程与分页，取消切换保留草稿 ${width}px`,async({page,request},info)=>{
  test.setTimeout(120000);await page.setViewportSize({width,height:1000});const s=await setup(page,request,false);
  const folder=await(await request.post(base+'/note-folders',{headers:s.headers,data:{course_id:s.course.id,name:'复习'}})).json();
  const child=await(await request.post(base+'/note-folders',{headers:s.headers,data:{course_id:s.course.id,name:'重点',parent_id:folder.id}})).json();
  const target=await(await request.post(base+'/notes',{headers:s.headers,data:{course_id:s.course.id,folder_id:child.id,title:'目录目标',content:'# 目录目标正文\n\n保持专注窗口。'}})).json();
  for(let index=0;index<30;index++)await request.post(base+'/notes',{headers:s.headers,data:{course_id:s.course.id,title:'分页笔记'+String(index).padStart(2,'0'),content:'分页内容'}});
  const other=await(await request.post(base+'/courses',{headers:s.headers,data:{name:'另一门课程'}})).json();
  const cross=await(await request.post(base+'/notes',{headers:s.headers,data:{course_id:other.id,title:'跨课程阅读',content:'# 另一课程正文'}})).json();
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  const editor=page.getByLabel('Markdown 正文');await expect(editor).toHaveValue(s.content);
  await editor.fill(s.content+'\n\n未保存理解。');
  await page.getByRole('button',{name:'阅读模式',exact:true}).click();await page.getByRole('button',{name:'专注阅读',exact:true}).click();
  const focus=page.getByRole('dialog',{name:'专注阅读',exact:true});await expect(focus).toBeVisible();
  const library=focus.getByRole('region',{name:'专注笔记列表',exact:true});
  await expect(library).toContainText('32 篇');await library.getByRole('button',{name:'下一页笔记',exact:true}).click();await expect(library).toContainText('第 2 / 2 页');
  await library.getByLabel('阅读文件夹范围').selectOption(folder.id);await expect(library.getByRole('navigation',{name:'阅读笔记导航'}).getByRole('button')).toHaveCount(1);
  page.once('dialog',d=>d.dismiss());await library.getByRole('button',{name:/^目录目标/}).click();await expect(focus).toBeVisible();await expect(focus.getByRole('article')).toContainText('未保存理解');
  page.once('dialog',d=>d.accept());await library.getByRole('button',{name:/^目录目标/}).click();await expect(focus.getByRole('article')).toContainText('目录目标正文');await expect(focus).toBeVisible();
  await library.getByLabel('阅读课程范围').selectOption('');await library.getByLabel('查找阅读笔记').fill('跨课程');
  await library.getByRole('button',{name:/^跨课程阅读/}).click();await expect(focus.getByRole('article')).toContainText('另一课程正文');await expect(focus).toBeVisible();
  await expect(focus.locator('.note-reader-heading')).toContainText(cross.title);
  expect(await focus.evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);
  await shot(page,`focus-library-${width}-${info.project.name}`);
  await page.keyboard.press('Escape');await expect(focus).not.toBeVisible();
  expect((await(await request.get(base+'/notes/'+s.note.id,{headers:s.headers})).json()).content).toBe(s.content);
  expect((await(await request.get(base+'/notes/'+target.id,{headers:s.headers})).json()).revision).toBe(1);
});

for(const width of [390,1440])test(`笔记助手选文预览/确认/采纳/撤销，五类任务与默认手动保存 ${width}px`,async({page,request},info)=>{
  test.setTimeout(90000);await page.setViewportSize({width,height:1000});const s=await setup(page,request);
  let calls=0;const sent:any[]=[];const answer='## AI建议\n\n隔离控制并发事务的相互影响。\n\n- [ ] 对比例子并复习';
  await page.route('**/api/v1/note-assistant/generate',async route=>{calls++;sent.push(route.request().postDataJSON());await route.fulfill({status:200,json:{request_id:crypto.randomUUID(),markdown:answer,model:'deepseek-flash',task:'解释内容',usage:{total_tokens:50},notice:'AI建议'}});});
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);const editor=page.getByLabel('Markdown 正文');await expect(editor).toHaveValue(s.content);
  await expect(page.getByLabel('自动保存笔记')).not.toBeChecked();await editor.focus();
  const selected='事务隔离使并发操作互不干扰。';const start=s.content.indexOf(selected);await editor.evaluate((el:HTMLTextAreaElement,{start,length})=>el.setSelectionRange(start,start+length),{start,length:selected.length});
  await page.getByRole('button',{name:'笔记AI助手',exact:true}).click();const dialog=page.getByRole('dialog',{name:'笔记AI助手',exact:true});
  await expect(dialog.getByLabel('笔记AI发送范围')).toHaveValue('selection');
  for(const task of ['summary','explain','organize','review','custom']){
    await dialog.getByLabel('笔记AI任务').selectOption(task);if(task==='custom')await dialog.getByLabel('笔记AI补充要求').fill('用比喻解释');
    await dialog.getByRole('button',{name:'预览发送内容',exact:true}).click();
    const preview=dialog.getByRole('region',{name:'笔记AI发送预览'});await expect(preview).toContainText('deepseek-flash');
    await expect(dialog.getByRole('button',{name:'确认发送并生成',exact:true})).toBeDisabled();expect(calls).toBe(0);
  }
  await dialog.getByLabel('同意发送笔记文本').check();await dialog.getByRole('button',{name:'确认发送并生成',exact:true}).click();
  await expect(dialog.getByRole('region',{name:'笔记AI建议'})).toContainText('隔离控制并发事务');expect(calls).toBe(1);expect(sent[0].input.text).toBe(selected);expect(sent[0].confirm).toBe(true);
  await expect(editor).toHaveValue(s.content);await shot(page,`note-assistant-${width}-${info.project.name}`);
  await dialog.getByRole('button',{name:'追加到笔记末尾',exact:true}).click();await expect(dialog).not.toBeVisible();await expect(editor).toHaveValue(s.content+'\n\n'+answer);
  expect((await(await request.get(base+'/notes/'+s.note.id,{headers:s.headers})).json()).revision).toBe(1);
  await editor.focus();await page.keyboard.press('Control+z');await expect(editor).toHaveValue(s.content);
  await page.keyboard.press('Control+y');await expect(editor).toHaveValue(s.content+'\n\n'+answer);
  await page.getByRole('button',{name:'立即保存',exact:true}).click();await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const saved=await(await request.get(base+'/notes/'+s.note.id,{headers:s.headers})).json();expect(saved.revision).toBe(2);expect(saved.content).toBe(s.content+'\n\n'+answer);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

test('其他模型配置与原智谱页面并存，选择/测试不泄露密钥',async({page,request},info)=>{
  const s=await setup(page,request,false);await page.goto('/api-connect');await expect(page.getByLabel('智谱API Key',{exact:true})).toBeVisible();
  const advanced=page.getByRole('region',{name:'高级模型接入',exact:true});await advanced.getByLabel('模型配置名称').fill('DeepSeek新增验收');await advanced.getByLabel('其他模型API Key').fill('synthetic-ui-model-secret');
  await advanced.getByRole('button',{name:'保存其他模型配置',exact:true}).click();await expect(advanced.getByLabel('其他模型API Key')).toHaveValue('');
  const row=advanced.locator('.model-profile-list article').filter({hasText:'DeepSeek新增验收'});await row.getByRole('button',{name:'使用此模型',exact:true}).click();await expect(row).toContainText('正在使用');
  const config=await(await request.get(base+'/model-connections',{headers:s.headers})).json();expect(config.active).toBeTruthy();expect(JSON.stringify(config)).not.toContain('synthetic-ui-model-secret');
  expect((await(await request.get(base+'/api-connection',{headers:s.headers})).json()).configured).toBe(false);
  let probes=0;await page.route('**/api/v1/model-connections/test',async route=>{probes++;expect(route.request().postDataJSON().confirm).toBe(true);await route.fulfill({status:200,json:{connected:true,model:'deepseek-flash',message:'隔离测试成功'}});});
  await expect(advanced.getByRole('button',{name:'测试所选模型',exact:true})).toBeDisabled();await advanced.getByRole('checkbox',{name:/同意发送极短/}).check();await advanced.getByRole('button',{name:'测试所选模型',exact:true}).click();await expect(advanced).toContainText('连接成功');expect(probes).toBe(1);
  expect(await page.evaluate(()=>JSON.stringify(localStorage))).not.toContain('synthetic-ui-model-secret');await shot(page,`model-config-${info.project.name}`);
});

test('关闭等待中的笔记AI拒绝迟到结果，401让出登录且草稿保留',async({page,request})=>{
  const s=await setup(page,request);await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);const editor=page.getByLabel('Markdown 正文');await expect(editor).toHaveValue(s.content);
  const draft=s.content+'\n\n保留的草稿。';await editor.fill(draft);let release!:()=>void;const gate=new Promise<void>(r=>{release=r;});let started=false;
  await page.route('**/api/v1/note-assistant/generate',async route=>{started=true;await gate;await route.fulfill({status:200,json:{request_id:'late',markdown:'不应插入的迟到内容',model:'deepseek-flash',task:'摘要',usage:{},notice:'AI'}}).catch(()=>{});});
  const open=async()=>{await page.getByRole('button',{name:'笔记AI助手',exact:true}).click();const dialog=page.getByRole('dialog',{name:'笔记AI助手',exact:true});await dialog.getByRole('button',{name:'预览发送内容',exact:true}).click();await dialog.getByLabel('同意发送笔记文本').check();await dialog.getByRole('button',{name:'确认发送并生成',exact:true}).click();return dialog;};
  try{const dialog=await open();await expect.poll(()=>started).toBe(true);await dialog.getByRole('button',{name:'关闭笔记AI助手',exact:true}).click();release();await expect(editor).toHaveValue(draft);await expect(page.getByRole('region',{name:'笔记AI建议'})).toHaveCount(0);
    await page.unroute('**/api/v1/note-assistant/generate');await page.route('**/api/v1/note-assistant/generate',route=>route.fulfill({status:401,json:{error:{message:'测试会话过期'}}}));await open();
    await expect(page.getByRole('dialog',{name:/登录已过期/})).toBeVisible();await expect(page.locator('dialog[open]')).toHaveCount(0);await expect(editor).toHaveValue(draft);
    expect((await(await request.get(base+'/notes/'+s.note.id,{headers:s.headers})).json()).revision).toBe(1);
  }finally{release();}
});
