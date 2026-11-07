import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
const strictBank=(stems:string[])=>`# Hustudy 题库 v1\n\n${stems.map((stem,i)=>`## 题目 ${i+1}\n### 题型\n解答题\n### 题干\n${stem}`).join("\n\n")}\n`;
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'batch_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};const c=await(await request.post(base+'/courses',{headers,data:{name:'校正与目录'}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);return {headers,c};
}

test('多级子树中出现同题时父级不再重复展示，题目原记录保留',async({page,request})=>{
 const {headers,c}=await setup(page,request);
 const root=await(await request.post(`${base}/courses/${c.id}/topics`,{headers,data:{name:'父标签'}})).json();const child=await(await request.post(`${base}/courses/${c.id}/topics`,{headers,data:{name:'子标签',parent_id:root.id}})).json();await request.post(`${base}/courses/${c.id}/topics`,{headers,data:{name:'孙标签',parent_id:child.id}});
 await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'同题不同层级',content:'1. 共享题。\n知识标签：父标签\n2. 共享题。\n知识标签：父标签,子标签,孙标签\n3. 父级独有。\n知识标签：父标签'}});
 await page.goto(`/exam?course=${c.id}`);await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await page.getByRole('button',{name:'父标签 · 2题',exact:true}).click();await expect(page.locator('.bank-directory-question')).toHaveCount(1);await expect(page.locator('.bank-directory-question')).toContainText('父级独有');
 await page.getByRole('button',{name:'子标签 · 1题',exact:true}).click();await expect(page.locator('.bank-directory-question')).toHaveCount(0);await page.getByRole('button',{name:'孙标签 · 1题',exact:true}).click();await expect(page.locator('.bank-directory-question')).toHaveCount(1);await expect(page.locator('.bank-directory-question')).toContainText('共享题');
 expect((await(await request.get(`${base}/courses/${c.id}/question-bank`,{headers})).json()).total).toBe(3);
});

test('全选批量保存当前草稿，冲突保留草稿，未选编辑保持且手机适配',async({page,request})=>{
 const {headers,c}=await setup(page,request);await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'批量保存',content:'1. 第一题。\n2. 第二题。\n3. 第三题。'}});
 await page.goto(`/exam?course=${c.id}`);const editors=page.locator('.bank-question-editor');
 for(let i=0;i<3;i++){const editor=editors.nth(i);if(await editor.getAttribute('open')===null)await editor.locator(':scope > summary').click();await editor.getByText('编辑Markdown源码与答案',{exact:true}).click();await editor.getByRole('textbox',{name:'题干',exact:true}).fill(`本地校正${i+1}。`);}
 await page.getByLabel('选择题号 1',{exact:true}).check();await page.getByLabel('选择题号 2',{exact:true}).check();let sent:any;
 await page.route('**/question-bank/save',async route=>{sent=route.request().postDataJSON();await route.fulfill({status:409,json:{error:{code:'REVISION_CONFLICT',message:'题目已变化，请保留草稿',details:{}}}});await page.unroute('**/question-bank/save');});
 await page.getByRole('button',{name:'保存所选（2）',exact:true}).click();await expect(page.getByText('题目已变化，请保留草稿',{exact:false}).first()).toBeVisible();expect(sent.items.map((v:any)=>v.stem)).toEqual(['本地校正1。','本地校正2。']);await expect(editors.nth(0).getByRole('textbox',{name:'题干',exact:true})).toHaveValue('本地校正1。');
 await page.getByRole('button',{name:'保存所选（2）',exact:true}).click();await expect(page.getByText('已保存所选2题校正，仍需核验',{exact:true})).toBeVisible();await expect(editors.nth(2).getByRole('textbox',{name:'题干',exact:true})).toHaveValue('本地校正3。');
 let rows=(await(await request.get(`${base}/courses/${c.id}/question-bank`,{headers})).json()).items;expect(rows.find((v:any)=>v.number==='3').stem).toBe('第三题。');
 await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'保存所选（3）',exact:true}).click();await expect(page.getByText('已保存所选3题校正，仍需核验',{exact:true})).toBeVisible();rows=(await(await request.get(`${base}/courses/${c.id}/question-bank`,{headers})).json()).items;expect(rows.map((v:any)=>v.stem).sort()).toEqual(['本地校正1。','本地校正2。','本地校正3。']);expect(rows.every((v:any)=>v.status==='DRAFT')).toBeTruthy();
 await page.setViewportSize({width:390,height:900});await page.getByRole('button',{name:'保存所选（3）',exact:true}).scrollIntoViewIfNeeded();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'../.artifacts/e2e/batch-save-mobile.png',fullPage:false});
});

test('进入上传校正和导入完成均不自动跳到下方校验区',async({page,request})=>{
 const {c}=await setup(page,request);await page.goto(`/exam?course=${c.id}`);await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'top.md',mimeType:'text/markdown',buffer:Buffer.from(strictBank(['页面顶部测试。']))});await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();await page.evaluate(()=>window.scrollTo(0,0));await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible({timeout:30000});await expect.poll(()=>page.evaluate(()=>window.scrollY)).toBeLessThan(150);
 await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await page.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));await page.getByRole('button',{name:'上传与校正题库',exact:true}).click();await expect.poll(()=>page.evaluate(()=>window.scrollY)).toBeLessThan(150);await expect(page.getByRole('heading',{name:'上传自己的题库'})).toBeVisible();
});
