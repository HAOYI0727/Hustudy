import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
test('题目默认显示编译Markdown表格与公式，源码折叠、保存规范化、可下载md',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'md_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};const c=await(await request.post(base+'/courses',{headers,data:{name:'Markdown题目'}})).json();
 const p=await(await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'表格题',content:'1. 根据表格解释 $D_8\\oplus D_7$。\n输入\t输出\n0\t≤ 2\n1\t$x_1$'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);await page.goto(`/exam?course=${c.id}`);
 const q=page.locator('.bank-question-editor').first();if(await q.getAttribute('open')===null)await q.locator(':scope > summary').click();
 await expect(q.locator('.bank-math table')).toBeVisible();await expect(q.locator('.bank-math .katex').first()).toBeVisible();await expect(q.getByRole('textbox',{name:'题干',exact:true})).not.toBeVisible();
 await q.getByText('编辑Markdown源码与答案',{exact:true}).click();await expect(q.getByRole('textbox',{name:'题干',exact:true})).toHaveValue(/\| 输入 \| 输出 \|/);
 await q.getByRole('textbox',{name:'题干',exact:true}).fill('根据下表解释 $D_8$。\n状态\t值\n启用\t∑ ≤ 3\n关闭\t0');await q.getByRole('button',{name:'保存本题校正',exact:true}).click();
 const stored=await(await request.get(`${base}/courses/${c.id}/question-bank`,{headers})).json();expect(stored.items[0].stem).toContain('| 状态 | 值 |');expect(stored.items[0].bank_data.content_format).toBe('markdown');
 await expect(q.locator('.bank-math table')).toContainText('∑ ≤ 3');
 const md=await request.get(`${base}/past-questions/${p.questions[0].id}/markdown`,{headers});expect(md.headers()['content-type']).toContain('text/markdown');expect(await md.text()).toContain('| 状态 | 值 |');
 const download=page.waitForEvent('download');await q.getByRole('button',{name:'下载题目Markdown',exact:true}).click();expect((await download).suggestedFilename()).toMatch(/\.md$/);
 await page.setViewportSize({width:390,height:900});await q.locator('.bank-math').first().scrollIntoViewIfNeeded();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'../.artifacts/e2e/m4-markdown-table-mobile.png'});
});
