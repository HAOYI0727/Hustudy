import { FormEvent, lazy, Suspense, useRef, useState } from "react";
import { api, Course } from "../../api/client";
import { Icon, IconName } from "../../components/Icon";
import { EmptyInline } from "../../components/workspace";
import {CourseWorkspace, useCourseWorkspace, type OpenWorkspace} from "./CourseWorkspace";
import { CourseEditor, courseTags, validCourseTags } from "./CourseEditor";
import {CourseAgenda} from "./CourseAgenda";
import type {PackageIntent} from '../packages/PackageTransfer';
const PackageTransfer=lazy(()=>import('../packages/PackageTransfer'));

type Destination = "materials" | "notes" | "ai" | "exam" | "review";
type Props = { onRecords:()=>void; onOpen:OpenWorkspace; onNote: (id: string) => void; token: string; courses: Course[]; courseId: string; onRefresh: () => Promise<void>; onSelect: (id: string) => void; onNavigate: (section: Destination) => void; onNotice: (s: string) => void; onError: (e: unknown) => void };
export function Overview({ token, courses, courseId, onRefresh, onSelect, onNavigate, onNotice, onError, onNote, onOpen, onRecords }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [sort, setSort] = useState("newest");
  const [newCategory, setNewCategory] = useState("");
  const [newTags, setNewTags] = useState("");
  const [editing, setEditing] = useState<Course | null>(null);
  const [busy, setBusy] = useState(false);
  const [packageIntent,setPackageIntent]=useState<PackageIntent|null>(null),[packageVisited,setPackageVisited]=useState(false);
  const packageSerial=useRef(0);
  const showPackage=(request:Omit<PackageIntent,'nonce'>)=>{setPackageVisited(true);setPackageIntent({...request,nonce:++packageSerial.current});};
  const {parts,retry} = useCourseWorkspace(token,courseId);
  const course = courses.find((row) => row.id === courseId);
  const notes = parts.notes.data?.recent || [];
  const loading = parts.notes.loading, failed = parts.notes.error;
  const create = async (event: FormEvent) => {
    event.preventDefault(); if (busy || !name.trim()) return; setBusy(true);
    const tags = courseTags(newTags);
    if (!validCourseTags(tags)) {setBusy(false); onError(new Error("课程标签最多12个，每个不超过32字")); return;}
    try { await api.createCourse(token, name.trim(), description.trim(), {category: newCategory.trim() || "未分类", tags}); setName(""); setDescription(""); setNewCategory(""); setNewTags(""); await onRefresh(); onNotice("课程已创建，可以开始导入资料"); }
    catch (reason) { onError(reason); } finally { setBusy(false); }
  };
  const metric = (domain:keyof typeof parts,key:string) => parts[domain].loading ? "…" : parts[domain].error ? "—" : parts[domain].data?.counts[key] ?? "—";
  const categories = [...new Set(courses.map(row => row.category))].sort();
  const tags = [...new Set(courses.flatMap(row => row.tags))].sort();
  const visibleCourses = courses.filter(row => `${row.name} ${row.description || ""} ${row.category} ${row.tags.join(" ")}`.toLowerCase().includes(query.trim().toLowerCase()) && (!category || row.category === category) && (!tag || row.tags.includes(tag))).sort((a, b) => (sort === "name" ? a.name.localeCompare(b.name, "zh-CN") : (sort === "updated" ? b.updated_at.localeCompare(a.updated_at) : b.created_at.localeCompare(a.created_at))) || a.id.localeCompare(b.id));
  const dateLabel = new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date());
  return <div className="page dashboard">
    <section className="dashboard-hero">
      <div><span className="hero-date">{dateLabel} · 学习由你掌握</span><h2>把零散的资料，<br />连成清晰的知识</h2><p>{course ? `继续学习「${course.name}」，从阅读到练习，每一步都有来处。` : "创建一门课程，开启你的个人学习空间。"}</p><div className="hero-actions"><button className="primary" onClick={() => courseId ? onNavigate("materials") : document.getElementById("new-course-name")?.focus()}>{courseId ? "继续阅读资料" : "创建第一门课程"} <Icon name="arrow" size={17}/></button><button className="hero-secondary" onClick={() => onNavigate("review")}>查看待复习任务 <Icon name="arrow" size={16}/></button></div></div>
      <div className="knowledge-orbit" aria-hidden="true"><div className="orbit-ring" /><div className="orbit-core">H<span>KNOWLEDGE</span></div><span className="orbit-note one"><Icon name="file"/>课程资料</span><span className="orbit-note two"><Icon name="notes"/>我的理解</span><span className="orbit-note three"><Icon name="link"/>来源证据</span></div>
    </section>
    <section className="dashboard-metrics" aria-label="学习数据">
      {[{ title: "我的课程", value: courses.length, detail: "全部课程", icon: "folder", tone:"course" }, { title: "课程资料", value: metric("materials","total"), detail: course?.name || "尚未选择课程", icon: "file", tone:"material" }, { title: "知识笔记", value: metric("notes","total"), detail: "当前课程已保存", icon: "notes", tone:"notes" }, { title: "待复习", value: metric("practice","due_reviews"), detail: "当前课程 · 今日及逾期", icon: "review", tone:"review" }].map((item) => <article className={`metric-card metric-${item.tone}`} key={item.title}><div><span>{item.title}</span><strong>{item.value}</strong><small>{item.detail}</small></div><span className="metric-icon"><Icon name={item.icon as IconName} size={22}/></span></article>)}
    </section>
    {courseId && <CourseAgenda key={`${token}:${courseId}`} token={token} courseId={courseId} courseName={course?.name||"当前课程"} onOpen={onOpen} onError={onError}/>}
    {courseId && <CourseWorkspace parts={parts} retry={retry} onOpen={onOpen} onRecords={onRecords}/>}
    <div className="package-open-actions"><button className="secondary" onClick={()=>showPackage({mode:"import",kind:"course",courseId})}><Icon name="upload" size={16}/>导入课程包</button></div>
    <div className="dashboard-columns"><section><div className="section-heading"><div><p className="eyebrow">MY COURSES</p><h2>你的课程空间</h2></div><input className="course-search" aria-label="搜索课程" placeholder="搜索名称、分类或标签…" maxLength={200} value={query} onChange={(e) => setQuery(e.target.value)} /></div>
      <div className="course-filters"><label>分类<select value={category} onChange={e => setCategory(e.target.value)}><option value="">全部分类</option>{[...new Set([...categories, ...(category ? [category] : [])])].map(item => <option key={item}>{item}</option>)}</select></label><label>标签<select value={tag} onChange={e => setTag(e.target.value)}><option value="">全部标签</option>{[...new Set([...tags, ...(tag ? [tag] : [])])].map(item => <option key={item}>{item}</option>)}</select></label><label>排序<select value={sort} onChange={e => setSort(e.target.value)}><option value="newest">最近创建</option><option value="updated">最近整理</option><option value="name">课程名称</option></select></label><button className="secondary" disabled={!query && !category && !tag && sort === "newest"} onClick={() => {setQuery(""); setCategory(""); setTag(""); setSort("newest");}}>重置筛选</button></div>
      <p className="hint" role="status">显示 {visibleCourses.length} / {courses.length} 门课程 · 分类与标签只整理课程</p>
      <div className="course-grid">{visibleCourses.map(row => <article className={`course-card course-color-${parseInt(row.id.slice(0, 2), 16) % 3} ${row.id === courseId ? "current-course" : ""}`} key={row.id}><div className="course-card-top"><span className="course-icon">{row.name.slice(0, 1)}</span>{row.id === courseId && <span className="course-current">当前课程</span>}</div><strong>{row.name}</strong><p className="course-description" title={row.description || undefined}>{row.description || "在这里积累资料、笔记与练习。"}</p><div className="course-labels"><button aria-label={`按分类筛选：${row.category}`} aria-pressed={category === row.category} onClick={() => setCategory(category === row.category ? "" : row.category)}>{row.category}</button>{row.tags.map(item => <button key={item} aria-label={`按标签筛选：${item}`} aria-pressed={tag === item} onClick={() => setTag(tag === item ? "" : item)}>#{item}</button>)}</div><div className="course-card-actions"><button className="link-button" onClick={() => onSelect(row.id)}>打开课程 <Icon name="arrow" size={16}/></button><button className="secondary" aria-label={`导出课程包：${row.name}`} onClick={()=>showPackage({mode:"export",kind:"course",courseId:row.id})}>导出课程包</button><button className="secondary" aria-label={`整理课程：${row.name}`} onClick={() => setEditing(row)}><Icon name="edit" size={15}/>整理</button></div></article>)}</div>
      {!visibleCourses.length && <EmptyInline text={courses.length ? "没有符合筛选的课程，请调整关键词或重置筛选" : "还没有课程，在下方创建你的第一门课程"} />}
      <details className="course-create-details" open={courses.length===0?true:undefined}><summary><Icon name="plus" size={17}/>新增课程空间</summary><form className="course-create-inline panel" onSubmit={create}><div><h3>＋ 开启一门新课程</h3><p className="hint">为每门课保留独立的学习空间。</p></div><label>课程名称<input id="new-course-name" maxLength={200} disabled={busy} value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：操作系统" required /></label><label>课程描述<input maxLength={5000} disabled={busy} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="本学期的学习目标（可选）" /></label><div className="course-new-organization"><label>课程分类<input maxLength={64} disabled={busy} value={newCategory} onChange={e => setNewCategory(e.target.value)} placeholder="专业必修（可选）"/></label><label>课程标签<input maxLength={1000} disabled={busy} value={newTags} onChange={e => setNewTags(e.target.value)} placeholder="大二、期末复习（可选）"/></label></div><button className="primary" disabled={busy || !name.trim()}>{busy ? "创建中…" : "创建课程"}</button></form></details>
      {editing && <CourseEditor key={editing.id} course={editing} token={token} onClose={() => setEditing(null)} onRefresh={onRefresh} onDeleted={async () => {await onRefresh(); onNotice("课程已删除，关联来源已撤销访问");}} onError={onError} onSaved={async () => {await onRefresh(); onNotice("课程整理已保存，资料和笔记链接保持有效");}}/>}
    </section><aside className="dashboard-aside">
      <section className="panel"><div className="panel-title"><h3>最近保存的笔记</h3><Icon className="aside-icon" name="notes"/></div>{loading ? <p className="hint" role="status">正在读取笔记…</p> : failed ? <p className="hint">暂时无法读取</p> : notes.length ? [...notes].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 3).map((note) => <button className="dashboard-note" key={note.id} onClick={() => onNote(note.id)}><strong>{note.title}</strong><p>{new Date(note.updated_at).toLocaleDateString("zh-CN")} · 已保存</p><small>继续编辑这篇笔记 →</small></button>) : <EmptyInline text="还没有笔记，试试概念学习模板" />}<button className="secondary full" onClick={() => onNavigate("notes")}>打开笔记工作台</button></section>
      <section className="panel review-preview"><div className="panel-title"><h3>把薄弱处，再走一遍</h3><Icon className="aside-icon" name="review"/></div><p className="hint">当前课程 · 真实作答记录</p><div className="review-summary-numbers"><div><strong>{metric("practice","mistakes")}</strong><span>保留的错题</span></div><div><strong>{metric("practice","due_reviews")}</strong><span>到期复习任务</span></div></div><p className="hint">错题库可以查看全部课程；答对、自评与掌握状态分别记录。</p><button className="secondary full" onClick={() => onNavigate("review")}>进入错题与复习 →</button></section>
      <section className="evidence-tip"><Icon name="ai" size={24}/><div><strong>让每个结论都有来处</strong><p>真实AI先核对发送片段，再确认调用。结果分模式标识，核对原文后再写进笔记。</p></div></section>
    </aside></div>
    {packageVisited&&<Suspense fallback={packageIntent?<p role="status">正在打开标准包工具…</p>:null}><PackageTransfer token={token} intent={packageIntent} courses={courses} disabled={busy} onClose={()=>setPackageIntent(null)} onError={onError} onNotice={onNotice} onChanged={async result=>{await onRefresh();if(result.course_id===courseId){retry("materials");retry("notes");retry("study");retry("practice");}}}/></Suspense>}
  </div>;
}
