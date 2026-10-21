import { StrictMode, lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { ConfigProvider, Alert } from "antd";
import zhCN from "antd/locale/zh_CN";
import { createBrowserRouter, RouterProvider, useBlocker, useLocation, useNavigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient, clearSessionQueries, sessionPartition } from "./api/query";
import { parseWorkspace, workspaceHref, Section } from "./features/platform/routing";
import { createRoot } from "react-dom/client";
import { api, ApiError, Course } from "./api/client";




import { AuthScreen } from "./features/platform";
import { EmptyState, ScrollToTop } from "./components/workspace";
import { Icon } from "./components/Icon";
import { WorkspaceNavigation, navigationItems } from "./components/WorkspaceNavigation";
import type { MaterialTarget } from "./features/platform/Search";


import "./styles.css";
import "./responsive.css";

const Materials = lazy(() => import("./features/materials").then(module => ({default:module.Materials})));
const Notes = lazy(() => import("./features/notes").then(module => ({default:module.Notes})));
const AIStudy = lazy(() => import("./features/ai").then(module => ({default:module.AIStudy})));
const Search = lazy(() => import("./features/platform/Search").then(module => ({default:module.Search})));
const Help = lazy(() => import("./features/platform/Help").then(module => ({default:module.Help})));
const Backups = lazy(() => import("./features/platform/Backups").then(module => ({default:module.Backups})));
const Overview = lazy(() => import("./features/platform/Overview").then(module => ({default:module.Overview})));
const ExamPilot = lazy(() => import("./features/exams").then(module => ({default:module.ExamPilot})));
const ApiConnect = lazy(() => import("./features/platform/ApiConnect"));
const FeedbackPage = lazy(() => import("./features/exams").then(module => ({default:module.FeedbackPage})));
const Review = lazy(() => import("./features/exams").then(module => ({default:module.Review})));
const SessionDialog = lazy(() => import("./features/platform/SessionDialog"));


export function App() {
  const location = useLocation(), routerNavigate = useNavigate();
  const route = useMemo(() => parseWorkspace(location.pathname, location.search), [location.pathname, location.search]);
  const {section, courseId, noteId: noteTarget, mistakeId, material: materialTarget} = route;
  const activeSection = navigationItems.find(item => item.id === section) || {label:"使用指南", icon:"help" as const};
  const routeRef = useRef(route); routeRef.current = route;
  const [token, setToken] = useState(() => localStorage.getItem("hustudy_token") || "");
  const tokenRef = useRef(token); tokenRef.current = token;
  const [userName, setUserName] = useState(() => localStorage.getItem("hustudy_user") || "");
  const [authNotice, setAuthNotice] = useState("");
  const [expired, setExpired] = useState(false);
  const expiredRef = useRef(expired); expiredRef.current = expired;
  const bypass = useRef(false);
  const canNavigate = () => window.dispatchEvent(new Event("hustudy:before-navigate", { cancelable: true }));
  const blocker = useBlocker(({currentLocation, nextLocation}) => {
    if (bypass.current) {bypass.current = false; return false;}
    if (!token || (currentLocation.pathname === nextLocation.pathname && currentLocation.search === nextLocation.search)) return false;
    if (expiredRef.current) return true;
    return !canNavigate();
  });
  useEffect(() => {if (blocker.state === "blocked") blocker.reset();}, [blocker]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [notice, setNotice] = useState(""); const [error, setError] = useState("");
  const selectedCourse = useMemo(() => courses.find((course) => course.id === courseId), [courses, courseId]);
  const go = (next: Section, id = courseId, extra?: {noteId?: string; mistakeId?:string; material?: MaterialTarget}, replace = false) => {
    void routerNavigate(workspaceHref(next, id, extra), {replace});
  };
  const navigate = (next: Section) => go(next);
  const expireSession = () => {
    if (token !== tokenRef.current || expiredRef.current) return;
    expiredRef.current = true; setExpired(true); setError("");
  };
  const reportError = (reason: unknown) => {
    if (token !== tokenRef.current) return;
    if (reason instanceof ApiError && reason.status === 401) {expireSession(); return;}
    if (!expiredRef.current) setError(reason instanceof Error ? reason.message : "操作失败，请检查后端服务和输入");
  };
  const refreshCourses = async () => {
    if (!token) return;
    const list = await api.courses(token);
    if (token !== tokenRef.current || expiredRef.current) return;
    setCourses(list);
    const current = routeRef.current;
    if (current.courseId && list.some(course => course.id === current.courseId)) return;
    const id = list[0]?.id || "";
    if (current.courseId !== id) go(current.section, id, {noteId:current.noteId,mistakeId:current.mistakeId,material:current.material}, true);
  };
  useEffect(() => {void refreshCourses().catch(reportError);}, [token]);
  useEffect(() => {
    const unauthorized = (event: Event) => {
      if ((event as CustomEvent).detail === sessionPartition(token)) expireSession();
    };
    window.addEventListener("hustudy:unauthorized", unauthorized);
    return () => window.removeEventListener("hustudy:unauthorized", unauthorized);
  }, [token]);
  useEffect(() => {window.scrollTo({top:0, behavior:"instant"}); setError(""); setNotice("");}, [section, courseId, mistakeId]);
  const signOut = () => {
    if (!canNavigate()) return;
    clearSessionQueries(); localStorage.removeItem("hustudy_token"); localStorage.removeItem("hustudy_user");
    tokenRef.current = ""; setToken(""); setExpired(false); expiredRef.current = false;
    setAuthNotice(""); setCourses([]); setNotice(""); setError("");
    bypass.current = true; go("overview", "", undefined, true); bypass.current = false;
  };
  const signedIn = (nextToken: string, username: string) => {
    clearSessionQueries(); localStorage.setItem("hustudy_token", nextToken); localStorage.setItem("hustudy_user", username);
    tokenRef.current = nextToken; expiredRef.current = false;
    setAuthNotice(""); setToken(nextToken); setUserName(username); setExpired(false);
  };
  const openNote = async (id: string) => {
    try {const note = await api.note(token, id); if (token === tokenRef.current) go("notes", note.course_id || courseId, {noteId:id});}
    catch (reason) {reportError(reason);}
  };
  const openSource = async (versionId: string, chunkId: string) => {
    try {
      const version = await api.version(token, versionId), doc = await api.document(token, version.document_id);
      if (token === tokenRef.current) go("materials", doc.course_id, {material:{documentId:doc.id, versionId, chunkId}});
    } catch (reason) {reportError(reason);}
  };
  if (!token) return <AuthScreen message={authNotice} onSuccess={signedIn}/>;
  return <><div className="app-shell" inert={expired} aria-hidden={expired || undefined}><a className="skip-link" href="#workspace-content">跳到主要内容</a><WorkspaceNavigation username={userName} section={section} locationKey={location.key} expired={expired} onNavigate={navigate} onSignOut={signOut}/><main className="content" id="workspace-content" tabIndex={-1}><header className="topbar"><div><p className="workspace-context"><Icon name={activeSection.icon} size={15}/><span>学习工作台</span><span className="context-divider" aria-hidden="true">/</span><strong>{activeSection.label}</strong></p><h1>{section==="api-connect"?"API接入":section==="feedback"?"使用反馈":section==="review"?"错题复习":selectedCourse?.name || "开始你的课程学习"}</h1></div>{!["api-connect","feedback","review"].includes(section)&&<div className="course-picker"><label htmlFor="active-course">当前课程</label><select id="active-course" value={courseId} onChange={(event) => go(section,event.target.value)}><option value="">选择课程</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.name}</option>)}</select></div>}</header>{route.invalid && <Alert type="warning" showIcon title="地址中的页面或定位无效，请从导航重新选择。"/>}{notice && <div className="toast success" role="status"><Icon name="check" size={18}/><span>{notice}</span><button aria-label="关闭成功提示" onClick={() => setNotice("")}>×</button></div>}{error && <div className="toast error" role="alert"><Icon name="info" size={18}/><span>{error}</span><button aria-label="关闭错误提示" onClick={() => setError("")}>×</button></div>}{!courseId && section !== "overview" && section !== "review" && section !== "help" && section !== "backup" && section !== "api-connect" && section !== "feedback" ? <EmptyState title="先选择一门课程" text="从课程总览创建或选择课程后，再开始上传资料和学习。" action="去课程总览" onAction={() => navigate("overview")} /> : <Suspense fallback={<section className="panel" role="status">正在打开工作区…</section>}>{section === "api-connect" && <ApiConnect token={token} onNotice={setNotice} onError={reportError}/>}{section === "feedback" && <FeedbackPage token={token} onNotice={setNotice} onError={reportError}/>}{section === "backup" && <Backups token={token} onError={reportError} onNotice={setNotice} onRestored={refreshCourses}/>}{section === "help" && <Help onNavigate={navigate} />}{section === "search" && <Search key={courseId} token={token} courseId={courseId} onError={reportError} onNote={openNote} onMaterial={target => go("materials",courseId,{material:target})} />}{section === "overview" && <Overview token={token} courses={courses} courseId={courseId} onNavigate={navigate} onNote={openNote} onRefresh={refreshCourses} onSelect={id => go("materials",id)} onNotice={setNotice} onError={reportError} />}{section === "materials" && <Materials onNote={openNote} initialTarget={materialTarget} key={`${courseId}-${JSON.stringify(materialTarget)}`} token={token} courseId={courseId} onNotice={setNotice} onError={reportError} />}{section === "notes" && <Notes onSource={openSource} initialNoteId={noteTarget} key={`${courseId}-${noteTarget || ""}`} token={token} courseId={courseId} onNotice={setNotice} onError={reportError} />}{section === "ai" && <AIStudy onSource={openSource} key={courseId} token={token} courseId={courseId} onNotice={setNotice} onError={reportError} />}{section === "exam" && <ExamPilot key={courseId} token={token} courseId={courseId} onNotice={setNotice} onError={reportError} />}{section === "review" && <Review token={token} mistakeId={mistakeId} onOpen={id=>go("review",courseId,{mistakeId:id})} onBack={()=>go("review")} onError={reportError}/>}</Suspense>}</main><ScrollToTop/></div>{expired && <Suspense fallback={<div className="toast" role="status">正在恢复登录…</div>}><SessionDialog username={userName} onSuccess={signedIn} onExit={signOut}/></Suspense>}</>;
}


const router = createBrowserRouter([{path:"*", element:<App/>}]);
createRoot(document.getElementById("root")!).render(<StrictMode><ConfigProvider locale={zhCN} theme={{token:{colorPrimary:"#4864dc",borderRadius:12,fontSize:13,controlHeight:36,fontFamily:'-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif'},components:{Modal:{contentBg:"#ffffff"}}}}><QueryClientProvider client={queryClient}><RouterProvider router={router}/></QueryClientProvider></ConfigProvider></StrictMode>);
