import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
const password='Test-password-2026';
async function account(request:APIRequestContext){
  const username='e2e_'+crypto.randomUUID().replaceAll('-','');
  const response=await request.post(base+'/auth/register',{data:{username,password}});expect(response.status()).toBe(201);
  const auth=await response.json();return {username,token:auth.access_token,headers:{Authorization:'Bearer '+auth.access_token}};
}
async function seed(request:APIRequestContext){
  const user=await account(request);
  const course=await (await request.post(base+'/courses',{headers:user.headers,data:{name:'端到端验收课程',description:'自制测试资料'}})).json();
  const upload=await request.post(base+`/courses/${course.id}/documents`,{headers:user.headers,multipart:{file:{name:'e2e.md',mimeType:'text/markdown',buffer:Buffer.from('# 缓冲区\n缓冲区用于暂存传输的数据。')}}});
  expect(upload.status()).toBe(202);const result=await upload.json();
  const versionId=result.resource_id;
  const version=await (await request.get(base+`/versions/${versionId}`,{headers:user.headers})).json();
  await expect.poll(async()=>{const r=await request.get(base+`/versions/${versionId}`,{headers:user.headers});return (await r.json()).index_status;},{timeout:20_000}).toBe('SUCCEEDED');
  const chunks=await (await request.get(base+`/versions/${versionId}/chunks`,{headers:user.headers})).json();
  const note=await (await request.post(base+'/notes',{headers:user.headers,data:{course_id:course.id,title:'已保存的原笔记',content:'服务器原文'}})).json();
  return {...user,course,versionId,doc:{id:version.document_id},chunk:chunks[0],note};
}
async function signedIn(page:Page,user:{token:string;username:string}){
  await page.addInitScript(user=>{localStorage.setItem('hustudy_token',user.token);localStorage.setItem('hustudy_user',user.username);},user);
}
test('真实 API：登录、建课、上传、解析阅读与课程搜索',async({page,request})=>{
  const user=await account(request);await page.goto('/');
  await page.getByLabel('用户名',{exact:true}).fill(user.username);await page.getByLabel('密码',{exact:true}).fill(password);
  await page.getByRole('button',{name:'登录',exact:true}).click();
  await page.getByLabel('课程名称',{exact:true}).fill('浏览器建课');await page.getByRole('button',{name:'创建课程',exact:true}).click();
  await expect(page.getByRole('heading',{name:'浏览器建课',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'资料阅读',exact:true}).click();
  await page.getByLabel('选择课程文件').setInputFiles({name:'阅读测试.md',mimeType:'text/markdown',buffer:Buffer.from('# 传输\n传输层提供端到端通信。')});
  await page.getByRole('button',{name:'上传并开始整理'}).click();
  await expect(page.locator('.reading-paper')).toContainText('传输层提供端到端通信。',{timeout:20_000});
  await page.getByRole('button',{name:'课程查找',exact:true}).click();
  await page.getByLabel('查找课程资料与笔记').fill('通信');
  await page.getByRole('button',{name:'查找',exact:true}).click();
  await expect(page.locator('.search-group').first()).toContainText('传输层提供端到端通信。');
});
test('历史来源深链接刷新、前后退与离开草稿确认',async({page,request})=>{
  const s=await seed(request);await signedIn(page,s);
  const material=`/materials?course=${s.course.id}&document=${s.doc.id}&version=${s.versionId}&chunk=${s.chunk.id}`;
  await page.goto(material);await expect(page.locator('.reading-paper')).toContainText('缓冲区用于暂存传输的数据。');
  await page.reload();await expect(page.locator('.chunk-highlight')).toContainText('暂存传输');
  await page.getByRole('button',{name:'知识笔记',exact:true}).click();await expect(page).toHaveURL(/\/notes\?course=/);
  await page.goBack();await expect(page.locator('.chunk-highlight')).toContainText('暂存传输');
  await page.goForward();await expect(page.getByLabel('笔记标题')).toBeVisible();
  // An untitled draft does not autosave and must survive a cancelled route change.
  await page.getByLabel('Markdown 正文').fill('尚未保存的正文');
  page.once('dialog',dialog=>dialog.dismiss());await page.getByRole('button',{name:'资料阅读',exact:true}).click();
  await expect(page).toHaveURL(/\/notes\?course=/);await expect(page.getByLabel('Markdown 正文')).toHaveValue('尚未保存的正文');
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'资料阅读',exact:true}).click();
  await expect(page).toHaveURL(/\/materials\?course=/);
});
test('401 原账户重新登录保留指定笔记草稿且不自动重放保存',async({page,request})=>{
  const s=await seed(request);await signedIn(page,s);
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('服务器原文');
  // Make save fail with an expired session while the underlying editor stays mounted.
  let writes=0;
  await page.route(`**/api/v1/notes/${s.note.id}`,async route=>{
    if(route.request().method()==='PATCH'){writes++;await route.fulfill({status:401,contentType:'application/json',body:JSON.stringify({error:{message:'登录已过期'}})});}else await route.continue();
  });
  await page.getByLabel('Markdown 正文').fill('必须保留的本地草稿');await page.getByRole('button',{name:'立即保存',exact:true}).click();
  const modal=page.getByRole('dialog');await expect(modal).toBeVisible();
  await expect(modal.getByLabel('用户名',{exact:true})).toHaveValue(s.username);await expect(modal.getByLabel('用户名',{exact:true})).toHaveAttribute('readonly','');
  await modal.getByLabel('密码',{exact:true}).fill(password);await modal.getByRole('button',{name:'登录',exact:true}).click();
  await expect(modal).not.toBeVisible();await expect(page.getByLabel('Markdown 正文')).toHaveValue('必须保留的本地草稿');expect(writes).toBe(1);
  await page.unroute(`**/api/v1/notes/${s.note.id}`);
  const before=await (await request.get(base+`/notes/${s.note.id}`,{headers:s.headers})).json();expect(before.content).toBe('服务器原文');
  await page.getByRole('button',{name:'立即保存',exact:true}).click();await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const after=await (await request.get(base+`/notes/${s.note.id}`,{headers:s.headers})).json();expect(after.content).toBe('必须保留的本地草稿');
});
test('M1 整理草稿在重新登录后保留，完整备份可实际下载并核对 hash',async({page,request})=>{
  const s=await seed(request);await signedIn(page,s);
  await page.goto(`/materials?course=${s.course.id}&document=${s.doc.id}&version=${s.versionId}&chunk=${s.chunk.id}`);
  await expect(page.locator('.reading-paper')).toContainText('暂存传输');
  await page.getByRole('button',{name:'整理',exact:true}).click();await page.getByLabel('资料名称',{exact:true}).fill('保留的资料整理草稿');
  await page.route(`**/api/v1/documents/${s.doc.id}`,async route=>{
    if(route.request().method()==='PATCH') await route.fulfill({status:401,contentType:'application/json',body:JSON.stringify({error:{message:'登录已过期'}})});else await route.continue();
  });
  await page.getByRole('button',{name:'保存整理',exact:true}).click();
  const modal=page.getByRole('dialog');await expect(modal).toBeVisible();
  await modal.getByLabel('密码',{exact:true}).fill(password);await modal.getByRole('button',{name:'登录',exact:true}).click();
  await expect(modal).not.toBeVisible();await expect(page.getByLabel('资料名称',{exact:true})).toHaveValue('保留的资料整理草稿');
  await page.unroute(`**/api/v1/documents/${s.doc.id}`);await page.getByRole('button',{name:'保存整理',exact:true}).click();
  await expect(page.locator('.reader-title')).toContainText('保留的资料整理草稿');
  await page.getByRole('button',{name:'备份与恢复',exact:true}).click();await page.getByRole('button',{name:'生成完整备份',exact:true}).click();
  const downloadButton=page.getByRole('button',{name:'下载完整备份',exact:true});await expect(downloadButton).toBeVisible({timeout:20_000});
  const received=page.waitForEvent('download');await downloadButton.click();const download=await received;
  const {readFile}=await import('node:fs/promises');const {createHash}=await import('node:crypto');const bytes=await readFile((await download.path())!);
  expect(bytes.subarray(0,2).toString()).toBe('PK');
  const records=await (await request.get(base+'/backups',{headers:s.headers})).json();expect(createHash('sha256').update(bytes).digest('hex')).toBe(records[0].sha256);
});
