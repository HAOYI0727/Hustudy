const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export type Course = { id: string; name: string; description?: string | null };
export type DocumentItem = { id: string; name: string; original_filename: string; latest_version_id?: string; parse_status?: string; preview_status?: string; index_status?: string; parse_error?: string | null };
export type Chunk = { id: string; version_id: string; locator_type: string; locator_value: string; text: string };
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
  constructor(message: string, status: number) { super(message); this.status = status; }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
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
    let message = `请求失败（${response.status}）`;
    try { const body = await response.json(); message = body.error?.message || body.detail || message; } catch { /* keep status message */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (username: string, password: string) => request<{ access_token: string; user: { id: string; username: string } }>("/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) => request<{ access_token: string; user: { id: string; username: string } }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  courses: (token: string) => request<Course[]>("/courses", {}, token),
  createCourse: (token: string, name: string, description: string) => request<Course>("/courses", { method: "POST", body: JSON.stringify({ name, description }) }, token),
  documents: (token: string, courseId: string) => request<DocumentItem[]>(`/courses/${courseId}/documents`, {}, token),
  uploadDocument: (token: string, courseId: string, file: File) => { const data = new FormData(); data.append("file", file); return request<{ id: string; status: string }>(`/courses/${courseId}/documents`, { method: "POST", body: data }, token); },
  chunks: (token: string, versionId: string) => request<Chunk[]>(`/versions/${versionId}/chunks`, {}, token),
  search: (token: string, courseId: string, query: string) => request<Array<{ chunk_id: string; document_name: string; locator_type: string; locator_value: string; text: string }>>(`/courses/${courseId}/search?q=${encodeURIComponent(query)}`, {}, token),
  notes: (token: string, courseId?: string) => request<Note[]>(`/notes${courseId ? `?course_id=${courseId}` : ""}`, {}, token),
  createNote: (token: string, payload: { title: string; content: string; course_id?: string }) => request<Note>("/notes", { method: "POST", body: JSON.stringify(payload) }, token),
  updateNote: (token: string, id: string, payload: { title: string; content: string; course_id?: string; revision: number }) => request<Note>(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  citation: (token: string, noteId: string, payload: { version_id: string; chunk_id: string; quote: string }) => request(`/notes/${noteId}/citations`, { method: "POST", body: JSON.stringify(payload) }, token),
  aiQuery: (token: string, courseId: string, query: string) => request<{ status: string; model_mode: string; result: { answer?: string; message?: string; citations?: Array<{ locator: { value: string }; quote: string }>; model_notice?: string } }>(`/courses/${courseId}/ai-queries`, { method: "POST", body: JSON.stringify({ query, mode: "demo" }) }, token),
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
  paperWithAnswers: (token: string, paperId: string) => request<ExamPaper>(`/exam-papers/${paperId}?include_answers=true`, {}, token),
  answer: (token: string, attemptId: string, questionId: string, answer: unknown) => request<Attempt>(`/attempts/${attemptId}/answers/${questionId}`, { method: "PUT", body: JSON.stringify({ answer }) }, token),
  submit: (token: string, attemptId: string) => request<Attempt>(`/attempts/${attemptId}/submit`, { method: "POST" }, token),
  mistakes: (token: string) => request<Array<{ id: string; question: Question; given: unknown }>>("/mistakes", {}, token),
  reviewTasks: (token: string) => request<Array<{ id: string; title: string; due_date: string; status: string }>>("/review-tasks/today", {}, token),
  feedback: (token: string, payload: { kind: string; content: string; rating?: number }) => request("/feedback", { method: "POST", body: JSON.stringify(payload) }, token),
};
