import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';

test('全部保存核验后显示已确认，重复保存保持，批量标签两种模式及对齐',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'review_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'审核与标签'}})).json();
 const old=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'原标签'}})).json();
 const next=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'新标签'}})).json();
 await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'状态验收',content:'1. 解释甲。\n2. 解释乙。',default_topic_ids:[old.id]}});
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);
 const paperStatus=page.locator('.bank-paper-review .bank-badge');await expect(paperStatus).toHaveText('待审核');
 await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'保存所选（2）',exact:true}).click();
 await page.getByRole('button',{name:'核验所选（2）',exact:true}).click();await expect(paperStatus).toHaveText('已确认');
 await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'保存所选（2）',exact:true}).click();
 await expect(page.getByText('已保存所选2题校正，核验状态保持',{exact:true})).toBeVisible();await expect(paperStatus).toHaveText('已确认');
 await page.reload();await expect(paperStatus).toHaveText('已确认');await page.getByLabel('全选本页').check();
 const search=page.getByLabel('批量知识标签',{exact:true});await search.fill('新标签');await page.getByRole('button',{name:'＋ 新标签',exact:true}).click();
 const add=page.getByRole('button',{name:'都添加这个标签',exact:true}),replace=page.getByRole('button',{name:'都改成这个标签',exact:true});
 const boxes=await Promise.all([search.boundingBox(),add.boundingBox(),replace.boundingBox()]);expect(Math.max(...boxes.map(b=>b!.y))-Math.min(...boxes.map(b=>b!.y))).toBeLessThan(2);expect(Math.max(...boxes.map(b=>b!.height))-Math.min(...boxes.map(b=>b!.height))).toBeLessThan(2);
 await page.locator('.bank-review-toolbar').screenshot({path:'local_only/batch-tags-aligned.png'});
 await add.click();await expect(page.getByText('已为所选题目追加标签，原标签保留',{exact:true})).toBeVisible();await expect(paperStatus).toHaveText('待审核');
 const rows=async()=>(await(await request.get(`${base}/courses/${course.id}/question-bank`,{headers})).json()).items;
 expect((await rows()).every((q:any)=>JSON.stringify(q.bank_data.topic_ids)===JSON.stringify([old.id,next.id]))).toBeTruthy();
 await replace.click();await expect(page.getByText('已将所选题目的标签统一替换',{exact:true})).toBeVisible();expect((await rows()).every((q:any)=>JSON.stringify(q.bank_data.topic_ids)===JSON.stringify([next.id]))).toBeTruthy();
 await page.getByRole('button',{name:'核验所选（2）',exact:true}).click();await expect(paperStatus).toHaveText('已确认');
 await page.setViewportSize({width:390,height:900});await page.locator('.bank-bulk-tags').scrollIntoViewIfNeeded();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.locator('.bank-review-toolbar').screenshot({path:'local_only/batch-tags-mobile.png'});
});

test('追加超过5标签逐题列出题库和原题号且整批不改',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'limit_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};const course=await(await request.post(base+'/courses',{headers,data:{name:'标签上限'}})).json();
 const topics=[];for(let i=0;i<6;i++)topics.push(await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:`标签${i}`}})).json());
 for(const title of ['试卷甲','试卷乙'])await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title,content:`1. 解释${title}中的问题。`,default_topic_ids:topics.slice(0,5).map(t=>t.id)}});
 const rows=async()=>(await(await request.get(`${base}/courses/${course.id}/question-bank`,{headers})).json()).items;
 const before=await rows();expect(before).toHaveLength(2);
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);await page.goto(`/exam?course=${course.id}`);
 await expect(page.locator('.bank-question-editor')).toHaveCount(2);await page.getByLabel('全选本页').check();await page.getByLabel('批量知识标签',{exact:true}).fill('标签5');await page.getByRole('button',{name:'＋ 标签5',exact:true}).click();await page.getByRole('button',{name:'都添加这个标签',exact:true}).click();
 const alert=page.locator('.bank-manager > .course-conflict');await expect(alert).toContainText('每题5个标签');await expect(alert).toContainText('题库「试卷甲」题号 1（6/5个标签）');await expect(alert).toContainText('题库「试卷乙」题号 1（6/5个标签）');
 expect(await rows()).toEqual(before);await expect(page.getByRole('button',{name:'核验所选（2）',exact:true})).toBeEnabled();
});
