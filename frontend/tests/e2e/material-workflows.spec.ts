import {test,expect,type APIRequestContext,type Page} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';
async function setup(request:APIRequestContext,page:Page){
  const username='m1_'+crypto.randomUUID().replaceAll('-','');
  const response=await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}});expect(response.status()).toBe(201);
  const auth=await response.json();const headers={Authorization:'Bearer '+auth.access_token};
  const course=await (await request.post(base+'/courses',{headers,data:{name:'M1业务验收'}})).json();
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  return {headers,course};
}
async function imported(request:APIRequestContext,headers:Record<string,string>,courseId:string,name:string,buffer:Buffer){
  const response=await request.post(base+`/courses/${courseId}/documents`,{headers,multipart:{file:{name,mimeType:'application/octet-stream',buffer}}});expect(response.status()).toBe(202);
  const job=await response.json();
  await expect.poll(async()=>{const r=await request.get(base+`/jobs/${job.id}`,{headers});return (await r.json()).status;},{timeout:20_000}).toMatch(/SUCCEEDED|FAILED/);
  return (await (await request.get(base+`/versions/${job.resource_id}`,{headers})).json());
}
test('分页检索全部命中、安全摘要、独立翻页与来源定位',async({page,request})=>{
  const s=await setup(request,page);
  const body=Array.from({length:67},(_,i)=>`# 章节${i}\n${'背景😀。'.repeat(100)}量子协议第${i}项。<img src=x onerror="window.leaked=true">`).join('\n\n');
  const version=await imported(request,s.headers,s.course.id,'all-hits.md',Buffer.from(body));
  await expect.poll(async()=>{return (await (await request.get(base+`/versions/${version.id}`,{headers:s.headers})).json()).index_status;}).toBe('SUCCEEDED');
  for(let i=0;i<17;i++) expect((await request.post(base+'/notes',{headers:s.headers,data:{course_id:s.course.id,title:`检索笔记${i}`,content:'前言。'.repeat(150)+'量子协议笔记。'}})).status()).toBe(201);
  // Knowledge discovery must not fetch every note body or every document.
  const unbounded:string[]=[];page.on('request',r=>{if(/\/notes\?course_id=|\/documents\?$/.test(r.url()))unbounded.push(r.url());});
  await page.goto(`/search?course=${s.course.id}`);
  await page.getByLabel('查找课程资料与笔记').fill('量子协议');await page.getByRole('button',{name:'查找',exact:true}).click();
  await expect(page.getByText('「量子协议」 · 67 个资料片段 · 17 篇笔记',{exact:true})).toBeVisible();
  await expect(page.locator('.search-group').first().locator('.knowledge-hit')).toHaveCount(12);
  await expect(page.locator('.search-group').first().locator('mark').first()).toHaveText('量子协议');
  await expect(page.locator('.search-group img')).toHaveCount(0);expect(await page.evaluate(()=>Reflect.get(window,'leaked'))).toBeUndefined();
  await page.getByLabel('资料结果下一页',{exact:true}).click();
  await expect(page.getByLabel('资料结果分页')).toContainText('13–24 / 67');
  await page.getByLabel('笔记结果下一页',{exact:true}).click();
  await expect(page.getByLabel('笔记结果分页')).toContainText('13–17 / 17');
  await expect(page.getByLabel('资料结果分页')).toContainText('13–24 / 67');
  // Another window can remove hits between page requests: no inverted range.
  const notes=await (await request.get(base+`/courses/${s.course.id}/note-search?q=量子协议&limit=100`,{headers:s.headers})).json();
  for(const note of notes.items.slice(0,15)) expect((await request.delete(base+`/notes/${note.id}`,{headers:s.headers})).status()).toBe(204);
  await page.getByLabel('资料结果上一页',{exact:true}).click();
  await expect(page.getByLabel('笔记结果分页')).toContainText('当前页已无结果，共 2 条');
  await page.getByLabel('笔记结果上一页',{exact:true}).click();
  await expect(page.getByLabel('笔记结果分页')).toContainText('1–2 / 2');
  expect(unbounded).toEqual([]);
  const hit=page.locator('.search-group').first().locator('.knowledge-hit').first();
  const label=await hit.locator('.hit-meta').innerText();expect(label).toContain('v1');
  await hit.click();await expect(page).toHaveURL(new RegExp(`version=${version.id}.*chunk=`));
  await expect(page.locator('.chunk-highlight')).toContainText('量子协议');
});

test('无正文PDF：人工草稿不检索、确认引用、撤回失效',async({page,request})=>{
  const s=await setup(request,page);
  const buffer=await readFile(fileURLToPath(new URL('../../../fixtures/no_text_demo.pdf',import.meta.url)));
  const version=await imported(request,s.headers,s.course.id,'no-text.pdf',buffer);
  expect(version.parse_status).toBe('FAILED');
  await expect.poll(async()=>(await (await request.get(base+`/versions/${version.id}`,{headers:s.headers})).json()).preview_status).toBe('SUCCEEDED');
  const note=await (await request.post(base+'/notes',{headers:s.headers,data:{course_id:s.course.id,title:'补录引用笔记',content:'保留我的理解。'}})).json();
  await page.goto(`/materials?course=${s.course.id}&document=${version.document_id}&version=${version.id}`);
  await page.getByLabel('人工补录正文').fill('人工星图协议需要确认接收。');await page.getByRole('button',{name:'保存草稿',exact:true}).click();
  await expect(page.getByText('草稿已保存，尚未进入检索',{exact:true})).toBeVisible();
  expect((await (await request.get(base+`/courses/${s.course.id}/search/page?q=人工星图协议`,{headers:s.headers})).json()).total).toBe(0);
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'核对并确认',exact:true}).click();
  await expect(page.locator('.reading-paper')).toContainText('人工星图协议需要确认接收。');
  await page.getByLabel('引用到笔记',{exact:true}).selectOption(note.id);
  await page.getByRole('button',{name:'引用到所选笔记',exact:true}).click();
  const citations=await (await request.get(base+`/notes/${note.id}/citations`,{headers:s.headers})).json();expect(citations).toHaveLength(1);expect(citations[0].availability).toBe('active');
  expect((await (await request.get(base+`/courses/${s.course.id}/search/page?q=人工星图协议`,{headers:s.headers})).json()).total).toBe(1);
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'撤回补录',exact:true}).click();
  await expect(page.locator('.transcript-controls')).toContainText('已撤回');
  expect((await (await request.get(base+`/courses/${s.course.id}/search/page?q=人工星图协议`,{headers:s.headers})).json()).total).toBe(0);
  await page.goto(`/notes?course=${s.course.id}&note=${note.id}`);
  await expect(page.locator('.citation-card')).toContainText('不可用');
  expect((await (await request.get(base+`/notes/${note.id}`,{headers:s.headers})).json()).content).toBe('保留我的理解。');
});

test('索引重建不改变引用，浏览器课程删除使文件与检索撤权',async({page,request})=>{
  const s=await setup(request,page);
  const version=await imported(request,s.headers,s.course.id,'retirement.md',Buffer.from('# 原文\n共享撤权协议保留引用身份。'));
  await expect.poll(async()=>(await (await request.get(base+`/versions/${version.id}`,{headers:s.headers})).json()).index_status).toBe('SUCCEEDED');
  const chunks=await (await request.get(base+`/versions/${version.id}/chunks`,{headers:s.headers})).json();
  const note=await (await request.post(base+'/notes',{headers:s.headers,data:{title:'外部保留笔记',content:'不应删除外部正文。',citations:[{version_id:version.id,chunk_id:chunks[0].id,quote:'共享撤权协议'}]}})).json();
  await page.goto(`/materials?course=${s.course.id}&document=${version.document_id}&version=${version.id}`);
  const queued=page.waitForResponse(r=>r.url().endsWith(`/versions/${version.id}/reindex`)&&r.request().method()==='POST');
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'重建索引',exact:true}).click();const response=await queued;expect(response.status()).toBe(202);const job=await response.json();
  await expect.poll(async()=>(await (await request.get(base+`/jobs/${job.id}`,{headers:s.headers})).json()).status).toBe('SUCCEEDED');
  const current=await (await request.get(base+`/versions/${version.id}/chunks`,{headers:s.headers})).json();expect(current.map((c:{id:string})=>c.id)).toEqual(chunks.map((c:{id:string})=>c.id));
  await page.getByRole('button',{name:'课程总览',exact:true}).click();
  await page.getByLabel('整理课程：M1业务验收',{exact:true}).click();
  await page.getByRole('button',{name:'删除课程…',exact:true}).click();
  const remove=page.getByRole('button',{name:'确认删除课程',exact:true});await expect(remove).toBeDisabled();
  await page.getByLabel('输入课程名称确认').fill('错误名称');await expect(remove).toBeDisabled();
  await page.getByLabel('输入课程名称确认').fill(s.course.name);await remove.click();
  await expect(page.getByLabel('整理课程：M1业务验收',{exact:true})).toHaveCount(0);
  for(const suffix of ['original','preview','chunks']) expect((await request.get(base+`/versions/${version.id}/${suffix}`,{headers:s.headers})).status()).toBe(404);
  expect((await request.get(base+`/courses/${s.course.id}/search/page?q=共享撤权协议`,{headers:s.headers})).status()).toBe(404);
  const old=await (await request.get(base+`/notes/${note.id}`,{headers:s.headers})).json();expect(old.content).toBe('不应删除外部正文。');
  const citations=await (await request.get(base+`/notes/${note.id}/citations`,{headers:s.headers})).json();expect(citations[0].availability).toBe('unavailable');
});
