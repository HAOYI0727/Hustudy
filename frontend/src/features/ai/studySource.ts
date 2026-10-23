import { api } from "../../api/client";
import type { StudyTarget } from "../platform/routing";

/** Resolve every edge through authorized APIs before preselecting an incoming source. */
export async function resolveStudySource(token: string, courseId: string, target: StudyTarget) {
  const version = await api.version(token, target.versionId);
  if (version.document_id !== target.documentId) throw new Error("阅读来源的资料与版本不一致，请返回资料页重新选择");
  const document = await api.document(token, version.document_id);
  if (document.course_id !== courseId) throw new Error("阅读来源不属于当前课程，请返回资料页重新选择");
  const chunks = await api.chunks(token, version.id);
  const chunk = target.chunkId ? chunks.find(row => row.id === target.chunkId) : undefined;
  if (target.chunkId && !chunk) throw new Error("阅读片段已不可用或不属于这个版本，请返回资料页重新选择");
  if (!chunks.length) throw new Error("这个版本暂无可用正文，请先完成解析或确认人工补录");
  return {document, version, chunk};
}
