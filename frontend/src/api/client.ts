import { queryClient, sessionPartition, sessionGeneration, advanceSessionGeneration } from "./query";
const API_BASE = import.meta.env?.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export type PreviewCapabilities = {native_pdf:boolean;office_available:boolean;office_status:string;message:string;installation_url:string};
export type ManualTranscript = {id:string;version_id:string;page:number;text:string;text_hash:string;revision:number;status:"DRAFT"|"CONFIRMED"|"SUPERSEDED"|"WITHDRAWN";supersedes_id:string|null;chunk_id:string|null;confirmed_by:string|null;confirmed_at:string|null;created_at:string;updated_at:string};
export type Course = { id: string; name: string; description?: string | null; category: string; tags: string[]; revision: number; created_at: string; updated_at: string };
export type CourseMetadata = {name: string; description: string | null; category: string; tags: string[]};
export type CourseDeletionPreview = {course: Course; counts: Record<string, number>};
export type DocumentItem = { id: string; course_id: string; name: string; category: string; tags: string[]; original_filename: string; size_bytes: number; created_at: string; updated_at: string; latest_version_id?: string; parse_status?: string; preview_status?: string; index_status?: string; parse_error?: string | null; preview_error?: string | null; latest_version_no?: number; confirmed_transcript_count?: number };
export type Asset = { id: string; name: string; tags: string[]; revision: number; created_at: string; updated_at: string; original_filename: string; mime_type: string; size_bytes: number; alt: string; source_version_id?: string | null; source_page?: number | null; source_locator_type?: string | null };
export type AssetFilters = {q: string; tag: string; origin: "all" | "captured" | "external"; sort: "newest" | "oldest" | "updated" | "name"; offset: number; limit: number};
export type AssetPage = {items: Asset[]; total: number; offset: number; limit: number; tags: string[]};
export type AssetMetadata = Asset & { source_document_id?: string | null; source_document_name?: string | null; source_version_no?: number | null; source_availability: "active" | "unavailable"; sha256: string; created_at: string };
export type Version = { id: string; document_id: string; version_no: number; original_filename: string; size_bytes: number; sha256: string; created_at: string; updated_at: string; parse_status: string; preview_status: string; index_status: string; parse_error?: string | null; preview_error?: string | null };
export type Job = { id: string; type: string; status: string; resource_id: string; progress: number; error?: string | null; attempt_count: number; max_attempts: number; document_id?: string; document_name?: string; version_no?: number };
export type MaterialExport = {id: string; course_id: string; created_at: string; snapshot_at: string | null; sha256: string | null; size_bytes: number; counts: Record<string,number>; availability: "pending" | "active" | "unavailable"; job: Job};
export type StudyReport = {summary:string; citations?:SourceCitation[]; validation_notices?:string[]; learning_goals:string[]; prerequisites:string[]; learning_sequence:string[]; topics:{topic_id:string;name:string;explanation:string;concept_group?:string|null;related_concepts?:{target:string;relation:string}[];breakthrough_steps?:string[];misconceptions:string[];labels:{kind:"key"|"difficult"|"exam";reason:string;origin:"ai_suggestion"}[];citations:SourceCitation[]}[];examples:ReportExercise[];self_checks:ReportExercise[];review_suggestions?:string[]};
export type ReportExercise = {generation_origin?:"rule_generated";question:string;answer:string;citations:SourceCitation[]};
export type ReportCoverage = {warnings?:string[];truncated:boolean;notice:string;versions:{version_id:string;document_name:string;total_chunks:number;selected_chunks:number;total_chars:number;sent_chars:number;truncated:boolean}[]};
export type ReportScope = {goal:string;scope_version_ids:string[];study_mode:"preview"|"systematic"|"revision";coverage:ReportCoverage};
export type CandidateOptions = {chapter_id:string;topic_ids:string[];type:"single_choice"|"boolean"|"short_answer";count:number;points:string;difficulty_label:"basic"|"application"|"advanced";mode:"historical"|"variant"|"weakness";original_past_question_ids:string[]};
export type CandidateContext = {topics:{id:string;name:string}[];references:{id:string;paper_id:string;title:string;year:number|null;stem:string;topic_id:string|null}[]};
export type CandidateScope = {request:CandidateOptions & {goal:string;version_ids:string[];chunk_ids:string[]};coverage:ReportCoverage;exam_context:CandidateContext};
export type QuestionDraft = {question_id:string;chapter_id:string;type:CandidateOptions["type"];stem:string;options:{id:string;text:string}[];answer:string|boolean|null;rubric:{criterion:string;points:number}[];points:number;explanation:string;topic_ids:string[];difficulty_label:string;mode:string;original_past_question_ids:string[];material_citations:SourceCitation[];generation_status:"draft"};
export type AIAnswer = {id: string; course_id: string; query: string; status: string; model_mode: string; result: {answer?: string; message?: string; citations?: SourceCitation[]; model_notice?: string; model?: string; error_code?: string; review_status?: string;study_report?:StudyReport;study_report_sections?:{title:string;report:StudyReport}[];partial?:boolean;validation_notices?:string[];coverage?:ReportCoverage;prompt_version?:string;question_drafts?:QuestionDraft[];exam_context?:CandidateContext;mode_notice?:string;integration_notice?:string;dependency_status?:string;provider_code?:string|null;retry_after_seconds?:number|null}};
export type AIProvider = {provider: string; configured: boolean; model: string; endpoint: string; checked_at: string; documentation_url: string; policy_status: string; policy_entry_url: string; max_context_chars: number; max_output_tokens: number};
export type AISource = {source_id: string; version_id: string; document_id: string; document_name: string; version_no: number; locator: {type: string; value: string}; text: string; source_kind: string; sha256: string};
export type RemoteQuery = {reusable_result?:AIAnswer|null;id: string; course_id: string; query: string; request_kind?:"qa"|"study_report"|"question_drafts";batch_progress?:{total:number;completed:number;max_calls:number;chars:number}|null;report_scope?:(ReportScope & {chunk_ids?:string[];batched?:boolean})|null;candidate_scope?:CandidateScope|null; model: string; endpoint: string; expires_at: string; consented_at: string | null; dispatched_at: string | null; sources: AISource[]; job: Job | null; result: AIAnswer | null};
export type MaterialReference = { citation_id: string; note_id: string; note_title: string; chunk_id: string; quote: string; locator_type: string; locator_value: string };
export type SearchHit = { source_kind?: string; transcript_id?: string | null; chunk_id: string; version_id: string; version_no: number; document_id: string; document_name: string; category: string; tags: string[]; locator_type: string; locator_value: string; text: string; score: number };
export type TextExcerpt = {text:string; start_offset:number; truncated_after:boolean; highlights:{start:number;end:number}[]};
export type PageResult<T> = {items:T[];total:number;offset:number;limit:number};
export type SearchPage = PageResult<Omit<SearchHit,"text"> & {excerpt:TextExcerpt}>;
export type NoteSearchPage = PageResult<{id:string;title:string;excerpt:TextExcerpt;updated_at:string}>;
export type MaterialFilters = { category?: string; tag?: string; latestOnly?: boolean };
export type DocumentBrowse = {q: string; category: string; tag: string; state: string; sort: string; offset: number; limit: number};
export type DocumentPage = {items: DocumentItem[]; total: number; offset: number; limit: number; stats: Record<string, number>; categories: string[]; tags: string[]};
export type JobPage = {items: Job[]; total: number; offset: number; limit: number; pending_count: number};
export type AccountArchive = {id: string; purpose: "export" | "restore"; created_at: string; sha256: string | null; size_bytes: number; counts: Record<string, number>; job: {id:string;status:string;progress:number;error:string | null}};
export type SourceCitation = { source_kind?: string; id?: string; document_id?: string; version_id: string; chunk_id: string; locator?: { type: string; value: string }; locator_type?: string; locator_value?: string; quote: string; availability: string };
export type Chunk = { source_kind?: string; transcript_id?: string | null; transcript_status?: string | null; confirmed_at?: string | null; id: string; version_id: string; locator_type: string; locator_value: string; text: string };
export type Note = { id: string; title: string; content: string; course_id?: string | null; revision: number; updated_at: string };
export type Topic = { id: string; name: string; aliases: string[] };
export type Paper = { id: string; title: string; year?: number | null; review_status: string; questions: PastQuestion[] };
export type PastQuestion = { id: string; number: string; stem: string; question_type: string; points?: number | null; answer?: string | null; answer_source: string; status: string; topic_id?: string | null };
export type Blueprint = { id: string; name: string; config: Record<string, unknown>; status: string };
export type ExamPaper = { id: string; title: string; mode: string; status: string; questions: Question[] };
export type Question = { id: string; type: string; stem: string; options?: string[]; points: number; topic: string; answer?: string | boolean; rubric?: string[]; explanation?: string };
export type Attempt = { id: string; paper_id: string; status: string; answers: Record<string, unknown>; score?: number | null };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number, public requestId?: string, public code?: string, public details?: Record<string, unknown>) { super(message); this.status = status; }
}

function notifyUnauthorized(status: number, token?: string) {
  if (status === 401 && token && typeof window !== "undefined") window.dispatchEvent(new CustomEvent("hustudy:unauthorized", {detail:sessionPartition(token)}));
}

async function fileRequest(path: string, token: string, signal?: AbortSignal): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal });
  if (!response.ok) {
    notifyUnauthorized(response.status, token);
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.error?.message || "文件暂不可用", response.status);
  }
  return response.blob();
}

async function transport<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("无法连接后端服务，请确认 Uvicorn 正在 127.0.0.1:8000 运行", 0);
  }
  if (!response.ok) {
    notifyUnauthorized(response.status, token);
    let message = `请求失败（${response.status}）`;
    let code: string | undefined;
    let details: Record<string, unknown> | undefined;
    let requestId = response.headers.get("X-Request-ID") || undefined;
    try { const body = await response.json(); message = body.error?.message || body.detail || message; code = body.error?.code; details = body.error?.details; requestId = body.error?.request_id || requestId; } catch { /* keep status message */ }
    throw new ApiError(message, response.status, requestId, code, details);
  }
  if (response.status === 204) return undefined as T;
  if (response.headers.get("Content-Type")?.startsWith("text/markdown")) return await response.text() as T;
  return response.json() as Promise<T>;
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const scope = sessionPartition(token);
  if (!options.method || options.method.toUpperCase()==="GET") return queryClient.fetchQuery({queryKey:["api",scope,path,sessionGeneration(scope)],queryFn:({signal})=>transport<T>(path,{...options,signal},token)});
  const result = await transport<T>(path,options,token);
  advanceSessionGeneration(scope);
  await queryClient.invalidateQueries({queryKey:["api",scope],refetchType:"none"});
  return result;
}

export const api = {
  materialCapabilities: (token:string) => request<PreviewCapabilities>("/material-capabilities",{},token),
  requestPreview: (token:string,id:string) => request<Job>(`/versions/${id}/preview-jobs`,{method:"POST"},token),
  accountArchives: (token: string) => request<AccountArchive[]>("/backups", {}, token),
  createAccountArchive: (token: string) => request<AccountArchive>("/backups", {method:"POST"}, token),
  restoreAccountArchive: (token: string, file: File) => { const body = new FormData(); body.append("file",file); body.append("confirm","RESTORE_EMPTY_ACCOUNT"); return request<AccountArchive>("/backups/restore",{method:"POST",body},token); },
  downloadAccountArchive: (token: string, id: string) => fileRequest(`/backups/${id}/download`,token),
  removeAccountArchive: (token: string, id: string) => request<void>(`/backups/${id}`,{method:"DELETE"},token),
  document: (token: string, id: string) => request<DocumentItem>(`/documents/${id}`, {}, token),
  documentPage: (token: string, id: string, filters: DocumentBrowse) => request<DocumentPage>(`/courses/${id}/documents/page?${new URLSearchParams(Object.entries(filters).map(([k,v]) => [k,String(v)]))}`, {}, token),
  jobPage: (token: string, id: string, status: string, offset: number) => request<JobPage>(`/courses/${id}/jobs/page?${new URLSearchParams({status,offset:String(offset),limit:"10"})}`, {}, token),
  aiProvider: (token: string) => request<AIProvider>("/ai/provider", {}, token),
  previewStudyReport: (token:string,courseId:string,goal:string,versionIds:string[],studyMode:string,chunkIds:string[]=[]) => request<RemoteQuery>(`/courses/${courseId}/study-reports/preview`,{method:"POST",body:JSON.stringify({goal,version_ids:versionIds,study_mode:studyMode,chunk_ids:chunkIds})},token),
  studyReports: (token:string,courseId:string) => request<AIAnswer[]>(`/courses/${courseId}/study-reports`,{},token),
  demoStudyReport: (token:string,courseId:string,goal:string,versionIds:string[],studyMode:string,chunkIds:string[]=[]) => request<AIAnswer>(`/courses/${courseId}/study-reports/demo`,{method:"POST",body:JSON.stringify({goal,version_ids:versionIds,study_mode:studyMode,chunk_ids:chunkIds})},token),
  aiResults: (token:string,courseId:string) => request<AIAnswer[]>(`/courses/${courseId}/ai-results`,{},token),
  candidateContext: (token:string,courseId:string) => request<CandidateContext>(`/courses/${courseId}/question-draft-context`,{},token),
  questionDrafts: (token:string,courseId:string) => request<AIAnswer[]>(`/courses/${courseId}/question-drafts`,{},token),
  previewQuestionDrafts: (token:string,courseId:string,goal:string,versionIds:string[],chunkIds:string[],config:CandidateOptions) => request<RemoteQuery>(`/courses/${courseId}/question-drafts/preview`,{method:"POST",body:JSON.stringify({...config,goal,version_ids:versionIds,chunk_ids:chunkIds})},token),
  demoQuestionDrafts: (token:string,courseId:string,goal:string,versionIds:string[],chunkIds:string[],config:CandidateOptions) => request<AIAnswer>(`/courses/${courseId}/question-drafts/demo`,{method:"POST",body:JSON.stringify({...config,goal,version_ids:versionIds,chunk_ids:chunkIds})},token),
  previewRemoteQuery: (token: string, courseId: string, query: string, versionIds: string[],chunkIds:string[]=[]) => request<RemoteQuery>(`/courses/${courseId}/remote-queries/preview`, {method: "POST", body: JSON.stringify({query, version_ids: versionIds,chunk_ids:chunkIds})}, token),
  remoteQuery: (token: string, id: string) => request<RemoteQuery>(`/remote-queries/${id}`, {}, token),
  confirmRemoteQuery: (token: string, id: string) => request<RemoteQuery>(`/remote-queries/${id}/confirm`, {method: "POST", body: JSON.stringify({confirm_remote_send: true})}, token),
  reuseRemoteQuery: (token:string,id:string,resultId:string) => request<AIAnswer>(`/remote-queries/${id}/reuse`,{method:"POST",body:JSON.stringify({result_id:resultId})},token),
  resumeRemoteQuery: (token:string,id:string) => request<RemoteQuery>(`/remote-queries/${id}/resume`,{method:"POST",body:JSON.stringify({confirm_remote_send:true})},token),
  cancelRemoteQuery: (token: string, id: string) => request<RemoteQuery>(`/remote-queries/${id}/cancel`, {method: "POST"}, token),
  transcripts: (token:string,versionId:string) => request<ManualTranscript[]>(`/versions/${versionId}/transcripts`,{},token),
  createTranscript: (token:string,versionId:string,payload:{page:number;text:string;supersedes_id?:string}) => request<ManualTranscript>(`/versions/${versionId}/transcripts`,{method:"POST",body:JSON.stringify(payload)},token),
  updateTranscript: (token:string,id:string,payload:{revision:number;text:string}) => request<ManualTranscript>(`/transcripts/${id}`,{method:"PATCH",body:JSON.stringify(payload)},token),
  confirmTranscript: (token:string,id:string,revision:number) => request<ManualTranscript>(`/transcripts/${id}/confirm`,{method:"POST",body:JSON.stringify({revision})},token),
  withdrawTranscript: (token:string,id:string,revision:number) => request<ManualTranscript>(`/transcripts/${id}/withdraw`,{method:"POST",body:JSON.stringify({revision})},token),
  updateDocument: (token: string, id: string, payload: {name?: string; category?: string; tags?: string[]}) => request<DocumentItem>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  materialReferences: (token: string, id: string, chunkId?: string) => request<MaterialReference[]>(`/versions/${id}/references${chunkId ? '?chunk_id=' + encodeURIComponent(chunkId) : ''}`, {}, token),
  assets: (token: string, id: string) => request<Asset[]>(`/courses/${id}/assets`, {}, token),
  asset: (token: string, id: string) => fileRequest(`/assets/${id}`, token),
  assetMetadata: (token: string, id: string) => request<AssetMetadata>(`/assets/${id}/metadata`, {}, token),
  assetPage: (token: string, id: string, filters: AssetFilters) => { const params = new URLSearchParams({q: filters.q, origin: filters.origin, sort: filters.sort, offset: String(filters.offset), limit: String(filters.limit)}); if (filters.tag) params.set("tag", filters.tag); return request<AssetPage>(`/courses/${id}/assets/page?${params}`, {}, token); },
  updateAsset: (token: string, id: string, payload: {revision: number; name: string; alt: string; tags: string[]}) => request<Asset>(`/assets/${id}`, {method: "PATCH", body: JSON.stringify(payload)}, token),
  assetReferences: (token: string, id: string) => request<Note[]>(`/assets/${id}/references`, {}, token),
  deleteAsset: (token: string, id: string) => request<void>(`/assets/${id}`, { method: "DELETE" }, token),
  uploadAsset: (token: string, id: string, file: File, alt: string, source?: {versionId: string; page: number}) => { const body = new FormData(); body.append("file", file); const params = new URLSearchParams({alt}); if (source) { params.set("source_version_id", source.versionId); params.set("source_page", String(source.page)); } return request<Asset>(`/courses/${id}/assets?${params}`, { method: "POST", body }, token); },
  version: (token: string, id: string) => request<Version>(`/versions/${id}`, {}, token),
  versions: (token: string, id: string) => request<Version[]>(`/documents/${id}/versions`, {}, token),
  jobs: (token: string, id: string) => request<Job[]>(`/courses/${id}/jobs`, {}, token),
  retryJob: (token: string, id: string) => request<Job>(`/jobs/${id}/retry`, { method: "POST" }, token),
  cancelJob: (token: string, id: string) => request<Job>(`/jobs/${id}/cancel`, {method: "POST"}, token),
  materialExports: (token: string, id: string) => request<MaterialExport[]>(`/courses/${id}/material-exports`, {}, token),
  createMaterialExport: (token: string, id: string, requestId: string) => request<MaterialExport>(`/courses/${id}/material-exports`, {method: "POST", body: JSON.stringify({request_id: requestId})}, token),
  retryMaterialExport: (token: string, id: string) => request<MaterialExport>(`/material-exports/${id}/retry`, {method: "POST"}, token),
  removeMaterialExport: (token: string, id: string) => request<void>(`/material-exports/${id}`, {method: "DELETE"}, token),
  downloadMaterialExport: (token: string, id: string) => fileRequest(`/material-exports/${id}/download`, token),
  reindexVersion: (token: string, id: string, requestId: string) => request<Job>(`/versions/${id}/reindex`, {method: "POST", body: JSON.stringify({request_id: requestId})}, token),
  deleteDocument: (token: string, id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }, token),
  uploadVersion: (token: string, id: string, file: File) => { const data = new FormData(); data.append("file", file); return request<Job>(`/documents/${id}/versions`, { method: "POST", body: data }, token); },
  original: (token: string, id: string, signal?:AbortSignal) => fileRequest(`/versions/${id}/original`, token,signal),
  preview: (token: string, id: string) => fileRequest(`/versions/${id}/preview`, token),
  citations: (token: string, id: string) => request<SourceCitation[]>(`/notes/${id}/citations`, {}, token),
  completeReviewTask: (token: string, id: string) => request(`/review-tasks/${id}/complete`, {method: "POST"}, token),
  note: (token: string, id: string) => request<Note>(`/notes/${id}`, {}, token),
  backlinks: (token: string, id: string) => request<Note[]>(`/notes/${id}/backlinks`, {}, token),
  exportNote: (token: string, id: string) => request<string>(`/notes/${id}/export`, {}, token),

  createReviewTask: (token: string, payload: { mistake_id: string; title: string; due_date: string }) => request("/review-tasks", { method: "POST", body: JSON.stringify(payload) }, token),
  register: (username: string, password: string) => request<{ access_token: string; user: { id: string; username: string } }>("/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) => request<{ access_token: string; user: { id: string; username: string } }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  courses: (token: string) => request<Course[]>("/courses", {}, token),
  createCourse: (token: string, name: string, description: string, organization: {category: string; tags: string[]} = {category: "未分类", tags: []}) => request<Course>("/courses", { method: "POST", body: JSON.stringify({ name, description, ...organization }) }, token),
  updateCourse: (token: string, id: string, payload: Partial<CourseMetadata> & {revision: number}) => request<Course>(`/courses/${id}`, {method: "PATCH", body: JSON.stringify(payload)}, token),
  courseDeletionPreview: (token: string, id: string) => request<CourseDeletionPreview>(`/courses/${id}/deletion-preview`, {}, token),
  deleteCourse: (token: string, id: string, revision: number) => request<void>(`/courses/${id}?revision=${revision}`, {method: "DELETE"}, token),
  documents: (token: string, courseId: string, filters: MaterialFilters = {}) => { const params = new URLSearchParams(); if (filters.category) params.set("category", filters.category); if (filters.tag) params.set("tag", filters.tag); return request<DocumentItem[]>(`/courses/${courseId}/documents?${params}`, {}, token); },
  uploadDocument: (token: string, courseId: string, file: File) => { const data = new FormData(); data.append("file", file); return request<Job>(`/courses/${courseId}/documents`, { method: "POST", body: data }, token); },
  chunks: (token: string, versionId: string) => request<Chunk[]>(`/versions/${versionId}/chunks`, {}, token),
  searchPage: (token:string,courseId:string,query:string,filters:MaterialFilters={},offset=0,limit=12) => { const params=new URLSearchParams({q:query,offset:String(offset),limit:String(limit)}); if(filters.category) params.set("category",filters.category); if(filters.tag) params.set("tag",filters.tag); if(filters.latestOnly!==undefined) params.set("latest_only",String(filters.latestOnly)); return request<SearchPage>(`/courses/${courseId}/search/page?${params}`,{},token); },
  noteSearch: (token:string,courseId:string,query:string,offset=0,limit=12) => request<NoteSearchPage>(`/courses/${courseId}/note-search?${new URLSearchParams({q:query,offset:String(offset),limit:String(limit)})}`,{},token),
  search: (token: string, courseId: string, query: string, filters: MaterialFilters = {}) => { const params = new URLSearchParams({q: query}); if (filters.category) params.set("category", filters.category); if (filters.tag) params.set("tag", filters.tag); if (filters.latestOnly !== undefined) params.set("latest_only", String(filters.latestOnly)); return request<SearchHit[]>(`/courses/${courseId}/search?${params}`, {}, token); },
  notes: (token: string, courseId?: string) => request<Note[]>(`/notes${courseId ? `?course_id=${courseId}` : ""}`, {}, token),
  createNote: (token: string, payload: { title: string; content: string; course_id?: string; citations?: {version_id: string; chunk_id: string; quote: string}[] }) => request<Note>("/notes", { method: "POST", body: JSON.stringify(payload) }, token),
  updateNote: (token: string, id: string, payload: { title: string; content: string; course_id?: string; revision: number }) => request<Note>(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  citation: (token: string, noteId: string, payload: { version_id: string; chunk_id: string; quote: string }) => request(`/notes/${noteId}/citations`, { method: "POST", body: JSON.stringify(payload) }, token),
  aiQuery: (token: string, courseId: string, query: string) => request<AIAnswer>(`/courses/${courseId}/ai-queries`, { method: "POST", body: JSON.stringify({ query, mode: "demo" }) }, token),
  topics: (token: string, courseId: string) => request<Topic[]>(`/courses/${courseId}/topics`, {}, token),
  createTopic: (token: string, courseId: string, name: string) => request<Topic>(`/courses/${courseId}/topics`, { method: "POST", body: JSON.stringify({ name, aliases: [] }) }, token),
  papers: (token: string, courseId: string) => request<Paper[]>(`/courses/${courseId}/past-papers`, {}, token),
  createPaper: (token: string, courseId: string, payload: { title: string; year?: number; content: string }) => request<Paper>(`/courses/${courseId}/past-papers`, { method: "POST", body: JSON.stringify(payload) }, token),
  extractPaper: (token: string, paperId: string) => request<Paper>(`/past-papers/${paperId}/extract`, { method: "POST" }, token),
  confirmPaper: (token: string, paperId: string) => request<Paper>(`/past-papers/${paperId}/confirm`, { method: "POST" }, token),
  createBlueprint: (token: string, courseId: string, payload: Record<string, unknown>) => request<Blueprint>(`/exam-blueprints?course_id=${courseId}`, { method: "POST", body: JSON.stringify(payload) }, token),
  generatePaper: (token: string, blueprintId: string) => request<ExamPaper>(`/exam-blueprints/${blueprintId}/generate`, { method: "POST" }, token),
  reviewPaper: (token: string, paperId: string) => request<ExamPaper>(`/exam-papers/${paperId}/review`, { method: "POST" }, token),
  startAttempt: (token: string, paperId: string) => request<Attempt>(`/exam-papers/${paperId}/attempts`, { method: "POST" }, token),
  examPaper: (token: string, id: string) => request<ExamPaper>(`/exam-papers/${id}`, {}, token),
  attemptResult: (token: string, id: string) => request<ExamPaper>(`/attempts/${id}/result`, {}, token),
  paperWithAnswers: (token: string, paperId: string) => request<ExamPaper>(`/exam-papers/${paperId}?include_answers=true`, {}, token),
  answer: (token: string, attemptId: string, questionId: string, answer: unknown) => request<Attempt>(`/attempts/${attemptId}/answers/${questionId}`, { method: "PUT", body: JSON.stringify({ answer }) }, token),
  submit: (token: string, attemptId: string) => request<Attempt>(`/attempts/${attemptId}/submit`, { method: "POST" }, token),
  mistakes: (token: string) => request<Array<{ id: string; question: Question; given: unknown }>>("/mistakes", {}, token),
  reviewTasks: (token: string) => request<Array<{ id: string; title: string; due_date: string; status: string }>>("/review-tasks/today", {}, token),
  feedback: (token: string, payload: { kind: string; content: string; rating?: number }) => request("/feedback", { method: "POST", body: JSON.stringify(payload) }, token),
};
