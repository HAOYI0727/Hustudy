import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const base = 'http://127.0.0.1:8056/api/v1';
async function seed(page: Page, request: APIRequestContext) {
  const username = 'text_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '文本插入验收'}})).json();
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '保留标题', content: '开头待替换结尾'}})).json();
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  await page.goto('/notes?course=' + course.id + '&note=' + note.id);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(note.content);
  return {headers, course, note};
}
function capture(courseId: string) {
  return {id: 'test-capture', filename: '课堂.pdf', course_id: courseId, status: 'SUCCEEDED', kind: 'NOTE_CAPTURE', error: null,
    result: {text: '### 第1页\n\n原始识别内容', parts: [{location: '第1页', text: '原始识别内容', method: 'ocr'}], warnings: ['请核对识别结果']}, ai_result: {markdown: '# 旧AI结果'}};
}
async function mockCapture(page: Page, courseId: string) {
  await page.route('**/note-captures?*', route => route.fulfill({json: [capture(courseId)]}));
}
for (const width of [390, 1440]) test('识别仅插入当前笔记、关闭保留、撤销保存 ' + width, async ({page, request}, info) => {
  await page.setViewportSize({width, height: 960});
  const {headers, course, note} = await seed(page, request);
  await mockCapture(page, course.id);
  const writes: string[] = [];
  page.on('request', req => {if (req.method() === 'POST' && (req.url().endsWith('/notes') || req.url().includes('/organize'))) writes.push(req.url());});
  const editor = page.getByLabel('Markdown 正文');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(2, 5);});
  await page.getByRole('button', {name: '文字识别', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '文字识别', exact: true});
  await dialog.getByLabel('识别任务', {exact: true}).selectOption('test-capture');
  await expect(dialog.getByLabel('识别文字', {exact: true})).toHaveValue('原始识别内容');
  await expect(dialog.getByLabel('识别笔记标题')).toHaveCount(0);
  await expect(dialog.getByRole('button', {name: /AI|保存为笔记/})).toHaveCount(0);
  await dialog.getByLabel('识别文字', {exact: true}).fill('核对后的文本\n第二行');
  await dialog.getByRole('button', {name: '关闭文字识别'}).click();
  await expect(editor).toHaveValue(note.content);
  await page.getByRole('button', {name: '文字识别', exact: true}).click();
  await expect(dialog.getByLabel('识别文字', {exact: true})).toHaveValue('核对后的文本\n第二行');
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  if (process.env.HUSTUDY_M3_EVIDENCE) {
    await mkdir(resolve('../docs/fzk/evidence'), {recursive: true});
    await page.screenshot({path: resolve('../docs/fzk/evidence/capture-text-' + width + '-' + info.project.name + '.png')});
  }
  await dialog.getByRole('button', {name: '插入正文', exact: true}).click();
  const content = '开头核对后的文本\n第二行结尾';
  await expect(editor).toHaveValue(content);
  await expect(page.getByLabel('笔记标题')).toHaveValue(note.title);
  await page.getByRole('button', {name: '撤销', exact: true}).click();
  await expect(editor).toHaveValue(note.content);
  await page.getByRole('button', {name: '重做', exact: true}).click();
  await expect(editor).toHaveValue(content);
  await editor.press('Control+s'); await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const notes = await (await request.get(base + '/notes', {headers})).json();
  expect(notes).toHaveLength(1); expect(notes[0].id).toBe(note.id); expect(notes[0].content).toBe(content);
  expect(writes).toEqual([]);
  await page.reload(); await expect(editor).toHaveValue(content);
});

test('真实DOCX后台识别为文本并追加当前笔记，没有生成新笔记', async ({page, request}) => {
  test.setTimeout(90000);
  const {headers, note} = await seed(page, request);
  const data = execFileSync('python', ['-c', 'from docx import Document; import io,sys; d=Document(); d.add_heading("Source title",1); d.add_paragraph("Plain recognized text."); b=io.BytesIO(); d.save(b); sys.stdout.buffer.write(b.getvalue())']);
  const editor = page.getByLabel('Markdown 正文');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(el.value.length, el.value.length);});
  await page.getByRole('button', {name: '文字识别', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '文字识别', exact: true});
  await dialog.locator('input[type=file]').setInputFiles({name: 'self-authored.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: data});
  await dialog.getByRole('button', {name: '上传并识别 / 重试上传'}).click();
  await expect(dialog.getByLabel('识别文字', {exact: true})).toHaveValue('Source title\n\nPlain recognized text.', {timeout: 40000});
  expect(await (await request.get(base + '/notes', {headers})).json()).toHaveLength(1);
  await dialog.getByRole('button', {name: '插入正文', exact: true}).click();
  await expect(editor).toHaveValue(note.content + 'Source title\n\nPlain recognized text.');
  await editor.press('Control+s'); await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect(await (await request.get(base + '/notes', {headers})).json()).toHaveLength(1);
});

test('识别401后草稿恢复，管理页无AI或识别新建入口', async ({page, request}) => {
  const {course} = await seed(page, request);
  let expired = false;
  await page.route('**/note-captures?*', route => expired ? route.fulfill({status: 401, json: {error: {message: '登录已过期'}}}) : route.fulfill({json: [capture(course.id)]}));
  await page.getByRole('button', {name: '文字识别', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '文字识别', exact: true});
  await dialog.getByLabel('识别任务', {exact: true}).selectOption('test-capture');
  await dialog.getByLabel('识别文字', {exact: true}).fill('登录后保留的文本'); expired = true;
  const login = page.getByRole('dialog', {name: /登录已过期/});
  await expect(login).toBeVisible(); await expect(dialog).not.toBeVisible(); expired = false;
  await login.getByLabel('密码', {exact: true}).fill('Test-password-2026');
  await login.getByRole('button', {name: '登录', exact: true}).click(); await expect(login).not.toBeVisible();
  await page.getByRole('button', {name: '文字识别', exact: true}).click();
  await expect(dialog.getByLabel('识别文字', {exact: true})).toHaveValue('登录后保留的文本');
  await dialog.getByRole('button', {name: '插入正文', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(/登录后保留的文本/);
  await page.getByLabel('Markdown 正文').press('Control+s'); await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await page.goto('/notes?course=' + course.id);
  await expect(page.getByRole('button', {name: '新建笔记', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: /^(文字识别导入|AI 配置|文字识别)$/})).toHaveCount(0);
});

test('并发409保留识别文字且禁止覆盖，重新定位后可插入', async ({page, request}) => {
  const {headers, course, note} = await seed(page, request);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await mockCapture(page, course.id);
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release = resolve;});
  await page.route('**/api/v1/notes/*', async route => {
    if (route.request().method() === 'PATCH') await gate;
    await route.continue();
  });
  const editor = page.getByLabel('Markdown 正文');
  await editor.fill('未保存的本地正文');
  await page.getByRole('button', {name: '文字识别', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '文字识别', exact: true});
  await dialog.getByLabel('识别任务', {exact: true}).selectOption('test-capture');
  await dialog.getByLabel('识别文字', {exact: true}).fill('待插入文字');
  await request.patch(base + '/notes/' + note.id, {headers, data: {revision: note.revision, content: '并发版本'}});
  release();
  await expect(page.getByRole('heading', {name: '检测到另一处修改'})).toBeVisible({timeout: 10000});
  await expect(dialog.getByRole('button', {name: '插入正文', exact: true})).toBeDisabled();
  await expect(editor).toHaveValue('未保存的本地正文');
  await dialog.getByRole('button', {name: '关闭文字识别'}).click();
  page.once('dialog', d => d.accept());
  await page.getByRole('button', {name: '载入服务端版本'}).click();
  await expect(editor).toHaveValue('并发版本');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.setSelectionRange(el.value.length, el.value.length);});
  await page.getByRole('button', {name: '文字识别', exact: true}).click();
  await expect(dialog.getByLabel('识别文字', {exact: true})).toHaveValue('待插入文字');
  await dialog.getByRole('button', {name: '插入正文', exact: true}).click();
  await expect(editor).toHaveValue('并发版本待插入文字');
});

test('语音输入预览去重、停止插入选区、权限错误与关闭释放', async ({page, request}) => {
  const username = `dictation_${Date.now()}`;
  const auth = await (await request.post('http://127.0.0.1:8056/api/v1/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const course = await (await request.post('http://127.0.0.1:8056/api/v1/courses', {headers: {Authorization: 'Bearer ' + auth.access_token}, data: {name: '听写测试'}})).json();
  await page.addInitScript(({token, username}) => {
    localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);
    const w = window as any;
    w.speechCalls = 0; w.speechAborts = 0;
    w.SpeechRecognition = class {
      onresult: any; onend: any; onerror: any;
      start() {w.speechCalls++; w.speech = this;}
      stop() {this.onend?.();}
      abort() {w.speechAborts++; this.onend?.();}
    };
  }, {token: auth.access_token, username});
  await page.goto(`/notes?course=${course.id}`);
  await page.getByRole('button', {name: '新建笔记', exact: true}).click();
  const editor = page.getByLabel('Markdown 正文');
  await editor.fill('开头待替换结尾');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.setSelectionRange(2, 5);});
  await page.getByRole('button', {name: '语音输入', exact: true}).click();
  await expect(page.getByRole('button', {name: '开始语音输入'})).toBeDisabled();
  expect(await page.evaluate(() => (window as any).speechCalls)).toBe(0);
  await page.getByLabel('允许本次使用浏览器语音服务').check();
  await page.getByRole('button', {name: '开始语音输入'}).click();
  const emit = () => page.evaluate(() => {const w = window as any; w.speech.onresult({results: [{isFinal: true, 0: {transcript: '事务具有原子性。'}}, {isFinal: false, 0: {transcript: '正在识别'}}]});});
  await emit(); await emit();
  await expect(page.getByLabel('语音识别文字')).toHaveValue('事务具有原子性。');
  await expect(page.getByRole('button', {name: '插入正文', exact: true})).toBeDisabled();
  await page.getByRole('button', {name: '停止语音输入'}).click();
  await page.getByRole('button', {name: '插入正文', exact: true}).click();
  await expect(editor).toHaveValue('开头事务具有原子性。结尾');
  await page.getByRole('button', {name: '语音输入', exact: true}).click();
  await page.getByRole('button', {name: '开始语音输入'}).click();
  await page.evaluate(() => {const w = window as any; w.speech.onerror({error: 'not-allowed'}); w.speech.onend();});
  await expect(page.getByRole('alert').filter({hasText: '麦克风权限被拒绝'})).toBeVisible();
  await page.getByRole('button', {name: '开始语音输入'}).click();
  await page.getByRole('button', {name: '关闭语音输入'}).click();
  expect(await page.evaluate(() => (window as any).speechAborts)).toBeGreaterThan(0);
  await expect(editor).toHaveValue('开头事务具有原子性。结尾');
});
