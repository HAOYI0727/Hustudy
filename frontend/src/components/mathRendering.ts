import katex from 'katex';

export const MAX_FORMULA_LENGTH = 4000;

/** Only KaTeX's generated markup may reach the formula HTML sink. */
export function renderFormula(source: string, displayMode: boolean): {html: string; error: string} {
  if (!source.trim()) return {html: '', error: '请输入公式，或选择一个常用模板。'};
  if (source.length > MAX_FORMULA_LENGTH) return {html: '', error: `单个公式最多 ${MAX_FORMULA_LENGTH} 个字符，请拆分后编辑。`};
  try {
    return {html: katex.renderToString(source, {
      displayMode, output: 'htmlAndMathml', throwOnError: true,
      trust: false, strict: 'ignore', maxSize: 10, maxExpand: 200,
      // A fresh object prevents definitions from leaking into another formula.
      macros: {},
    }), error: ''};
  } catch (error) {
    const detail = error instanceof Error ? error.message.replace(/^KaTeX parse error:\s*/, '') : '无法解析此公式';
    return {html: '', error: `公式语法有误，请检查命令与括号：${detail}`};
  }
}
