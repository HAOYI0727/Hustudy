import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
test('题库文件识别显示DeepSeek实际模型，独立图片入口已移除',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'ds_'+crypto.randomUUID().replaceAll('-',''),password:'Synthetic-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'DeepSeek隔离验收'}})).json();
 const status=await(await request.get(base+'/model-connections',{headers})).json();
 const saved=await(await request.put(base+'/model-connections',{headers,data:{revision:status.revision,name:'DeepSeek',vendor:'deepseek',endpoint:'https://api.deepseek.com/chat/completions',model:'deepseek-flash',key:'synthetic-test-key-never-real',vision:true,thinking:false,json_mode:true}})).json();
 const selected=await request.post(base+'/model-connections/active',{headers,data:{revision:saved.revision,profile_id:saved.profiles[0].id}});expect(selected.ok()).toBeTruthy();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);
 await expect(page.getByLabel('识别方式',{exact:true}).locator('option[value=ai]')).toContainText('DeepSeek · deepseek-flash');
 await expect(page.getByRole('button',{name:'AI图片识别（可选）',exact:true})).toHaveCount(0);
 await expect(page.getByLabel('选择题目图片（PNG/JPEG/WebP，可多选）')).toHaveCount(0);
 await page.getByLabel('识别方式',{exact:true}).selectOption('ai');
 await expect(page.getByLabel('上传题库文件（PDF/ZIP/PPTX/DOCX/Markdown）')).toBeVisible();
 expect(await(await request.get(`${base}/courses/${course.id}/question-bank/image-jobs`,{headers})).json()).toHaveLength(0);
});
