import {afterEach, expect, test, vi} from "vitest";
import {api, type Chunk, type DocumentItem, type Version} from "../../src/api/client";
import {resolveStudySource} from "../../src/features/ai/studySource";
import {parseWorkspace, workspaceHref, type StudyTarget} from "../../src/features/platform/routing";

const course = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const target: StudyTarget = {documentId: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", versionId: "cccccccc-cccc-cccc-cccc-cccccccccccc", chunkId: "dddddddd-dddd-dddd-dddd-dddddddddddd", mode: "qa"};
afterEach(() => vi.restoreAllMocks());
function source() {
  vi.spyOn(api, "version").mockResolvedValue({id: target.versionId, document_id: target.documentId, version_no: 1} as Version);
  vi.spyOn(api, "document").mockResolvedValue({id: target.documentId, course_id: course, latest_version_id: "new-version"} as DocumentItem);
  vi.spyOn(api, "chunks").mockResolvedValue([{id: target.chunkId, version_id: target.versionId, text: "历史原文"}] as Chunk[]);
}
test.each(["qa", "report"] as const)("来源与学习模式 %s 可刷新往返", mode => {
  const url = new URL(workspaceHref("ai", course, {study: {...target, mode}}), "http://localhost");
  expect(parseWorkspace(url.pathname, url.search)).toMatchObject({study: {...target, mode}, invalid: false});
});
test.each(["/ai?study=qa", "/ai?study=unknown", "/materials?study=report"])("无效学习入口不能作为已选来源：%s", href => {
  const url = new URL(href, "http://localhost"); expect(parseWorkspace(url.pathname, url.search)).toMatchObject({invalid: true});
});
test("历史版本保持原身份，来源校验不创建AI请求", async () => {
  source(); const preview = vi.spyOn(api, "previewRemoteQuery");
  const result = await resolveStudySource("test-token", course, target);
  expect(result.version.id).toBe(target.versionId); expect(result.chunk?.text).toBe("历史原文");
  expect(preview).not.toHaveBeenCalled();
});
test("拒绝版本、课程、片段错配和撤权，不退化成全课程来源", async () => {
  source();
  await expect(resolveStudySource("test", course, {...target, documentId: "wrong"})).rejects.toThrow("资料与版本不一致");
  await expect(resolveStudySource("test", "wrong-course", target)).rejects.toThrow("不属于当前课程");
  await expect(resolveStudySource("test", course, {...target, chunkId: "wrong"})).rejects.toThrow("片段已不可用");
  vi.mocked(api.version).mockRejectedValue(new Error("来源已撤权"));
  await expect(resolveStudySource("test", course, target)).rejects.toThrow("来源已撤权");
});
