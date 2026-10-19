export type MarkdownCommand = 'bold' | 'italic' | 'strike' | 'code' | 'link' | 'heading' | 'list' | 'ordered' | 'task' | 'quote' | 'fence' | 'table' | 'rule' | 'indent' | 'outdent';
export type Edit = {text: string; start: number; end: number};
export function formatMarkdown(text: string, start: number, end: number, command: MarkdownCommand): Edit {
  const selected = text.slice(start, end);
  const wrap: Partial<Record<MarkdownCommand, [string,string,string]>> = {bold: ['**','**','重点'], italic: ['*','*','强调'], strike: ['~~','~~','删除线'], code: ['`','`','代码'], link: ['[','](https://example.com)','链接文字'], fence: ['\n```\n','\n```\n','代码块']};
  if (wrap[command]) {
    const [before, after, fallback] = wrap[command]!;
    const body = selected || fallback;
    return {text: text.slice(0,start) + before + body + after + text.slice(end), start: start + before.length, end: start + before.length + body.length};
  }
  if (command === 'table' || command === 'rule') {
    const insert = command === 'table' ? '\n| 项目 | 内容 |\n| --- | --- |\n| 示例 | 说明 |\n' : '\n\n---\n\n';
    return {text: text.slice(0,start) + insert + text.slice(end), start: start + insert.length, end: start + insert.length};
  }
  const left = text.lastIndexOf('\n', start - 1) + 1;
  const right = text.indexOf('\n', end > start && text[end - 1] === '\n' ? end - 1 : end);
  const limit = right < 0 ? text.length : right;
  const lines = text.slice(left, limit).split('\n');
  const prefix: Partial<Record<MarkdownCommand,string>> = {heading: '## ', list: '- ', task: '- [ ] ', quote: '> ', indent: '  '};
  const body = lines.map((line, index) => command === 'outdent' ? line.replace(/^( {1,2}|\t)/, '') : command === 'ordered' ? `${index + 1}. ${line.replace(/^\d+\. /, '')}` : command === 'heading' ? '## ' + (line.replace(/^#{1,6}\s+/, '') || '小节标题') : (prefix[command] || '') + line).join('\n');
  return {text: text.slice(0,left) + body + text.slice(limit), start: left, end: left + body.length};
}

export function continueList(text: string, at: number): Edit | null {
  const start = text.lastIndexOf('\n', at - 1) + 1, line = text.slice(start, at);
  const match = /^(\s*)([-+*]|\d+\.)(\s+)(\[[ xX]\]\s+)?(.*)$/.exec(line);
  if (!match) return null;
  if (!match[5].trim()) return {text: text.slice(0,start) + text.slice(at), start, end: start};
  const marker = /^\d/.test(match[2]) ? `${parseInt(match[2], 10) + 1}.` : match[2];
  const insert = `\n${match[1]}${marker} ${match[4] ? '[ ] ' : ''}`;
  return {text: text.slice(0,at) + insert + text.slice(at), start: at + insert.length, end: at + insert.length};
}

export function markdownOutline(text: string) {
  const result: {label: string; level: number; offset: number}[] = [];
  let offset = 0, fence = '';
  for (const line of text.split('\n')) {
    const marker = /^\s*(`{3,}|~{3,})/.exec(line);
    if (marker) {if (!fence) fence = marker[1][0]; else if (fence === marker[1][0]) fence = '';}
    else if (!fence) {const title = /^(#{1,6})\s+(.+)$/.exec(line); if (title) result.push({label: title[2].replace(/\s+#+\s*$/, ''), level: title[1].length, offset});}
    offset += line.length + 1;
  }
  return result;
}
