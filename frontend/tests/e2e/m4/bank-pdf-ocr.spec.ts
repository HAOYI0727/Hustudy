import {test,expect} from '@playwright/test';
import JSZip from 'jszip';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';

for(const zipped of [false,true])test(`${zipped?'ZIP内混合':'纯扫描'}PDF进入AI原页转写前预览并明确确认`,async({page,request})=>{
 test.setTimeout(120000);
 const auth=await(await request.post(base+'/auth/register',{data:{username:'scan_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const c=await(await request.post(base+'/courses',{headers,data:{name:'扫描PDF验收'}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.route('**/question-bank/ai-capabilities',r=>r.fulfill({json:{configured:true,vision_configured:true,model:'glm-5.3-flash'}}));await page.goto(`/exam?course=${c.id}`);await page.getByLabel('识别方式',{exact:true}).selectOption('ai');
 const file=zipped?'question_bank_mixed_demo.pdf':'question_bank_scan_demo.pdf';
 const raw=readFileSync(fileURLToPath(new URL(`../../../../fixtures/${file}`,import.meta.url)));
 const zip=new JSZip();zip.file('扫描题库/'+file,raw);
 await page.getByLabel('上传题库文件（PDF/ZIP/PPTX/DOCX/Markdown）').setInputFiles({name:zipped?'scans.zip':'scans.pdf',mimeType:zipped?'application/zip':'application/pdf',buffer:zipped?await zip.generateAsync({type:'nodebuffer'}):raw});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 const recognize=page.getByRole('button',{name:/^AI转写原页与公式/});
 await expect(recognize).toBeVisible({timeout:60000});
 await expect(page.locator('.bank-import-results')).toContainText('可能是扫描页或空白页');
 expect(await(await request.get(`${base}/courses/${c.id}/question-bank/image-jobs`,{headers})).json()).toEqual([]);
 expect((await(await request.get(`${base}/courses/${c.id}/question-bank`,{headers})).json()).total).toBe(0);
 let sent:any=null;await page.route('**/question-bank/pdf/*/ocr',route=>{sent=route.request().postDataJSON();return route.fulfill({json:{paper_id:crypto.randomUUID(),status:'QUEUED'}});});
 page.once('dialog',d=>{expect(d.message()).toContain('glm-5.3-flash');d.accept();});await recognize.click();await expect.poll(()=>sent?.engine).toBe('ai');expect(sent.confirm_remote_send).toBe(true);expect(sent.questions_only).toBe(false);expect(sent.classify_topics).toBe(true);
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.screenshot({path:`../.artifacts/e2e/m4-pdf-ocr-${zipped?'mixed':'scan'}-mobile.png`,fullPage:false});
});
