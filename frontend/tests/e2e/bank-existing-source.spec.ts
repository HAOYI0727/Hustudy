import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any,name:string,raw:Buffer){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'source_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};
 const c=await(await request.post(base+'/courses',{headers,data:{name:'统一导入'}})).json();
 const job=await(await request.post(`${base}/courses/${c.id}/documents`,{headers,multipart:{file:{name,mimeType:name.endsWith('.pdf')?'application/pdf':'text/markdown',buffer:raw}}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${c.id}`);await page.getByRole('button',{name:'从资料库导入',exact:true}).click();await page.getByLabel('从已上传资料或题库原件导入（含人工补录）').selectOption(job.resource_id);
 return {headers,c,job};
}

test('已有扫描PDF复用本地转图OCR与AI原页选项，不重复上传',async({page,request})=>{
 test.setTimeout(120000);
 await page.route('**/question-bank/ai-capabilities',route=>route.fulfill({json:{configured:true,vision_configured:true,model:'glm-5.3-flash'}}));
 const raw=readFileSync(fileURLToPath(new URL('../../../fixtures/question_bank_scan_demo.pdf',import.meta.url)));
 const {headers,c,job}=await setup(page,request,'已有扫描.pdf',raw);
 await page.getByLabel('识别方式',{exact:true}).selectOption('ai');await page.getByRole('button',{name:'识别已上传题库',exact:true}).click();const aiButton=page.getByRole('button',{name:/^AI转写原页与公式/});await expect(aiButton).toBeVisible({timeout:60000});
 expect(await(await request.get(`${base}/courses/${c.id}/question-bank/image-jobs`,{headers})).json()).toEqual([]);
 expect(await(await request.get(`${base}/courses/${c.id}/documents`,{headers})).json()).toHaveLength(1);
 let sent:any=null;await page.route(`**/question-bank/pdf/${job.resource_id}/ocr`,route=>{sent=route.request().postDataJSON();return route.fulfill({json:{paper_id:'isolated-vision-job',status:'QUEUED'}});});
 page.once('dialog',d=>{expect(d.message()).toContain('glm-5.3-flash');d.accept();});await aiButton.click();await expect.poll(()=>sent?.engine).toBe('ai');expect(sent.confirm_remote_send).toBe(true);expect(sent.classify_topics).toBe(true);expect(sent.questions_only).toBe(false);
});

test('已有文字文件复用AI原文预览，确认前不发送模型请求',async({page,request})=>{
 await page.route('**/question-bank/ai-capabilities',route=>route.fulfill({json:{configured:true}}));
 let previews=0,confirms=0;await page.route('**/question-bank/ai-preview',route=>{previews++;return route.fulfill({json:{paper_id:'isolated-preview',status:'PREVIEW',model:'glm-5.3-flash',endpoint:'https://open.bigmodel.cn',sources:[{text:'1. 简述原题。'}]}});});
 await page.route('**/question-bank/ai/*/confirm',route=>{confirms++;return route.fulfill({json:{paper_id:'isolated-preview',status:'QUEUED'}});});
 const {headers,c}=await setup(page,request,'已有原文.md',Buffer.from('1. 简述原题。'));
 await page.getByLabel('识别方式',{exact:true}).selectOption('ai');await page.getByRole('button',{name:'识别已上传题库',exact:true}).click();await expect(page.getByRole('heading',{name:'确认发送原文进行AI识别'})).toBeVisible({timeout:30000});
 expect(previews).toBe(1);expect(confirms).toBe(0);await expect(page.locator('.bank-ai-consent pre')).toContainText('简述原题');
 expect(await(await request.get(`${base}/courses/${c.id}/documents`,{headers})).json()).toHaveLength(1);
});
