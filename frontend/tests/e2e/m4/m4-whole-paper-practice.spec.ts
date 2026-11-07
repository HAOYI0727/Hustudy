import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
for(const width of [1440,390])test(`整卷完整作答与最终状态 ${width}`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});
 const auth=await(await request.post(base+'/auth/register',{data:{username:'whole_'+crypto.randomUUID().replaceAll('-',''),password:'Synthetic-test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'隔离整卷练习'}})).json();
 const content='1. 第一问。\n知识标签：综合\n2. 重复问题。\n知识标签：综合\n3. 重复问题。\n知识标签：综合\n4. 选择数字。\nA. 一 B. 二 C. 三 D. 四\n答案：B\n知识标签：综合';
 const source=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'自制完整试卷',content}})).json();
 expect((await request.post(`${base}/past-papers/${source.id}/confirm`,{headers})).ok()).toBeTruthy();
 await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'待审核试卷',content:'1. 待审核题目。\n知识标签：综合'}});
 await page.addInitScript((a)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);
 await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();
 await page.getByLabel('选择练习方式',{exact:true}).selectOption('whole');
 const select=page.getByLabel('选择题库试卷',{exact:true});
 await expect(select.locator('option').filter({hasText:'待审核试卷'})).toHaveAttribute('disabled','');
 await select.selectOption(source.id);
 await page.getByRole('button',{name:'载入整套试卷',exact:true}).click();
 await expect(page.locator('.bank-practice .question-card')).toHaveCount(4);
 await expect(page.locator('.bank-practice .question-card').filter({hasText:'重复问题。'})).toHaveCount(2);
 await page.getByRole('button',{name:'已核对题干，确认练习'}).click();
 await page.getByRole('button',{name:'开始作答',exact:true}).click();
 const first=page.locator('.bank-practice .question-card').first();
 for(const text of ['旧答案','最终答案']){
  await first.getByLabel('解答内容').fill(text);
  await first.getByRole('button',{name:'保存本题答案'}).click();
  await expect(first.getByRole('button',{name:'保存本题答案'})).toBeDisabled();
 }
 const choice=page.locator('.bank-practice .question-card').last();
 for(const index of [0,2,1]){
  await choice.locator('button.option').nth(index).click();
  await expect(choice.locator('button.option').nth(index)).toHaveClass(/selected-option/);
 }
 await page.reload();
 await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();
 await expect(first.getByLabel('解答内容')).toHaveValue('最终答案');
 await expect(choice.locator('button.option').nth(1)).toHaveClass(/selected-option/);
 await page.getByRole('button',{name:'交卷并查看答案'}).click();
 await expect(page.getByRole('heading',{name:'自制完整试卷 · 整卷练习 · 已完成',exact:true})).toBeVisible();
 await expect(first.getByText('你的答案：最终答案',{exact:true})).toBeVisible();
 await page.locator('.bank-practice-history summary').click();
 await expect(page.getByRole('button',{name:'第1次作答 · 已完成',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:/待开始 · 打开练习/})).toHaveCount(0);
 const history=await(await request.get(`${base}/courses/${course.id}/exam-papers`,{headers})).json();
 expect(history[0].attempts).toHaveLength(1);
 const result=await(await request.get(`${base}/attempts/${history[0].attempts[0].id}`,{headers})).json();
 expect(Object.values(result.answers)).toEqual(expect.arrayContaining(['最终答案','B']));
 expect(Object.values(result.answers)).not.toContain('旧答案');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.screenshot({path:`../.artifacts/e2e/m4-whole-paper-${width}.png`,fullPage:true});
 await page.getByRole('button',{name:'重新练习本套',exact:true}).click();
 await expect(first.getByLabel('解答内容')).toHaveValue('');
 const next=await(await request.get(`${base}/courses/${course.id}/exam-papers`,{headers})).json();
 expect(next[0].attempts).toHaveLength(2);
 expect(next[0].attempts[1].status).toBe('SCORED');
});
