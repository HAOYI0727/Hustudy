import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(page: Page, request: APIRequestContext) {
  const username = 'layout_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '笔记工作区'}})).json();
  const createFolder = async (name: string, parent_id: string | null = null) => (await request.post(base + '/note-folders', {headers, data: {course_id: course.id, name, parent_id}})).json();
  const a = await createFolder('数据库'), b = await createFolder('课堂整理'), child = await createFolder('第一章', a.id);
  const notes = [];
  for (const title of ['数据库-事务与并发', '数据库-索引与查询', '计算机网络-TCP与UDP']) notes.push(await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title, content: '# 私有正文\n\n这段正文只属于编辑器，不应出现在侧栏。', tags: ['期末','重点']}})).json());
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  await page.goto(`/notes?course=${course.id}`);
  await expect(page.locator('.note-manager-row')).toHaveCount(3);
  const showLibrary = async () => {const button = page.getByRole('button', {name: /笔记列表与新建/}); if (await button.isVisible() && await button.getAttribute('aria-expanded') === 'false') await button.click();};
  const readNotes = async () => (await request.get(base + '/notes', {headers, maxRetries: 2})).json();
  const readFolders = async () => (await request.get(base + '/note-folders?course_id=' + course.id, {headers, maxRetries: 2})).json();
  return {headers, course, notes, a, b, child, readNotes, readFolders, showLibrary, createFolder};
}
async function evidence(page: Page, name: string) {
  if (!process.env.HUSTUDY_M3_WORKSPACE_EVIDENCE) return;
  await mkdir(resolve('../docs/fzk/evidence'), {recursive: true});
  await page.evaluate(() => {(document.activeElement as HTMLElement)?.blur(); window.scrollTo({top: 0, behavior: 'instant'});});
  await page.screenshot({path: resolve(`../docs/fzk/evidence/${name}.png`), fullPage: true, animations: 'disabled'});
}

for (const width of [390, 1440]) test(`中央选择与批量操作、简洁侧栏及弹窗键盘 ${width}px`, async ({page, request}) => {
  await page.setViewportSize({width, height: 1000});
  const s = await seed(page, request); await s.showLibrary();
  const sidebar = page.locator('.knowledge-library');
  await expect(sidebar).not.toContainText('私有正文');
  await expect(sidebar.getByRole('checkbox')).toHaveCount(0);
  await expect(sidebar.locator('.knowledge-item')).toHaveCount(3);
  await expect(page.locator('.note-manager').getByLabel('选择笔记 数据库-事务与并发')).toBeVisible();
  await page.getByLabel('选择笔记 数据库-事务与并发').check();
  await page.getByRole('button', {name: '导出已选', exact: true}).click();
  await expect(page.getByRole('dialog', {name: '导出笔记', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: '导出所选笔记（1）', exact: true})).toBeEnabled();
  await expect(page.locator('.note-export-choice').filter({hasText: s.notes[0].title}).getByRole('checkbox')).toBeChecked();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', {name: '导出已选', exact: true})).toBeFocused();
  if (width === 390) await page.getByRole('button', {name: /笔记列表与新建/}).click();
  await evidence(page, `note-workspace-${width}`);
  const trigger = page.getByRole('button', {name: '导入 Markdown', exact: true}); await trigger.click();
  await page.getByLabel('导入统一标签').fill('保留的设置');
  await page.getByLabel('选择Markdown文件').setInputFiles({name: '关闭后继续.md', mimeType: 'text/markdown', buffer: Buffer.from('# 文本')});
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => !!document.querySelector('dialog[open]')?.contains(document.activeElement))).toBe(true);
  await evidence(page, `note-import-dialog-${width}`);
  await page.keyboard.press('Escape'); await expect(trigger).toBeFocused(); await trigger.click();
  await expect(page.getByLabel('导入统一标签')).toHaveValue('保留的设置');
  await expect(page.locator('.note-import-results')).toContainText('关闭后继续.md');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  const dialog = page.getByRole('dialog', {name: '导入 Markdown', exact: true});
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
});

test('真实拖动多篇笔记、未归档与文件夹层级，取消和循环不写入', async ({page, request}) => {
  const s = await seed(page, request);
  await page.getByLabel(`选择笔记 ${s.notes[0].title}`).check(); await page.getByLabel(`选择笔记 ${s.notes[1].title}`).check();
  const row = (id: string) => page.locator(`.note-manager-row[data-note-id="${id}"]`);
  const folder = (id: string) => page.locator(`.note-folder-row[data-folder-id="${id}"] .folder-choice`);
  await row(s.notes[0].id).dragTo(folder(s.child.id));
  await expect(page.getByRole('status').filter({hasText: '已将 2 篇笔记'})).toBeVisible();
  expect((await s.readNotes()).filter((n: {folder_id: string}) => n.folder_id === s.child.id)).toHaveLength(2);
  await row(s.notes[0].id).dragTo(page.getByRole('button', {name: /^未归档/}));
  await expect.poll(async () => (await s.readNotes()).find((n: {id: string}) => n.id === s.notes[0].id).folder_id).toBeNull();
  await folder(s.b.id).dragTo(folder(s.a.id));
  await expect.poll(async () => (await s.readFolders()).find((f: {id: string}) => f.id === s.b.id).parent_id).toBe(s.a.id);
  let patches = 0; page.on('request', r => {if (r.method() === 'PATCH' && r.url().includes('/note-folders/')) patches++;});
  await folder(s.a.id).dragTo(folder(s.b.id));
  expect(patches).toBe(0);
  expect((await s.readFolders()).find((f: {id: string}) => f.id === s.a.id).parent_id).toBeNull();
  const transfer = await page.evaluateHandle(() => new DataTransfer());
  await folder(s.b.id).dispatchEvent('dragstart', {dataTransfer: transfer});
  await page.locator('.folder-root-drop').dispatchEvent('dragover', {dataTransfer: transfer});
  await page.locator('.folder-root-drop').dispatchEvent('drop', {dataTransfer: transfer});
  await folder(s.b.id).dispatchEvent('dragend', {dataTransfer: transfer});
  await expect.poll(async () => (await s.readFolders()).find((f: {id: string}) => f.id === s.b.id).parent_id).toBeNull();
  const before = patches;
  await folder(s.child.id).dispatchEvent('dragstart', {dataTransfer: transfer});
  await folder(s.child.id).dispatchEvent('dragend', {dataTransfer: transfer});
  await folder(s.b.id).dispatchEvent('drop', {dataTransfer: transfer}); // No active internal drag.
  expect(patches).toBe(before);
  await page.reload();
  await expect(page.locator('.note-manager-row')).toHaveCount(3);
  expect((await s.readNotes()).find((n: {id: string}) => n.id === s.notes[1].id).folder_id).toBe(s.child.id);
});

test('文件夹拖动沿用revision和深度校验，外部拖入不产生写入', async ({page, request}) => {
  const s = await seed(page, request);
  let deep = s.child;
  for (let level = 3; level <= 6; level++) deep = await s.createFolder(`第${level}层`, deep.id);
  await page.reload(); await expect(page.locator('.note-folder-row')).toHaveCount(7);
  const source = page.locator(`.note-folder-row[data-folder-id="${s.b.id}"] .folder-choice`);
  const target = page.locator(`.note-folder-row[data-folder-id="${s.a.id}"]`);
  const transfer = await page.evaluateHandle(() => new DataTransfer());
  let patches = 0; page.on('request', r => {if (r.method() === 'PATCH' && r.url().includes('/note-folders/')) patches++;});
  await target.dispatchEvent('drop', {dataTransfer: transfer});
  expect(patches).toBe(0);
  await request.patch(base + '/note-folders/' + s.b.id, {headers: s.headers, data: {revision: 1, name: '远端改名'}});
  const drop = async (destination: ReturnType<Page['locator']>) => {
    await source.dispatchEvent('dragstart', {dataTransfer: transfer});
    await destination.dispatchEvent('dragover', {dataTransfer: transfer});
    await destination.dispatchEvent('drop', {dataTransfer: transfer});
    await source.dispatchEvent('dragend', {dataTransfer: transfer});
  };
  await drop(target);
  await expect(page.locator('.toast.error')).toBeVisible();
  let saved = (await s.readFolders()).find((f: {id: string}) => f.id === s.b.id);
  expect(saved.parent_id).toBeNull(); expect(saved.name).toBe('远端改名');
  await expect(source).toContainText('课堂整理');
  await page.getByRole('button', {name: '刷新文件夹', exact: true}).click();
  await expect(source).toContainText('远端改名');
  await expect(page.getByRole('button', {name: '刷新文件夹', exact: true})).toBeEnabled();
  await drop(page.locator(`.note-folder-row[data-folder-id="${deep.id}"]`));
  await expect(page.locator('.toast.error')).toContainText('6');
  saved = (await s.readFolders()).find((f: {id: string}) => f.id === s.b.id);
  expect(saved.parent_id).toBeNull(); expect(saved.revision).toBe(2);
});

test('拖动冲突不覆盖，未保存草稿禁止拖动，视图切换保持撤销历史', async ({page, request}) => {
  const s = await seed(page, request);
  await request.patch(base + '/notes/' + s.notes[0].id, {headers: s.headers, data: {revision: 1, content: '另一窗口的新正文'}});
  await page.locator(`.note-manager-row[data-note-id="${s.notes[0].id}"]`).dragTo(page.locator(`.note-folder-row[data-folder-id="${s.a.id}"]`));
  await expect(page.getByRole('alert').filter({hasText: '未修改任何笔记'}).first()).toBeVisible();
  const saved = (await s.readNotes()).find((n: {id: string}) => n.id === s.notes[0].id);
  expect(saved.folder_id).toBeNull(); expect(saved.content).toBe('另一窗口的新正文');
  await page.locator('.note-title-link').filter({hasText: s.notes[0].title}).click();
  await page.getByLabel('笔记标题').fill('');
  await page.getByLabel('Markdown 正文').fill('本地草稿');
  await page.getByRole('button', {name: '笔记管理', exact: true}).click();
  await expect(page.locator('.note-manager-row').first()).toHaveAttribute('draggable', 'false');
  await expect(page.getByRole('button', {name: '批量整理', exact: true})).toBeDisabled();
  await page.getByRole('button', {name: '编辑笔记', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('本地草稿');
  await page.getByRole('button', {name: '撤销', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('另一窗口的新正文');
  await page.getByRole('button', {name: '关闭错误提示', exact: true}).click();
  await page.getByLabel('笔记标题').fill(s.notes[0].title);
  await page.getByLabel('Markdown 正文').fill('# 事务与并发\n\n事务把相关操作组成一个整体。\n\n## 复习重点\n\n- 原子性\n- 隔离性\n\n## 自测\n\n解释两个事务同时修改数据时需要注意什么。');
  await page.getByLabel('Markdown 正文').press('Control+s');
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await page.getByRole('button', {name: '分屏预览', exact: true}).click();
  await evidence(page, 'note-workspace-editor');
});

test('导入处理中不能关闭，401让出登录窗口，重开显式重试保留文件', async ({page, request}) => {
  const s = await seed(page, request);
  let release!: () => void; const gate = new Promise<void>(r => {release = r;});
  let calls = 0;
  await page.route('**/api/v1/notes/import-markdown', async route => {calls++; await gate; await route.fulfill({status: 401, contentType: 'application/json', body: JSON.stringify({error: {message: '登录已过期'}})});});
  await page.getByRole('button', {name: '导入 Markdown', exact: true}).click();
  await page.getByLabel('选择Markdown文件').setInputFiles({name: '登录后重试.md', mimeType: 'text/markdown', buffer: Buffer.from('登录后保留')});
  await page.getByRole('button', {name: '开始导入（1）', exact: true}).click();
  await expect(page.getByRole('button', {name: '关闭导入 Markdown', exact: true})).toBeDisabled();
  await page.keyboard.press('Escape'); await expect(page.locator('dialog[open]')).toBeVisible();
  release();
  const auth = page.getByRole('dialog', {name: /登录已过期/}); await expect(auth).toBeVisible();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await auth.getByLabel('密码', {exact: true}).fill('Test-password-2026'); await auth.getByRole('button', {name: '登录', exact: true}).click();
  await expect(auth).not.toBeVisible(); expect(calls).toBe(1);
  await page.unroute('**/api/v1/notes/import-markdown');
  await page.getByRole('button', {name: '导入 Markdown', exact: true}).click();
  await expect(page.locator('.note-import-results')).toContainText('登录后重试.md');
  await page.getByRole('button', {name: '重试未完成文件', exact: true}).click();
  await expect(page.locator('.note-import-panel')).toContainText('已导入 1/1');
  // Login refreshes the token, so query through the now-authenticated browser's local storage.
  const token = await page.evaluate(() => localStorage.getItem('hustudy_token'));
  const rows = await (await request.get(base + '/notes', {headers: {Authorization: 'Bearer ' + token}})).json();
  expect(rows.filter((n: {title: string}) => n.title === '登录后重试')).toHaveLength(1);
  expect(rows).toHaveLength(s.notes.length + 1);
});
