export type Section = "api-connect" | "feedback" | "backup" | "search" | "help" | "overview" | "materials" | "notes" | "ai" | "exam" | "review" | "topics";
export type SourceTarget = {documentId:string;versionId:string;chunkId:string;previewPage?:number};
export type StudyTarget = SourceTarget & {mode: "qa" | "report"};
export type ExamTab = "bank" | "analysis" | "practice";
export type WorkspaceExtra = {topicId?:string;noteId?:string;mistakeId?:string;reviewMode?:"plan";material?:SourceTarget;study?:StudyTarget;aiResultId?:string;aiMode?:"qa"|"report";examTab?:ExamTab;attemptId?:string};
const sections: Section[] = ["api-connect","feedback","backup","search","help","overview","materials","notes","ai","exam","review","topics"];
const uuid = (value: string | null) => value && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value) ? value.toLowerCase() : "";

export function parseWorkspace(pathname: string, search: string) {
  const name = pathname.replace(/^\/+|\/+$/g, "") || "overview";
  const section = sections.includes(name as Section) ? name as Section : "overview";
  const params = new URLSearchParams(search);
  const courseId = uuid(params.get("course"));
  const noteId = uuid(params.get("note")) || undefined;
  const mistakeId = section === "review" ? uuid(params.get("mistake")) || undefined : undefined;
  const reviewMode = section === "review" && mistakeId && params.get("review") === "plan" ? "plan" as const : undefined;
  const documentId = uuid(params.get("document")), versionId = uuid(params.get("version")), chunkId = uuid(params.get("chunk"));
  const page = Number(params.get("page"));
  const material: SourceTarget | undefined = documentId && versionId ? {documentId,versionId,chunkId,previewPage:Number.isInteger(page)&&page>0&&page<=100000?page:undefined} : undefined;
  const studyMode = params.get("study");
  const study: StudyTarget | undefined = section === "ai" && material && (studyMode === "qa" || studyMode === "report") ? {...material, mode: studyMode} : undefined;
  const aiResultId = section === "ai" ? uuid(params.get("result")) : "";
  const aiMode = section === "ai" && ["qa", "report"].includes(params.get("mode") || "") ? params.get("mode") as "qa" | "report" : undefined;
  const examTab = section === "exam" && ["bank", "analysis", "practice"].includes(params.get("tab") || "") ? params.get("tab") as ExamTab : undefined;
  const attemptId = section === "exam" ? uuid(params.get("attempt")) : "";
  const topicId = (section === "topics" || section === "exam" && examTab === "practice") ? uuid(params.get("topic")) : "";
  const invalid = name!==section || ["course","note","document","version","chunk","mistake"].some(key => params.has(key) && !uuid(params.get(key)))
    || (["document","version","chunk","page"].some(key => params.has(key)) && !(documentId && versionId))
    || (params.has("page") && !(Number.isInteger(page) && page > 0 && page <= 100000))
    || (params.has("study") && !study)
    || (params.has("result") && !aiResultId) || (params.has("mode") && !aiMode)
    || (params.has("tab") && !examTab) || (params.has("attempt") && (!attemptId || examTab !== "practice"))
    || (params.has("topic") && !topicId) || (params.has("review") && !reviewMode);
  return {section,courseId,noteId,mistakeId,material,...(study ? {study} : {}),...(aiResultId ? {aiResultId} : {}),...(aiMode ? {aiMode} : {}),...(examTab ? {examTab} : {}),...(attemptId ? {attemptId} : {}),...(topicId ? {topicId} : {}),...(reviewMode?{reviewMode}:{}),invalid};
}

export function workspaceHref(section:Section, courseId:string, extra?:WorkspaceExtra) {
  const params = new URLSearchParams();
  if (uuid(courseId)) params.set("course",courseId);
  if(extra?.noteId) params.set("note",extra.noteId);
  if(section === "review" && extra?.mistakeId && uuid(extra.mistakeId)) params.set("mistake",extra.mistakeId);
  if(section === "review" && params.has("mistake") && extra?.reviewMode === "plan") params.set("review","plan");
  const source = section === "ai" && extra?.study ? extra.study : extra?.material;
  if(source) {
    params.set("document",source.documentId);params.set("version",source.versionId);
    if(source.chunkId)params.set("chunk",source.chunkId);
    if(source.previewPage)params.set("page",String(source.previewPage));
  }
  if(section === "ai" && extra?.study) params.set("study",extra.study.mode);
  if(section === "ai" && extra?.aiResultId) params.set("result",extra.aiResultId);
  if(section === "ai" && extra?.aiMode) params.set("mode",extra.aiMode);
  if(section === "exam" && extra?.examTab) params.set("tab",extra.examTab);
  if(section === "exam" && extra?.attemptId) {params.set("tab","practice"); params.set("attempt",extra.attemptId);}
  if(extra?.topicId && uuid(extra.topicId) && (section === "topics" || section === "exam" && params.get("tab") === "practice")) params.set("topic",extra.topicId);
  return "/"+section+(params.size?"?"+params.toString():"");
}
