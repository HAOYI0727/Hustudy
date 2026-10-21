import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
// Candidate generation UI is retired; historical backend records remain compatible.
for(const width of [390,1440])test(`AI学习移除练习模块，三种学习模式保留 ${width}px`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});
 const auth=await(await request.post(base+'/auth/register',{data:{username:'retired_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};const course=await(await request.post(base+'/courses',{headers,data:{name:'学习入口'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 const calls:string[]=[];page.on('request',r=>{if(r.method()==='POST'&&/question-drafts|question-bank\/draw/.test(r.url()))calls.push(r.url());});
 await page.goto(`/ai?course=${course.id}`);
 await expect(page.getByRole('group',{name:'AI模式'}).getByRole('button')).toHaveCount(3);
 await expect(page.getByRole('button',{name:'练习题生成',exact:true})).toHaveCount(0);
 await expect(page.locator('.bank-practice')).toHaveCount(0);
 await expect(page.getByText('AI也会犯错，请仔细甄别',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'资料问答',exact:true}).click();await expect(page.getByRole('button',{name:'练习题生成',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'学习报告',exact:true}).click();await expect(page.getByRole('button',{name:'练习题生成',exact:true})).toHaveCount(0);
 if(width<=1100)await page.getByRole('button',{name:'打开导航菜单',exact:true}).click();
 await page.getByRole('button',{name:'真题与模拟卷',exact:true}).click();await page.getByRole('button',{name:'随机练习与作答',exact:true}).click();
 await expect(page.getByRole('button',{name:'随机抽取题库练习',exact:true})).toBeVisible();
 expect(calls).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
