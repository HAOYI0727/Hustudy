import {test,expect,type APIRequestContext} from '@playwright/test';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';
const content=`1. 哪个属于传输层？\nA. IP\nB. TCP\nC. ARP\nD. ICMP\n答案：B\n知识标签：网络\n2. TCP名称是____。\n答案：传输控制协议\n知识标签：网络\n3. 解释TCP。\n知识标签：网络`;
async function seed(request:APIRequestContext){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'bank_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'题库课程'}})).json();
 return {auth,headers,course};
}

test('已有练习记录时进入真题与模拟卷仍显示第一个板块',async({page,request})=>{
 const s=await seed(request);
 await page.addInitScript(({auth,courseId})=>{
  localStorage.setItem('hustudy_token',auth.access_token);
  localStorage.setItem('hustudy_user',auth.user.username);
  localStorage.setItem(`hustudy-bank-attempt:${courseId}`,'saved-attempt');
 },{auth:s.auth,courseId:s.course.id});
 await page.goto(`/exam?course=${s.course.id}`);
 await expect(page.getByRole('button',{name:'上传与校正题库',exact:true})).toHaveClass('primary');
 await expect(page.getByLabel('上传题库文件（PDF/ZIP/PPTX/DOCX/Markdown）')).toBeVisible();
 await page.getByRole('button',{name:'使用反馈',exact:true}).click();
 await page.getByRole('button',{name:'真题与模拟卷',exact:true}).click();
 await expect(page.getByRole('button',{name:'上传与校正题库',exact:true})).toHaveClass('primary');
 await page.reload();
 await expect(page.getByRole('button',{name:'上传与校正题库',exact:true})).toHaveClass('primary');
 expect(await page.evaluate(id=>localStorage.getItem(`hustudy-bank-attempt:${id}`),s.course.id)).toBe('saved-attempt');
});
test('上传Markdown题库，识别选项与含空位解答题并确认',async({page,request})=>{
 const s=await seed(request);await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},s.auth);
 await page.goto(`/exam?course=${s.course.id}`);
 await page.getByLabel('上传题库文件（PDF/ZIP/PPTX/DOCX/Markdown）').setInputFiles({name:'题库.md',mimeType:'text/markdown',buffer:Buffer.from(content)});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共3题'})).toBeVisible({timeout:30000});
 const item=page.locator('details.panel').filter({has:page.locator('summary').filter({hasText:'题号 2'})});
 if(await item.getAttribute('open')===null)await item.locator(':scope > summary').click();await item.getByText('编辑Markdown源码与答案',{exact:true}).click();await expect(item.getByLabel('题型',{exact:true})).toHaveValue('solution');
 await item.getByRole('button',{name:'保存本题校正'}).click();
 await expect(item.getByRole('button',{name:'保存本题校正'})).toBeEnabled();
 await page.getByRole('button',{name:'确认题库「题库.md」'}).click();
 await page.getByText('知识标签与题库概览',{exact:true}).click();
 await expect(page.getByText('可抽取 3 题',{exact:false})).toBeVisible();
});

for(const width of [1440,390])test(`题库练习保存恢复和分类批改 ${width}`,async({page,request})=>{
 await page.setViewportSize({width,height:900});const s=await seed(request);
 const imported=await(await request.post(`${base}/courses/${s.course.id}/question-bank/import`,{headers:s.headers,data:{title:'练习题库',content}})).json();
 for(const q of imported.questions){if(q.question_type==='fill_blank'){
  const r=await request.patch(`${base}/past-questions/${q.id}`,{headers:s.headers,data:{revision:q.revision,stem:q.stem,question_type:'fill_blank',answer:q.answer,blank_answers:q.bank_data.blank_answers,unique_answer:false,topic_ids:q.bank_data.topic_ids}});expect(r.ok()).toBeTruthy();
 }}
 expect((await request.post(`${base}/past-papers/${imported.id}/confirm`,{headers:s.headers})).ok()).toBeTruthy();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},s.auth);
 const calls:string[]=[];page.on('request',r=>{if(r.method()==='POST'&&/question-drafts|remote-queries/.test(r.url()))calls.push(r.url());});
 await page.goto(`/exam?course=${s.course.id}`);await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();
 await page.getByLabel('搜索知识标签',{exact:true}).fill('网络');await page.getByRole('button',{name:'＋ 网络',exact:true}).click();await page.getByLabel('题数',{exact:true}).fill('3');
 await page.getByRole('button',{name:'随机抽取题库练习'}).click();
 await page.getByRole('button',{name:'已核对题干，确认练习'}).click();await page.getByRole('button',{name:'开始作答',exact:true}).click();
 const choice=page.locator('.question-card').filter({hasText:'哪个属于传输层？'});
 await choice.getByRole('button',{name:/TCP/}).click();
 const fill=page.locator('.question-card').filter({hasText:'TCP名称是'});await fill.getByLabel('解答内容').fill('自己的说法');await fill.getByRole('button',{name:'保存本题答案'}).click();
 const solution=page.locator('.question-card').filter({hasText:'解释TCP。'});await solution.getByLabel('解答内容').fill('我提交了解答');await solution.getByRole('button',{name:'保存本题答案'}).click();
 await expect(solution.getByText('与服务器保存内容一致')).toBeVisible();
 await page.reload();await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();
 await expect(solution.getByLabel('解答内容')).toHaveValue('我提交了解答');
 await page.getByRole('button',{name:'交卷并查看答案'}).click();
 await expect(fill.getByRole('region',{name:'参考答案与解答'})).toContainText('传输控制协议');
 await fill.getByRole('button',{name:'我答错了'}).click();await expect(fill.getByText('自评错误',{exact:true})).toBeVisible();
 await expect(solution.getByText('解答题不自动判对错，可自行判断正误。')).toBeVisible();
 expect(calls).toEqual([]);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});

test('统计快照、标签改名后陈旧提示和完整蓝图抽题',async({page,request})=>{
 const s=await seed(request);
 const p=await(await request.post(`${base}/courses/${s.course.id}/question-bank/import`,{headers:s.headers,data:{title:'分析样卷',content,year:2024}})).json();
 for(const q of p.questions){if(q.question_type==='fill_blank')expect((await request.patch(`${base}/past-questions/${q.id}`,{headers:s.headers,data:{revision:q.revision,stem:q.stem,question_type:'fill_blank',blank_answers:q.bank_data.blank_answers,unique_answer:true,topic_ids:q.bank_data.topic_ids}})).ok()).toBeTruthy();}
 expect((await request.post(`${base}/past-papers/${p.id}/confirm`,{headers:s.headers})).ok()).toBeTruthy();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},s.auth);
 await page.goto(`/exam?course=${s.course.id}`);await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();
 await page.getByText('历史统计与资料缺口',{exact:true}).click();await page.getByRole('button',{name:'生成或重算统计快照'}).click();await expect(page.getByText('独立样本 1 份',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'网络 · 3题',exact:true}).click();const topic=page.locator('.bank-topic-content');
 await topic.getByLabel('标签名称',{exact:true}).fill('网络基础');await topic.getByRole('button',{name:'保存标签名称与别名'}).click();
 await expect(page.getByText('快照状态：STALE')).toBeVisible();await page.getByRole('button',{name:'生成或重算统计快照'}).click();await expect(page.getByText('快照状态：READY')).toBeVisible();
 await page.getByText('题库蓝图：明确题型、分值和标签数量',{exact:true}).click();await page.getByRole('button',{name:'确认蓝图并从题库抽取'}).click();await expect(page.getByRole('button',{name:'已核对题干，确认练习'})).toBeVisible();
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});

test('拆分与合并只保留当前叶子题，原题保留历史',async({page,request})=>{
 const s=await seed(request);
 const p=await(await request.post(`${base}/courses/${s.course.id}/question-bank/import`,{headers:s.headers,data:{title:'拆合题库',content:'1. 父题两个要求。\n分值：10\n知识标签：网络'}})).json();
 expect((await request.post(`${base}/past-papers/${p.id}/confirm`,{headers:s.headers})).ok()).toBeTruthy();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},s.auth);
 await page.goto(`/exam?course=${s.course.id}`);
 const parent=page.locator('details.panel').first();await parent.locator(':scope > summary').click();
 await parent.getByText('拆分本题为多个子题',{exact:true}).click();await parent.getByLabel('拆分子题正文').fill('第一子题。\n---\n第二子题。');
 await parent.getByRole('button',{name:'确认拆分本题'}).click();await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible();
 const items=page.locator('details.panel');for(let i=0;i<2;i++){await items.nth(i).locator(':scope > summary').click();await items.nth(i).getByRole('checkbox',{name:/选择题号/}).check();}
 page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'合并所选题目（2）',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible();
});

test('仅题目提示、批量标签、大尺寸选择和审核删除',async({page,request})=>{
 const s=await seed(request);
 const p=await(await request.post(`${base}/courses/${s.course.id}/question-bank/import`,{headers:s.headers,data:{title:'无答案题目',content:'1. 下列哪个正确？\nA.甲 B.乙 C.丙 D.丁\n2. 解释网络。'}})).json();
 const topic=await(await request.post(`${base}/courses/${s.course.id}/topics`,{headers:s.headers,data:{name:'测试标签'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},s.auth);
 await page.goto(`/exam?course=${s.course.id}`);
 const choice=page.locator('details.bank-question-editor').first();await choice.locator(':scope > summary').click();
 await expect(choice.getByText('导入内容：仅题目，未提供答案')).toBeVisible();
 await expect(choice.getByLabel('正确选项')).toHaveValue('');
 await page.getByLabel('全选本页').check();
 const rect=await page.getByLabel('全选本页').boundingBox();expect(rect!.width).toBeGreaterThanOrEqual(22);expect(rect!.height).toBeGreaterThanOrEqual(22);
 await page.getByLabel('批量知识标签',{exact:true}).fill(topic.name);await page.getByRole('button',{name:`＋ ${topic.name}`,exact:true}).click();await page.getByRole('button',{name:'都改成这个标签',exact:true}).click();
 await expect(choice.getByLabel('主知识标签（分值统计仅计此标签）')).toHaveValue(topic.id);
 await choice.getByRole('button',{name:'删除本题',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible();
 await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'删除所选',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共0题'})).toBeVisible();
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 expect(p.questions).toHaveLength(2);
});

test('本地实际图片OCR显式启动、按题号切分、裁取插图并确认',async({page,request})=>{
 const s=await seed(request);
 const topic=await(await request.post(`${base}/courses/${s.course.id}/topics`,{headers:s.headers,data:{name:'图文网络'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},s.auth);
 await page.goto(`/exam?course=${s.course.id}`);
 await page.getByLabel('统一知识标签（可选）',{exact:true}).fill(topic.name);await page.getByRole('button',{name:`＋ ${topic.name}`,exact:true}).click();
 await page.getByRole('button',{name:'图片识别（可选）',exact:true}).click();
 await page.getByLabel('选择题目图片（PNG/JPEG/WebP，可多选）').setInputFiles(fileURLToPath(new URL('../../../fixtures/question_bank_scan_demo.png',import.meta.url)));
 expect((await request.get(`${base}/courses/${s.course.id}/question-bank/image-jobs`,{headers:s.headers}).then(r=>r.json()))).toEqual([]);
 await page.getByRole('button',{name:'识别图片文字并拆分题目',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible({timeout:45000});
 const solution=page.locator('details.bank-question-editor').filter({has:page.locator('summary').filter({hasText:'题号 2'})});
 await expect(solution).toHaveAttribute('open','');
 await solution.getByText('编辑Markdown源码与答案',{exact:true}).click();
 await solution.getByText('从题目原图截图 / 裁取插图',{exact:true}).click();
 await expect(solution.getByRole('img',{name:'OCR原图区域（仅审核，不在作答展示）'})).toBeVisible();
 await solution.getByRole('button',{name:'调整裁剪区域'}).click();
 const picker=solution.getByRole('group',{name:'在原图拖动框选插图'});
 await expect(picker.getByRole('img')).toBeVisible();await picker.scrollIntoViewIfNeeded();const region=await picker.boundingBox();
 await page.mouse.move(region!.x+region!.width*.1,region!.y+region!.height*.6);await page.mouse.down();await page.mouse.move(region!.x+region!.width*.9,region!.y+region!.height*.8,{steps:5});await page.mouse.up();
 await solution.getByText('精确调整裁剪位置',{exact:true}).click();
 await expect(solution.getByLabel('裁剪宽度 %')).toHaveValue('80');
 for(const [label,value] of [['左侧位置 %','8'],['顶部位置 %','61'],['裁剪宽度 %','82'],['裁剪高度 %','17']])await solution.getByLabel(label).fill(value);
 await solution.getByRole('button',{name:'将预览区域用作插图'}).click();
 await solution.getByLabel('已核对插图').check();
 await solution.getByRole('button',{name:'保存本题校正',exact:true}).click();
 await expect(solution.getByRole('button',{name:'保存本题校正',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'确认题库「我的课程题库」',exact:true}).click();
 await expect(page.locator('.bank-paper-review .bank-badge').filter({hasText:'已确认'})).toBeVisible();
 await page.screenshot({path:'../local_only/m4-image-review-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.screenshot({path:'../local_only/m4-image-review-mobile.png',fullPage:true});
 const questions=await(await request.get(`${base}/courses/${s.course.id}/question-bank`,{headers:s.headers})).json();
 expect(questions.items.find((q:{number:string})=>q.number==='2').bank_data.illustrations).toHaveLength(1);
});

test('批量图片调整顺序并按双栏阅读顺序识别',async({page,request})=>{
 const s=await seed(request);
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},s.auth);
 await page.goto(`/exam?course=${s.course.id}`);await page.getByRole('button',{name:'图片识别（可选）',exact:true}).click();
 await page.getByLabel('选择题目图片（PNG/JPEG/WebP，可多选）').setInputFiles(['question_bank_columns_2.png','question_bank_columns_1.png'].map(name=>fileURLToPath(new URL('../../../fixtures/'+name,import.meta.url))));
 await page.getByRole('button',{name:'上移图片2',exact:true}).click();
 await expect(page.locator('.bank-image-queue li').first()).toContainText('question_bank_columns_1.png');
 await page.getByLabel('图片版面').selectOption('double');await page.getByRole('button',{name:'识别图片文字并拆分题目'}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共4题'})).toBeVisible({timeout:45000});
 const result=await(await request.get(`${base}/courses/${s.course.id}/question-bank`,{headers:s.headers})).json();
 expect(result.items.map((q:{number:string})=>q.number)).toEqual(['1','2','3','4']);
 expect(result.items.map((q:{bank_data:{source_images:Array<{box:number[]}>}})=>q.bank_data.source_images[0].box[0])).toEqual([0,.5,0,.5]);
});
