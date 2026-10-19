import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkMath from 'remark-math';
import type {Edit} from './markdownEditing';

const parser = unified().use(remarkParse).use(remarkMath);
export type FormulaSelection = {start: number; end: number; source: string; display: boolean; existing: boolean; blocked: boolean};
type PositionedNode = {type: string; value?: string; position?: {start: {offset?: number}; end: {offset?: number}}; children?: PositionedNode[]};

export function formulaInsertionError(source: string, display: boolean): string {
  // Markdown treats dollars as delimiters even inside TeX's escaped text;
  // folding an inline newline would also extend a TeX comment over later terms.
  if (!display && (source.includes('$') || /(^|[^\\])(?:\\\\)*%[^\r\n]*[\r\n]/.test(source))) {
    return '此公式含美元符号或多行注释，请选择“独立公式”，以免 Markdown 截断内容。';
  }
  return '';
}

/** Parse Markdown rather than matching dollars inside escaped text or code. */
export function formulaSelection(text: string, start: number, end: number): FormulaSelection {
  const fallback = {start, end, source: text.slice(start, end), display: false, existing: false, blocked: false};
  const stack: PositionedNode[] = [parser.parse(text)];
  while (stack.length) {
    const node = stack.pop()!, from = node.position?.start.offset, to = node.position?.end.offset;
    if (from !== undefined && to !== undefined && start >= from && end <= to && start < to) {
      if (node.type === 'math' || node.type === 'inlineMath') return {...fallback, start: from, end: to, source: node.value || '', display: node.type === 'math', existing: true};
      if (node.type === 'code' || node.type === 'inlineCode') return {...fallback, blocked: true};
    }
    if (node.children) stack.push(...node.children);
  }
  return fallback;
}

export function insertFormula(text: string, selection: FormulaSelection, source: string, display: boolean): Edit {
  const before = text.slice(0, selection.start), after = text.slice(selection.end);
  const body = source.trim().replace(display ? /\r\n/g : /[\r\n]+/g, display ? '\n' : ' ');
  const opening = display ? `${before && !before.endsWith('\n') ? '\n\n' : ''}$$\n` : (before.endsWith('$') ? ' $' : '$');
  const closing = display ? `\n$$${after && !after.startsWith('\n') ? '\n\n' : ''}` : (after.startsWith('$') ? '$ ' : '$');
  return {text: before + opening + body + closing + after, start: before.length + opening.length, end: before.length + opening.length + body.length};
}
