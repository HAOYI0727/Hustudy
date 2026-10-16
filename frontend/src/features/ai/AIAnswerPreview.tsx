import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Model text cannot create external navigation or image requests.
export function AIAnswerPreview({content}: {content: string}) {
  return <div className="markdown-preview"><Markdown skipHtml remarkPlugins={[remarkGfm]} components={{
    a: ({children}) => <span>{children}</span>,
    img: () => <span className="hint">图片请在原文中核对</span>,
  }}>{content}</Markdown></div>;
}
