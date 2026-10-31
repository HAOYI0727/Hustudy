import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
const strictBank=`# Hustudy 题库 v1\n\n## 题目 1\n### 题型\n解答题\n### 题干\n简述第一题。\n\n## 题目 2\n### 题型\n解答题\n### 题干\n简述第二题。\n`;
async function setup(page:any,request:any){
 const a=await(await request.post(base+'/auth/register',{data:{username:'lib_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+a.access_token};
 const c=await(await request.post(base+'/courses',{headers,data:{name:'题库隔离与删除'}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},a);
 return {headers,c};
}
async function upload(page:any,c:any){
 await page.goto(`/exam?course=${c.id}`);
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'bank.md',mimeType:'text/markdown',buffer:Buffer.from(strictBank)});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible({timeout:30000});
}

test('本地文件进入独立题库，标题直接删除可撤销，整份题库一次删除可撤销',async({page,request})=>{
 const {headers,c}=await setup(page,request);await upload(page,c);
 const library=page.getByRole('region',{name:'题库文件库'});
 await expect(library).toContainText('bank.md');await expect(library).toContainText('独立题库文件');
 expect(await(await request.get(`${base}/courses/${c.id}/documents`,{headers})).json()).toEqual([]);
 const first=page.locator('details.bank-question-editor').first();if(await first.getAttribute('open')!==null)await first.locator(':scope > summary').click();
 await expect(first.getByRole('button',{name:'删除本题',exact:true})).toBeVisible();
 let dialogs=0;page.on('dialog',async d=>{dialogs++;await d.accept();});
 await first.getByRole('button',{name:'删除本题',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible();expect(dialogs).toBe(0);
 await page.getByRole('button',{name:'撤销删除题号 1',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible();
 await page.getByRole('button',{name:'删除整份题库',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共0题'})).toBeVisible();expect(dialogs).toBe(1);
 await expect(library).toContainText('bank.md');
 await page.getByRole('button',{name:'撤销删除题库「bank.md」',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible();
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.screenshot({path:'../local_only/m4-library-delete-mobile.png',fullPage:false});
});

test('批量删除无需逐题确认并可一次撤销',async({page,request})=>{
 const {c}=await setup(page,request);await upload(page,c);
 let dialogs=0;page.on('dialog',async d=>{dialogs++;await d.dismiss();});
 await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'删除所选',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共0题'})).toBeVisible();expect(dialogs).toBe(0);
 await page.getByRole('button',{name:'撤销删除2道题目',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible();
});

test('旧题目资料可明确移入题库且不改变原版本',async({page,request})=>{
 const {headers,c}=await setup(page,request);
 const v=await(await request.post(`${base}/courses/${c.id}/documents`,{headers,multipart:{file:{name:'old.md',mimeType:'text/markdown',buffer:Buffer.from('1. 简述旧题目。')}}})).json();
 await expect.poll(async()=> (await(await request.get(`${base}/versions/${v.resource_id}`,{headers})).json()).index_status).toBe('SUCCEEDED');
 await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'旧题来源',version_id:v.resource_id}});
 await page.goto(`/exam?course=${c.id}`);
 const library=page.getByRole('region',{name:'题库文件库'});await expect(library).toContainText('旧资料来源');
 await library.getByRole('button',{name:'移入题库文件库',exact:true}).click();
 await expect(library).toContainText('独立题库文件');
 expect(await(await request.get(`${base}/courses/${c.id}/documents`,{headers})).json()).toEqual([]);
 const files=await(await request.get(`${base}/courses/${c.id}/question-bank/files`,{headers})).json();expect(files[0].latest_version_id).toBe(v.resource_id);
});


test('从资料库入口查找独立题库原件、重新识别及直接打开已保存题库',async({page,request})=>{
 const {headers,c}=await setup(page,request);await upload(page,c);
 await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'手动粘贴保存题库',content:'1. 解释手动样题。'}});
 await page.reload();await page.getByRole('button',{name:'从资料库导入',exact:true}).click();
 await page.getByLabel('查找已上传资料或题库').fill('bank.md');
 const select=page.getByLabel('从已上传资料或题库原件导入（含人工补录）');await expect(select.locator('option')).toContainText(['请选择已上传文件','题库原件：bank（bank.md）']);
 const files=await(await request.get(`${base}/courses/${c.id}/question-bank/files`,{headers})).json();await select.selectOption(files[0].latest_version_id);
 await expect(page.getByRole('button',{name:'识别已上传题库',exact:true})).toBeEnabled();await page.getByRole('button',{name:'识别已上传题库',exact:true}).click();await expect(page.getByText('题目已自动识别并展开，请核对参考解答与来源',{exact:true})).toBeVisible();
 expect(await(await request.get(`${base}/courses/${c.id}/documents`,{headers})).json()).toEqual([]);
 const before=await(await request.get(`${base}/courses/${c.id}/question-bank/papers`,{headers})).json();
 await page.getByLabel('查找已上传资料或题库').fill('手动粘贴');await page.getByText('查找已保存题库（直接打开，不重复导入）',{exact:true}).click();await page.getByRole('button',{name:'手动粘贴保存题库 · 1题',exact:true}).click();await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible();
 expect(await(await request.get(`${base}/courses/${c.id}/question-bank/papers`,{headers})).json()).toHaveLength(before.length);
});
