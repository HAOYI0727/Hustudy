import { Children, isValidElement, useEffect, useState } from "react";
import Markdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import {MathFormula} from './MathFormula';
import { api, NoteSummary } from "../api/client";

export function AssetImage({ token, id, alt }: { token: string; id: string; alt: string }) {
  const [url, setUrl] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true; let created = "";
    setUrl(""); setFailed(false);
    void api.asset(token, id).then(blob => { if (live) { created = URL.createObjectURL(blob); setUrl(created); } })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; if (created) URL.revokeObjectURL(created); };
  }, [token, id]);
  return failed ? <span className="missing-asset">图片已删除或无法读取 · {alt}</span> : url ? <img className="knowledge-image" src={url} alt={alt}/> : <span role="status">正在加载图片…</span>;
}

export function NotePreview({ content, token, notes, onNote, singleTilde = true }: { singleTilde?: boolean; content: string; token: string; notes: NoteSummary[]; onNote: (note: NoteSummary) => void }) {
  const transformed = content.replace(/!\[\[asset:([0-9a-fA-F-]{36})(?:\|([^\]]*))?\]\]/g,
    (_match, id, label) => `![${String(label || "课程图片").replace(/[\[\]\n]/g, " ")}](asset://${id})`)
    .replace(/\[\[note:([0-9a-fA-F-]{36})(?:\|([^\]]*))?\]\]/g,
    (_match, id, label) => `[${String(label || notes.find(n=>n.id===id)?.title || "笔记").replace(/[\[\]\n]/g, " ")}](note://${id})`);
  return <div className="markdown-preview"><Markdown skipHtml remarkPlugins={[[remarkGfm, {singleTilde}], remarkMath]} urlTransform={url => /^(asset|note):\/\/[0-9a-fA-F-]{36}$/.test(url) ? url : defaultUrlTransform(url)} components={{
    code: ({className, children}) => /\bmath-(inline|display)\b/.test(className || '')
      ? <MathFormula source={String(children).replace(/\n$/, '')} display={className?.includes('math-display')}/>
      : <code className={className}>{children}</code>,
    pre: ({children}) => {
      const child = Children.toArray(children)[0];
      return isValidElement<{className?: string}>(child) && child.props.className?.includes('math-display')
        ? <div className="math-block">{children}</div> : <pre>{children}</pre>;
    },
    img: ({ src, alt }) => src?.startsWith("asset://") ? <AssetImage token={token} id={src.slice(8)} alt={alt || "课程图片"}/> : <span className="missing-asset">外部图片请先上传到课程资料库 · {alt}</span>,
    a: ({ href, children }) => {
      if (href?.startsWith("note://")) { const target = notes.find(n=>n.id===href.slice(7)); return target ? <button className="link-button" onClick={()=>onNote(target)}>{target.title} ↗</button> : <span className="missing-asset">目标笔记已删除</span>; }
      return href && /^(https?:|mailto:)/i.test(href) ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span>;
    }
  }}>{transformed}</Markdown></div>;
}
