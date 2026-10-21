import {test,expect} from '@playwright/test';
import JSZip from 'jszip';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';

for(const zipped of [false,true])test(`${zipped?'ZIP内混合':'纯扫描'}PDF先提示可选图片转文字，确认后自动显示题目`,async({page,request})=>{
 test.setTimeout(120000);
 const auth=await(await request.post(base+'/auth/register',{data:{username:'scan_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const c=await(await request.post(base+'/courses',{headers,data:{name:'扫描PDF验收'}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${c.id}`);
 const file=zipped?'question_bank_mixed_demo.pdf':'question_bank_scan_demo.pdf';
 const raw=readFileSync(fileURLToPath(new URL(`../../../fixtures/${file}`,import.meta.url)));
 const zip=new JSZip();zip.file('扫描题库/'+file,raw);
 await page.getByLabel('上传题库文件（PDF/ZIP/PPTX/DOCX/Markdown）').setInputFiles({name:zipped?'scans.zip':'scans.pdf',mimeType:zipped?'application/zip':'application/pdf',buffer:zipped?await zip.generateAsync({type:'nodebuffer'}):raw});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 const recognize=page.getByRole('button',{name:'识别扫描页并拆分题目',exact:true});
 await expect(recognize).toBeVisible({timeout:30000});
 await expect(page.locator('.bank-import-results')).toContainText('可能是扫描页或空白页');
 expect(await(await request.get(`${base}/courses/${c.id}/question-bank/image-jobs`,{headers})).json()).toEqual([]);
 expect((await(await request.get(`${base}/courses/${c.id}/question-bank`,{headers})).json()).total).toBe(0);
 await recognize.click();
 await expect(page.getByRole('heading',{name:`题目校正 · 共${zipped?3:2}题`})).toBeVisible({timeout:90000});
 const first=page.locator('.bank-question-editor').first();await first.getByText('编辑Markdown源码与答案',{exact:true}).click();
 await expect(first.getByRole('textbox',{name:'题干',exact:true})).toHaveValue(/协议.*传输层/);
 await expect(first.getByRole('combobox',{name:'正确选项',exact:true})).toHaveValue('B');
 if(zipped){await page.locator('.bank-question-editor').last().getByText('编辑Markdown源码与答案',{exact:true}).click();await expect(page.locator('.bank-question-editor').last().getByRole('textbox',{name:'题干',exact:true})).toHaveValue('Explain reliable transport protocols.');}
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.screenshot({path:`../local_only/m4-pdf-ocr-${zipped?'mixed':'scan'}-mobile.png`,fullPage:false});
});
