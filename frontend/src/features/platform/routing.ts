export type Section = "backup" | "search" | "help" | "overview" | "materials" | "notes" | "ai" | "exam" | "review";
export type SourceTarget = {documentId:string;versionId:string;chunkId:string;previewPage?:number};
const sections: Section[] = ["backup","search","help","overview","materials","notes","ai","exam","review"];
const uuid = (value: string | null) => value && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value) ? value.toLowerCase() : "";

export function parseWorkspace(pathname: string, search: string) {
  const name = pathname.replace(/^\/+|\/+$/g, "") || "overview";
  const section = sections.includes(name as Section) ? name as Section : "overview";
  const params = new URLSearchParams(search);
  const courseId = uuid(params.get("course"));
  const noteId = uuid(params.get("note")) || undefined;
  const documentId = uuid(params.get("document")), versionId = uuid(params.get("version")), chunkId = uuid(params.get("chunk"));
  const page = Number(params.get("page"));
  const material: SourceTarget | undefined = documentId && versionId ? {documentId,versionId,chunkId,previewPage:Number.isInteger(page)&&page>0&&page<=100000?page:undefined} : undefined;
  const invalid = name!==section || ["course","note","document","version","chunk"].some(key => params.has(key) && !uuid(params.get(key)))
    || (["document","version","chunk","page"].some(key => params.has(key)) && !(documentId && versionId))
    || (params.has("page") && !(Number.isInteger(page) && page > 0 && page <= 100000));
  return {section,courseId,noteId,material,invalid};
}

export function workspaceHref(section:Section, courseId:string, extra?:{noteId?:string;material?:SourceTarget}) {
  const params = new URLSearchParams();
  if (uuid(courseId)) params.set("course",courseId);
  if(extra?.noteId) params.set("note",extra.noteId);
  if(extra?.material) {
    params.set("document",extra.material.documentId);params.set("version",extra.material.versionId);
    if(extra.material.chunkId)params.set("chunk",extra.material.chunkId);
    if(extra.material.previewPage)params.set("page",String(extra.material.previewPage));
  }
  return "/"+section+(params.size?"?"+params.toString():"");
}
