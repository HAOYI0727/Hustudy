import {test, expect, type Page} from "@playwright/test";
import {createServer, request as proxyRequest, type Server} from "node:http";
import {readFile} from "node:fs/promises";
import {resolve, extname, sep} from "node:path";
import {fileURLToPath} from "node:url";

// Serve the actual production build and proxy its same-origin API to the
// disposable backend. No daily account, external server or model is used.
const root = fileURLToPath(new URL("../../../dist", import.meta.url));
let server: Server;
let origin: string;
test.beforeAll(async () => {
  await readFile(resolve(root, "index.html"));
  server = createServer((req, res) => {
    if (req.url?.startsWith("/api/v1/")) {
      const upstream = proxyRequest({hostname:"127.0.0.1", port:8056, path:req.url, method:req.method, headers:{...req.headers, host:"127.0.0.1:8056"}}, reply => {
        res.writeHead(reply.statusCode || 502, reply.headers);
        reply.pipe(res);
      });
      upstream.on("error", () => {res.writeHead(502); res.end();});
      req.pipe(upstream);
      return;
    }
    void (async () => {
      const path = decodeURIComponent(new URL(req.url || "/", "http://localhost").pathname);
      const file = resolve(root, "." + path);
      if (!file.startsWith(root + sep)) {res.writeHead(403); res.end(); return;}
      const types: Record<string,string> = {".js":"text/javascript", ".css":"text/css", ".svg":"image/svg+xml", ".png":"image/png", ".woff2":"font/woff2"};
      try {
        const bytes = await readFile(file);
        res.setHeader("Content-Type", types[extname(file)] || "application/octet-stream");
        res.end(bytes);
      } catch {
        if (extname(path)) {res.writeHead(404); res.end(); return;}
        res.setHeader("Content-Type", "text/html");
        res.end(await readFile(resolve(root, "index.html")));
      }
    })().catch(() => {res.writeHead(500); res.end();});
  });
  await new Promise<void>(done => server.listen(0, "127.0.0.1", done));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Missing test server");
  origin = `http://127.0.0.1:${address.port}`;
});
test.afterAll(async () => {
  if (server) await new Promise<void>((done, reject) => {
    server.close(error => error ? reject(error) : done());
    server.closeIdleConnections();
  });
});

async function api(page: Page, path: string, method = "GET", body?: object) {
  return page.evaluate(async ({path, method, body}) => {
    const response = await fetch("/api/v1" + path, {method, headers:{Authorization:"Bearer " + localStorage.getItem("hustudy_token"), "Content-Type":"application/json"}, ...(body ? {body:JSON.stringify(body)} : {})});
    return {status:response.status, body:await response.json()};
  }, {path, method, body});
}

for (const width of [390, 1440]) test(`生产同源API：独立窗口共用账户、刷新笔记、冲突与权限 ${width}px`, async ({browser, request}) => {
  test.setTimeout(90000);
  const first = await browser.newContext({viewport:{width, height:1000}});
  const second = await browser.newContext({viewport:{width, height:1000}});
  try {
    const a = await first.newPage(), b = await second.newPage();
    const destinations: string[] = [];
    for (const page of [a,b]) page.on("request", req => {
      if (req.url().includes("/api/v1/")) destinations.push(new URL(req.url()).origin);
    });
    const username = "cloud_" + crypto.randomUUID().replaceAll("-", "");
    const password = "Isolated-password-2026";
    await a.goto(origin + "/overview");
    await a.getByRole("button", {name:"还没有账户？注册一个", exact:true}).click();
    await a.getByLabel("用户名", {exact:true}).fill(username);
    await a.getByLabel("密码", {exact:true}).fill(password);
    await a.getByRole("button", {name:"创建账户", exact:true}).click();
    await expect(a.locator(".app-shell")).toBeVisible();
    const identity = await api(a, "/auth/me"); expect(identity.status).toBe(200);
    const course = await api(a, "/courses", "POST", {name:"云端共用验收"}); expect(course.status).toBe(201);
    const note = await api(a, "/notes", "POST", {course_id:course.body.id, title:"跨窗口同一篇笔记", content:"已保存的原始理解"}); expect(note.status).toBe(201);

    await b.goto(origin + "/overview");
    expect(await b.evaluate(() => localStorage.getItem("hustudy_token"))).toBeNull();
    await b.getByLabel("用户名", {exact:true}).fill(username);
    await b.getByLabel("密码", {exact:true}).fill(password);
    await b.getByRole("button", {name:"登录", exact:true}).click();
    await expect(b.locator(".app-shell")).toBeVisible();
    expect((await api(b, "/auth/me")).body.id).toBe(identity.body.id);
    expect((await api(b, "/courses")).body.map((row:{id:string}) => row.id)).toContain(course.body.id);
    const url = origin + `/notes?course=${course.body.id}&note=${note.body.id}`;
    await a.goto(url); await b.goto(url);
    await expect(a.getByLabel("Markdown 正文", {exact:true})).toHaveValue("已保存的原始理解");
    await expect(b.getByLabel("Markdown 正文", {exact:true})).toHaveValue("已保存的原始理解");
    const updated = await api(a, `/notes/${note.body.id}`, "PATCH", {revision:note.body.revision, content:"第一端保存的新理解"}); expect(updated.status).toBe(200);
    await b.reload();
    await expect(b.getByLabel("Markdown 正文", {exact:true})).toHaveValue("第一端保存的新理解");
    const conflict = await api(b, `/notes/${note.body.id}`, "PATCH", {revision:note.body.revision, content:"旧版本不能覆盖"}); expect(conflict.status).toBe(409);
    expect((await api(a, `/notes/${note.body.id}`)).body.content).toBe("第一端保存的新理解");

    const stranger = await request.post(origin + "/api/v1/auth/register", {data:{username:username + "_other", password}});
    expect(stranger.status()).toBe(201);
    const auth = await stranger.json();
    const headers = {Authorization:"Bearer " + auth.access_token};
    expect((await request.get(origin + `/api/v1/notes/${note.body.id}`, {headers})).status()).toBe(404);
    expect(await (await request.get(origin + "/api/v1/courses", {headers})).json()).toEqual([]);
    expect(destinations.length).toBeGreaterThan(8);
    expect(new Set(destinations)).toEqual(new Set([origin]));
  } finally {await first.close(); await second.close();}
});
