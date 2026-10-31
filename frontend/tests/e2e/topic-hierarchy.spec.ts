import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
async function dragTopic(page:any,name:string,target:string){
 await page.getByRole('button',{name,exact:true}).locator('..').dragTo(page.locator(target),{timeout:12000});
}

test('标签父子管理、贴标签搜索和自动归属、父级题数及抽题',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'tree_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'层级测试'}})).json();
 const root=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'计算机组成'}})).json();
 const child=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'高速缓存',aliases:['Cache'],parent_id:root.id}})).json();
 await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'层级样题',content:'1. 解释缓存。'}});
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);const editor=page.locator('.bank-question-editor').first();if(!(await editor.evaluate(e=>(e as HTMLDetailsElement).open))){await editor.locator(':scope > summary').click();}await editor.getByLabel('搜索其他知识标签').fill('Cache');
 await editor.locator('.bank-topic-option').filter({hasText:'高速缓存'}).locator('input').check();await expect(editor.getByLabel('自动归属父标签')).toContainText('计算机组成');
 await editor.getByRole('button',{name:'保存本题校正',exact:true}).click();await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'核验所选（1）',exact:true}).click();await expect(page.getByText('所选题目已核验，题库审核状态已同步',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await expect(page.getByRole('button',{name:'计算机组成 · 1题',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'高速缓存 · 1题',exact:true})).toHaveCount(0);await page.getByRole('button',{name:'计算机组成 · 1题',exact:true}).click();await page.getByRole('button',{name:'高速缓存 · 1题',exact:true}).click();await page.locator('.bank-directory-question > summary').click();await expect(page.locator('.bank-directory-question')).toContainText('解释缓存。');
 const row=page.locator('.bank-topic-content');await expect(row.getByLabel('上级知识标签',{exact:true})).toHaveValue('计算机组成');
 await row.getByLabel('标签名称',{exact:true}).fill('一级缓存');await row.getByRole('button',{name:'保存标签名称与别名'}).click();await expect(page.getByRole('button',{name:'一级缓存 · 1题',exact:true})).toBeVisible();
 await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:'local_only/topic-directory-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'local_only/topic-directory-questions-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1000});
 await page.getByRole('button',{name:'计算机组成 · 1题',exact:true}).click();await page.getByRole('button',{name:'在上传与校正中查看'}).click();await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible();
 await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await page.getByLabel('搜索知识标签',{exact:true}).fill('计算机组成');await page.getByRole('button',{name:'＋ 计算机组成',exact:true}).click();await page.getByLabel('题数',{exact:true}).fill('1');await page.getByRole('button',{name:'随机抽取题库练习',exact:true}).click();await expect(page.getByRole('button',{name:'已核对题干，确认练习'})).toBeVisible();
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'local_only/topic-tree-mobile.png',fullPage:true});
});


test('目录拖动、拒绝循环、冲突不假更新和草稿离开保护',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'drag_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};
 const c=await(await request.post(base+'/courses',{headers,data:{name:'目录拖动'}})).json();
 const a=await(await request.post(`${base}/courses/${c.id}/topics`,{headers,data:{name:'标签甲'}})).json();
 const b=await(await request.post(`${base}/courses/${c.id}/topics`,{headers,data:{name:'标签乙'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${c.id}`);await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();
 await page.locator(`[data-topic-id="${b.id}"]`).dragTo(page.locator(`[data-topic-id="${a.id}"]`),{timeout:12000});
 await expect.poll(async()=> (await(await request.get(`${base}/courses/${c.id}/topics`,{headers})).json()).find((t:any)=>t.id===b.id).parent_id).toBe(a.id);
 await expect(page.getByRole('button',{name:'标签乙 · 0题',exact:true})).toBeVisible();
 await dragTopic(page,'标签甲 · 0题',`[data-topic-id="${b.id}"]`);
 expect((await(await request.get(`${base}/courses/${c.id}/topics`,{headers})).json()).find((t:any)=>t.id===a.id).parent_id).toBeNull();
 await dragTopic(page,'标签乙 · 0题','.bank-topic-root-drop');
 await expect.poll(async()=> (await(await request.get(`${base}/courses/${c.id}/topics`,{headers})).json()).find((t:any)=>t.id===b.id).parent_id).toBeNull();
 await dragTopic(page,'标签乙 · 0题',`[data-topic-id="${a.id}"]`);
 await expect.poll(async()=> (await(await request.get(`${base}/courses/${c.id}/topics`,{headers})).json()).find((t:any)=>t.id===b.id).parent_id).toBe(a.id);
 await page.getByRole('button',{name:'标签乙 · 0题',exact:true}).click();const editor=page.locator('.bank-topic-content');await editor.getByLabel('标签名称',{exact:true}).fill('未保存名称');
 page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'未归类',exact:false}).click();await expect(editor.getByLabel('标签名称',{exact:true})).toHaveValue('未保存名称');
 await editor.getByLabel('标签名称',{exact:true}).fill('标签乙');await editor.getByRole('button',{name:'清除上级知识标签',exact:true}).click();await editor.getByRole('button',{name:'保存标签名称与别名'}).click();
 await expect.poll(async()=> (await(await request.get(`${base}/courses/${c.id}/topics`,{headers})).json()).find((t:any)=>t.id===b.id).parent_id).toBeNull();
 await page.route(`**/topics/${b.id}`,route=>route.fulfill({status:409,json:{error:{code:'REVISION_CONFLICT',message:'标签已被修改，请刷新',details:{}}}}));
 await dragTopic(page,'标签乙 · 0题',`[data-topic-id="${a.id}"]`);await expect(page.getByText('标签已被修改，请刷新',{exact:false}).first()).toBeVisible();
 expect((await(await request.get(`${base}/courses/${c.id}/topics`,{headers})).json()).find((t:any)=>t.id===b.id).parent_id).toBeNull();
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'local_only/topic-directory-mobile.png',fullPage:true});
});


test('搜索创建子标签、改父级、删除关联标签后进入未归类',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'organize_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};
 const c=await(await request.post(base+'/courses',{headers,data:{name:'标签管理'}})).json();
 await request.post(`${base}/courses/${c.id}/topics`,{headers,data:{name:'计算机组成'}});await request.post(`${base}/courses/${c.id}/topics`,{headers,data:{name:'体系结构'}});
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${c.id}`);await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await page.getByText('新建大标签 / 小标签',{exact:true}).click();await page.getByLabel('新标签名称').fill('临时缓存');
 await expect(page.getByRole('button',{name:'＋ 计算机组成',exact:true})).toHaveCount(0);await page.getByLabel('所属大标签',{exact:true}).fill('组成');await page.getByRole('button',{name:'＋ 计算机组成',exact:true}).click();await page.getByRole('button',{name:'创建知识标签',exact:true}).click();
 await page.getByRole('button',{name:'计算机组成 · 0题',exact:true}).click();await page.getByRole('button',{name:'临时缓存 · 0题',exact:true}).click();const editor=page.locator('.bank-topic-content');await editor.getByLabel('上级知识标签',{exact:true}).fill('体系');await editor.getByRole('button',{name:'＋ 体系结构',exact:true}).click();await editor.getByRole('button',{name:'保存标签名称与别名'}).click();
 await page.getByRole('button',{name:'体系结构 · 0题',exact:true}).click();await page.getByRole('button',{name:'临时缓存 · 0题',exact:true}).click();page.once('dialog',d=>d.accept());await editor.getByRole('button',{name:'删除标签',exact:true}).click();await expect(page.getByRole('button',{name:'临时缓存 · 0题',exact:true})).toHaveCount(0);
 await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'保护题库',content:'1. 简述组成。\n知识标签：计算机组成'}});await page.reload();await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await page.getByRole('button',{name:'计算机组成 · 1题',exact:true}).click();await page.setViewportSize({width:390,height:900});await editor.getByRole('button',{name:'删除标签',exact:true}).scrollIntoViewIfNeeded();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'local_only/tag-delete-mobile.png',fullPage:true});page.once('dialog',d=>d.accept());await editor.getByRole('button',{name:'删除标签',exact:true}).click();await page.getByRole('button',{name:'未归类',exact:false}).click();await expect(page.locator('.bank-directory-question')).toHaveCount(1);await page.locator('.bank-directory-question > summary').click();await expect(page.locator('.bank-directory-question')).toContainText('简述组成');await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
