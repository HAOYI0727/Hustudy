import {test, expect, type APIRequestContext, type Page} from '@playwright/test';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {resolve, dirname} from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ReactMarkdown from 'react-markdown';

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(request: APIRequestContext, page: Page) {
  const username = 'folders_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '笔记整理验收'}})).json();
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '未归档笔记', content: '# 总览\n\n用于整理的笔记。', tags: ['基础']}})).json();
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  await page.goto(`/notes?course=${course.id}&note=${note.id}`);
  await expect(page.getByLabel('笔记标题')).toHaveValue(note.title);
  const showLibrary = async () => {const toggle = page.getByRole('button', {name: /笔记列表与新建/}); if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'false') await toggle.click();};
  await showLibrary();
  const notes = async () => await (await request.get(base + '/notes', {headers})).json();
  return {headers, course, note, showLibrary, notes};
}
async function evidence(page: Page, name: string) {
  if (!process.env.HUSTUDY_M3_EVIDENCE) return;
  await mkdir(resolve('../docs/fzk/evidence'), {recursive: true});
  await page.evaluate(() => {(document.activeElement as HTMLElement)?.blur(); window.scrollTo({top: 0, behavior: 'instant'});});
  await page.screenshot({path: resolve(`../docs/fzk/evidence/${name}.png`), fullPage: name !== 'note-editor-focus', animations: 'disabled'});
}

for (const width of [390, 1440]) test(`多级文件夹、批量MD和标签整理、原层级ZIP与离线图片 ${width}px`, async ({page, request, browser}, testInfo) => {
  test.setTimeout(120000);
  await page.setViewportSize({width, height: 1000});
  const s = await seed(request, page);
  await page.getByRole('button', {name: '＋ 新建文件夹', exact: true}).click();
  await page.getByLabel('文件夹名称', {exact: true}).fill('函数式编程');
  await page.getByRole('button', {name: '创建文件夹', exact: true}).click();
  await expect(page.locator('.folder-choice.active')).toContainText('函数式编程');
  await page.getByRole('button', {name: '编辑文件夹', exact: true}).click();
  await expect(page.getByLabel('上级文件夹')).toHaveValue('');
  await page.getByLabel('文件夹名称', {exact: true}).fill('编程基础');
  await page.getByRole('button', {name: '保存文件夹', exact: true}).click();
  await expect(page.locator('.folder-choice.active')).toContainText('编程基础');
  await page.getByRole('button', {name: '＋ 新建文件夹', exact: true}).click();
  await page.getByLabel('文件夹名称', {exact: true}).fill('第一章');
  await page.getByRole('button', {name: '创建文件夹', exact: true}).click();
  await expect(page.locator('.folder-choice.active')).toContainText('第一章');
  const folders = await (await request.get(base + '/note-folders?course_id=' + s.course.id, {headers: s.headers})).json();
  const child = folders.find((f: {name: string}) => f.name === '第一章');
  const bytes = await page.evaluate(() => {const c = document.createElement('canvas'); c.width = 32; c.height = 16; c.getContext('2d')!.fillRect(0,0,32,16); return c.toDataURL().split(',')[1];});
  const asset = await (await request.post(base + `/courses/${s.course.id}/assets`, {headers: s.headers, multipart: {file: {name: '图 #1.png', mimeType: 'image/png', buffer: Buffer.from(bytes, 'base64')}}})).json();
  await page.getByRole('button', {name: '导入 Markdown', exact: true}).click();
  await page.getByLabel('导入到文件夹').selectOption(child.id);
  await page.getByLabel('导入统一标签').fill('统一标签，重点');
  await page.getByLabel('选择Markdown文件').setInputFiles([
    {name: 'A 纯函数.md', mimeType: 'text/markdown', buffer: Buffer.from(`# 纯函数\n\n不修改外部状态。\n\n[[note:${s.note.id}|根目录笔记]]\n![[asset:${asset.id}|示意图]]`)},
    {name: 'B 不可变.md', mimeType: 'text/markdown', buffer: Buffer.from('# 不可变\n\n保留原值。')}
  ]);
  await page.getByRole('button', {name: '开始导入（2）', exact: true}).click();
  await expect(page.locator('.note-import-panel')).toContainText('已导入 2/2');
  let rows = await s.notes(); expect(rows).toHaveLength(3);
  expect(rows.filter((n: {folder_id: string}) => n.folder_id === child.id)).toHaveLength(2);
  await page.getByRole('button', {name: '关闭导入 Markdown', exact: true}).click();
  await page.getByRole('button', {name: '笔记管理', exact: true}).click();
  await page.getByLabel('选择笔记 A 纯函数', {exact: true}).check();
  await page.getByLabel('选择笔记 B 不可变', {exact: true}).check();
  await page.getByRole('button', {name: '批量整理', exact: true}).click();
  await page.getByLabel('批量标签', {exact: true}).fill('期末');
  page.once('dialog', d => d.accept());
  await page.getByRole('button', {name: '为所选添加标签', exact: true}).click();
  await expect(page.locator('.note-organizer')).toContainText('已更新 2 篇笔记');
  await page.getByRole('button', {name: '关闭批量整理', exact: true}).click();
  await page.getByRole('button', {name: '标签管理', exact: true}).click();
  await page.getByLabel('管理现有标签').selectOption('统一标签');
  await page.getByLabel('标签新名称').fill('重点');
  page.once('dialog', d => d.accept());
  await page.getByRole('button', {name: '改名或合并标签', exact: true}).click();
  await expect(page.getByLabel('管理现有标签').getByRole('option', {name: /统一标签/})).toHaveCount(0);
  await page.getByRole('button', {name: '关闭标签管理', exact: true}).click();
  await page.getByLabel('选择笔记 B 不可变', {exact: true}).check();
  await page.getByRole('button', {name: '批量整理', exact: true}).click();
  page.once('dialog', d => d.accept());
  await page.getByRole('button', {name: '移动所选笔记', exact: true}).click();
  await expect(page.locator('dialog[open] .note-organizer')).toContainText('已更新 1 篇笔记');
  await page.getByRole('button', {name: '关闭批量整理', exact: true}).click();
  await page.getByRole('button', {name: /^全部笔记/}).click();
  await expect(page.locator('.knowledge-item')).toHaveCount(3);
  rows = await s.notes();
  expect(rows.find((n: {title: string}) => n.title === 'B 不可变').folder_id).toBeNull();
  expect(rows.find((n: {title: string}) => n.title === 'A 纯函数').tags).toEqual(['重点','期末']);
  await page.locator('.knowledge-item').filter({hasText: 'A 纯函数'}).click();
  await page.getByRole('button', {name: /^文件夹与标签/}).click();
  await expect(page.getByLabel('笔记所在文件夹')).toHaveValue(child.id);
  await page.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
  await page.getByRole('button', {name: '分屏预览', exact: true}).click();
  await expect(page.locator('.markdown-preview img')).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await evidence(page, `note-organization-${width}`);
  await page.getByRole('button', {name: '选择笔记导出', exact: true}).click();
  await page.getByRole('button', {name: '全选当前列表', exact: true}).click();
  await page.getByRole('button', {name: '导出所选笔记（3）', exact: true}).click();
  await expect(page.getByRole('button', {name: '下载 ZIP', exact: true})).toBeVisible({timeout: 25000});
  const download = page.waitForEvent('download'); await page.getByRole('button', {name: '下载 ZIP', exact: true}).click();
  const zip = testInfo.outputPath('folders.zip'), destination = testInfo.outputPath('notes'); await (await download).saveAs(zip);
  const result = spawnSync('python', ['-c', 'import json,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None; z.extractall(sys.argv[2]); print(json.dumps(z.namelist()))', zip, destination], {encoding: 'utf8', windowsHide: true});
  expect(result.status, result.stderr).toBe(0);
  expect(JSON.parse(result.stdout).sort()).toEqual(['未归档笔记.md','B 不可变.md','编程基础/第一章/A 纯函数.md','images/图 #1.png'].sort());
  const member = resolve(destination, '编程基础/第一章/A 纯函数.md');
  const markdown = await readFile(member, 'utf8');
  const html = resolve(dirname(member), 'offline.html'); await writeFile(html, '<!doctype html><meta charset="utf-8">' + renderToStaticMarkup(createElement(ReactMarkdown, {children: markdown})));
  const offline = await browser.newContext({offline: true});
  try {const local = await offline.newPage(); await local.goto(pathToFileURL(html).href); await expect.poll(() => local.locator('img').evaluate(img => (img as HTMLImageElement).naturalWidth)).toBe(32); expect(await local.locator('a').first().getAttribute('href')).toContain('../../');} finally {await offline.close();}
});

test('MD响应丢失后显式重试，成功文件不重导且待导入继续', async ({page, request}) => {
  const s = await seed(request, page);
  await page.getByRole('button', {name: '导入 Markdown', exact: true}).click();
  let calls = 0;
  await page.route('**/api/v1/notes/import-markdown', async route => {
    calls++;
    if (calls !== 2) return route.continue();
    // WebKit's intercepted body omits file bytes. Submit the known fixture with
    // its original request UUID, then lose only the response seen by the page.
    const body=route.request().postDataBuffer()!.toString();
    const id=/name="request_id"\r\n\r\n([a-f0-9-]+)/.exec(body)![1];
    const response=await request.post(base+'/notes/import-markdown',{headers:s.headers,multipart:{file:{name:'乙.md',mimeType:'text/markdown',buffer:Buffer.from('内容 乙')},request_id:id,course_id:s.course.id,tags:'[]'}});
    expect(response.status()).toBe(201);expect((await response.json()).content).toBe('内容 乙');
    await route.abort('failed');
  });
  await page.getByLabel('选择Markdown文件').setInputFiles(['甲','乙','丙'].map(name => ({name: name+'.md', mimeType: 'text/markdown', buffer: Buffer.from('内容 '+name)})));
  await page.getByRole('button', {name: '开始导入（3）', exact: true}).click();
  await expect(page.locator('.note-import-panel')).toContainText('已导入 1/3');
  expect(await s.notes()).toHaveLength(3); // Seed + first + second, whose response was lost.
  await page.getByRole('button', {name: '重试未完成文件', exact: true}).click();
  await expect(page.locator('.note-import-panel')).toContainText('已导入 3/3');
  expect(calls).toBe(4); expect(await s.notes()).toHaveLength(4);
});

test('分类建议有依据、确认移动和批量冲突不覆盖', async ({page, request}) => {
  const s = await seed(request, page);
  const folder = await (await request.post(base + '/note-folders', {headers: s.headers, data: {course_id: s.course.id, name: '纯函数'}})).json();
  await request.post(base + '/notes', {headers: s.headers, data: {course_id: s.course.id, folder_id: folder.id, title: '代表笔记', tags: ['不可变']}});
  const candidate = await (await request.post(base + '/notes', {headers: s.headers, data: {course_id: s.course.id, title: '函数案例', tags: ['不可变']}})).json();
  await page.reload(); await s.showLibrary();
  await page.getByRole('button', {name: '推荐归类', exact: true}).click();
  await page.getByLabel('推荐目标文件夹').selectOption(folder.id);
  const suggestion = page.locator('.note-recommendations .note-export-choice').filter({hasText: candidate.title});
  await expect(suggestion).toContainText('共同标签：不可变');
  await suggestion.getByRole('checkbox').check();
  await request.patch(base + '/notes/' + candidate.id, {headers: s.headers, data: {revision: 1, content: '远端编辑'}});
  page.once('dialog', d => d.accept()); await page.getByRole('button', {name: '将勾选候选归入文件夹', exact: true}).click();
  await expect(page.locator('.toast.error')).toContainText('未修改任何笔记');
  expect((await s.notes()).find((n: {id: string}) => n.id === candidate.id).folder_id).toBeNull();
  await page.getByRole('button', {name: '关闭推荐归类', exact: true}).click();
  await page.getByRole('button', {name: '笔记管理', exact: true}).click();
  await page.getByRole('button', {name: '刷新笔记列表', exact: true}).click();
  await expect(page.getByRole('button', {name: '刷新笔记列表', exact: true})).toBeEnabled();
  await page.getByRole('button', {name: '推荐归类', exact: true}).click();
  page.once('dialog', d => d.accept()); await page.getByRole('button', {name: '将勾选候选归入文件夹', exact: true}).click();
  await expect(page.locator('.note-organizer')).toContainText('已更新 1 篇笔记');
  expect((await s.notes()).find((n: {id: string}) => n.id === candidate.id).folder_id).toBe(folder.id);
  await page.getByRole('button', {name: '关闭推荐归类', exact: true}).click();
  await page.getByRole('button', {name: '编辑笔记', exact: true}).click();
  await page.getByLabel('笔记标题').fill(''); await page.getByLabel('Markdown 正文').fill('本地未保存内容');
  await page.getByRole('button', {name: '笔记管理', exact: true}).click();
  await expect(page.getByRole('button', {name: '批量整理', exact: true})).toBeDisabled();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('本地未保存内容');
});

test('编辑器选区格式、撤销重做、列表、大纲、查找、分屏与快捷保存', async ({page, request}) => {
  await page.setViewportSize({width: 1440, height: 1000});
  const s = await seed(request, page);
  const editor = page.getByLabel('Markdown 正文');
  await editor.fill('# 标题\n\n选择重点');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(6,10);});
  await page.getByRole('button', {name: '加粗', exact: true}).click();
  await expect(editor).toHaveValue('# 标题\n\n**选择重点**');
  await editor.press('Control+z'); await expect(editor).toHaveValue('# 标题\n\n选择重点');
  await editor.press('Control+Shift+z'); await expect(editor).toHaveValue('# 标题\n\n**选择重点**');
  await editor.fill('- [x] 已完成'); await editor.press('End'); await editor.press('Enter');
  await expect(editor).toHaveValue('- [x] 已完成\n- [ ] ');
  await editor.press('Enter'); await expect(editor).toHaveValue('- [x] 已完成\n');
  await editor.fill('# 标题\n\n## 章节\n\n可查找的内容 <script>window.bad=true</script>');
  await page.getByLabel('笔记大纲').selectOption('6');
  await expect.poll(()=>editor.evaluate((el: HTMLTextAreaElement) => el.selectionStart)).toBe(6);
  await page.getByLabel('查找正文').fill('查找'); await page.getByRole('button', {name: '下一个匹配', exact: true}).click();
  await expect.poll(()=>editor.evaluate((el: HTMLTextAreaElement) => el.value.slice(el.selectionStart, el.selectionEnd))).toBe('查找');
  await editor.press('Control+s'); await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await page.getByRole('button', {name: '分屏预览', exact: true}).click();
  await expect(page.getByLabel('笔记实时预览')).toContainText('可查找的内容');
  expect(await page.evaluate(() => (window as unknown as {bad?: boolean}).bad)).toBeUndefined();
  await page.getByRole('button', {name: '专注编辑', exact: true}).click(); await expect(page.locator('.knowledge-editor.is-focused')).toBeVisible();
  await evidence(page, 'note-editor-focus');
  await page.keyboard.press('Escape'); await expect(page.locator('.knowledge-editor.is-focused')).toHaveCount(0);
  expect((await s.notes()).find((n: {id: string}) => n.id === s.note.id).content).toContain('可查找的内容');
});

test('首次自动保存保持正文焦点与撤销历史，换笔记清空历史', async ({page, request}) => {
  const s = await seed(request, page);
  await page.getByRole('button', {name: '新建笔记', exact: true}).click();
  await page.getByLabel('笔记标题').fill('首次保存');
  const editor = page.getByLabel('Markdown 正文');
  await editor.fill('自动保存时继续编辑');
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await expect(editor).toBeFocused();
  await page.getByRole('button', {name: '撤销', exact: true}).click();
  await expect(editor).toHaveValue('');
  await page.getByRole('button', {name: '重做', exact: true}).click();
  await expect(editor).toHaveValue('自动保存时继续编辑');
  await s.showLibrary();
  await page.locator('.knowledge-item').filter({hasText: '未归档笔记'}).click();
  await expect(page.getByRole('button', {name: '撤销', exact: true})).toBeDisabled();
  await expect(editor).toHaveValue(s.note.content);
});

test('批量请求期间锁定正文，完成后继续编辑保留新标签', async ({page, request}) => {
  const s = await seed(request, page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release = resolve;});
  await page.route('**/api/v1/notes/batch', async route => {await gate; await route.continue();});
  await page.getByRole('button', {name: '笔记管理', exact: true}).click();
  await page.getByLabel('选择笔记 未归档笔记', {exact: true}).check();
  await page.getByRole('button', {name: '批量整理', exact: true}).click();
  await page.getByLabel('批量标签', {exact: true}).fill('批量标签');
  page.once('dialog', d => d.accept());
  await page.getByRole('button', {name: '为所选添加标签', exact: true}).click();
  const editor = page.getByLabel('Markdown 正文');
  await expect(page.locator('.knowledge-editor')).toHaveAttribute('inert', '');
  await editor.evaluate((el: HTMLTextAreaElement) => el.focus());
  await expect(editor).not.toBeFocused();
  await page.keyboard.type('不能进入正文');
  release();
  await expect(page.locator('.note-organizer')).toContainText('已更新 1 篇笔记');
  await expect(page.locator('.knowledge-editor')).not.toHaveAttribute('inert', '');
  await page.getByRole('button', {name: '关闭批量整理', exact: true}).click();
  await page.getByRole('button', {name: '编辑笔记', exact: true}).click();
  await expect(editor).toHaveValue(s.note.content);
  await editor.fill('批量结束后继续写作'); await editor.press('Control+s');
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const saved = (await s.notes()).find((n: {id: string}) => n.id === s.note.id);
  expect(saved.tags).toContain('批量标签'); expect(saved.content).toBe('批量结束后继续写作');
});
