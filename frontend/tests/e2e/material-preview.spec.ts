import {test,expect,type APIRequestContext,type Page} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';
async function sample(request:APIRequestContext,page:Page,ext:string) {
  const username='preview_'+crypto.randomUUID().replaceAll('-','');
  const auth=await (await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await (await request.post(base+'/courses',{headers,data:{name:'原页预览验收'}})).json();
  const bytes=await readFile(fileURLToPath(new URL(`../../../fixtures/preview_demo.${ext}`,import.meta.url)));
  const uploaded=await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'preview.'+ext,mimeType:'application/octet-stream',buffer:bytes}}});expect(uploaded.status()).toBe(202);
  const job=await uploaded.json();
  await expect.poll(async()=>{const r=await request.get(base+`/versions/${job.resource_id}`,{headers});return (await r.json()).preview_status;},{timeout:35_000}).toBe('SUCCEEDED');
  const version=await (await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  await page.goto(`/materials?course=${course.id}&document=${version.document_id}&version=${version.id}`);
  return {course,version,headers};
}
for(const ext of ['pdf','pptx','docx']) test(`${ext} 真实原页预览与截图来源`,async({request,page})=>{
  test.setTimeout(75_000);
  const pageErrors:string[]=[];page.on('pageerror',error=>pageErrors.push(error.message));
  // Reproduce the actual Safari failure: modern Map upsert APIs are absent.
  await page.addInitScript(()=>{Reflect.deleteProperty(Map.prototype,'getOrInsertComputed');Reflect.deleteProperty(WeakMap.prototype,'getOrInsertComputed');});
  const s=await sample(request,page,ext);
  await page.getByRole('button',{name:ext==='pdf'?'PDF 预览':'兼容预览（PDF）',exact:true}).click();
  const canvas=page.locator('.pdf-canvas-stage canvas');await expect(canvas).toBeVisible({timeout:20_000});
  const original=await canvas.evaluate(node=>(node as HTMLCanvasElement).toDataURL());
  const desired=ext==='docx'?1:2;
  if(desired===2){await page.getByRole('region',{name:'PDF 按页阅读'}).getByRole('button',{name:'下一页',exact:true}).click();await expect(canvas).toHaveAttribute('aria-label',/2$/);expect(await canvas.evaluate(node=>(node as HTMLCanvasElement).toDataURL())).not.toBe(original);}
  await page.getByRole('button',{name:'保存当前页图片',exact:true}).click();
  await expect(page.getByText('已保存到课程图片，可在笔记工具栏插入。',{exact:true})).toBeVisible();
  const assets=await (await request.get(base+`/courses/${s.course.id}/assets`,{headers:s.headers})).json();
  expect(assets).toHaveLength(1);expect(assets[0].source_version_id).toBe(s.version.id);expect(assets[0].source_page).toBe(desired);
  expect(assets[0].source_locator_type).toBe(ext==='docx'?'preview_page':ext==='pptx'?'slide':'page');
  await page.getByRole('button',{name:'返回文本与引用',exact:true}).click();
  await page.getByRole('button',{name:'回到原页',exact:true}).click();
  await expect(canvas).toHaveAttribute('aria-label',new RegExp(desired+'$'));expect(pageErrors).toEqual([]);
});
