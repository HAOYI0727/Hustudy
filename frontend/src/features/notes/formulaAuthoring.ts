export type FormulaSlot = {label: string; start: number; end: number};
export type FormulaDraft = {source: string; slots: FormulaSlot[]};
export function expandFormulaSnippet(snippet: string, selection = ''): FormulaDraft {
  const slots: FormulaSlot[] = [];
  let source = '', last = 0;
  for (const match of snippet.matchAll(/«([^:»]+):([^»]*)»/g)) {
    source += snippet.slice(last, match.index);
    const value = !slots.length && selection ? selection : match[2];
    slots.push({label: match[1], start: source.length, end: source.length + value.length});
    source += value;
    last = match.index + match[0].length;
  }
  return {source: source + snippet.slice(last), slots};
}

/** Preserve fields enclosing an edit and shift subsequent fields; discard invalid partial overlaps. */
export function replaceFormulaRange(draft: FormulaDraft, start: number, end: number, value: string, inserted: FormulaSlot[] = []): FormulaDraft {
  const delta = value.length - (end - start);
  const slots = draft.slots.flatMap(slot => {
    if (slot.end < start || (slot.end === start && start !== end)) return [slot];
    if (slot.start > end || (slot.start === end && start !== end)) return [{...slot, start: slot.start + delta, end: slot.end + delta}];
    if (slot.start <= start && slot.end >= end && !inserted.length) return [{...slot, end: slot.end + delta}];
    if (slot.start < start && slot.end > end) return [{...slot, end: slot.end + delta}];
    return [];
  });
  return {
    source: draft.source.slice(0, start) + value + draft.source.slice(end),
    slots: [...slots, ...inserted.map(slot => ({...slot, start: slot.start + start, end: slot.end + start}))].sort((a, b) => a.start - b.start || a.end - b.end),
  };
}
export function updateFormulaSource(draft: FormulaDraft, source: string): FormulaDraft {
  let start = 0, oldEnd = draft.source.length, end = source.length;
  while (start < oldEnd && start < end && draft.source[start] === source[start]) start++;
  while (oldEnd > start && end > start && draft.source[oldEnd - 1] === source[end - 1]) {oldEnd--; end--;}
  return replaceFormulaRange(draft, start, oldEnd, source.slice(start, end));
}
export function insertFormulaSnippet(draft: FormulaDraft, start: number, end: number, snippet: string) {
  const expanded = expandFormulaSnippet(snippet, draft.source.slice(start, end));
  const next = replaceFormulaRange(draft, start, end, expanded.source, expanded.slots);
  const first = expanded.slots[0];
  return {draft: next, start: start + (first?.start ?? expanded.source.length), end: start + (first?.end ?? expanded.source.length)};
}

export const formulaGridKinds = [
  ['pmatrix', '圆括号矩阵'], ['bmatrix', '方括号矩阵'], ['Bmatrix', '花括号矩阵'],
  ['vmatrix', '行列式'], ['Vmatrix', '双竖线矩阵'], ['matrix', '无括号矩阵'],
  ['cases', '分段函数'], ['system', '方程组'], ['aligned', '对齐推导'],
  ['gathered', '居中多行'], ['array', '自定列对齐 / 增广矩阵'],
] as const;
export type FormulaGridKind = typeof formulaGridKinds[number][0];
export const MAX_GRID_SIZE = 8;
export function formulaGridColumnCount(kind: FormulaGridKind, columns: number) {
  return ['system', 'gathered'].includes(kind) ? 1 : ['cases', 'aligned'].includes(kind) ? 2 : columns;
}
export function buildFormulaGrid(kind: FormulaGridKind, cells: string[][], alignment = 'cc'): {source: string; error: string} {
  if (!formulaGridKinds.some(([value]) => value === kind) || !cells.length || cells.length > MAX_GRID_SIZE || !cells[0].length || cells[0].length > MAX_GRID_SIZE || cells.some(row => row.length !== cells[0].length)) return {source: '', error: '请填写 1–8 行、1–8 列的规则表格。'};
  if (formulaGridColumnCount(kind, cells[0].length) !== cells[0].length) return {source: '', error: '此结构的列数不匹配。'};
  const cols = cells[0].length;
  if (kind === 'array' && (!/^[lcr|]+$/.test(alignment) || alignment.replace(/\|/g, '').length !== cols)) return {source: '', error: '每列填写一个 l、c 或 r，可插入 | 分隔线，例如 cc|c。'};
  if (cells.some(row => row.some(cell => !cell.trim()))) return {source: '', error: '还有空单元格；空白项可填写 {}，条件文字用 \\text{中文}。'};
  // A cell is an expression, not an extra row/column. Nested matrix environments remain allowed.
  for (const row of cells) for (const cell of row) {
    let depth = 0;
    const tokens = cell.match(/\\begin\{[^}]+\}|\\end\{[^}]+\}|\\\\|\\.|&|[^\\&]+/g) ?? [];
    for (const token of tokens) {
      if (token.startsWith('\\begin{')) depth++;
      else if (token.startsWith('\\end{')) depth--;
      else if ((token === '&' || token === '\\\\') && depth === 0) return {source: '', error: '一个单元格只填一个表达式；换行、对齐由表格自动生成。复杂结构也可直接编辑公式源码。'};
    }
  }
  const environment = kind === 'system' ? 'cases' : kind;
  const rows = cells.map(row => row.map(value => value.trim()).join(' & '));
  return {source: '\\begin{' + environment + '}' + (kind === 'array' ? '{' + alignment + '}' : '') + '\n' + rows.join(' \\\\\n') + '\n\\end{' + environment + '}', error: ''};
}

export const formulaGuide = [
  {title: '从零开始组合', text: '先选分数、根号等模板。点击参数按钮选中要改的位置，直接输入；再次点模板可嵌套。用“下一项”逐个填写，或按 Alt+↓ / Alt+↑。参数只是编辑辅助，保存时不会留下占位标记。', example: '\\frac{\\sqrt{x^2+1}}{n+1}'},
  {title: '上下标与分组', text: '多个字符放进花括号。底数、下标、上标都能是复杂表达式；同一层不要连续写两个上标。', example: 'x_{n+1}^{2}+a_{ij}'},
  {title: '分式与根式', text: 'frac 的两个花括号依次为分子、分母；sqrt 的方括号是根指数。它们可以任意嵌套。', example: '\\sqrt[3]{\\frac{a+b}{c}}'},
  {title: '函数、中文与单位', text: 'sin、log 等函数使用反斜杠命令，文字用 text，单位用 mathrm；数学模式内普通空格大多被忽略。', example: '\\sin x\\quad\\text{且}\\quad v=3\\,\\mathrm{m/s}'},
  {title: '括号自动伸缩', text: 'left 和 right 必须成对，圆括号、方括号、绝对值和范数均支持。单边括号的另一侧用点号。', example: '\\left(\\frac{a}{b}\\right)\\quad\\left.F(x)\\right|_a^b'},
  {title: '上下限与微积分', text: 'sum、prod、int、lim 后填写上下标；强制正下方用 limits 或 underset。积分中的微分 d 可以使用正体。', example: '\\int_0^1 x^2\\,\\mathrm{d}x=\\frac13'},
  {title: '矩阵与行列式', text: '生成器支持 1–8 行列，键盘 Tab 可逐格填写。& 分列，双反斜杠换行，更多行列或嵌套结构可在源码继续编辑。', example: '\\begin{bmatrix}1&0\\\\0&1\\end{bmatrix}'},
  {title: '多行、分段与增广矩阵', text: 'aligned 的 & 放在等号前；cases 每行写表达式与条件；array 用 l/c/r 决定列对齐，用 | 加分隔线。结构自动切为独立公式。', example: '\\begin{aligned}a&=b+c\\\\&=d\\end{aligned}'},
  {title: '字体与重音', text: 'mathbb 适合数集，mathcal 是花体，boldsymbol 能加粗希腊字母；hat、vec、overline 等命令修饰其花括号内的整体。', example: '\\boldsymbol{\\alpha}\\in\\mathbb{R}^n\\quad\\widehat{AB}'},
  {title: '颜色、标记与编号', text: 'textcolor 使用颜色名或 #RRGGBB；boxed、cancel 标记结果。参考页的 MathJax bbox 可用“背景颜色 / 彩色边框”模板实现相应效果，本项目不识别 bbox 命令。tag 仅用于独立公式，编号由自己填写，不会跨笔记自动编号。', example: '\\boxed{\\textcolor{blue}{x=1}}\\tag{1}'},
  {title: 'Markdown 与公式边界', text: '窗口内只写公式，确认后自动包裹 $ 或 $$。粘贴时若已有这些边界，请先去掉；代码块内的美元符号不会作为公式。美元字符和多行百分号注释请用独立公式。Markdown 表格中需要将竖线改用 \\vert 或 \\mid。', example: '\\text{价格}\\;\\$10'},
  {title: '错误排查与支持范围', text: '红色提示会指出语法错误；先检查缺失的花括号、成对括号、命令大小写及矩阵分隔。当前为本地 KaTeX 数学排版，直接编写支持的 LaTeX 数学命令；不支持 documentclass、usepackage、TikZ 或外部文件导入。单个公式最多4000字符，宏展开有上限。', example: '\\underbrace{a+b+c}_{\\text{三项}}'},
];
