import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import type {PackageCatalog, PackageSelection} from '../../../src/api/client';

const base='http://127.0.0.1:8056/api/v1';
const password='Test-password-2026';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEklEQVR4nGNMCjzGwMDAxAAGABFyAX2FpPujAAAAAElFTkSuQmCC','base64');
const selected=(catalog:PackageCatalog):PackageSelection=>Object.fromEntries([...new Set(catalog.items.map(row=>row.category))].map(category=>[category,catalog.items.filter(row=>row.category===category).map(row=>row.id)]));

async function setup(page:Page,request:APIRequestContext){
  const username='package_'+crypto.randomUUID().replaceAll('-','');
  const registered=await request.post(base+'/auth/register',{data:{username,password}});
  expect(registered.status()).toBe(201);
  const auth=await registered.json(),headers={Authorization:'Bearer '+auth.access_token};
  const create=async(path:string,data:unknown)=>{const response=await request.post(base+path,{headers,data});expect(response.ok(),await response.text()).toBeTruthy();return response.json();};
  const course=await create('/courses',{name:'浏览器标准包课程',category:'隔离测试',tags:['标准包']});
  const folder=await create('/note-folders',{course_id:course.id,name:'协议笔记'});
  const image=await request.post(base+`/courses/${course.id}/assets`,{headers,multipart:{file:{name:'样例.png',mimeType:'image/png',buffer:png}}});
  expect(image.status()).toBe(201);
  const asset=await image.json();
  const b=await create('/notes',{course_id:course.id,title:'B 未归档笔记',content:'# B\n\n此笔记留在根目录。',tags:['自制样例']});
  const a=await create('/notes',{course_id:course.id,folder_id:folder.id,title:'A 图片与双链',content:`# A\n\n![[asset:${asset.id}|样例图片]]\n\n[[note:${b.id}|查看B]]`,tags:['自制样例']});
  await page.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
  const getPackage=async(kind:'course'|'folder')=>{
    const response=await request.get(base+`/courses/${course.id}/packages/catalog?kind=${kind}`,{headers});
    expect(response.status()).toBe(200);
    const catalog:PackageCatalog=await response.json();
    const exported=await request.post(base+'/packages/export',{headers,data:{course_id:course.id,kind,selection:selected(catalog)}});
    expect(exported.status(),await exported.text()).toBe(200);
    return {name:'自制标准包.zip',mimeType:'application/zip',buffer:await exported.body()};
  };
  return {headers,course,folder,asset,a,b,getPackage};
}

async function openImport(page:Page){
  await page.getByRole('button',{name:'导入课程包',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'导入标准数据包',exact:true});
  await expect(dialog).toBeVisible();
  // The uploader waits until the account identity has been checked.
  const input=dialog.getByLabel('选择标准ZIP',{exact:true});
  if(await input.count())await expect(input).toBeEnabled();
  return dialog;
}

test('课程标准包可预览、自选导入，创建新对象并保留原课程',async({page,request})=>{
  const s=await setup(page,request),file=await s.getPackage('course');
  await page.goto('/overview');
  const dialog=await openImport(page);
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  await expect(dialog.getByRole('heading',{name:s.course.name,exact:true})).toBeVisible();
  const before=await request.get(base+'/courses',{headers:s.headers});
  expect((await before.json()).length).toBe(1);
  await dialog.getByLabel('新课程名称',{exact:true}).fill('自选导入的新课程');
  await dialog.getByRole('checkbox',{name:'选择条目：B 未归档笔记',exact:true}).uncheck();
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  const review=dialog.getByRole('region',{name:'标准包确认预览',exact:true});
  await expect(review).toContainText('自选导入的新课程');
  const response=page.waitForResponse(r=>r.url().endsWith('/packages/import')&&r.request().method()==='POST');
  await dialog.getByRole('button',{name:'确认导入所选内容',exact:true}).click();
  const imported=await (await response).json();
  await expect(dialog.getByRole('heading',{name:'导入完成',exact:true})).toBeVisible();
  expect(imported.course_id).not.toBe(s.course.id);
  const notes=await request.get(base+`/notes?course_id=${imported.course_id}`,{headers:s.headers});
  const rows=await notes.json();
  expect(rows).toHaveLength(1);
  expect(rows[0].title).toBe(s.a.title);
  expect(rows[0].content).not.toContain(s.b.id);
  expect(rows[0].content).toContain('查看B');
  expect(rows[0].id).not.toBe(s.a.id);
  const original=await request.get(base+`/notes/${s.a.id}`,{headers:s.headers});
  expect((await original.json()).content).toBe(s.a.content);
});

test('导出按钮生成可回导ZIP，文件名可读，默认全选含未归档',async({page,request},testInfo)=>{
  const s=await setup(page,request);
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('/overview');
  await page.getByRole('button',{name:`导出课程包：${s.course.name}`,exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'导出标准数据包',exact:true});
  await expect(dialog.getByRole('checkbox',{name:'选择条目：B 未归档笔记',exact:true})).toBeChecked();
  await dialog.getByRole('button',{name:'取消全部选择',exact:true}).click();
  await expect(dialog.getByRole('button',{name:'预览所选内容',exact:true})).toBeDisabled();
  await dialog.getByRole('button',{name:'全选可识别内容',exact:true}).click();
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  await dialog.getByRole('button',{name:'确认导出并下载ZIP',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:`../.artifacts/e2e/optional/portable-package-1440-${testInfo.project.name}.png`,fullPage:false});
  const downloaded=page.waitForEvent('download');
  await dialog.getByRole('button',{name:'确认导出并下载ZIP',exact:true}).click();
  const download=await downloaded;
  expect(download.suggestedFilename()).toContain(s.course.name);
  expect(download.suggestedFilename()).toMatch(/\.zip$/);
  const path=await download.path();
  expect(path).toBeTruthy();
  const preview=await request.post(base+'/packages/preview',{headers:s.headers,multipart:{file:{name:download.suggestedFilename(),mimeType:'application/zip',buffer:await readFile(path!)}}});
  expect(preview.status()).toBe(200);
  const content:PackageCatalog=await preview.json();
  expect(content.items.filter(item=>item.category==='notes').map(item=>item.title).sort()).toEqual([s.a.title,s.b.title].sort());
});

test('文件夹包导入已有课程根目录，图片和内部双链可用',async({page,request})=>{
  const s=await setup(page,request),file=await s.getPackage('folder');
  const targetResponse=await request.post(base+'/courses',{headers:s.headers,data:{name:'接收笔记的已有课程'}});
  const target=await targetResponse.json();
  await page.goto('/overview');
  const dialog=await openImport(page);
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  await dialog.getByRole('combobox',{name:'标准包目标课程',exact:true}).selectOption(target.id);
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  await dialog.getByRole('button',{name:'确认导入所选内容',exact:true}).click();
  await expect(dialog.getByRole('heading',{name:'导入完成',exact:true})).toBeVisible();
  const response=await request.get(base+`/notes?course_id=${target.id}`,{headers:s.headers}),notes=await response.json();
  expect(notes).toHaveLength(2);
  const a=notes.find((n:{title:string})=>n.title===s.a.title),b=notes.find((n:{title:string})=>n.title===s.b.title);
  expect(b.folder_id).toBeNull();
  expect(a.content).toContain(`[[note:${b.id}|`);
  const assetId=/!\[\[asset:([a-f0-9-]+)/.exec(a.content)?.[1];
  expect(assetId).toBeTruthy();
  expect(assetId).not.toBe(s.asset.id);
  expect((await request.get(base+`/assets/${assetId}`,{headers:s.headers})).status()).toBe(200);
});

test('课程包合并进已有课程，自选内容且不覆盖目标信息和同名笔记',async({page,request})=>{
  const s=await setup(page,request),file=await s.getPackage('course');
  const targetResponse=await request.post(base+'/courses',{headers:s.headers,data:{name:'合并接收课程',description:'原介绍',category:'原分类',tags:['保留标签']}});
  const target=await targetResponse.json();
  const oldResponse=await request.post(base+'/notes',{headers:s.headers,data:{course_id:target.id,title:s.a.title,content:'这篇同名笔记不可覆盖'}});
  const old=await oldResponse.json();
  await page.goto('/overview');
  const dialog=await openImport(page);
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  await dialog.getByRole('radio',{name:'合并到已有课程',exact:true}).check();
  await dialog.getByRole('combobox',{name:'标准包目标课程',exact:true}).selectOption(target.id);
  await dialog.getByRole('checkbox',{name:'选择条目：B 未归档笔记',exact:true}).uncheck();
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  await expect(dialog.getByRole('region',{name:'标准包确认预览',exact:true})).toContainText('合并到：合并接收课程');
  await dialog.getByRole('button',{name:'确认导入所选内容',exact:true}).click();
  await expect(dialog.getByRole('heading',{name:'导入完成',exact:true})).toBeVisible();
  const courses=await (await request.get(base+'/courses',{headers:s.headers})).json();
  expect(courses).toHaveLength(2);
  expect(courses.find((row:{id:string})=>row.id===target.id)).toMatchObject({name:'合并接收课程',description:'原介绍',category:'原分类',tags:['保留标签']});
  const notes=await (await request.get(base+`/notes?course_id=${target.id}`,{headers:s.headers})).json();
  expect(notes).toHaveLength(2);
  expect(notes.find((row:{id:string})=>row.id===old.id).content).toBe('这篇同名笔记不可覆盖');
  const added=notes.find((row:{id:string})=>row.id!==old.id);
  expect(added.title).toBe(s.a.title);
  expect(added.content).not.toContain(s.b.id);
});

test('提交响应丢失后冻结范围，核对成功记录不重复创建',async({page,request})=>{
  const s=await setup(page,request),file=await s.getPackage('course');
  await page.goto('/overview');
  const dialog=await openImport(page);
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  let submissions=0;
  await page.route('**/api/v1/packages/import',async route=>{
    submissions++;
    const response=await route.fetch();
    expect(response.status()).toBe(200);
    await route.abort('failed');
  });
  await dialog.getByRole('button',{name:'确认导入所选内容',exact:true}).click();
  await expect(dialog).toContainText('上次导入结果尚未确认');
  await expect(dialog.getByRole('checkbox',{name:'选择条目：B 未归档笔记',exact:true})).toBeDisabled();
  await dialog.getByRole('button',{name:'核对导入结果',exact:true}).click();
  await expect(dialog.getByRole('heading',{name:'导入完成',exact:true})).toBeVisible();
  expect(submissions).toBe(1);
  expect((await (await request.get(base+'/courses',{headers:s.headers})).json()).length).toBe(2);
});

test('错误包拒绝，取消预览不创建业务，390px可操作且无横向溢出',async({page,request},testInfo)=>{
  const s=await setup(page,request),file=await s.getPackage('course');
  await page.setViewportSize({width:390,height:844});
  await page.goto('/overview');
  let dialog=await openImport(page);
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles({name:'损坏.zip',mimeType:'application/zip',buffer:Buffer.from('this is not a zip')});
  await expect(dialog.getByRole('alert')).toBeVisible();
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  await expect(dialog.getByRole('heading',{name:s.course.name,exact:true})).toBeVisible();
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  await expect(dialog.getByRole('button',{name:'确认导入所选内容',exact:true})).toBeEnabled();
  expect(await dialog.evaluate(element=>element.scrollWidth<=element.clientWidth+1)).toBeTruthy();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
  await dialog.getByRole('button',{name:'确认导入所选内容',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:`../.artifacts/e2e/optional/portable-package-390-${testInfo.project.name}.png`,fullPage:false});
  await dialog.getByRole('button',{name:'关闭导入标准数据包',exact:true}).click();
  expect((await (await request.get(base+'/courses',{headers:s.headers})).json()).length).toBe(1);
  dialog=await openImport(page);
  await expect(dialog).toBeVisible();
  expect((await (await request.get(base+'/courses',{headers:s.headers})).json()).length).toBe(1);
});

test('导入401关闭窗口，重新打开不自动重放写请求',async({page,request})=>{
  const s=await setup(page,request),file=await s.getPackage('course');
  await page.goto('/overview');
  const dialog=await openImport(page);
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  let submissions=0;
  await page.route('**/api/v1/packages/import',route=>{submissions++;return route.fulfill({status:401,json:{error:{message:'登录已过期'}}});});
  await dialog.getByRole('button',{name:'确认导入所选内容',exact:true}).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();
  await page.getByLabel('密码',{exact:true}).fill(password);
  await page.getByRole('button',{name:'登录',exact:true}).click();
  await expect(page.getByRole('button',{name:'导入课程包',exact:true})).toBeVisible();
  await openImport(page);
  await page.waitForTimeout(200);
  expect(submissions).toBe(1);
});

test('刷新后仍能管理并删除遗留文件预览',async({page,request})=>{
  const s=await setup(page,request),file=await s.getPackage('course');
  await page.goto('/overview');
  let dialog=await openImport(page);
  const response=page.waitForResponse(r=>r.url().endsWith('/packages/preview')&&r.request().method()==='POST');
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  const preview=await (await response).json();
  await expect(dialog.getByRole('heading',{name:s.course.name,exact:true})).toBeVisible();
  await page.reload();
  dialog=await openImport(page);
  await dialog.getByRole('button',{name:'管理已上传的预览',exact:true}).click();
  const list=dialog.getByRole('list',{name:'已上传预览列表',exact:true});
  await expect(list).toContainText(preview.preview_id);
  await list.getByRole('button',{name:`删除预览：${preview.preview_id}`,exact:true}).click();
  await list.getByRole('button',{name:'确认删除预览',exact:true}).click();
  await expect(dialog).toContainText('没有保留的文件预览。');
  expect((await (await request.get(base+'/packages/previews',{headers:s.headers})).json())).toEqual([]);
  expect((await (await request.get(base+'/courses',{headers:s.headers})).json()).length).toBe(1);
});

test('未确认导入遇到401后仍允许退出账户',async({page,request})=>{
  const s=await setup(page,request),file=await s.getPackage('course');
  await page.goto('/overview');
  const dialog=await openImport(page);
  await dialog.getByLabel('选择标准ZIP',{exact:true}).setInputFiles(file);
  await dialog.getByRole('button',{name:'预览所选内容',exact:true}).click();
  await page.route('**/api/v1/packages/import',route=>route.fulfill({status:401,json:{error:{message:'登录已过期'}}}));
  await dialog.getByRole('button',{name:'确认导入所选内容',exact:true}).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole('button',{name:'退出账户（离开前检查未保存内容）',exact:true}).click();
  await expect(page.getByRole('button',{name:'退出账户（离开前检查未保存内容）',exact:true})).not.toBeVisible();
  await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('hustudy_token'))).toBeNull();
});
