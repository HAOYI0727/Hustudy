import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(page: Page, request: APIRequestContext) {
  const username = 'trash_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '回收站测试'}})).json();
  const notes = [];
  for (const title of ['数据库复习', '网络整理', '保留的笔记']) notes.push(await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title, content: '# 正文不丢失', tags: ['期末']}})).json());
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  await page.goto(`/notes?course=${course.id}`);
  await expect(page.locator('.note-manager-row')).toHaveCount(3);
  const trash = async () => (await request.get(base + '/notes/trash', {headers, maxRetries: 2})).json();
  return {headers, course, notes, trash};
}
const confirm = (page: Page) => page.once('dialog', dialog => dialog.accept());
async function capture(page: Page, name: string) {
  if (!process.env.HUSTUDY_M3_TRASH_EVIDENCE) return;
  await mkdir(resolve('../docs/fzk/evidence'), {recursive: true});
  await page.screenshot({path: resolve(`../docs/fzk/evidence/${name}.png`), fullPage: true, animations: 'disabled'});
}

for (const width of [390, 1440]) test(`批量删除、恢复、彻底删除与回收站布局 ${width}px`, async ({page, request}) => {
  await page.setViewportSize({width, height: 1000});
  const s = await seed(page, request);
  for (const title of ['数据库复习', '网络整理']) await page.getByLabel(`选择笔记 ${title}`, {exact: true}).check();
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('button', {name: '批量删除', exact: true}).click();
  await expect(page.locator('.note-manager-row')).toHaveCount(3);
  confirm(page); await page.getByRole('button', {name: '批量删除', exact: true}).click();
  await expect(page.locator('.note-manager-row')).toHaveCount(1);
  await page.getByRole('button', {name: '回收站', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '笔记回收站', exact: true});
  await expect(dialog.locator('.note-trash-row')).toHaveCount(2);
  await expect(dialog).toContainText('保留 30 天');
  await expect(dialog).not.toContainText('正文不丢失');
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  const checkbox = await dialog.locator('.note-trash-row input').first().boundingBox();
  expect(checkbox!.width).toBeLessThan(24);
  await capture(page, `note-trash-${width}`);
  await page.getByLabel('选择本页回收站笔记').check();
  confirm(page); await page.getByRole('button', {name: '恢复所选', exact: true}).click();
  await expect(dialog).toContainText('回收站是空的');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', {name: '回收站', exact: true})).toBeFocused();
  await expect(page.locator('.note-manager-row')).toHaveCount(3);
  await page.locator('.note-manager').getByRole('button', {name: '数据库复习', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('# 正文不丢失');
  confirm(page); await page.getByRole('button', {name: '删除这篇笔记', exact: true}).click();
  await page.getByRole('button', {name: '回收站', exact: true}).click();
  await expect(dialog.locator('.note-trash-row')).toHaveCount(1);
  await page.getByLabel('选择本页回收站笔记').check();
  confirm(page); await page.getByRole('button', {name: '彻底删除所选', exact: true}).click();
  await expect(dialog).toContainText('回收站是空的');
  expect((await s.trash()).total).toBe(0);
});

test('未保存草稿禁止批量删除与回收站写入，关闭窗口保留正文', async ({page, request}) => {
  const s = await seed(page, request);
  await request.delete(base + `/notes/${s.notes[2].id}?revision=1`, {headers: s.headers});
  await page.locator('.note-manager').getByRole('button', {name: '数据库复习', exact: true}).click();
  await page.route('**/notes/' + s.notes[0].id, route => route.request().method() === 'PATCH' ? route.abort('failed') : route.continue());
  await page.getByLabel('自动保存笔记').check();
  await page.getByLabel('Markdown 正文').fill('尚未保存的草稿内容');
  await expect(page.getByRole('alert').filter({hasText: '本地内容仍在'})).toBeVisible();
  await page.getByRole('button', {name: '笔记管理', exact: true}).click();
  await expect(page.getByRole('button', {name: '批量删除', exact: true})).toBeDisabled();
  await page.getByRole('button', {name: '回收站', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '笔记回收站', exact: true});
  await expect(dialog.locator('.note-trash-row')).toHaveCount(1);
  await expect(page.getByRole('button', {name: '清空回收站', exact: true})).toBeDisabled();
  await expect(page.getByLabel('选择本页回收站笔记')).toBeDisabled();
  await page.keyboard.press('Escape');
  await page.getByRole('button', {name: '编辑笔记', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('尚未保存的草稿内容');
  expect((await s.trash()).total).toBe(1);
});

test('保留设置持久化，清空拒绝旧快照并可刷新重试', async ({page, request}) => {
  const s = await seed(page, request);
  await page.getByLabel('选择当前筛选结果').check(); confirm(page);
  await page.getByRole('button', {name: '批量删除', exact: true}).click();
  await expect(page.locator('.note-manager-row')).toHaveCount(0);
  await page.getByRole('button', {name: '回收站', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '笔记回收站', exact: true});
  await expect(dialog.locator('.note-trash-row')).toHaveCount(3);
  await page.locator('.note-trash-settings summary').click();
  await page.getByLabel('启用自动清理', {exact: true}).uncheck();
  confirm(page); await page.getByRole('button', {name: '保存清理设置', exact: true}).click();
  await expect(dialog.locator('.note-trash-settings summary')).toContainText('已关闭');
  await expect(dialog.getByText('自动清理已关闭', {exact: true})).toHaveCount(3);
  await page.reload(); await page.getByRole('button', {name: '回收站', exact: true}).click();
  await expect(dialog.locator('.note-trash-settings summary')).toContainText('已关闭');
  await page.locator('.note-trash-settings summary').click();
  await page.getByLabel('启用自动清理', {exact: true}).check();
  await page.getByLabel('回收站保留天数').fill('7');
  confirm(page); await page.getByRole('button', {name: '保存清理设置', exact: true}).click();
  await expect(dialog.locator('.note-trash-settings summary')).toContainText('7 天');
  const newNote = await (await request.post(base + '/notes', {headers: s.headers, data: {course_id: s.course.id, title: '刚移入回收站'}})).json();
  await request.delete(base + `/notes/${newNote.id}?revision=1`, {headers: s.headers});
  confirm(page); await page.getByRole('button', {name: '清空回收站', exact: true}).click();
  await expect(dialog.getByRole('alert')).toContainText('回收站内容已变化');
  expect((await s.trash()).total).toBe(4);
  await page.getByRole('button', {name: '刷新回收站', exact: true}).click();
  await expect(dialog.locator('.note-trash-row')).toHaveCount(4);
  confirm(page); await page.getByRole('button', {name: '清空回收站', exact: true}).click();
  await expect(dialog).toContainText('回收站是空的');
});

test('批量删除版本冲突不部分修改，网络失败可刷新重试', async ({page, request}) => {
  const s = await seed(page, request);
  await page.getByLabel('选择当前筛选结果').check();
  await request.patch(base + '/notes/' + s.notes[0].id, {headers: s.headers, data: {revision: 1, content: '其他窗口修改'}});
  confirm(page); await page.getByRole('button', {name: '批量删除', exact: true}).click();
  await expect(page.locator('.toast.error')).toContainText('版本已变化');
  await expect(page.locator('.note-manager-row')).toHaveCount(3);
  expect((await s.trash()).total).toBe(0);
  await page.getByRole('button', {name: '刷新笔记列表', exact: true}).click();
  await expect(page.getByRole('button', {name: '批量删除', exact: true})).toBeEnabled();
  confirm(page); await page.getByRole('button', {name: '批量删除', exact: true}).click();
  await expect(page.locator('.note-manager-row')).toHaveCount(0);
  await page.getByRole('button', {name: '回收站', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '笔记回收站', exact: true});
  await expect(dialog.locator('.note-trash-row')).toHaveCount(3);
  await page.getByLabel('选择本页回收站笔记').check();
  await page.route('**/notes/trash/batch', route => route.abort('failed'));
  confirm(page); await page.getByRole('button', {name: '恢复所选', exact: true}).click();
  await expect(dialog.getByRole('alert')).toBeVisible();
  await expect(dialog.locator('.note-trash-row')).toHaveCount(3);
  await page.unroute('**/notes/trash/batch');
  confirm(page); await page.getByRole('button', {name: '恢复所选', exact: true}).click();
  await expect(dialog).toContainText('回收站是空的');
});
