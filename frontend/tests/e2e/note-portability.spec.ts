import {test, expect, type APIRequestContext, type Page} from '@playwright/test';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ReactMarkdown from 'react-markdown';

async function testImage(page: Page) {
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 320; canvas.height = 160;
    const context = canvas.getContext('2d')!;
    context.fillStyle = '#e9f0ff'; context.fillRect(0, 0, 320, 160);
    context.fillStyle = '#4665cc'; context.fillRect(24, 44, 100, 72); context.fillRect(196, 44, 100, 72);
    context.fillStyle = '#ffffff'; context.font = '18px sans-serif'; context.fillText('READY', 40, 86); context.fillText('RUNNING', 202, 86);
    context.strokeStyle = '#4665cc'; context.lineWidth = 4; context.beginPath(); context.moveTo(132, 80); context.lineTo(184, 80); context.stroke();
    return canvas.toDataURL('image/png').split(',')[1];
  });
  return {name: '进程 状态图.png', mimeType: 'image/png', buffer: Buffer.from(encoded, 'base64')};
}

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(request: APIRequestContext, page: Page) {
  const username = 'portable_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '笔记导出与生命周期'}})).json();
  const target = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '链接目标', content: '目标概念正文', tags: ['定义']}})).json();
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '复习提纲', content: `## 复习\n\n[[note:${target.id}|原始名称]]`, tags: ['期末']}})).json();
  await page.addInitScript(({token, username}) => {
    localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);
  }, {token: auth.access_token, username});
  await page.goto(`/notes?course=${course.id}&note=${note.id}`);
  await expect(page.getByLabel('笔记标题')).toHaveValue('复习提纲');
  return {headers, course, target, note};
}

test('批量图片插入、精确选择ZIP及解压后断网Markdown图片显示', async ({page, request, browser}, testInfo) => {
  // Includes Vite cold start, a real worker ZIP, and a second offline browser context.
  test.setTimeout(90000);
  const s = await seed(request, page);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  const first = {...await testImage(page), name: '图 A #1.png'};
  const second = {...first, name: '图 B 中文.png'};
  await expect(page.getByLabel('选择上传的笔记图片')).toHaveAttribute('multiple', '');
  await page.getByLabel('选择上传的笔记图片').setInputFiles([first, second]);
  await expect(page.locator('.image-upload-status')).toContainText('已上传并插入 2 张图片');
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const body = await page.getByLabel('Markdown 正文').inputValue();
  const ids = [...body.matchAll(/!\[\[asset:([\w-]+)/g)].map(match => match[1]);
  expect(ids).toHaveLength(2);
  expect(body.indexOf('图 A #1')).toBeLessThan(body.indexOf('图 B 中文'));
  await request.patch(base + '/notes/' + s.target.id, {headers: s.headers, data: {revision: 1, content: `![[asset:${ids[0]}|共用图片]]`}});
  const extra = await (await request.post(base + `/courses/${s.course.id}/assets`, {headers: s.headers, multipart: {file: {...first, name: '不应导出.png'}}})).json();
  await request.post(base + '/notes', {headers: s.headers, data: {course_id: s.course.id, title: '不应导出的第三篇', content: `![[asset:${extra.id}|未选图片]]`}});
  await page.reload();
  await page.getByRole('button', {name: 'Markdown 预览', exact: true}).click();
  await expect(page.locator('.markdown-preview img')).toHaveCount(2);
  await expect.poll(() => page.locator('.markdown-preview img').evaluateAll(images => images.every(image => (image as HTMLImageElement).naturalWidth === 320))).toBe(true);
  await page.getByRole('button', {name: '选择笔记导出', exact: true}).click();
  for (const title of ['复习提纲', '链接目标']) await page.locator('.note-export-choice').filter({hasText: title}).getByRole('checkbox').check();
  await page.getByRole('button', {name: '导出所选笔记（2）', exact: true}).click();
  const exports = page.getByRole('region', {name: '知识库导出'});
  await expect(exports.getByRole('button', {name: '下载 ZIP', exact: true})).toBeVisible({timeout: 20000});
  const pending = page.waitForEvent('download');
  await exports.getByRole('button', {name: '下载 ZIP', exact: true}).click();
  const zip = testInfo.outputPath('selected-images.zip'); await (await pending).saveAs(zip);
  const directory = testInfo.outputPath('extracted');
  const extracted = spawnSync(process.platform === 'win32' ? 'python' : 'python3', ['-c',
    'import json,sys,zipfile,pathlib; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None; assert all(not pathlib.PurePosixPath(n).is_absolute() and ".." not in pathlib.PurePosixPath(n).parts for n in z.namelist()); z.extractall(sys.argv[2]); print(json.dumps(z.namelist()))', zip, directory], {encoding: 'utf8', windowsHide: true});
  expect(extracted.status, extracted.stderr).toBe(0);
  expect(JSON.parse(extracted.stdout).sort()).toEqual(['复习提纲.md', '链接目标.md', 'images/图 A #1.png', 'images/图 B 中文.png'].sort());
  const markdown = await readFile(resolve(directory, '复习提纲.md'), 'utf8');
  // Render actual exported Markdown with the same standard Markdown renderer, then open as a local file.
  const html = '<!doctype html><meta charset="utf-8"><title>离线笔记图片验收</title>' + renderToStaticMarkup(createElement(ReactMarkdown, {children: markdown}));
  const documentPath = resolve(directory, 'offline-test.html'); await writeFile(documentPath, html);
  const offline = await browser.newContext({offline: true});
  try {
    const local = await offline.newPage();
    await local.goto(pathToFileURL(documentPath).href);
    await expect(local.locator('img')).toHaveCount(2);
    await expect.poll(() => local.locator('img').evaluateAll(images => images.every(image => (image as HTMLImageElement).naturalWidth === 320))).toBe(true);
    expect(await local.locator('img').evaluateAll(images => images.every(image => (image as HTMLImageElement).src.startsWith('file:')))).toBe(true);
    if (process.env.HUSTUDY_M3_EVIDENCE) await local.screenshot({path: resolve('../docs/fzk/evidence/note-offline-images.png'), fullPage: true});
  } finally {await offline.close();}
});

test('批量部分失败仅重试未完成项，图库也支持多选导入', async ({page, request}) => {
  const s = await seed(request, page);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  const first = {...await testImage(page), name: '第一张.png'};
  const failed = {...first, name: '第二张.png'};
  let attempts = 0;
  await page.route(`**/api/v1/courses/${s.course.id}/assets?*`, async route => {
    if (route.request().method() === 'POST' && ++attempts === 2) await route.fulfill({status: 422, contentType: 'application/json', body: JSON.stringify({error: {message: '测试图片校验失败'}})});
    else await route.continue();
  });
  await page.getByLabel('选择上传的笔记图片').setInputFiles([first, failed]);
  await expect(page.locator('.image-upload-status')).toContainText('已上传并插入 1 张图片，1 张未完成');
  await expect(page.locator('.note-upload-error')).toContainText('第二张.png');
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await page.getByRole('button', {name: '重试未完成图片（1）', exact: true}).click();
  await expect(page.locator('.note-upload-error')).toHaveCount(0);
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect(attempts).toBe(3);
  const saved = await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json();
  expect([...saved.content.matchAll(/!\[\[asset:/g)]).toHaveLength(2);
  await page.getByRole('button', {name: '管理图片', exact: true}).click();
  const library = page.getByRole('dialog', {name: '管理图片', exact: true}).locator('.asset-library');
  const input = library.getByLabel('选择图片', {exact: true});
  await expect(input).toHaveAttribute('multiple', '');
  await input.setInputFiles([{...first, name: '第三张.png'}, {...first, name: '第四张.png'}]);
  await library.getByRole('button', {name: '导入图片', exact: true}).click();
  await expect(library.locator('.image-upload-status')).toContainText('已导入 2 张图片');
  await expect(library.locator('.asset-grid article')).toHaveCount(4);
  expect(attempts).toBe(5);
  expect(await (await request.get(base + `/courses/${s.course.id}/assets`, {headers: s.headers})).json()).toHaveLength(4);
  expect((await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json()).content).toBe(saved.content);
});

for (const width of [390, 1440]) {
  test(`知识库真实worker打包、下载、删除及双链失效 ${width}px`, async ({page, request}, testInfo) => {
    await page.setViewportSize({width, height: 1000});
    const s = await seed(request, page);
    await page.getByLabel('自动保存笔记', {exact: true}).check();
    await page.getByRole('button', {name: '插入图片与双链', exact: true}).click();
    await expect(page.getByLabel('插入课程图片')).toBeDisabled();
    await page.getByRole('button', {name: '关闭插入图片与双链', exact: true}).click();
    const image = await testImage(page);
    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button', {name: '上传图片并插入', exact: true}).click();
    await (await chooser).setFiles(image);
    await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
    await page.getByRole('button', {name: 'Markdown 预览', exact: true}).click();
    const picture = page.getByRole('img', {name: '进程 状态图', exact: true});
    await expect(picture).toBeVisible();
    await expect.poll(() => picture.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBe(320);
    await page.getByRole('button', {name: '选择笔记导出', exact: true}).click();
    await page.getByRole('button', {name: '全选当前列表', exact: true}).click();
    await page.getByRole('button', {name: '导出所选笔记（2）', exact: true}).click();
    const exports = page.getByRole('region', {name: '知识库导出'});
    await expect(exports.getByRole('button', {name: '下载 ZIP', exact: true})).toBeVisible({timeout: 20000});
    await expect(exports).toContainText('2 篇笔记');
    await expect(exports).toContainText('1 张图片');
    const download = page.waitForEvent('download');
    await exports.getByRole('button', {name: '下载 ZIP', exact: true}).click();
    const saved = await download;
    expect(saved.suggestedFilename()).toMatch(/^Hustudy-笔记知识库-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d{3}\.zip$/);
    const path = testInfo.outputPath('notes.zip'); await saved.saveAs(path);
    expect((await readFile(path)).subarray(0, 2).toString()).toBe('PK');
    const python = process.platform === 'win32' ? 'python' : 'python3';
    const members = spawnSync(python, ['-c', 'import json,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None; print(json.dumps(z.namelist()))', path], {encoding: 'utf8', windowsHide: true});
    expect(members.status).toBe(0);
    expect(JSON.parse(members.stdout).sort()).toEqual(['复习提纲.md', '链接目标.md', 'images/进程 状态图.png'].sort());
    if (process.env.HUSTUDY_M3_EVIDENCE) {
      const directory = resolve('../docs/fzk/evidence'); await mkdir(directory, {recursive: true});
      await page.evaluate(() => { (document.activeElement as HTMLElement)?.blur(); window.scrollTo({top: 0, behavior: 'instant'}); });
      await page.screenshot({path: resolve(directory, `note-selected-images-${width}.png`), fullPage: true, animations: 'disabled'});
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.getByRole('button', {name: '关闭导出笔记', exact: true}).click();
    await page.getByRole('button', {name: /^引用与关联/}).click();
    await page.getByRole('button', {name: '↗ 链接目标', exact: true}).click();
    await page.getByLabel('笔记标题').fill('重命名后的目标');
    await page.getByRole('button', {name: '立即保存', exact: true}).click();
    await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
    await page.getByRole('button', {name: /^引用与关联/}).click();
    await page.getByRole('button', {name: '↙ 复习提纲', exact: true}).click();
    await page.getByRole('button', {name: /^引用与关联/}).click();
    await expect(page.getByRole('button', {name: '↗ 重命名后的目标', exact: true})).toBeVisible();
    await page.getByRole('button', {name: '↗ 重命名后的目标', exact: true}).click();
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('button', {name: '删除这篇笔记', exact: true}).click();
    await expect(page.getByLabel('笔记标题')).toHaveValue('重命名后的目标');
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', {name: '删除这篇笔记', exact: true}).click();
    await expect(page.getByLabel('笔记标题')).toHaveValue('');
    await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
    await page.getByRole('button', {name: 'Markdown 预览', exact: true}).click();
    await expect(page.locator('.markdown-preview')).toContainText('目标笔记已删除');
    await page.getByRole('button', {name: '选择笔记导出', exact: true}).click();
    await expect(exports).toContainText('包内来源或文件已不可用');
    await expect(exports.getByRole('button', {name: '下载 ZIP', exact: true})).toHaveCount(0);
    page.once('dialog', dialog => dialog.accept());
    await exports.getByRole('button', {name: '移除记录', exact: true}).click();
    await expect(exports).toContainText('尚无导出记录');
  });
}

test('已有笔记网络恢复自动保存，删除冲突保留本地内容', async ({page, request}) => {
  const s = await seed(request, page);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.route(`**/api/v1/notes/${s.note.id}`, route => route.request().method() === 'PATCH' ? route.abort('failed') : route.continue());
  await page.getByLabel('Markdown 正文').fill('离线修改正文');
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.getByRole('alert').filter({hasText: '网络连接失败'})).toBeVisible();
  await page.unroute(`**/api/v1/notes/${s.note.id}`);
  await page.evaluate(() => window.dispatchEvent(new Event('online')));
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const saved = await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json();
  expect(saved.content).toBe('离线修改正文');
  await request.patch(base + '/notes/' + s.note.id, {headers: s.headers, data: {revision: saved.revision, content: '另一窗口的较新版本'}});
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', {name: '删除这篇笔记', exact: true}).click();
  await expect(page.locator('.conflict-panel')).toContainText('另一窗口的较新版本');
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('离线修改正文');
  const stillThere = await request.get(base + '/notes/' + s.note.id, {headers: s.headers});
  expect(stillThere.status()).toBe(200);
});

test('新笔记响应丢失后自动恢复不重复创建，并保存等待期间的修改', async ({page, request}) => {
  const s = await seed(request, page);
  const toggle = page.getByRole('button', {name: /笔记列表与新建/});
  if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'false') await toggle.click();
  await page.getByRole('button', {name: '新建笔记', exact: true}).click();
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  let first = true;
  await page.route('**/api/v1/notes', async route => {
    if (route.request().method() === 'POST' && first) {
      first = false;
      const response = await route.fetch(); expect(response.status()).toBe(201);
      await route.abort('failed');
    } else await route.continue();
  });
  await page.getByLabel('笔记标题').fill('响应丢失恢复');
  await page.getByLabel('Markdown 正文').fill('最初的正文');
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.getByRole('alert').filter({hasText: '网络连接失败'})).toBeVisible();
  await page.getByLabel('Markdown 正文').fill('断网等待期间继续补充');
  await page.evaluate(() => window.dispatchEvent(new Event('online')));
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务', {timeout: 15000});
  await expect.poll(async () => {
    const rows = await (await request.get(base + '/notes?course_id=' + s.course.id, {headers: s.headers})).json();
    const matches = rows.filter((n: {title: string}) => n.title === '响应丢失恢复');
    return matches.length === 1 ? matches[0].content : 'duplicate or missing';
  }).toBe('断网等待期间继续补充');
});

test('跨课程双链可打开和保存，课程归属与目录保持正确', async ({page, request}) => {
  const s = await seed(request, page);
  const other = await (await request.post(base + '/courses', {headers: s.headers, data: {name: '第二课程'}})).json();
  const linked = await (await request.post(base + '/notes', {headers: s.headers, data: {course_id: other.id, title: '第二课程概念', content: '跨课程连接', tags: ['其他课标签']}})).json();
  await request.patch(base + '/notes/' + s.note.id, {headers: s.headers, data: {revision: 1, content: `[[note:${linked.id}|跨课]]`}});
  await page.reload();
  await page.getByRole('button', {name: /^引用与关联/}).click();
  await page.getByRole('button', {name: '↗ 第二课程概念', exact: true}).click();
  await expect(page.getByLabel('笔记标题')).toHaveValue('第二课程概念');
  await expect(page.getByText('当前打开的是其他课程的关联笔记；保存会保留其原有归属。')).toBeVisible();
  await page.getByLabel('Markdown 正文').fill('跨课程编辑后保存');
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const saved = await (await request.get(base + '/notes/' + linked.id, {headers: s.headers})).json();
  expect(saved.course_id).toBe(other.id);
  expect(saved.content).toBe('跨课程编辑后保存');
  await expect(page.locator('.knowledge-item')).toHaveCount(2);
  await expect(page.getByLabel('按标签筛选笔记').getByRole('option', {name: '其他课标签', exact: true})).toHaveCount(0);
});

test('图片校验失败保留正文，上传中继续输入不被覆盖', async ({page, request}) => {
  const s = await seed(request, page);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  const input = page.getByLabel('选择上传的笔记图片');
  await input.setInputFiles({name: '伪装图片.png', mimeType: 'image/png', buffer: Buffer.from('not an image')});
  await expect(page.locator('.note-upload-error')).toContainText('图片无法解码');
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.note.content);
  expect(await (await request.get(base + `/courses/${s.course.id}/assets`, {headers: s.headers})).json()).toHaveLength(0);
  await input.setInputFiles({name: '过大.png', mimeType: 'image/png', buffer: Buffer.alloc(10 * 1024 * 1024 + 1)});
  await expect(page.locator('.note-upload-error')).toContainText('不能超过 10 MiB');
  const file = await testImage(page);
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/api/v1/courses/${s.course.id}/assets?*`, async route => {
    await pending;
    // Keep the browser's original multipart body (WebKit route.fetch omits file bytes).
    await route.continue();
  });
  await input.setInputFiles(file);
  await expect(page.locator('.save-indicator')).toHaveText('正在上传图片…');
  await page.getByLabel('Markdown 正文').fill('图片上传期间补充的新正文');
  await page.getByRole('button', {name: '资料阅读', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('图片上传期间补充的新正文');
  release();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const saved = await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json();
  expect(saved.content).toMatch(/^图片上传期间补充的新正文\n!\[\[asset:/);
  await page.getByRole('button', {name: 'Markdown 预览', exact: true}).click();
  await expect(page.getByRole('img', {name: '进程 状态图', exact: true})).toBeVisible();
});

test('单篇标题下载与勾选纯Markdown ZIP，不导出未选择笔记', async ({page, request}, testInfo) => {
  await seed(request, page);
  const single = page.waitForEvent('download');
  await page.getByRole('button', {name: '导出 .md', exact: true}).click();
  expect((await single).suggestedFilename()).toBe('复习提纲.md');
  await page.getByRole('button', {name: '选择笔记导出', exact: true}).click();
  const exports = page.getByRole('region', {name: '知识库导出'});
  await expect(exports.getByRole('button', {name: '导出所选笔记（0）', exact: true})).toBeDisabled();
  await expect(exports).toContainText('仅包含所选笔记和引用图片');
  await expect(exports).toContainText('未归档笔记放在根目录');
  await page.getByLabel('查找待导出笔记').fill('复习');
  await page.getByRole('button', {name: '全选当前列表', exact: true}).click();
  await page.getByLabel('查找待导出笔记').fill('');
  await expect(page.locator('.note-export-choice').filter({hasText: '复习提纲'}).getByRole('checkbox')).toBeChecked();
  await expect(page.locator('.note-export-choice').filter({hasText: '链接目标'}).getByRole('checkbox')).not.toBeChecked();
  await page.getByRole('button', {name: '导出所选笔记（1）', exact: true}).click();
  await expect(exports.getByRole('button', {name: '下载 ZIP', exact: true})).toBeVisible({timeout: 20000});
  const pending = page.waitForEvent('download');
  await exports.getByRole('button', {name: '下载 ZIP', exact: true}).click();
  const path = testInfo.outputPath('selected.zip'); await (await pending).saveAs(path);
  const result = spawnSync(process.platform === 'win32' ? 'python' : 'python3', ['-c', 'import json,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); print(json.dumps({n:z.read(n).decode() for n in z.namelist()}))', path], {encoding: 'utf8', windowsHide: true});
  expect(result.status, result.stderr).toBe(0);
  const files = JSON.parse(result.stdout);
  expect(Object.keys(files)).toEqual(['复习提纲.md']);
  expect(files['复习提纲.md']).toContain('未随包导出');
  expect(files['复习提纲.md']).not.toContain('目标概念正文');
});

for (const width of [390, 1440]) {
  test(`笔记图片管理：改名、说明、标签、引用与删除 ${width}px`, async ({page, request}) => {
    await page.setViewportSize({width, height: 1000});
    const s = await seed(request, page);
    await page.getByLabel('自动保存笔记', {exact: true}).check();
    await page.getByLabel('选择上传的笔记图片').setInputFiles(await testImage(page));
    await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
    const body = await page.getByLabel('Markdown 正文').inputValue();
    await page.getByRole('button', {name: '管理图片', exact: true}).click();
    const library = page.getByRole('dialog', {name: '管理图片', exact: true}).locator('.asset-library');
    await expect(library.locator('.asset-grid article')).toHaveCount(1);
    await library.getByRole('button', {name: '整理', exact: true}).click();
    const editor = library.locator('.asset-editor');
    await editor.getByLabel('图片名称', {exact: true}).fill('进程状态图·整理版');
    await editor.getByRole('textbox', {name: '图片说明', exact: true}).fill('进程从就绪到运行');
    await editor.getByLabel('标签', {exact: false}).fill('重点、状态转换');
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('button', {name: '关闭管理图片', exact: true}).click();
    await expect(page.getByLabel('笔记标题')).toHaveValue('复习提纲');
    await expect(editor.getByLabel('图片名称', {exact: true})).toHaveValue('进程状态图·整理版');
    await editor.getByRole('button', {name: '保存整理', exact: true}).click();
    await expect(library.locator('.asset-grid')).toContainText('进程状态图·整理版');
    await library.getByRole('button', {name: '引用位置', exact: true}).click();
    await expect(library.locator('.asset-reference-panel')).toContainText('复习提纲');
    await page.getByRole('button', {name: '关闭管理图片', exact: true}).click();
    await page.getByRole('button', {name: '插入图片与双链', exact: true}).click();
    await expect(page.getByLabel('插入课程图片').getByRole('option', {name: '进程状态图·整理版', exact: true})).toHaveCount(1);
    await page.getByRole('button', {name: '关闭插入图片与双链', exact: true}).click();
    await page.getByRole('button', {name: 'Markdown 预览', exact: true}).click();
    await expect(page.locator('.markdown-preview img')).toBeVisible();
    await page.getByRole('button', {name: '管理图片', exact: true}).click();
    if (process.env.HUSTUDY_M3_EVIDENCE) {
      const directory = resolve('../docs/fzk/evidence'); await mkdir(directory, {recursive: true});
      await page.evaluate(() => { (document.activeElement as HTMLElement)?.blur(); window.scrollTo({top: 0, behavior: 'instant'}); });
      await page.screenshot({path: resolve(directory, `note-image-manager-${width}.png`), fullPage: true, animations: 'disabled'});
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    page.once('dialog', dialog => dialog.dismiss());
    await library.getByRole('button', {name: '删除图片 进程状态图·整理版', exact: true}).click();
    await expect(library.locator('.asset-grid article')).toHaveCount(1);
    page.once('dialog', dialog => dialog.accept());
    await library.getByRole('button', {name: '删除图片 进程状态图·整理版', exact: true}).click();
    await expect(library.locator('.asset-grid article')).toHaveCount(0);
    await page.getByRole('button', {name: '关闭管理图片', exact: true}).click();
    await expect(page.locator('.markdown-preview')).toContainText('图片已删除或无法读取');
    expect((await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json()).content).toBe(body);
    await page.getByRole('button', {name: '插入图片与双链', exact: true}).click();
    await expect(page.getByLabel('插入课程图片')).toBeDisabled();
  });
}
