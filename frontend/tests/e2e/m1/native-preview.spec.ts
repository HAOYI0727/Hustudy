import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';
for(const kind of ['pptx','docx'] as const) test(`${kind} 直接原格式预览、分页样式与隔离`,async({page,request})=>{
  const username='native_'+crypto.randomUUID().replaceAll('-','');
  const auth=await (await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await (await request.post(base+'/courses',{headers,data:{name:'原格式预览验收'}})).json();
  const bytes=await readFile(fileURLToPath(new URL(`../../../../fixtures/native_preview.${kind}`,import.meta.url)));
  const uploaded=await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:`native.${kind}`,mimeType:'application/octet-stream',buffer:bytes}}});expect(uploaded.status()).toBe(202);
  const job=await uploaded.json();
  const version=await (await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
  await page.addInitScript(({token,username})=>{if(window===window.top){localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);}Reflect.deleteProperty(Map.prototype,'getOrInsertComputed');},{token:auth.access_token,username});
  const outbound:string[]=[];
  page.on('request',req=>{if(req.url().startsWith('https://'))outbound.push(req.url());});
  // Prove this path never downloads or renders a converted PDF.
  let pdfReads=0;await page.route('**/api/v1/versions/*/preview',route=>{pdfReads++;return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:{message:'PDF conversion unavailable in direct-preview test'}})});});
  let releaseText=false;
  await page.route(`**/api/v1/versions/${version.id}/chunks`,route=>releaseText?route.continue():route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.goto(`/materials?course=${course.id}&document=${version.document_id}&version=${version.id}`);
  const label=kind==='pptx'?'PPT':'Word';
  await page.getByRole('button',{name:label+' 预览',exact:true}).click();
  const region=page.getByRole('region',{name:label+' 原格式阅读'});
  await expect(region).toHaveAttribute('aria-busy','false',{timeout:30_000});
  await expect(region.getByRole('alert')).toHaveCount(0);
  const iframe=region.locator('iframe');await expect(iframe).toHaveAttribute('sandbox','allow-scripts');
  const inner=page.frameLocator(`iframe[title="${label}原文件预览"]`);
  await expect(inner.getByText(kind==='pptx'?'Native PPTX Slide 1':'Native DOCX Page 1',{exact:true})).toBeVisible();
  await expect(inner.locator('table')).toBeVisible();
  await expect(inner.locator('img').first()).toBeVisible();
  // Emulate text arriving after the original-format reader has already opened.
  await expect.poll(async()=>(await (await request.get(base+`/versions/${version.id}`,{headers})).json()).index_status).toBe('SUCCEEDED');
  releaseText=true;
  const refreshed=page.waitForResponse(r=>r.url().endsWith(`/versions/${version.id}/chunks`));
  await page.getByLabel('刷新资料与处理状态',{exact:true}).click();await refreshed;
  await expect(inner.getByText(kind==='pptx'?'Native PPTX Slide 1':'Native DOCX Page 1',{exact:true})).toBeVisible();
  const secure=await inner.locator('body').evaluate(()=>{try{void parent.localStorage;return false;}catch{return true;}});expect(secure).toBe(true);
  const blocked=await inner.locator('body').evaluate(async()=>{try{await fetch('https://preview.invalid/network-probe');return false;}catch{return true;}});expect(blocked).toBe(true);
  const channel=await inner.locator('html').getAttribute('data-channel');
  await page.evaluate(channel=>window.postMessage({channel,type:'state',page:999,count:999},'*'),channel);
  await expect(region.locator('.pdf-page-controls')).toContainText('/ 2');
  await page.screenshot({path:test.info().outputPath(`native-${kind}-page1.png`),fullPage:true});
  // The source format keeps its own typography while its outer reader fits touch widths.
  for(const width of [390,820,1280]){
    await page.setViewportSize({width,height:900});
    await iframe.scrollIntoViewIfNeeded();
    await expect(inner.getByText(kind==='pptx'?'Native PPTX Slide 1':'Native DOCX Page 1',{exact:true})).toBeInViewport();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
    const bounds=await iframe.boundingBox();expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(width+1);
    if(width===390)await iframe.screenshot({path:test.info().outputPath(`native-${kind}-mobile.png`),animations:'disabled'});
  }
  await region.getByRole('button',{name:kind==='pptx'?'下一幻灯片':'下一阅读页',exact:true}).click();
  await expect(inner.getByText(kind==='pptx'?'Native PPTX Slide 2':'Native DOCX Page 2',{exact:true})).toBeVisible();
  await expect(region.getByLabel(`${label}${kind==='pptx'?'幻灯片':'阅读页'}序号`)).toHaveValue('2');
  await region.getByLabel(label+'预览缩放').selectOption('125');await expect(region).toHaveAttribute('aria-busy','false');
  if(kind==='pptx'){
    await region.getByRole('button',{name:'演示模式',exact:true}).click();await expect(region).toHaveClass(/native-presentation/);
    await page.keyboard.press('Escape');await expect(region).not.toHaveClass(/native-presentation/);
  }else{
    await expect(inner.locator('script').filter({hasText:'window.previewInjected'})).toHaveCount(0);
    expect(await inner.locator('body').evaluate(()=>Reflect.get(window,'previewInjected'))).toBeUndefined();
  }
  expect(outbound).toEqual([]);expect(pdfReads).toBe(0);
  await page.getByRole('button',{name:'返回文本与引用',exact:true}).click();await expect(iframe).toHaveCount(0);
});

test('原格式渲染失败显式重试，不伪装为成功或偷偷转PDF',async({page,request})=>{
  const username='native_retry_'+crypto.randomUUID().replaceAll('-','');
  const auth=await (await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
  const headers={Authorization:'Bearer '+auth.access_token};
  const course=await (await request.post(base+'/courses',{headers,data:{name:'失败恢复预览'}})).json();
  const bytes=await readFile(fileURLToPath(new URL('../../../../fixtures/native_preview.docx',import.meta.url)));
  const job=await (await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:'retry.docx',mimeType:'application/octet-stream',buffer:bytes}}})).json();
  const version=await (await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
  await page.addInitScript(({token,username})=>{if(window===window.top){localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);}},{token:auth.access_token,username});
  let reads=0,pdfReads=0,corrupted=true;
  await page.route(`**/api/v1/versions/${version.id}/original`,async route=>{reads++;if(corrupted)await route.fulfill({status:200,body:'invalid zip bytes'});else await route.continue();});
  await page.route('**/api/v1/versions/*/preview',route=>{pdfReads++;return route.abort();});
  await page.goto(`/materials?course=${course.id}&document=${version.document_id}&version=${version.id}`);
  await page.getByRole('button',{name:'Word 预览',exact:true}).click();
  const region=page.getByRole('region',{name:'Word 原格式阅读'});
  await expect(region.getByRole('alert')).toContainText('原格式预览未能完成');
  await expect(region.locator('iframe')).toHaveCount(0);
  const failedReads=reads;corrupted=false;await region.getByRole('button',{name:'重试原格式预览',exact:true}).click();
  await expect(page.frameLocator('iframe[title="Word原文件预览"]').getByText('Native DOCX Page 1',{exact:true})).toBeVisible({timeout:25_000});
  expect(reads).toBeGreaterThan(failedReads);expect(pdfReads).toBe(0);
});
