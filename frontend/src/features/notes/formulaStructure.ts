import {MAX_FORMULA_LENGTH} from '../../components/mathRendering';
import type {FormulaSlot, FormulaDraft} from './formulaAuthoring';

type Group = {start: number; end: number; after: number};
/** Textareas normalize CRLF, while an untouched imported formula may still contain it. */
export function formulaDomOffset(source: string, offset: number): number {
  return source.slice(0, offset).replace(/\r\n/g, '\n').length;
}
export function formulaSourceOffset(source: string, offset: number): number {
  let position = 0, normalized = 0;
  while (position < source.length && normalized < offset) {
    if (source[position] === '\r' && source[position + 1] === '\n') position++;
    position++; normalized++;
  }
  return position;
}
const mathArguments: Record<string, string[]> = {
  frac: ['分子', '分母'], dfrac: ['分子', '分母'], tfrac: ['分子', '分母'], cfrac: ['分子', '分母'],
  binom: ['上项', '下项'], dbinom: ['上项', '下项'], tbinom: ['上项', '下项'],
  overset: ['上方标记', '主体'], underset: ['下方标记', '主体'],
  overbrace: ['上括号内容'], underbrace: ['下括号内容'],
};
for (const command of ['vec','hat','widehat','bar','overline','underline','tilde','widetilde','dot','ddot','dddot','overrightarrow','overleftarrow','overleftrightarrow','breve','check','acute','grave','mathring','boxed','cancel','bcancel','xcancel','phantom','hphantom','vphantom','mathrm','mathit','mathbf','boldsymbol','mathbb','mathcal','mathscr','mathfrak','mathsf','mathtt']) mathArguments[command] = ['内容'];
const opaqueArguments: Record<string, number> = {
  text: 1, textrm: 1, textbf: 1, textit: 1, textsf: 1, texttt: 1, textnormal: 1,
  operatorname: 1, begin: 1, end: 1, tag: 1, label: 1, ref: 1,
  color: 1, hspace: 1, vspace: 1, url: 1, href: 2, includegraphics: 1,
};
const definitions = new Set(['def','gdef','edef','xdef','let','futurelet','newcommand','renewcommand','providecommand','newenvironment','renewenvironment','csname','catcode']);

/** Recover only explicit, balanced math arguments. Never execute macros or rewrite unknown TeX. */
export function recoverFormulaSlots(source: string): FormulaSlot[] {
  if (source.length > MAX_FORMULA_LENGTH) return [];
  const slots: FormulaSlot[] = [];
  let opaqueDefinition = false;
  const skipSpace = (position: number, limit: number) => {
    while (position < limit) {
      if (/\s/.test(source[position])) position++;
      else if (source[position] === '%') {const newline = source.indexOf('\n', position); position = newline < 0 ? limit : newline + 1;}
      else break;
    }
    return position;
  };
  const groupAt = (position: number, limit: number, opening = '{'): Group | null => {
    position = skipSpace(position, limit);
    if (source[position] !== opening) return null;
    const start = position + 1, closing = opening === '{' ? '}' : ']';
    let braces = 0, brackets = 0;
    for (let i = start; i < limit; i++) {
      const c = source[i];
      if (c === '\\') {i++; continue;}
      if (c === '%') {const newline = source.indexOf('\n', i); if (newline < 0) return null; i = newline; continue;}
      if (c === closing && braces === 0 && brackets === 0) return {start, end: i, after: i + 1};
      if (c === '{') braces++;
      else if (c === '}') {if (!braces) return null; braces--;}
      else if (opening === '[' && c === '[' && !braces) brackets++;
      else if (opening === '[' && c === ']' && !braces) brackets--;
      if (braces + brackets > 32) return null;
    }
    return null;
  };
  const push = (label: string, group: Group) => {if (slots.length < 80) slots.push({label, start: group.start, end: group.end});};
  const scan = (start: number, end: number, depth: number) => {
    if (depth > 24 || opaqueDefinition || slots.length >= 80) return;
    for (let i = start; i < end && !opaqueDefinition && slots.length < 80;) {
      if (source[i] === '%') {const n = source.indexOf('\n', i); i = n < 0 ? end : n + 1; continue;}
      if (source[i] === '\\') {
        const token = /^\\([a-zA-Z]+|.)/.exec(source.slice(i, end));
        if (!token) {i++; continue;}
        const command = token[1]; i += token[0].length;
        if (definitions.has(command)) {opaqueDefinition = true; return;}
        if (command === 'sqrt') {
          const index = groupAt(i, end, '['), body = groupAt(index?.after ?? i, end);
          if (body) {
            if (index) {push('根指数', index); scan(index.start, index.end, depth + 1);}
            push('被开方数', body); scan(body.start, body.end, depth + 1); i = body.after;
          }
          continue;
        }
        const labels = mathArguments[command];
        if (labels) {
          const groups: Group[] = []; let next = i;
          for (let k = 0; k < labels.length; k++) {const group = groupAt(next, end); if (!group) break; groups.push(group); next = group.after;}
          if (groups.length === labels.length) {
            groups.forEach((group, k) => {push(labels[k], group); scan(group.start, group.end, depth + 1);});
            i = next;
          } else {
            // Do not descend into an incomplete known command as if it were a standalone field.
            for (const group of groups) i = group.after;
          }
          continue;
        }
        if (command === 'textcolor' || command === 'colorbox' || command === 'fcolorbox') {
          const count = command === 'fcolorbox' ? 2 : 1;
          let next = i;
          for (let k = 0; k < count; k++) {const color = groupAt(next, end); if (!color) break; next = color.after;}
          const body = groupAt(next, end);
          if (body) {push('颜色内容', body); scan(body.start, body.end, depth + 1); i = body.after;}
          continue;
        }
        // Text, metadata and unknown macro arguments are intentionally opaque.
        const maximum = opaqueArguments[command] ?? 8;
        if (source[i] === '*' && opaqueArguments[command]) i++;
        for (let k = 0; k < maximum; k++) {
          const group = groupAt(i, end) ?? groupAt(i, end, '[');
          if (!group) break; i = group.after;
        }
        continue;
      }
      if (source[i] === '^' || source[i] === '_') {
        const label = source[i] === '^' ? '上标' : '下标', group = groupAt(i + 1, end);
        if (group) {push(label, group); scan(group.start, group.end, depth + 1); i = group.after; continue;}
      }
      if (source[i] === '{') {
        const group = groupAt(i, end);
        if (group) {scan(group.start, group.end, depth + 1); i = group.after; continue;}
      }
      i++;
    }
  };
  scan(0, source.length, 0);
  return opaqueDefinition ? [] : slots.sort((a, b) => a.start - b.start || b.end - a.end);
}
export function refreshFormulaSlots(draft: FormulaDraft): FormulaDraft {
  const previous = draft.slots.filter(slot => slot.start >= 0 && slot.end <= draft.source.length && slot.end >= slot.start);
  const slots = [...previous];
  for (const slot of recoverFormulaSlots(draft.source)) {
    if (!slots.some(old => old.start === slot.start && old.end === slot.end)) slots.push(slot);
  }
  return {...draft, slots: slots.sort((a, b) => a.start - b.start || b.end - a.end).slice(0, 80)};
}
