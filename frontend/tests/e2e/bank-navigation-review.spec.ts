import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'leave_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};const course=await(await request.post(base+'/courses',{headers,data:{name:'核对与离开'}})).json();
 await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'待审核试卷',content:'1. 缓存名称是____。\n2. 解释地址。'}});
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);await expect(page.locator('.bank-question-editor')).toHaveCount(2);return course;
}

test('多题草稿离开只提示一次，取消可继续编辑，接受可切页，未核验本身不拦截',async({page,request})=>{
 await setup(page,request);const editors=page.locator('.bank-question-editor');const fill=editors.nth(0),solution=editors.nth(1);
 await fill.locator(':scope > summary').click();await fill.getByText('编辑Markdown源码与答案',{exact:true}).click();await fill.getByRole('textbox',{name:'题干',exact:true}).fill('第一道题的未保存条件。');
 await solution.locator(':scope > summary').click();await solution.getByText('编辑Markdown源码与答案',{exact:true}).click();const stem=solution.getByRole('textbox',{name:'题干',exact:true});await stem.fill('未保存条件甲。');
 let accept=false;const prompts:string[]=[];page.on('dialog',async dialog=>{prompts.push(dialog.message());if(accept)await dialog.accept();else await dialog.dismiss();});
 await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await expect(page.getByRole('button',{name:'上传与校正题库',exact:true})).toHaveClass('primary');expect(prompts).toHaveLength(1);
 await expect(stem).toHaveValue('未保存条件甲。');await expect(fill.getByRole('textbox',{name:'题干',exact:true})).toHaveValue('第一道题的未保存条件。');await stem.fill('取消后继续修改。');
 accept=true;await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await expect(page.getByRole('button',{name:'考点、统计与蓝图',exact:true})).toHaveClass('primary');expect(prompts).toHaveLength(2);
 await page.getByRole('button',{name:'上传与校正题库',exact:true}).click();await expect(editors).toHaveCount(2);
 await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await expect(page.getByRole('button',{name:'题库练习与作答',exact:true})).toHaveClass('primary');expect(prompts).toHaveLength(2);
 await page.getByRole('button',{name:'上传与校正题库',exact:true}).click();await expect(editors).toHaveCount(2);const current=editors.nth(1);await current.locator(':scope > summary').click();await current.getByText('编辑Markdown源码与答案',{exact:true}).click();await current.getByRole('textbox',{name:'题干',exact:true}).fill('主导航离开测试。');
 await page.getByRole('button',{name:'使用反馈',exact:true}).click();await expect(page.getByRole('heading',{name:'使用反馈',exact:true}).first()).toBeVisible();expect(prompts).toHaveLength(3);
});

test('含空位题直接作为解答题，不再显示填空设置，保存草稿不拦截且选择框适配',async({page,request})=>{
 await setup(page,request);const item=page.locator('.bank-question-editor').first();await expect(item.locator('.bank-summary-warnings')).toHaveCount(0);
 await item.locator(':scope > summary').click();await expect(item.getByLabel('是否唯一答案')).toHaveCount(0);await expect(item.getByRole('group',{name:'填空题判分方式',exact:true})).toHaveCount(0);
 await item.getByText('编辑Markdown源码与答案',{exact:true}).click();const selector=item.getByLabel('题型',{exact:true});await expect(selector).toHaveValue('solution');await expect(selector.locator('option')).toHaveText(['选择题（四选一）','解答题（只检查提交）']);
 const control=await selector.boundingBox();expect(control!.height).toBeGreaterThanOrEqual(44);expect(await selector.evaluate(e=>getComputedStyle(e).backgroundSize)).toBe('20px 20px');await item.getByRole('button',{name:'保存本题校正',exact:true}).click();
 await expect(page.getByText('已保存校正，请核验修改后的题目',{exact:true})).toBeVisible();await expect(page.locator('.bank-paper-review .bank-badge')).toHaveText('待审核');await item.getByText('编辑Markdown源码与答案',{exact:true}).click();await page.setViewportSize({width:390,height:900});await selector.scrollIntoViewIfNeeded();expect((await selector.boundingBox())!.height).toBeGreaterThanOrEqual(48);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 let prompts=0;page.on('dialog',async dialog=>{prompts++;await dialog.dismiss();});await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await expect(page.getByRole('button',{name:'题库练习与作答',exact:true})).toHaveClass('primary');expect(prompts).toBe(0);
});
