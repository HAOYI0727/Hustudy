import {test, expect, type Page, type APIRequestContext, type Locator} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import type {Note, NoteGraphResponse} from '../../../src/api/client';

const base = 'http://127.0.0.1:8056/api/v1';
const password = 'Test-password-2026';
const graphRequest = (url: string) => /\/api\/v1\/courses\/[a-f0-9-]{36}\/note-graph(?:\?|$)/.test(url);
const noteBodyRequest = (url: string) => /\/api\/v1\/notes\/[a-f0-9-]{36}$/.test(url);

async function setup(page: Page, request: APIRequestContext) {
  const username = 'graph_' + crypto.randomUUID().replaceAll('-', '');
  const registration = await request.post(base + '/auth/register', {data: {username, password}});
  expect(registration.status()).toBe(201);
  const auth = await registration.json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const courseResponse = await request.post(base + '/courses', {headers, data: {name: '隔离笔记图谱'}});
  expect(courseResponse.status()).toBe(201);
  const course = await courseResponse.json();
  const otherCourseResponse = await request.post(base + '/courses', {headers, data: {name: '其他隔离课程'}});
  expect(otherCourseResponse.status()).toBe(201);
  const otherCourse = await otherCourseResponse.json();
  const create = async (title: string, courseId = course.id): Promise<Note> => {
    const response = await request.post(base + '/notes', {headers, data: {course_id: courseId, title, content: `# ${title}\n\n仅打开正文后可见的内容。`, tags: ['图谱练习']}});
    expect(response.status()).toBe(201);
    return response.json();
  };
  const a = await create('A 起点');
  const b = await create('B 双向关联');
  const c = await create('C 下一跳');
  const d = await create('D 二跳终点');
  const orphan = await create('O 孤立笔记');
  const removed = await create('不应显示的已删除笔记');
  const foreign = await create('不应显示的其他课程笔记', otherCourse.id);
  const link = (note: Note, label = note.title) => `[[note:${note.id}|${label}]]`;
  const edit = async (note: Note, links: string[]): Promise<Note> => {
    const response = await request.patch(base + `/notes/${note.id}`, {headers, data: {revision: note.revision, content: note.content + '\n\n' + links.join('\n')}});
    expect(response.status()).toBe(200);
    return response.json();
  };
  const updatedA = await edit(a, [link(b), link(b, '重复指向同一笔记'), link(a), link(removed), link(foreign), `[[note:${crypto.randomUUID()}|失效链接]]`]);
  const updatedB = await edit(b, [link(a), link(c)]);
  const updatedC = await edit(c, [link(d)]);
  expect((await request.delete(base + `/notes/${removed.id}`, {headers})).status()).toBe(204);
  await page.addInitScript(({token, username}) => {
    localStorage.setItem('hustudy_token', token);
    localStorage.setItem('hustudy_user', username);
  }, {token: auth.access_token, username});
  return {headers, course, auth, username, a: updatedA, b: updatedB, c: updatedC, d, orphan, removed, foreign};
}

const listButtons = (dialog: Locator) => dialog.getByLabel('图谱笔记列表', {exact: true}).getByRole('button', {name: /^选择笔记：/});
const selectNote = (dialog: Locator, title: string) => dialog.getByRole('button', {name: `选择笔记：${title}`, exact: true});
const detail = (dialog: Locator) => dialog.getByRole('region', {name: '选中笔记', exact: true});

async function openGraph(page: Page, expectedNodes: number | null = 5) {
  await page.getByRole('button', {name: '关系图谱', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '笔记关系图谱', exact: true});
  await expect(dialog).toBeVisible();
  if (expectedNodes !== null) await expect(listButtons(dialog)).toHaveCount(expectedNodes);
  return dialog;
}

async function graphAction(page: Page, action: () => Promise<unknown>): Promise<NoteGraphResponse> {
  const pending = page.waitForResponse(response => graphRequest(response.url()) && response.request().method() === 'GET');
  await action();
  const response = await pending;
  expect(response.status()).toBe(200);
  return response.json();
}

test('真实双链按方向去重，标题筛选保留完整度数，孤立与一跳聚焦明确且重命名可刷新', async ({page, request}) => {
  const s = await setup(page, request);
  let reads = 0;
  page.on('request', r => {if (graphRequest(r.url())) reads++;});
  await page.goto(`/notes?course=${s.course.id}`);
  const pending = page.waitForResponse(response => graphRequest(response.url()));
  const dialog = await openGraph(page);
  const full: NoteGraphResponse = await (await pending).json();
  expect(full.total_nodes).toBe(5);
  expect(full.total_edges).toBe(4);
  expect(full.edges.map(edge => `${edge.source_id}>${edge.target_id}`).sort()).toEqual([
    `${s.a.id}>${s.b.id}`, `${s.b.id}>${s.a.id}`, `${s.b.id}>${s.c.id}`, `${s.c.id}>${s.d.id}`,
  ].sort());
  await expect(dialog).toContainText('显示 5 / 5 篇笔记 · 4 / 4 条关系');
  await expect(dialog).not.toContainText('不应显示');
  const initialReads = reads; // Development StrictMode may abort and repeat the mount read.
  await dialog.getByLabel('按标题查找笔记', {exact: true}).fill('B 双向');
  await page.waitForTimeout(150);
  expect(reads).toBe(initialReads);
  await expect(listButtons(dialog)).toHaveCount(5);
  const filtered = await graphAction(page, () => dialog.getByRole('button', {name: '查询', exact: true}).click());
  expect(filtered.nodes.map(node => node.id)).toEqual([s.b.id]);
  expect(filtered.nodes[0]).toMatchObject({incoming_count: 1, outgoing_count: 2});
  expect(filtered.total_edges).toBe(0);
  await expect(listButtons(dialog)).toHaveCount(1);
  await selectNote(dialog, s.b.title).click();
  await expect(detail(dialog)).toContainText('课程内入链');
  await expect(detail(dialog)).toContainText('课程内出链');
  await expect(detail(dialog)).not.toContainText('孤立笔记');
  const focused = await graphAction(page, () => dialog.getByRole('button', {name: '聚焦关联', exact: true}).click());
  expect(focused.focus_note_id).toBe(s.b.id);
  expect(focused.nodes.map(node => node.id).sort()).toEqual([s.a.id, s.b.id, s.c.id].sort());
  expect(focused.nodes[0].id).toBe(s.b.id);
  expect(focused.total_edges).toBe(3);
  await expect(dialog.getByLabel('按标题查找笔记', {exact: true})).toHaveValue('');
  await expect(selectNote(dialog, s.d.title)).toHaveCount(0);
  await graphAction(page, () => dialog.getByRole('button', {name: '查看全课程', exact: true}).click());
  await dialog.getByRole('combobox', {name: '关系筛选', exact: true}).selectOption('isolated');
  const isolated = await graphAction(page, () => dialog.getByRole('button', {name: '查询', exact: true}).click());
  expect(isolated.nodes.map(node => node.id)).toEqual([s.orphan.id]);
  await expect(listButtons(dialog)).toHaveCount(1);
  await selectNote(dialog, s.orphan.title).click();
  await expect(detail(dialog)).toContainText('孤立');
  await dialog.getByRole('combobox', {name: '关系筛选', exact: true}).selectOption('linked');
  const linked = await graphAction(page, () => dialog.getByRole('button', {name: '查询', exact: true}).click());
  expect(linked.total_nodes).toBe(4);
  expect(linked.total_edges).toBe(4);
  const renamed = await request.patch(base + `/notes/${s.b.id}`, {headers: s.headers, data: {revision: s.b.revision, title: 'B 已重命名，关系保持'}});
  expect(renamed.status()).toBe(200);
  const refreshed = await graphAction(page, () => dialog.getByRole('button', {name: '刷新图谱', exact: true}).click());
  expect(refreshed.edges).toEqual(linked.edges);
  await expect(selectNote(dialog, 'B 已重命名，关系保持')).toBeVisible();
  await expect(selectNote(dialog, s.b.title)).toHaveCount(0);
});

test('图谱按需加载，浏览仅读元数据，明确打开所选笔记才读取正文', async ({page, request}) => {
  const s = await setup(page, request);
  const bodies: string[] = [];
  let graphReads = 0, writes = 0;
  page.on('request', r => {
    if (graphRequest(r.url())) graphReads++;
    if (r.method() === 'GET' && noteBodyRequest(r.url())) bodies.push(r.url());
    if (/\/api\/v1\//.test(r.url()) && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(r.method())) writes++;
  });
  await page.goto(`/notes?course=${s.course.id}`);
  await expect(page.getByRole('region', {name: '笔记管理列表'})).toBeVisible();
  expect(graphReads).toBe(0);
  expect(bodies).toEqual([]);
  const dialog = await openGraph(page);
  const openedReads = graphReads;
  expect(openedReads).toBeGreaterThan(0);
  for (const note of [s.a, s.b, s.orphan]) {
    await selectNote(dialog, note.title).click();
    await expect(detail(dialog)).toContainText(note.title);
  }
  expect(graphReads).toBe(openedReads);
  expect(bodies).toEqual([]);
  await expect(dialog).not.toContainText('仅打开正文后可见的内容');
  await selectNote(dialog, s.b.title).click();
  await page.route(`**/api/v1/notes/${s.b.id}`, route => route.fulfill({status: 503, json: {error: {message: '隔离正文读取失败'}}}));
  await dialog.getByRole('button', {name: '打开笔记', exact: true}).click();
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('隔离正文读取失败');
  expect(bodies).toEqual([base + `/notes/${s.b.id}`]);
  await page.unroute(`**/api/v1/notes/${s.b.id}`);
  await dialog.getByRole('button', {name: '打开笔记', exact: true}).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel('笔记标题', {exact: true})).toHaveValue(s.b.title);
  await expect(page.getByLabel('Markdown 正文', {exact: true})).toHaveValue(s.b.content);
  expect(bodies).toEqual([base + `/notes/${s.b.id}`, base + `/notes/${s.b.id}`]);
  expect(writes).toBe(0);
  for (const note of [s.a, s.b, s.c, s.d, s.orphan]) {
    const saved = await (await request.get(base + `/notes/${note.id}`, {headers: s.headers})).json();
    expect(saved).toMatchObject({revision: note.revision, content: note.content});
  }
});

test('未保存草稿可浏览已保存关系，取消打开保留草稿与弹窗，确认后才切换正文', async ({page, request}) => {
  const s = await setup(page, request);
  await page.route(`**/api/v1/notes/${s.a.id}`, async route => {
    if (route.request().method() === 'PATCH') await route.fulfill({status: 503, json: {error: {message: '隔离保存失败'}}});
    else await route.continue();
  });
  await page.goto(`/notes?course=${s.course.id}&note=${s.a.id}`);
  await expect(page.getByLabel('Markdown 正文', {exact: true})).toHaveValue(s.a.content);
  const unsaved = s.a.content + '\n尚未保存的理解不能丢失。';
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('Markdown 正文', {exact: true}).fill(unsaved);
  await expect(page.locator('.save-indicator')).toContainText('未保存');
  const bodyReads: string[] = [];
  page.on('request', r => {if (r.method() === 'GET' && noteBodyRequest(r.url())) bodyReads.push(r.url());});
  const dialog = await openGraph(page);
  await expect(dialog).toContainText(/草稿|未保存/);
  await selectNote(dialog, s.b.title).click();
  page.once('dialog', d => d.dismiss());
  await dialog.getByRole('button', {name: '打开笔记', exact: true}).click();
  await expect(dialog).toBeVisible();
  await expect(page.getByLabel('Markdown 正文', {exact: true})).toHaveValue(unsaved);
  expect(bodyReads).toEqual([]);
  expect((await (await request.get(base + `/notes/${s.a.id}`, {headers: s.headers})).json()).content).toBe(s.a.content);
  page.once('dialog', d => d.accept());
  await dialog.getByRole('button', {name: '打开笔记', exact: true}).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel('Markdown 正文', {exact: true})).toHaveValue(s.b.content);
  expect(bodyReads).toEqual([base + `/notes/${s.b.id}`]);
  await expect.poll(() => page.evaluate(userId => Object.keys(localStorage)
    .filter(key => key.startsWith(`hustudy-note-recovery:v1:${userId}:`))
    .map(key => JSON.parse(localStorage.getItem(key)!)).some(row => row.draft.content.includes('尚未保存的理解不能丢失。')), s.auth.user.id)).toBe(true);
});

test('关闭加载中的图谱拒绝迟到响应，重开获取新快照并恢复触发焦点', async ({page, request}) => {
  const s = await setup(page, request);
  const url = `**/api/v1/courses/${s.course.id}/note-graph?*`;
  let release!: () => void, captured!: () => void, calls = 0, hold = true;
  const gate = new Promise<void>(resolve => {release = resolve;});
  const started = new Promise<void>(resolve => {captured = resolve;});
  await page.route(url, async route => {
    calls++;
    if (!hold) {await route.continue(); return;}
    const response = await route.fetch();
    const old: NoteGraphResponse = await response.json();
    old.nodes = old.nodes.map(node => ({...node, title: '不应出现的迟到标题'}));
    captured();
    await gate;
    await route.fulfill({json: old}).catch(() => {});
  });
  try {
    await page.goto(`/notes?course=${s.course.id}`);
    const dialog = await openGraph(page, null);
    await started;
    await dialog.getByRole('button', {name: '关闭笔记关系图谱', exact: true}).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByRole('button', {name: '关系图谱', exact: true})).toBeFocused();
    hold = false;
    const beforeReopen = calls;
    await openGraph(page);
    expect(calls).toBeGreaterThan(beforeReopen);
    release();
    await expect(selectNote(dialog, s.a.title)).toBeVisible();
    await expect(dialog).not.toContainText('不应出现的迟到标题');
    await dialog.getByRole('button', {name: '关闭笔记关系图谱', exact: true}).click();
    await expect(page.getByRole('button', {name: '关系图谱', exact: true})).toBeFocused();
  } finally {release();}
});

test('读取失败保留明确重试入口，401关闭图谱让出登录且登录后不自动重放', async ({page, request}) => {
  const s = await setup(page, request);
  const url = `**/api/v1/courses/${s.course.id}/note-graph?*`;
  let calls = 0;
  let phase: 'failure' | 'ready' | 'expired' = 'failure';
  page.on('request', r => {if (graphRequest(r.url())) calls++;});
  await page.route(url, async route => {
    if (phase === 'failure') await route.fulfill({status: 503, json: {error: {message: '隔离图谱服务暂不可用'}}});
    else if (phase === 'expired') await route.fulfill({status: 401, json: {error: {message: '隔离登录过期'}}});
    else await route.continue();
  });
  await page.goto(`/notes?course=${s.course.id}`);
  const dialog = await openGraph(page, null);
  await expect(dialog.getByRole('alert')).toContainText('隔离图谱服务暂不可用');
  const beforeRetry = calls;
  await expect(listButtons(dialog)).toHaveCount(0);
  phase = 'ready';
  await dialog.getByRole('button', {name: '重试图谱', exact: true}).click();
  await expect(listButtons(dialog)).toHaveCount(5);
  expect(calls).toBeGreaterThan(beforeRetry);
  phase = 'expired';
  await dialog.getByRole('button', {name: '刷新图谱', exact: true}).click();
  const login = page.getByRole('dialog', {name: '登录已过期 · 保留当前工作', exact: true});
  await expect(login).toBeVisible();
  await expect(dialog).not.toBeVisible();
  const beforeLogin = calls;
  await page.unroute(url);
  await login.getByLabel('密码', {exact: true}).fill(password);
  await login.getByRole('button', {name: '登录', exact: true}).click();
  await expect(login).not.toBeVisible();
  await expect(dialog).not.toBeVisible();
  expect(calls).toBe(beforeLogin);
  await openGraph(page);
  expect(calls).toBeGreaterThan(beforeLogin);
});

test('其他共享请求的当前会话401关闭图谱，其他会话事件被忽略，重登保留草稿且不重开图谱', async ({page, request}) => {
  const s = await setup(page, request);
  await page.route(`**/api/v1/notes/${s.a.id}`, async route => {
    if (route.request().method() === 'PATCH') await route.fulfill({status: 503, json: {error: {message: '隔离保存失败'}}});
    else await route.continue();
  });
  await page.goto(`/notes?course=${s.course.id}&note=${s.a.id}`);
  await expect(page.getByLabel('Markdown 正文', {exact: true})).toHaveValue(s.a.content);
  const unsaved = s.a.content + '\n登录过期前尚未保存的理解。';
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('Markdown 正文', {exact: true}).fill(unsaved);
  await expect(page.locator('.save-indicator')).toContainText('未保存');
  let graphReads = 0;
  page.on('request', r => {if (graphRequest(r.url())) graphReads++;});
  const dialog = await openGraph(page);
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('hustudy:unauthorized', {detail: 'unrelated-session-for-test'})));
  await expect(dialog).toBeVisible();
  const beforeExpired = graphReads;
  await page.route('**/api/v1/processing/status', route => route.fulfill({status: 401, json: {error: {message: '隔离共享请求会话过期'}}}));
  await page.evaluate(async () => {
    const path = '/src/api/client.ts';
    const {api} = await import(/* @vite-ignore */ path);
    await api.processingStatus(localStorage.getItem('hustudy_token')!).catch(() => {});
  });
  const login = page.getByRole('dialog', {name: '登录已过期 · 保留当前工作', exact: true});
  await expect(login).toBeVisible();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel('Markdown 正文', {exact: true})).toHaveValue(unsaved);
  await page.unroute('**/api/v1/processing/status');
  await login.getByLabel('密码', {exact: true}).fill(password);
  await login.getByRole('button', {name: '登录', exact: true}).click();
  await expect(login).not.toBeVisible();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel('Markdown 正文', {exact: true})).toHaveValue(unsaved);
  expect(graphReads).toBe(beforeExpired);
  expect((await (await request.get(base + `/notes/${s.a.id}`, {headers: s.headers})).json()).content).toBe(s.a.content);
});

for (const width of [390, 1440]) test(`图谱与列表均可用键盘选择，弹窗与长标题布局不溢出 ${width}px`, async ({page, request}) => {
  await page.setViewportSize({width, height: 1000});
  const s = await setup(page, request);
  const longTitle = 'B 双向关联 · 公式、概念与例题的长标题用于核对窄屏换行和完整名称';
  expect((await request.patch(base + `/notes/${s.b.id}`, {headers: s.headers, data: {revision: s.b.revision, title: longTitle}})).status()).toBe(200);
  await page.goto(`/notes?course=${s.course.id}`);
  const dialog = await openGraph(page);
  const listNode = selectNote(dialog, longTitle);
  await listNode.focus();
  await page.keyboard.press('Enter');
  await expect(detail(dialog)).toContainText(longTitle);
  const svgNode = dialog.getByRole('button', {name: `选择图中笔记：${s.a.title}`, exact: true});
  await svgNode.focus();
  await page.keyboard.press('Space');
  await expect(detail(dialog)).toContainText(s.a.title);
  const labels = await dialog.locator('svg text').evaluateAll(elements => elements.map(element => {
    const rect = element.getBoundingClientRect();
    return {title: element.textContent, left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom};
  }));
  for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) {
    const a = labels[i], b = labels[j];
    expect(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top,
      `图谱标签不应重叠：${a.title} / ${b.title}`).toBe(true);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true);
  expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth + 2)).toBe(true);
  expect(await dialog.evaluate(element => element.getBoundingClientRect().width <= innerWidth)).toBe(true);
  await dialog.screenshot({path: fileURLToPath(new URL(`../../../../.artifacts/e2e/optional/note-graph-${width}-${test.info().project.name}.png`, import.meta.url))});
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole('button', {name: '关系图谱', exact: true})).toBeFocused();
});
