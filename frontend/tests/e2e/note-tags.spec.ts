import {test, expect, type APIRequestContext, type Page} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(request: APIRequestContext, page: Page) {
  const username = 'm3_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: 'M3 笔记标签验收'}})).json();
  const target = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '调度算法', content: '记录时间片与优先级。', tags: ['定义']}})).json();
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '操作系统复习', content: `## 复习要点\n\n整理进程调度与线程模型。\n\n[[note:${target.id}|调度算法]]`, tags: ['期末']}})).json();
  await page.addInitScript(({token, username}) => {
    localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);
  }, {token: auth.access_token, username});
  const url = `/notes?course=${course.id}&note=${note.id}`;
  await page.goto(url);
  await expect(page.getByLabel('笔记标题')).toHaveValue(note.title);
  return {headers, course, note, target, url};
}

async function showLibrary(page: Page) {
  const toggle = page.getByRole('button', {name: /笔记列表与新建/});
  if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'false') await toggle.click();
}

for (const width of [390, 1440]) {
  test(`M3 标签自动保存、重载、筛选与页外双链 ${width}px`, async ({page, request}) => {
    await page.setViewportSize({width, height: 1000});
    const s = await seed(request, page);
    await page.getByLabel('自动保存笔记', {exact: true}).check();
    await page.getByRole('button', {name: /^文件夹与标签/}).click();
    await page.getByLabel('新标签', {exact: true}).fill('  高频考点  ');
    await page.getByRole('button', {name: '添加标签', exact: true}).click();
    await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
    const saved = await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json();
    expect(saved.tags).toEqual(['期末', '高频考点']);
    await page.reload();
    await page.getByRole('button', {name: /^文件夹与标签/}).click();
    await expect(page.getByRole('button', {name: '移除标签 高频考点', exact: true})).toBeVisible();
    await page.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
    await showLibrary(page);
    await page.getByRole('button', {name: '笔记管理', exact: true}).click();
    await page.getByLabel('按标签筛选笔记').selectOption('高频考点');
    await page.getByLabel('搜索笔记', {exact: true}).fill('期末');
    await expect(page.locator('.knowledge-item')).toHaveCount(1);
    await expect(page.locator('.note-filter-summary')).toContainText('找到 1 篇');
    if (process.env.HUSTUDY_M3_EVIDENCE) {
      const directory = resolve('../docs/fzk/evidence'); await mkdir(directory, {recursive: true});
      await page.screenshot({path: resolve(directory, `note-tags-${width}.png`), fullPage: true});
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.getByRole('button', {name: '编辑笔记', exact: true}).click();
    await page.getByRole('button', {name: /^引用与关联/}).click();
    await page.getByRole('button', {name: '↗ 调度算法', exact: true}).click();
    await expect(page.getByLabel('笔记标题')).toHaveValue('调度算法');
    await page.getByRole('button', {name: /^文件夹与标签/}).click();
    await expect(page.getByRole('button', {name: '移除标签 定义', exact: true})).toBeVisible();
  });

  test(`M3 标签冲突保留本地草稿、显式载入与清空 ${width}px`, async ({page, request}) => {
    await page.setViewportSize({width, height: 1000});
    const s = await seed(request, page);
    const remote = await request.patch(base + '/notes/' + s.note.id, {headers: s.headers, data: {revision: 1, tags: ['远端标签'], content: '另一窗口保存的内容'}});
    expect(remote.status()).toBe(200);
    await page.getByRole('button', {name: /^文件夹与标签/}).click();
    await page.getByLabel('新标签', {exact: true}).fill('本地标签');
    await page.getByRole('button', {name: '添加标签', exact: true}).click();
    await page.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
    await page.getByRole('button', {name: '立即保存', exact: true}).click();
    await expect(page.locator('.conflict-panel')).toContainText('服务端标签：远端标签');
    await page.getByRole('button', {name: /^文件夹与标签/}).click();
    await expect(page.getByRole('button', {name: '移除标签 本地标签', exact: true})).toBeVisible();
    await page.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
    await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.note.content);
    await expect(page.getByRole('button', {name: '立即保存', exact: true})).toBeDisabled();
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', {name: '载入服务端版本', exact: true}).click();
    await expect(page.getByLabel('Markdown 正文')).toHaveValue('另一窗口保存的内容');
    await page.getByLabel('自动保存笔记', {exact: true}).check();
    await page.getByRole('button', {name: /^文件夹与标签/}).click();
    await page.getByRole('button', {name: '移除标签 远端标签', exact: true}).click();
    await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
    const saved = await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json();
    expect(saved.tags).toEqual([]); expect(saved.revision).toBe(3);
  });
}

test('M3 未添加的标签输入阻止离页，并保留校验失败输入', async ({page, request}) => {
  await seed(request, page);
  await page.getByRole('button', {name: /^文件夹与标签/}).click();
  await page.getByLabel('新标签', {exact: true}).fill('未完成的标签');
  await page.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('button', {name: '资料阅读', exact: true}).click();
  await page.getByRole('button', {name: /^文件夹与标签/}).click();
  await expect(page.getByLabel('新标签', {exact: true})).toHaveValue('未完成的标签');
  await page.getByLabel('新标签', {exact: true}).fill('长'.repeat(33));
  await page.getByRole('button', {name: '添加标签', exact: true}).click();
  await expect(page.getByRole('alert')).toContainText('最多 32');
  await expect(page.getByLabel('新标签', {exact: true})).toHaveValue('长'.repeat(33));
  await expect(page.getByRole('button', {name: '立即保存', exact: true})).toBeDisabled();
});

test('M3 登录过期后恢复原账户仍保留标签且不会自动重放', async ({page, request}) => {
  const s = await seed(request, page);
  let writes = 0;
  await page.route(`**/api/v1/notes/${s.note.id}`, async route => {
    if (route.request().method() === 'PATCH') {
      writes++;
      await route.fulfill({status: 401, contentType: 'application/json', body: JSON.stringify({error: {message: '登录已过期'}})});
    } else await route.continue();
  });
  await page.getByRole('button', {name: /^文件夹与标签/}).click();
  await page.getByLabel('新标签', {exact: true}).fill('会话恢复草稿');
  await page.getByRole('button', {name: '添加标签', exact: true}).click();
  await page.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  const modal = page.getByRole('dialog', {name: /登录已过期/}); await expect(modal).toBeVisible();
  await modal.getByLabel('密码', {exact: true}).fill('Test-password-2026');
  await modal.getByRole('button', {name: '登录', exact: true}).click();
  await expect(modal).not.toBeVisible();
  await page.getByRole('button', {name: /^文件夹与标签/}).click();
  await expect(page.getByRole('button', {name: '移除标签 会话恢复草稿', exact: true})).toBeVisible();
  await page.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
  expect(writes).toBe(1);
  const before = await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json();
  expect(before.tags).toEqual(['期末']);
  await page.unroute(`**/api/v1/notes/${s.note.id}`);
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const after = await (await request.get(base + '/notes/' + s.note.id, {headers: s.headers})).json();
  expect(after.tags).toEqual(['期末', '会话恢复草稿']);
});
