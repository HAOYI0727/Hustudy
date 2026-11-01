import type {DisplayGroup} from "../features/exams/questionGroups";
export type NoteAIConfig = {provider: string; model: string; configured: boolean; has_personal_key: boolean; revision: number; source: "personal" | "server" | "none"; reason: string | null; endpoint: string};
export type ModelProfile={id:string;name:string;vendor:'deepseek'|'compatible';model:string;endpoint:string;vision:boolean;thinking:boolean;json_mode:boolean;configured:boolean};
export type ModelConnections={revision:number;active:string|null;profiles:ModelProfile[];builtin:{name:string;model:string;configured:boolean};allowed_hosts:string[]};
export type ModelProfileInput=Omit<ModelProfile,'id'|'configured'>&{id?:string;key?:string;revision:number};
export type NoteAssistantInput={course_id:string;note_id?:string;revision?:number;task:'summary'|'explain'|'organize'|'review'|'custom';scope:'full'|'selection';text:string;instruction:string};
export type NoteAssistantPreview={preview_token:string;expires_at:number;model:string;endpoint:string;task:string;scope:string;text:string;instruction:string;characters:number;notice:string};
export type NoteAssistantResult={request_id:string;markdown:string;model:string;task:string;usage:Record<string,number>;notice:string};
import { queryClient, sessionPartition, sessionGeneration, advanceSessionGeneration } from "./query";
import {resolveApiBase} from "./base";
const API_BASE = resolveApiBase(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD);

export type PreviewCapabilities = {native_pdf:boolean;office_available:boolean;office_status:string;message:string;installation_url:string};
export type ProcessingServiceStatus={state:"ready"|"starting"|"unavailable";checked_at:string;message:string};
export type ManualTranscript = {id:string;version_id:string;page:number;text:string;text_hash:string;revision:number;status:"DRAFT"|"CONFIRMED"|"SUPERSEDED"|"WITHDRAWN";supersedes_id:string|null;chunk_id:string|null;confirmed_by:string|null;confirmed_at:string|null;created_at:string;updated_at:string};
export type Course = { id: string; name: string; description?: string | null; category: string; tags: string[]; revision: number; created_at: string; updated_at: string };
export type CourseMetadata = {name: string; description: string | null; category: string; tags: string[]};
export type CourseDeletionPreview = {course: Course; counts: Record<string, number>};
export type DocumentItem = { id: string; course_id: string; name: string; category: string; tags: string[]; original_filename: string; size_bytes: number; created_at: string; updated_at: string; latest_version_id?: string; parse_status?: string; preview_status?: string; index_status?: string; parse_error?: string | null; preview_error?: string | null; latest_version_no?: number; confirmed_transcript_count?: number };
export type DocumentMetadata = Pick<DocumentItem,"id"|"course_id"|"name"|"category"|"tags"|"updated_at">;
export type DocumentOrganizeChange = {category?:string;tags_mode:"keep"|"add"|"remove"|"replace"|"clear";tags:string[]};
export type NoteOption = Pick<Note,"id"|"title"|"updated_at">;
export type NoteOptionPage = PageResult<NoteOption>;
export type Asset = { id: string; name: string; tags: string[]; revision: number; created_at: string; updated_at: string; original_filename: string; mime_type: string; size_bytes: number; alt: string; source_version_id?: string | null; source_page?: number | null; source_locator_type?: string | null };
export type AssetFilters = {q: string; tag: string; origin: "all" | "captured" | "external"; sort: "newest" | "oldest" | "updated" | "name"; offset: number; limit: number};
export type AssetPage = {items: Asset[]; total: number; offset: number; limit: number; tags: string[]};
export type AssetMetadata = Asset & { source_document_id?: string | null; source_document_name?: string | null; source_version_no?: number | null; source_availability: "active" | "unavailable"; sha256: string; created_at: string };
export type Version = { id: string; document_id: string; version_no: number; original_filename: string; size_bytes: number; sha256: string; created_at: string; updated_at: string; parse_status: string; preview_status: string; index_status: string; parse_error?: string | null; preview_error?: string | null };
export type Job = { id: string; type: string; status: string; resource_id: string; progress: number; error?: string | null; attempt_count: number; max_attempts: number; document_id?: string; document_name?: string; version_no?: number };
export type MaterialExport = {id: string; course_id: string; created_at: string; snapshot_at: string | null; sha256: string | null; size_bytes: number; counts: Record<string,number>; availability: "pending" | "active" | "unavailable"; scope?:"course"|"selected";selected_count?:number;job: Job};
export type TeacherMark={kind:"key"|"difficult"|"exam";version_id:string;chunk_id:string;quote:string;reason:string;confirmed:true};
export type AISupplementSelection={note_ids:string[];notes_confirmed:boolean};
export type LabelEvidence={question_id?:string;paper_title?:string;year?:number|null;topic_name?:string;quote?:string;reason?:string};
export type ReportLabel={kind:"key"|"difficult"|"exam";reason:string;origin:"ai_suggestion"|"teacher_mark"|"observed_exam";notice?:string;availability?:string;evidence?:LabelEvidence[]};
export type AISupplement={notes:{id:string;title:string;revision:number;content:string}[];teacher_marks:TeacherMark[];exam_evidence:LabelEvidence[];exam_paper_ids?:string[]};
export type StudyReport = {summary:string; citations?:SourceCitation[]; validation_notices?:string[]; learning_goals:string[]; prerequisites:string[]; learning_sequence:string[]; topics:{topic_id:string;name:string;explanation:string;concept_group?:string|null;related_concepts?:{target:string;relation:string}[];breakthrough_steps?:string[];misconceptions:string[];labels:ReportLabel[];citations:SourceCitation[]}[];examples:ReportExercise[];self_checks:ReportExercise[];review_suggestions?:string[]};
export type ReportExercise = {generation_origin?:"rule_generated";question:string;answer:string;citations:SourceCitation[]};
export type ReportCoverage = {warnings?:string[];truncated:boolean;notice:string;versions:{version_id:string;document_name:string;total_chunks:number;selected_chunks:number;total_chars:number;sent_chars:number;truncated:boolean}[]};
export type ReportScope = {goal:string;scope_version_ids:string[];study_mode:"preview"|"systematic"|"revision";coverage:ReportCoverage};
export type CandidateOptions = {chapter_id:string;topic_ids:string[];type:"single_choice"|"boolean"|"short_answer";count:number;points:string;difficulty_label:"basic"|"application"|"advanced";mode:"historical"|"variant"|"weakness";original_past_question_ids:string[]};
export type CandidateContext = {topics:{id:string;name:string}[];references:{id:string;paper_id:string;title:string;year:number|null;stem:string;topic_id:string|null}[]};
export type CandidateScope = {request:CandidateOptions & {goal:string;version_ids:string[];chunk_ids:string[]};coverage:ReportCoverage;exam_context:CandidateContext};
export type QuestionDraft = {question_id:string;chapter_id:string;type:CandidateOptions["type"];stem:string;options:{id:string;text:string}[];answer:string|boolean|null;rubric:{criterion:string;points:number}[];points:number;explanation:string;topic_ids:string[];difficulty_label:string;mode:string;original_past_question_ids:string[];material_citations:SourceCitation[];generation_status:"draft"};
export type AIAnswer = {id: string; course_id: string; query: string; status: string; model_mode: string; result: {m2_supplement?:AISupplement;supplement_notice?:string;execution?:AIExecution;answer?: string; message?: string; citations?: SourceCitation[]; model_notice?: string; model?: string; error_code?: string; review_status?: string;study_report?:StudyReport;study_report_sections?:{title:string;report:StudyReport}[];partial?:boolean;validation_notices?:string[];coverage?:ReportCoverage;prompt_version?:string;question_drafts?:QuestionDraft[];exam_context?:CandidateContext;mode_notice?:string;integration_notice?:string;dependency_status?:string;provider_code?:string|null;retry_after_seconds?:number|null}};
export type AIProvider = {provider: string; configured: boolean; model: string; endpoint: string; checked_at: string; documentation_url: string; policy_status: string; policy_entry_url: string; max_context_chars: number; max_output_tokens: number};
export type AISource = {m2_supplement?:AISupplement;source_id: string; version_id: string; document_id: string; document_name: string; version_no: number; locator: {type: string; value: string}; text: string; source_kind: string; sha256: string};
export type AIExecution = {budget_seconds:number;max_structure_repairs:number;repairs_used:number;total_calls:number;window_number:number;window_calls:number;window_call_limit:number;window_started_at:string|null;deadline_at:string|null;remaining_seconds:number;phase:string};
export type RelatedAnswer = {id:string;query:string;answer_preview:string;model:string;created_at:string};
export type RemoteQuery = {related_results?:RelatedAnswer[];execution?:AIExecution|null;reusable_result?:AIAnswer|null;id: string; course_id: string; query: string; request_kind?:"qa"|"study_report"|"question_drafts";batch_progress?:{kind?:"qa";phase?:string;batch_count?:number;checked_batches?:number;total:number;completed:number;max_calls:number;chars:number}|null;qa_scope?:{mode:string;coverage:ReportCoverage;batch_count:number;batched:boolean}|null;report_scope?:(ReportScope & {chunk_ids?:string[];batched?:boolean})|null;candidate_scope?:CandidateScope|null; model: string; endpoint: string; expires_at: string; consented_at: string | null; dispatched_at: string | null; sources: AISource[]; job: Job | null; result: AIAnswer | null};
export type MaterialReference = { citation_id: string; note_id: string; note_title: string; chunk_id: string; quote: string; locator_type: string; locator_value: string };
export type ReferenceNote={note_id:string;note_title:string;note_course_id:string|null;updated_at:string;citation_count:number;citation_id:string;chunk_id:string;locator_type:string;locator_value:string;quote_excerpt:string};
export type ReferenceNotePage={course_id:string;document_id:string;version_id:string;chunk_id:string|null;items:ReferenceNote[];total:number;offset:number;limit:number;checked_at:string};
export type SearchHit = { source_kind?: string; transcript_id?: string | null; chunk_id: string; version_id: string; version_no: number; document_id: string; document_name: string; category: string; tags: string[]; locator_type: string; locator_value: string; text: string; score: number };
export type TextExcerpt = {text:string; start_offset:number; truncated_after:boolean; highlights:{start:number;end:number}[]};
export type PageResult<T> = {items:T[];total:number;offset:number;limit:number};
export type LearningTopic = {id:string;name:string;aliases:string[];parent_id:string|null;revision:number;confirmed:number;pending:number;needs_review:number};
export type TopicSource = {version_id:string;chunk_id:string;availability:"active"|"unavailable";document_id?:string;title?:string;version_no?:number;locator?:string;quote?:string};
export type TopicLearning = {course_id:string;topic:Omit<LearningTopic,"confirmed"|"pending"|"needs_review">;counts:Pick<LearningTopic,"confirmed"|"pending"|"needs_review">;sources:TopicSource[];candidates:Required<Omit<TopicSource,"availability">>[];notes:{id:string;title:string;updated_at:string;relation:"shared_source"|"same_tag_candidate"}[];mistakes:{id:string;updated_at:string}[];reviews:{id:string;title:string;due_date:string;mistake_id:string}[];review_total:number;today:string;timezone:string;checked_at:string};
export type SearchPage = PageResult<Omit<SearchHit,"text"> & {excerpt:TextExcerpt}>;
export type NoteSearchPage = PageResult<{id:string;title:string;excerpt:TextExcerpt;updated_at:string}>;
export type MaterialFilters = { category?: string; tag?: string; latestOnly?: boolean };
export type DocumentBrowse = {q: string; category: string; tag: string; state: string; sort: string; offset: number; limit: number};
export type DocumentPage = {items: DocumentItem[]; total: number; offset: number; limit: number; stats: Record<string, number>; categories: string[]; tags: string[]};
export type JobPage = {items: Job[]; total: number; offset: number; limit: number; pending_count: number};
export type AccountArchive = {id: string; purpose: "export" | "restore"; created_at: string; sha256: string | null; size_bytes: number; counts: Record<string, number>; job: {id:string;status:string;progress:number;error:string | null}};
export type SourceCitation = { document_name?: string | null; version_no?: number | null; source_kind?: string; id?: string; document_id?: string | null; version_id: string; chunk_id: string; locator?: { type: string; value: string }; locator_type?: string; locator_value?: string; quote: string; availability: string };
export type Chunk = { source_kind?: string; transcript_id?: string | null; transcript_status?: string | null; confirmed_at?: string | null; id: string; version_id: string; locator_type: string; locator_value: string; text: string };
export type Note = { id: string; title: string; content: string; tags: string[]; course_id?: string | null; folder_id?: string | null; revision: number; updated_at: string };
export type NoteSummary = Omit<Note,"content">;
export type NoteGraphNode = NoteSummary & {incoming_count:number;outgoing_count:number};
export type NoteGraphQuery = {q?:string;link_state?:"all"|"linked"|"isolated";focus_note_id?:string;limit?:number};
export type NoteGraphResponse = {course_id:string;focus_note_id:string|null;nodes:NoteGraphNode[];edges:{source_id:string;target_id:string}[];total_nodes:number;total_edges:number;node_limit:number;edge_limit:number;nodes_truncated:boolean;edges_truncated:boolean};
export type NoteCatalog = PageResult<NoteSummary>;
export const noteSummary=(note:NoteSummary):NoteSummary=>({id:note.id,title:note.title,tags:note.tags,course_id:note.course_id,folder_id:note.folder_id,revision:note.revision,updated_at:note.updated_at});
export type NoteFolder = {id: string; name: string; parent_id: string | null; course_id: string; revision: number};
export type NoteTrashEntry = Pick<Note, 'id' | 'title' | 'tags' | 'course_id' | 'folder_id' | 'revision'> & {course_name: string; deleted_at: string; purge_after: string | null; restore_requires_course: boolean};
export type NoteTrashPage = {items: NoteTrashEntry[]; total: number; snapshot: string};
export type NoteTrashPolicy = {retention_days: number | null; revision: number};
export type NoteBatchChange = {add_tags?: string[]; remove_tags?: string[]; folder_id?: string | null};
export type NoteExport = Omit<MaterialExport, "course_id"> & {filename: string; layout: "simple" | "legacy"};
export type Topic = { parent_id?:string|null; id: string; name: string; aliases: string[];revision:number;merged_into_id?:string|null };
export type ExamAnalysis = {id:string;course_id:string;status:string;report:{sample_count:number;all_papers:number;pending_papers:number;question_count:number;known_years:number[];unknown_years:number;unknown_points:number;known_points:number;known_points_coverage:number|null;by_type:Record<string,number>;topics:Array<{id:string;name:string;count:number;involvement_rate:number|null;year_rate:number|null;primary_known_points:number;points_rate:number|null}>}};
export type GapMatrix = {status:string;topics:Array<{id:string;name:string;revision:number;confirmed_sources:SourceCitation[];material_candidates:Array<{version_id:string;chunk_id:string;document_id:string;name:string;quote:string}>;notes:Array<{id:string;title:string}>;images:Array<{id:string;name:string;alt:string}>;match_status:string;mastery:string;judged_count:number;error_count:number;current_pending:number;current_mastered:number}>};
export type Paper = { id: string; title: string; year?: number | null; review_status: string; questions: PastQuestion[] };
export type BankArchiveEntry={path:string;kind:"document"|"image"|"skip";status:"uploaded"|"failed"|"skipped";version_id?:string;asset_id?:string;error?:string};
export type BankAIJob={paper_id:string;title:string;model:string;endpoint:string;status:string;job_id?:string;error?:string;sources?:{source_id:string;text:string}[];expires_at:string};
export type BankImage = {asset_id:string;box?:number[];alt?:string};
export type BankPDFInfo={version_id:string;pages:number;ocr_pages:number[];ocr_available:boolean};
export type BankImageJob = {engine?:string;completed_pages?:number;auto_topic_status?:string;pdf_version_id?:string;force_ocr?:boolean;id:string;paper_id:string;title:string;status:string;error?:string;progress:number;asset_ids:string[];layout:"single"|"double"};
export type BankTopicJob={auto_apply?:boolean;batch_count?:number;preview_id?:string;paper_id:string;status:string;model:string;endpoint?:string;expires_at?:string;error?:string;input?:{questions:{question_id:string;revision:number;stem:string;options:string[]}[];topics:{id:string;name:string;aliases:string[];revision:number}[]}};
export type BankTopicIndex = {selection_reviewed?:boolean;reason?:string;version?:string;auto_assigned?:boolean;existing?:{topic_id:string;name:string;method:string;reason:string}[];candidates?:string[]};
export type BankData = {year?:number|null;content_format?:"markdown";topic_index?:BankTopicIndex;content_profile?:string;import_warnings?:string[];source_images?:BankImage[];illustrations?:BankImage[];images_reviewed?:boolean;options?:string[];blank_answers?:string[];unique_answer?:boolean|null;topic_ids?:string[];explanation?:string;warnings?:string[];citations?:SourceCitation[]};
export type BankDeleteResult={changed:number;revisions:Record<string,number>;paper_id?:string;paper_revision?:number};
export type BankFile=DocumentItem&{library_scope:"material"|"question_bank"};
export type BankPaperMeta = {recognition?:{status:string;error?:string;completed_pages:number;total_pages:number;engine:string}|null;question_count:number;question_snapshot:string;id:string;title:string;year:number|null;status:string;metadata:{revision?:number;exam_identity?:{kind:"exercise"|"past_exam";confirmed:boolean;revision?:number;confirmed_at?:string|null};variant?:string;provenance?:string;duplicate_of?:string|null}};
export type PastQuestion = {display_group?:DisplayGroup|null; id: string; number: string; stem: string; question_type: string; points?: number | null; answer?: string | null; answer_source: string; status: string; topic_id?: string | null;revision:number;bank_data:BankData;paper_id?:string };
export type QuestionDirectoryItem = Pick<PastQuestion,"id"|"paper_id"|"number"|"stem"|"question_type"|"status"|"revision"|"topic_id"> & {fingerprint:string;bank_data:{topic_ids:string[]}};
export type Blueprint = { id: string; name: string; config: Record<string, unknown>; status: string };
export type ExamPaper = { id: string; title: string; mode: string; status: string; questions: Question[] };
export type Question = {points_known?:boolean;source_question_id?:string;practice_unit?:"major";whole_stem?:string;whole_illustrations?:BankImage[];source_number?:string;context_stem?:string;context_illustrations?:BankImage[];display_group?:DisplayGroup|null;illustrations?:BankImage[]; id: string; type: string; stem: string; options?: string[]; points: number; topic: string; answer?: string | boolean; rubric?: string[]; explanation?: string;blank_count?:number;blank_answers?:string[];unique_answer?:boolean|null;topic_ids?:string[] };
export type PracticePaper = {id:string;title:string;year:number|null;question_count:number;major_question_count:number;eligible_count:number;available:boolean;reason:string};
export type ApiConnection={configured:boolean;model:string;revision:number;scope:string;endpoint:string;test_status:string;tested_at?:string;message:string;guide_url:string;key_url:string};
export type Redo={id:string;question:Question;status:string;answer:unknown;grading:Grade|null;correct:boolean|null};
export type DailyRedo={date:string;goal:number;target:number;completed:number;available:number;done:boolean;remaining_ids:string[];completed_ids:string[]};
export type MistakeItem={id:string;question:Question;given:unknown;topics:Topic[];mastered:boolean;mastered_at:string|null};
export type Grade = {status:string;automatic:boolean;submitted:boolean;score?:number;max_score?:number;self_correct?:boolean};
export type Attempt = { id: string; paper_id: string; status: string; answers: Record<string, unknown>; score?: number | null;grading:Record<string,Grade>;deadline_at?:string;questions?:Question[] };

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
    throw new ApiError("暂时无法连接学习服务，请检查连接与本机服务状态后重试。", 0);
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

export type NoteCapture = {id: string; filename: string; course_id: string; status: string; kind: string; error: string | null; result: {text?: string; parts?: {location: string; text: string; method: string}[]; warnings?: string[]}; ai_result: {markdown?: string; warnings?: string[]}};
export type ReviewPlan = {id:string;mistake_id:string|null;title:string;due_date:string;status:string};
export type ReviewPlanPage = {items:ReviewPlan[];total:number;offset:number;limit:number;today:string;timezone:string};
export type AgendaView="due"|"overdue"|"today"|"upcoming"|"completed"|"pending";
export type CourseAgendaPage=ReviewPlanPage&{course_id:string;counts:Record<AgendaView,number>};
export type WorkspaceDomain = "materials" | "notes" | "study" | "practice";
export type WorkspaceItem = {id:string;title:string;kind:"material"|"note"|"qa"|"report"|"attempt"|"mistake";status:string;updated_at:string;document_id?:string|null;version_id?:string|null};
export type WorkspaceSection = {course_id:string;domain:WorkspaceDomain;counts:Record<string,number>;recent:WorkspaceItem[];checked_at:string};
export type LearningRecordKind = "all"|WorkspaceItem["kind"];
export type LearningRecordPage = {course_id:string;items:WorkspaceItem[];total:number;counts:Record<WorkspaceItem["kind"],number>;offset:number;limit:number;checked_at:string};
export type LearningLinkItem = {id:string;title:string;kind:"note"|"qa"|"report"|"topic"|"mistake";status:string;updated_at:string;source_relation?:"citation"|"version"|null;review?:{mastered:boolean|null;pending_count:number;due_count:number;next_due_date:string|null}|null};
export type LearningLinkKind = "all"|LearningLinkItem["kind"];
export type MaterialHealthIssue="all"|"attention"|"text"|"parse"|"index"|"preview"|"processing";
export type MaterialHealthJob=Pick<Job,"id"|"type"|"status"|"attempt_count"|"max_attempts"|"error">;
export type MaterialHealthItem={document_id:string;name:string;updated_at:string;version_id:string;version_no:number;parse_status:string;index_status:string;preview_status:string;has_text:boolean;issues:MaterialHealthIssue[];jobs:MaterialHealthJob[]};
export type MaterialHealthPage={course_id:string;items:MaterialHealthItem[];counts:Record<string,number>;total:number;offset:number;limit:number;checked_at:string};
export type LearningLinkPage = {course_id:string;document_id:string;version_id:string;chunk_id:string|null;items:LearningLinkItem[];counts:Record<LearningLinkItem["kind"],number>;total:number;offset:number;limit:number;checked_at:string;today:string;timezone:string};
export type MistakeSources = {course_id:string;items:{version_id:string;chunk_id:string;document_id?:string|null;title:string;locator:string;availability:"active"|"unavailable"}[]};
export type PackageKind = "course" | "folder";
export type PackageCategory = "notes" | "folders" | "documents" | "assets" | "topics" | "past_papers" | "exam_papers" | "ai_results" | "reports" | "blueprints";
export type PackageSelection = Partial<Record<PackageCategory, string[]>>;
export type PackageItem = {id:string;category:PackageCategory;title:string;detail?:string|null;parent_id?:string|null;folder_id?:string|null};
export type PackageCatalog = {format:"hustudy-package-v1";kind:PackageKind;title:string;items:PackageItem[];counts:Record<string,number>;warnings:string[]};
export type PackagePreview = PackageCatalog & {preview_id:string;sha256:string;expires_at?:string};
export type StoredPackagePreview = {id:string;created_at:string;expires_at:string;size_bytes:number;sha256:string};
export type PackageScope = {course_id:string;kind:PackageKind;folder_id?:string};
export type PackageSelectionRequest = ({preview_id:string;target_course_id?:string;parent_folder_id?:string;title?:string} | PackageScope) & {selection:PackageSelection};
export type PackageSelectionPreview = PackageCatalog & {selection:PackageSelection;selection_sha256:string};
export type PackageImportRequest = {preview_id:string;request_id:string;selection:PackageSelection;expected_sha256?:string;target_course_id?:string;parent_folder_id?:string;title?:string};
export type PackageImportResult = {course_id:string;note_count:number;folder_count:number;counts:Record<string,number>;warnings:string[];import_id:string};

async function downloadPackage(token:string,payload:PackageScope & {selection:PackageSelection;expected_sha256?:string},signal?:AbortSignal):Promise<{blob:Blob;filename:string}> {
  let response:Response;
  try {response=await fetch(`${API_BASE}/packages/export`,{method:"POST",headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},body:JSON.stringify(payload),signal,cache:"no-store"});}
  catch {throw new ApiError("标准包下载未完成，请恢复连接后重试。",0);}
  if(!response.ok){notifyUnauthorized(response.status,token);const body=await response.json().catch(()=>({}));throw new ApiError(body.error?.message||body.detail||"标准包导出失败",response.status,body.error?.request_id,body.error?.code,body.error?.details);}
  const disposition=response.headers.get("Content-Disposition")||"";
  const encoded=/filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1],plain=/filename="([^"]+)"/i.exec(disposition)?.[1];
  let filename=plain||"Hustudy标准数据包.zip";
  if(encoded)try{filename=decodeURIComponent(encoded);}catch{/* Keep safe fallback when the response header is malformed. */}
  return {blob:await response.blob(),filename};
}
export const api = {
  modelConnections:(token:string)=>transport<ModelConnections>('/model-connections',{cache:'no-store'},token),
  saveModelConnection:(token:string,payload:ModelProfileInput)=>request<ModelConnections>('/model-connections',{method:'PUT',body:JSON.stringify(payload)},token),
  selectModelConnection:(token:string,revision:number,id:string|null)=>request<ModelConnections>('/model-connections/active',{method:'POST',body:JSON.stringify({revision,profile_id:id})},token),
  removeModelConnection:(token:string,revision:number,id:string)=>request<ModelConnections>(`/model-connections/${id}?revision=${revision}`,{method:'DELETE'},token),
  testModelConnection:(token:string,revision:number,id:string|null)=>request<{connected:boolean;model:string;message:string}>('/model-connections/test',{method:'POST',body:JSON.stringify({revision,profile_id:id,confirm:true})},token),
  previewNoteAssistant:(token:string,input:NoteAssistantInput,signal?:AbortSignal)=>transport<NoteAssistantPreview>('/note-assistant/preview',{method:'POST',body:JSON.stringify(input),signal},token),
  generateNoteAssistant:(token:string,input:NoteAssistantInput,preview_token:string,signal?:AbortSignal)=>transport<NoteAssistantResult>('/note-assistant/generate',{method:'POST',body:JSON.stringify({input,preview_token,confirm:true}),signal},token),
  packageCatalog:(token:string,scope:PackageScope,signal?:AbortSignal)=>transport<PackageCatalog>(`/courses/${scope.course_id}/packages/catalog?${new URLSearchParams({kind:scope.kind,...(scope.folder_id?{folder_id:scope.folder_id}:{})})}`,{signal,cache:"no-store"},token),
  previewPackage:(token:string,file:File,signal?:AbortSignal)=>{const body=new FormData();body.append("file",file);return transport<PackagePreview>("/packages/preview",{method:"POST",body,signal},token);},
  removePackagePreview:(token:string,id:string,signal?:AbortSignal)=>transport<void>(`/packages/previews/${id}`,{method:"DELETE",signal},token),
  packagePreviews:(token:string,signal?:AbortSignal)=>transport<StoredPackagePreview[]>("/packages/previews",{signal,cache:"no-store"},token),
  previewPackageSelection:(token:string,payload:PackageSelectionRequest,signal?:AbortSignal)=>transport<PackageSelectionPreview>("/packages/selection-preview",{method:"POST",body:JSON.stringify(payload),signal},token),
  exportPackage:downloadPackage,
  importPackage:(token:string,payload:PackageImportRequest,signal?:AbortSignal)=>request<PackageImportResult>("/packages/import",{method:"POST",body:JSON.stringify(payload),signal},token),
  packageImportResult:(token:string,id:string,signal?:AbortSignal)=>transport<PackageImportResult>(`/packages/imports/${id}`,{signal,cache:"no-store"},token),
  processingStatus:(token:string,signal?:AbortSignal)=>transport<ProcessingServiceStatus>("/processing/status",{signal},token),
  learningTopics:(token:string,courseId:string,q="",state="all",offset=0)=>request<PageResult<LearningTopic>>(`/courses/${courseId}/learning-topics?${new URLSearchParams({q,state,offset:String(offset),limit:"12"})}`,{},token),
  topicLearning:(token:string,courseId:string,id:string)=>request<TopicLearning>(`/courses/${courseId}/learning-topics/${id}`,{},token),
  questionDirectory:(token:string,courseId:string,offset=0)=>request<PageResult<QuestionDirectoryItem>>(`/courses/${courseId}/question-directory?offset=${offset}&limit=200`,{},token),
  bankQuestion:(token:string,id:string)=>request<PastQuestion>(`/past-questions/${id}`,{},token),

  me: (token:string)=>request<{id:string;username:string;timezone:string}>("/auth/me",{},token),
  noteCatalog: (token:string,offset=0)=>request<NoteCatalog>(`/notes/catalog?offset=${offset}&limit=200`,{},token),
  noteMatches:(token:string,courseId:string,q:string,tag:string)=>request<{ids:string[]}>(`/courses/${courseId}/note-matches?${new URLSearchParams({q,tag})}`,{},token),
  backlinkOptions:(token:string,id:string)=>request<NoteSummary[]>(`/notes/${id}/backlink-options`,{},token),
  noteGraph:(token:string,courseId:string,query:NoteGraphQuery={},signal?:AbortSignal)=>transport<NoteGraphResponse>(`/courses/${courseId}/note-graph?${new URLSearchParams({q:query.q??"",link_state:query.link_state??"all",limit:String(query.limit??120),...(query.focus_note_id?{focus_note_id:query.focus_note_id}:{})})}`,{signal,cache:"no-store"},token),

  reviewSchedule: (token:string,state:"pending"|"all"="pending",offset=0,limit=20) => request<ReviewPlanPage>(`/review-tasks?state=${state}&offset=${offset}&limit=${limit}`,{},token),
  courseAgenda:(token:string,courseId:string,view:AgendaView,q:string,offset:number,signal?:AbortSignal)=>transport<CourseAgendaPage>(`/review-tasks?${new URLSearchParams({course_id:courseId,state:view==="completed"?"completed":"pending",period:view==="completed"||view==="pending"?"all":view,q,offset:String(offset),limit:"6"})}`,{signal,cache:"no-store"},token),
  workspace: (token:string,courseId:string,domain:WorkspaceDomain) => request<WorkspaceSection>(`/courses/${courseId}/workspace/${domain}`,{},token),
  // Explicit dialog reads must fail offline and honor close cancellation, without reconnect replay.
  learningRecords: (token:string,courseId:string,kind:LearningRecordKind,q:string,offset:number,signal?:AbortSignal) => transport<LearningRecordPage>(`/courses/${courseId}/learning-records?${new URLSearchParams({kind,q,offset:String(offset),limit:"12"})}`,{signal},token),
  sourceLearningLinks:(token:string,versionId:string,chunkId:string|null,kind:LearningLinkKind,q:string,offset:number,signal?:AbortSignal)=>transport<LearningLinkPage>(`/versions/${versionId}/learning-links?${new URLSearchParams({kind,q,offset:String(offset),limit:"12",...(chunkId?{chunk_id:chunkId}:{})})}`,{signal},token),
  materialHealth:(token:string,courseId:string,issue:MaterialHealthIssue,q:string,offset:number,signal?:AbortSignal)=>transport<MaterialHealthPage>(`/courses/${courseId}/material-health?${new URLSearchParams({issue,q,offset:String(offset),limit:"12"})}`,{signal},token),
  mistakeSources: (token:string,id:string) => request<MistakeSources>(`/mistakes/${id}/sources`,{},token),
  aiResult: (token:string,id:string) => request<AIAnswer>(`/ai-results/${id}`,{},token),

  noteAIConfig: (token: string) => request<NoteAIConfig>('/note-ai/config', {}, token),
  saveNoteAIConfig: (token: string, payload: {revision: number; model: string; api_key?: string}) => request<NoteAIConfig>('/note-ai/config', {method: 'PUT', body: JSON.stringify(payload)}, token),
  clearNoteAIConfig: (token: string, revision: number) => request<NoteAIConfig>(`/note-ai/config?revision=${revision}`, {method: 'DELETE'}, token),
  captureCapabilities: (token: string) => request<{ocr: boolean; speech: boolean; ai: boolean; model: string; ai_unavailable_reason?: string | null}>("/note-captures/capabilities", {}, token),
  captures: (token: string, courseId: string) => request<NoteCapture[]>(`/note-captures?course_id=${encodeURIComponent(courseId)}`, {}, token),
  uploadCapture: (token: string, file: File, courseId: string, id: string) => {const body = new FormData(); body.append('file', file); body.append('course_id', courseId); body.append('request_id', id); return request<NoteCapture>('/note-captures', {method: 'POST', body}, token);},
  organizeCapture: (token: string, id: string, payload: {request_id: string; text: string; mode: 'format' | 'summary' | 'outline'; model: string; confirmed: true}) => request<NoteCapture>(`/note-captures/${id}/organize`, {method: 'POST', body: JSON.stringify(payload)}, token),
  removeCapture: (token: string, id: string) => request<void>(`/note-captures/${id}`, {method: 'DELETE'}, token),
  captureFile: (token: string, id: string) => fileRequest(`/note-captures/${id}/file`, token),
  materialCapabilities: (token:string) => request<PreviewCapabilities>("/material-capabilities",{},token),
  requestPreview: (token:string,id:string) => request<Job>(`/versions/${id}/preview-jobs`,{method:"POST"},token),
  accountArchives: (token: string) => request<AccountArchive[]>("/backups", {}, token),
  createAccountArchive: (token: string) => request<AccountArchive>("/backups", {method:"POST"}, token),
  restoreAccountArchive: (token: string, file: File) => { const body = new FormData(); body.append("file",file); body.append("confirm","RESTORE_EMPTY_ACCOUNT"); return request<AccountArchive>("/backups/restore",{method:"POST",body},token); },
  downloadAccountArchive: (token: string, id: string) => fileRequest(`/backups/${id}/download`,token),
  removeAccountArchive: (token: string, id: string) => request<void>(`/backups/${id}`,{method:"DELETE"},token),
  document: (token: string, id: string) => request<DocumentItem>(`/documents/${id}`, {}, token),
  documentPage: (token: string, id: string, filters: DocumentBrowse) => request<DocumentPage>(`/courses/${id}/documents/page?${new URLSearchParams(Object.entries(filters).map(([k,v]) => [k,String(v)]))}`, {}, token),
  jobPage: (token: string, id: string, status: string, offset: number,kind="all") => request<JobPage>(`/courses/${id}/jobs/page?${new URLSearchParams({status,kind,offset:String(offset),limit:"10"})}`, {}, token),
  aiProvider: (token: string) => request<AIProvider>("/ai/provider", {}, token),
  previewStudyReport: (token:string,courseId:string,goal:string,versionIds:string[],studyMode:string,chunkIds:string[]=[],maxStructureRepairs=0,supplement:AISupplementSelection={note_ids:[],notes_confirmed:false}) => request<RemoteQuery>(`/courses/${courseId}/study-reports/preview`,{method:"POST",body:JSON.stringify({goal,version_ids:versionIds,study_mode:studyMode,chunk_ids:chunkIds,max_structure_repairs:maxStructureRepairs,...supplement})},token),
  studyReports: (token:string,courseId:string) => request<AIAnswer[]>(`/courses/${courseId}/study-reports`,{},token),
  demoStudyReport: (token:string,courseId:string,goal:string,versionIds:string[],studyMode:string,chunkIds:string[]=[]) => request<AIAnswer>(`/courses/${courseId}/study-reports/demo`,{method:"POST",body:JSON.stringify({goal,version_ids:versionIds,study_mode:studyMode,chunk_ids:chunkIds})},token),
  aiResults: (token:string,courseId:string) => request<AIAnswer[]>(`/courses/${courseId}/ai-results`,{},token),
  candidateContext: (token:string,courseId:string) => request<CandidateContext>(`/courses/${courseId}/question-draft-context`,{},token),
  questionDrafts: (token:string,courseId:string) => request<AIAnswer[]>(`/courses/${courseId}/question-drafts`,{},token),
  previewQuestionDrafts: (token:string,courseId:string,goal:string,versionIds:string[],chunkIds:string[],config:CandidateOptions) => request<RemoteQuery>(`/courses/${courseId}/question-drafts/preview`,{method:"POST",body:JSON.stringify({...config,goal,version_ids:versionIds,chunk_ids:chunkIds})},token),
  demoQuestionDrafts: (token:string,courseId:string,goal:string,versionIds:string[],chunkIds:string[],config:CandidateOptions) => request<AIAnswer>(`/courses/${courseId}/question-drafts/demo`,{method:"POST",body:JSON.stringify({...config,goal,version_ids:versionIds,chunk_ids:chunkIds})},token),
  previewRemoteQuery: (token: string, courseId: string, query: string, versionIds: string[],chunkIds:string[]=[],maxStructureRepairs=0,supplement:AISupplementSelection={note_ids:[],notes_confirmed:false}) => request<RemoteQuery>(`/courses/${courseId}/remote-queries/preview`, {method: "POST", body: JSON.stringify({query, version_ids: versionIds,chunk_ids:chunkIds,max_structure_repairs:maxStructureRepairs,...supplement})}, token),
  remoteQuery: (token: string, id: string) => request<RemoteQuery>(`/remote-queries/${id}`, {}, token),
  confirmRemoteQuery: (token: string, id: string) => request<RemoteQuery>(`/remote-queries/${id}/confirm`, {method: "POST", body: JSON.stringify({confirm_remote_send: true})}, token),
  reuseRemoteQuery: (token:string,id:string,resultId:string) => request<AIAnswer>(`/remote-queries/${id}/reuse`,{method:"POST",body:JSON.stringify({result_id:resultId})},token),
  relatedRemoteAnswer: (token:string,id:string,resultId:string,signal?:AbortSignal) => request<AIAnswer>(`/remote-queries/${id}/related-results/${resultId}`,{signal},token),
  reuseRelatedAnswer: (token:string,id:string,resultId:string,signal?:AbortSignal) => request<AIAnswer>(`/remote-queries/${id}/related-results/${resultId}/reuse`,{method:"POST",body:JSON.stringify({confirm_related_reuse:true}),signal},token),
  resumeRemoteQuery: (token:string,id:string) => request<RemoteQuery>(`/remote-queries/${id}/resume`,{method:"POST",body:JSON.stringify({confirm_remote_send:true})},token),
  cancelRemoteQuery: (token: string, id: string) => request<RemoteQuery>(`/remote-queries/${id}/cancel`, {method: "POST"}, token),
  transcripts: (token:string,versionId:string) => request<ManualTranscript[]>(`/versions/${versionId}/transcripts`,{},token),
  createTranscript: (token:string,versionId:string,payload:{page:number;text:string;supersedes_id?:string}) => request<ManualTranscript>(`/versions/${versionId}/transcripts`,{method:"POST",body:JSON.stringify(payload)},token),
  updateTranscript: (token:string,id:string,payload:{revision:number;text:string}) => request<ManualTranscript>(`/transcripts/${id}`,{method:"PATCH",body:JSON.stringify(payload)},token),
  confirmTranscript: (token:string,id:string,revision:number) => request<ManualTranscript>(`/transcripts/${id}/confirm`,{method:"POST",body:JSON.stringify({revision})},token),
  withdrawTranscript: (token:string,id:string,revision:number) => request<ManualTranscript>(`/transcripts/${id}/withdraw`,{method:"POST",body:JSON.stringify({revision})},token),
  organizeDocuments: (token:string,courseId:string,items:DocumentMetadata[],change:DocumentOrganizeChange) => request<{items:DocumentMetadata[];changed:number}>(`/courses/${courseId}/documents/organize`,{method:"POST",body:JSON.stringify({...change,items:items.map(item=>({id:item.id,expected_updated_at:item.updated_at}))})},token),
  noteOptions: (token:string,courseId:string,q="",offset=0,limit=20) => request<NoteOptionPage>(`/courses/${courseId}/note-options?${new URLSearchParams({q,offset:String(offset),limit:String(limit)})}`,{},token),
  updateDocument: (token: string, id: string, payload: {name?: string; category?: string; tags?: string[];expected_updated_at?:string}) => request<DocumentItem>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  materialReferences: (token: string, id: string, chunkId?: string) => request<MaterialReference[]>(`/versions/${id}/references${chunkId ? '?chunk_id=' + encodeURIComponent(chunkId) : ''}`, {}, token),
  referenceNotes:(token:string,versionId:string,q:string,chunkId:string,offset:number,signal?:AbortSignal)=>transport<ReferenceNotePage>(`/versions/${versionId}/reference-notes?${new URLSearchParams({q,offset:String(offset),limit:"6",...(chunkId?{chunk_id:chunkId}:{})})}`,{signal,cache:"no-store"},token),
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
  createMaterialExport: (token: string, id: string, requestId: string,documentIds?:string[]) => request<MaterialExport>(`/courses/${id}/material-exports`, {method: "POST", body: JSON.stringify({request_id: requestId,...(documentIds?{document_ids:documentIds}:{})})}, token),
  retryMaterialExport: (token: string, id: string) => request<MaterialExport>(`/material-exports/${id}/retry`, {method: "POST"}, token),
  removeMaterialExport: (token: string, id: string) => request<void>(`/material-exports/${id}`, {method: "DELETE"}, token),
  downloadMaterialExport: (token: string, id: string) => fileRequest(`/material-exports/${id}/download`, token),
  reindexVersion: (token: string, id: string, requestId: string) => request<Job>(`/versions/${id}/reindex`, {method: "POST", body: JSON.stringify({request_id: requestId})}, token),
  deleteDocument: (token: string, id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }, token),
  uploadVersion: (token: string, id: string, file: File) => { const data = new FormData(); data.append("file", file); return request<Job>(`/documents/${id}/versions`, { method: "POST", body: data }, token); },
  original: (token: string, id: string, signal?:AbortSignal) => fileRequest(`/versions/${id}/original`, token,signal),
  preview: (token: string, id: string) => fileRequest(`/versions/${id}/preview`, token),
  citations: (token: string, id: string) => request<SourceCitation[]>(`/notes/${id}/citations`, {}, token),
  removeCitation: (token: string, noteId: string, citationId: string) => request<void>(`/notes/${noteId}/citations/${citationId}`, {method: "DELETE"}, token),
  completeReviewTask: (token: string, id: string) => request(`/review-tasks/${id}/complete`, {method: "POST"}, token),
  note: (token: string, id: string, signal?:AbortSignal) => signal?transport<Note>(`/notes/${id}`,{signal},token):request<Note>(`/notes/${id}`, {}, token),
  noteFolders: (token: string, courseId: string) => request<NoteFolder[]>(`/note-folders?course_id=${encodeURIComponent(courseId)}`, {}, token),
  createNoteFolder: (token: string, payload: {course_id: string; parent_id: string | null; name: string}) => request<NoteFolder>("/note-folders", {method: "POST", body: JSON.stringify(payload)}, token),
  updateNoteFolder: (token: string, id: string, payload: {revision: number; parent_id?: string | null; name?: string}) => request<NoteFolder>(`/note-folders/${id}`, {method: "PATCH", body: JSON.stringify(payload)}, token),
  deleteNoteFolder: (token: string, id: string, revision: number) => request<void>(`/note-folders/${id}?revision=${revision}`, {method: "DELETE"}, token),
  batchNotes: (token: string, notes: {id: string; revision: number}[], change: NoteBatchChange) => request<Note[]>("/notes/batch", {method: "POST", body: JSON.stringify({notes, ...change})}, token),
  importMarkdown: (token: string, file: File, options: {request_id: string; course_id: string; folder_id: string | null; tags: string[]}) => {const body = new FormData(); body.append("file", file); body.append("request_id", options.request_id); body.append("course_id", options.course_id); body.append("tags", JSON.stringify(options.tags)); if (options.folder_id) body.append("folder_id", options.folder_id); return request<Note>("/notes/import-markdown", {method: "POST", body}, token);},
  backlinks: (token: string, id: string) => request<Note[]>(`/notes/${id}/backlinks`, {}, token),
  exportNote: (token: string, id: string) => request<string>(`/notes/${id}/export`, {}, token),
  deleteNote: (token: string, id: string, revision: number) => request<void>(`/notes/${id}?revision=${revision}`, {method: "DELETE"}, token),
  noteTrash: (token: string, offset = 0) => request<NoteTrashPage>(`/notes/trash?offset=${offset}&limit=50`, {}, token),
  noteTrashPolicy: (token: string) => request<NoteTrashPolicy>('/notes/trash/policy', {}, token),
  updateNoteTrashPolicy: (token: string, policy: NoteTrashPolicy) => request<NoteTrashPolicy>('/notes/trash/policy', {method: 'PUT', body: JSON.stringify(policy)}, token),
  trashNotes: (token: string, action: 'trash' | 'restore' | 'purge', notes: {id: string; revision: number}[], fallback_course_id?: string) => request<{affected: number}>('/notes/trash/batch', {method: 'POST', body: JSON.stringify({action, notes, fallback_course_id})}, token),
  emptyNoteTrash: (token: string, snapshot: string) => request<{affected: number}>('/notes/trash/empty', {method: 'POST', body: JSON.stringify({snapshot})}, token),
  noteExports: (token: string) => request<NoteExport[]>("/note-exports", {}, token),
  createNoteExport: (token: string, requestId: string, noteIds: string[], includeImages: boolean) => request<NoteExport>("/note-exports", {method: "POST", body: JSON.stringify({request_id: requestId, note_ids: noteIds, include_images: includeImages})}, token),
  retryNoteExport: (token: string, id: string) => request<NoteExport>(`/note-exports/${id}/retry`, {method: "POST"}, token),
  removeNoteExport: (token: string, id: string) => request<void>(`/note-exports/${id}`, {method: "DELETE"}, token),
  downloadNoteExport: (token: string, id: string) => fileRequest(`/note-exports/${id}/download`, token),

  createReviewTask: (token: string, payload: { mistake_id: string; title: string; due_date?: string }) => request<ReviewPlan>("/review-tasks", { method: "POST", body: JSON.stringify(payload) }, token),
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
  createNote: (token: string, payload: { title: string; content: string; tags?: string[]; course_id?: string; folder_id?: string | null; request_id?: string; citations?: {version_id: string; chunk_id: string; quote: string}[] }) => request<Note>("/notes", { method: "POST", body: JSON.stringify(payload) }, token),
  updateNote: (token: string, id: string, payload: { title: string; content: string; tags?: string[]; course_id?: string; folder_id?: string | null; revision: number }) => request<Note>(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  citation: (token: string, noteId: string, payload: { version_id: string; chunk_id: string; quote: string }) => request(`/notes/${noteId}/citations`, { method: "POST", body: JSON.stringify(payload) }, token),
  aiQuery: (token: string, courseId: string, query: string) => request<AIAnswer>(`/courses/${courseId}/ai-queries`, { method: "POST", body: JSON.stringify({ query, mode: "demo" }) }, token),
  topics: (token: string, courseId: string) => request<Topic[]>(`/courses/${courseId}/topics`, {}, token),
  deleteTopic: (token:string,id:string,revision:number) => request<{status:string;id:string}>(`/topics/${id}?revision=${revision}`,{method:"DELETE"},token),
  renameTopic: (token:string,id:string,payload:{revision:number;name:string;aliases:string[];parent_id?:string|null}) => request<Topic>(`/topics/${id}`,{method:"PATCH",body:JSON.stringify(payload)},token),
  mergeTopic: (token:string,id:string,payload:{revision:number;target_id:string;target_revision:number}) => request<Topic>(`/topics/${id}/merge`,{method:"POST",body:JSON.stringify(payload)},token),
  confirmTopicSource: (token:string,id:string,payload:{revision:number;version_id:string;chunk_id:string;quote:string}) => request<Topic>(`/topics/${id}/sources`,{method:"PUT",body:JSON.stringify(payload)},token),
  createAnalysis: (token:string,courseId:string) => request<ExamAnalysis>(`/courses/${courseId}/exam-analyses`,{method:"POST"},token),
  analysis: (token:string,id:string) => request<ExamAnalysis>(`/exam-analyses/${id}`,{},token),
  analysisHistory: (token:string,courseId:string) => request<Array<{id:string;status:string}>>(`/courses/${courseId}/exam-analyses`,{},token),
  analysisGaps: (token:string,id:string) => request<GapMatrix>(`/exam-analyses/${id}/gaps`,{},token),
  bankImport: (token:string,courseId:string,payload:{request_id?:string;title:string;content?:string;version_id?:string;year?:number;default_topic_ids?:string[];strict_markdown?:boolean}) => request<Paper>(`/courses/${courseId}/question-bank/import`,{method:"POST",body:JSON.stringify(payload)},token),
  bankQuestions: (token:string,courseId:string,offset=0,paperId="",topicId="") => request<{items:PastQuestion[];total:number}>(`/courses/${courseId}/question-bank?offset=${offset}&limit=50${paperId?`&paper_id=${encodeURIComponent(paperId)}`:""}${topicId?`&topic_id=${encodeURIComponent(topicId)}`:""}`,{},token),
  bankMarkdown:(token:string,id:string)=>fileRequest(`/past-questions/${id}/markdown`,token),
  bankArchiveInspect:(token:string,courseId:string,file:File)=>{const body=new FormData();body.append("file",file);return request<{entries:{path:string;kind:string;size:number}[]}>(`/courses/${courseId}/question-bank/archives/inspect`,{method:"POST",body},token);},
  bankVisionResume:(token:string,paperId:string)=>request<BankImageJob>(`/past-papers/${paperId}/vision-resume`,{method:"POST",body:JSON.stringify({confirm_remote_send:true})},token),
  bankRecognitionCancel:(token:string,paperId:string)=>request(`/past-papers/${paperId}/recognition-cancel`,{method:"POST"},token),
  bankArchive: (token:string,courseId:string,file:File,selectedPaths?:string[],mode:"local"|"ai"="local") => {const body=new FormData();body.append("file",file);body.append("mode",mode);if(selectedPaths)body.append("selected_paths",JSON.stringify(selectedPaths));return request<{entries:BankArchiveEntry[]}>(`/courses/${courseId}/question-bank/archives`,{method:"POST",body},token);},
  autoClassifyQuestions:(token:string,courseId:string,paperId:string,revisions:Record<string,number>)=>request<BankTopicJob>(`/courses/${courseId}/past-papers/${paperId}/auto-classify`,{method:"POST",body:JSON.stringify({revisions,confirm_remote_send:true})},token),
  autoClassifyQuestion:(token:string,courseId:string,id:string,revision:number)=>request<BankTopicJob>(`/courses/${courseId}/past-questions/${id}/auto-classify`,{method:"POST",body:JSON.stringify({revision,confirm_remote_send:true})},token),
  bankTopicPreview:(token:string,id:string,question_ids:string[])=>request<BankTopicJob>(`/past-papers/${id}/topic-ai-preview`,{method:"POST",body:JSON.stringify({question_ids})},token),
  bankTopicStatus:(token:string,id:string)=>request<BankTopicJob>(`/past-papers/${id}/topic-ai-preview`,{},token),
  bankTopicConfirm:(token:string,id:string,preview_id:string)=>request<BankTopicJob>(`/past-papers/${id}/topic-ai-confirm`,{method:"POST",body:JSON.stringify({confirm_remote_send:true,preview_id})},token),
  bankAICapabilities: (token:string) => request<{configured:boolean;model:string;vendor:string;endpoint:string;documentation_url:string;vision_configured?:boolean}>("/question-bank/ai-capabilities",{},token),
  bankAIPreview: (token:string,courseId:string,payload:{title:string;version_id:string;default_topic_ids:string[];year?:number}) => request<BankAIJob>(`/courses/${courseId}/question-bank/ai-preview`,{method:"POST",body:JSON.stringify(payload)},token),
  bankAIDetail: (token:string,id:string) => request<BankAIJob>(`/past-papers/${id}/ai-preview`,{},token),
  bankAIConfirm: (token:string,id:string) => request<BankAIJob>(`/past-papers/${id}/ai-confirm`,{method:"POST",body:JSON.stringify({confirm_remote_send:true})},token),
  bankAIJobs: (token:string,courseId:string) => request<BankAIJob[]>(`/courses/${courseId}/question-bank/ai-jobs`,{},token),
  bankImageImport: (token:string,courseId:string,payload:{request_id:string;title:string;asset_ids:string[];layout:string;year?:number;default_topic_ids?:string[];engine?:string;confirm_remote_send?:boolean;questions_only?:boolean;classify_topics?:boolean}) => request<BankImageJob>(`/courses/${courseId}/question-bank/images`,{method:"POST",body:JSON.stringify(payload)},token),
  bankPDFInfo:(token:string,courseId:string,versionId:string)=>request<BankPDFInfo>(`/courses/${courseId}/question-bank/pdf/${versionId}`,{},token),
  bankPDFOCR:(token:string,courseId:string,versionId:string,payload:{request_id:string;title:string;year?:number;default_topic_ids:string[];force_ocr:boolean;layout:string;engine?:string;confirm_remote_send?:boolean;questions_only?:boolean;classify_topics?:boolean})=>request<BankImageJob>(`/courses/${courseId}/question-bank/pdf/${versionId}/ocr`,{method:"POST",body:JSON.stringify(payload)},token),
  bankImageJobs: (token:string,courseId:string) => request<BankImageJob[]>(`/courses/${courseId}/question-bank/image-jobs`,{},token),
  bankIllustration: (token:string,courseId:string,image:BankImage,signal?:AbortSignal) => fileRequest(`/question-bank/illustrations/${image.asset_id}?${new URLSearchParams({course_id:courseId,box:(image.box||[0,0,1,1]).join(",")})}`,token,signal),
  deleteBankQuestion: (token:string,id:string,revision:number) => request<BankDeleteResult>(`/past-questions/${id}?revision=${revision}`,{method:"DELETE"},token),
  bankBatchValues:(token:string,courseId:string,payload:{question_ids:string[];revisions:Record<string,number>;year?:number|null;points?:number|null})=>request<BankDeleteResult>(`/courses/${courseId}/question-bank/batch-values`,{method:"POST",body:JSON.stringify(payload)},token),
  bankBatch: (token:string,courseId:string,payload:{question_ids:string[];revisions:Record<string,number>;action:"delete"|"tag"|"tag_add"|"confirm"|"review_topics";topic_ids?:string[]}) => request<BankDeleteResult>(`/courses/${courseId}/question-bank/batch`,{method:"POST",body:JSON.stringify(payload)},token),
  saveBankQuestions: (token:string,courseId:string,items:Record<string,unknown>[]) => request<{changed:number;needs_review:boolean;revisions:Record<string,number>}>(`/courses/${courseId}/question-bank/save`,{method:"POST",body:JSON.stringify({items})},token),
  editBankQuestion: (token:string,id:string,payload:Record<string,unknown>) => request<PastQuestion>(`/past-questions/${id}`,{method:"PATCH",body:JSON.stringify(payload)},token),
  splitBankQuestion: (token:string,id:string,revision:number,parts:string[]) => request<PastQuestion[]>(`/past-questions/${id}/split`,{method:"POST",body:JSON.stringify({revision,parts})},token),
  mergeBankQuestions: (token:string,courseId:string,question_ids:string[],revisions:Record<string,number>,stem:string) => request<PastQuestion>(`/courses/${courseId}/question-bank/merge`,{method:"POST",body:JSON.stringify({question_ids,revisions,stem})},token),
  bankDraw: (token:string,courseId:string,payload:{request_id:string;topic_ids:string[];count:number;question_type?:string;duration_minutes:number;title?:string}) => request<ExamPaper>(`/courses/${courseId}/question-bank/draw`,{method:"POST",body:JSON.stringify(payload)},token),
  examHistory: (token:string,courseId:string) => request<Array<{id:string;title:string;status:string;attempts?:Array<{id:string;status:string}>}>>(`/courses/${courseId}/exam-papers`,{},token),
  practicePapers: (token:string,courseId:string) => request<PracticePaper[]>(`/courses/${courseId}/question-bank/practice-papers`,{},token),
  practiceWholePaper: (token:string,courseId:string,paperId:string,payload:{request_id:string;duration_minutes:number}) => request<ExamPaper>(`/courses/${courseId}/question-bank/papers/${paperId}/practice`,{method:"POST",body:JSON.stringify(payload)},token),
  bankStats: (token:string,courseId:string) => request<{eligible_questions:number;confirmed_papers:number;unknown_points:number;known_points:number;by_type:Record<string,number>;by_topic:Array<{id:string;name:string;count:number}>}>(`/courses/${courseId}/question-bank/statistics`,{},token),
  uploadBankFile:(token:string,courseId:string,file:File,mode:"local"|"ai"="local")=>{const data=new FormData();data.append("file",file);data.append("mode",mode);return request<Job>(`/courses/${courseId}/question-bank/files`,{method:"POST",body:data},token);},
  bankFiles:(token:string,courseId:string)=>request<BankFile[]>(`/courses/${courseId}/question-bank/files`,{},token),
  moveBankFile:(token:string,courseId:string,id:string)=>request<{moved:boolean}>(`/courses/${courseId}/question-bank/files/${id}/move`,{method:"POST"},token),
  deleteBankPaper:(token:string,id:string,revision:number,question_snapshot:string)=>request<BankDeleteResult>(`/past-papers/${id}/delete`,{method:"POST",body:JSON.stringify({revision,question_snapshot})},token),
  restoreBankDeletion:(token:string,courseId:string,payload:Pick<BankDeleteResult,"revisions"|"paper_id"|"paper_revision">)=>request<{restored:number}>(`/courses/${courseId}/question-bank/restore`,{method:"POST",body:JSON.stringify(payload)},token),
  bankPapers: (token:string,courseId:string) => request<BankPaperMeta[]>(`/courses/${courseId}/question-bank/papers`,{},token),
  bankMetadataBatch:(token:string,courseId:string,items:Record<string,unknown>[])=>request(`/courses/${courseId}/question-bank/metadata-batch`,{method:"POST",body:JSON.stringify({items})},token),
  editBankMetadata: (token:string,id:string,payload:Record<string,unknown>) => request(`/past-papers/${id}/metadata`,{method:"PATCH",body:JSON.stringify(payload)},token),
  deleteAttempt: (token:string,id:string) => request<{deleted:boolean;mistakes_deleted:number;review_tasks_deleted:number}>(`/attempts/${id}?confirm_delete=true`,{method:"DELETE"},token),
  restoreAttempt: (token:string,id:string,courseId?:string) => request<Attempt>(`/attempts/${id}${courseId?"?course_id="+encodeURIComponent(courseId):""}`,{},token),
  selfScore:(token:string,id:string,qid:string,score:number)=>request<Attempt>(`/attempts/${id}/self-grades/${qid}`,{method:"POST",body:JSON.stringify({score})},token),
  selfGrade: (token:string,id:string,qid:string,correct:boolean) => request<Attempt>(`/attempts/${id}/self-grades/${qid}`,{method:"POST",body:JSON.stringify({correct})},token),
  createTopic: (token: string, courseId: string, name: string, parent_id?:string|null) => request<Topic>(`/courses/${courseId}/topics`, { method: "POST", body: JSON.stringify({ name, aliases: [],parent_id }) }, token),
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
  apiConnection:(token:string)=>request<ApiConnection>("/api-connection",{},token),
  saveApiConnection:(token:string,payload:{revision:number;model:string;key?:string})=>request<ApiConnection>("/api-connection",{method:"PUT",body:JSON.stringify(payload)},token),
  testApiConnection:(token:string,revision:number)=>request<ApiConnection>("/api-connection/test",{method:"POST",body:JSON.stringify({revision,confirm:true})},token),
  clearApiConnection:(token:string,revision:number)=>request<ApiConnection>(`/api-connection?revision=${revision}`,{method:"DELETE"},token),
  dailyRedo:(token:string,goal=3)=>request<DailyRedo>(`/mistakes/daily-progress?goal=${goal}`,{},token),
  startRedo:(token:string,id:string,request_id:string)=>request<Redo>(`/mistakes/${id}/redoes`,{method:"POST",body:JSON.stringify({request_id})},token),
  submitRedo:(token:string,id:string,rid:string,answer:unknown)=>request<Redo>(`/mistakes/${id}/redoes/${rid}/submit`,{method:"POST",body:JSON.stringify({answer})},token),
  judgeRedo:(token:string,id:string,rid:string,correct:boolean)=>request<Redo>(`/mistakes/${id}/redoes/${rid}/judge`,{method:"POST",body:JSON.stringify({correct})},token),
  removeMistake:(token:string,id:string)=>request<{status:string}>(`/mistakes/${id}`,{method:"DELETE"},token),
  mistakes: (token: string) => request<MistakeItem[]>("/mistakes", {}, token),
  reviewTasks: (token: string) => request<Array<{ id: string; title: string; due_date: string; status: string }>>("/review-tasks/today", {}, token),
  rescheduleReview: (token:string,id:string,due:string,expected:string) => request(`/review-tasks/${id}`,{method:"PATCH",body:JSON.stringify({due_date:due,expected_due_date:expected})},token),
  feedback: (token: string, payload: { kind: string; content: string; rating?: number }) => request("/feedback", { method: "POST", body: JSON.stringify(payload) }, token),
};
