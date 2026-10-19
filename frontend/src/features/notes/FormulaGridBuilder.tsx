import {useMemo, useState} from 'react';
import {renderFormula, MAX_FORMULA_LENGTH} from '../../components/mathRendering';
import {buildFormulaGrid, formulaGridColumnCount, formulaGridKinds, MAX_GRID_SIZE, type FormulaGridKind} from './formulaAuthoring';
function initialCells(kind: FormulaGridKind) {
  const examples = kind === 'cases' ? [['x^2', 'x\\ge 0'], ['-x', 'x<0']]
    : kind === 'system' || kind === 'gathered' ? [['x+y=1'], ['x-y=0']]
    : kind === 'aligned' ? [['a', '=b+c'], ['{}', '=d']] : [['1', '0'], ['0', '1']];
  return Array.from({length: MAX_GRID_SIZE}, (_, r) => Array.from({length: MAX_GRID_SIZE}, (_, c) => examples[r]?.[c] ?? '{}'));
}
export function FormulaGridBuilder({onInsert}: {onInsert: (source: string) => void}) {
  const [kind, setKind] = useState<FormulaGridKind>('pmatrix'), [rows, setRows] = useState(2), [columns, setColumns] = useState(2);
  const [drafts, setDrafts] = useState<Partial<Record<FormulaGridKind, string[][]>>>({});
  const [alignment, setAlignment] = useState('cc');
  const cells = drafts[kind] ?? initialCells(kind), columnCount = formulaGridColumnCount(kind, columns);
  const built = useMemo(() => buildFormulaGrid(kind, cells.slice(0, rows).map(row => row.slice(0, columnCount)), alignment), [kind, cells, rows, columnCount, alignment]);
  const rendered = useMemo(() => renderFormula(built.source, true), [built.source]);
  const error = built.error || rendered.error;
  const changeCell = (r: number, c: number, value: string) => setDrafts(previous => ({...previous, [kind]: cells.map((row, i) => row.map((cell, j) => i === r && j === c ? value : cell))}));
  return <div className="formula-grid-builder">
    <label>结构<select aria-label="公式表格结构" value={kind} onChange={e => setKind(e.target.value as FormulaGridKind)}>{formulaGridKinds.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <div className="formula-grid-dimensions">
      <label>行数<select aria-label="公式表格行数" value={rows} onChange={e => setRows(Number(e.target.value))}>{Array.from({length: MAX_GRID_SIZE}, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}</select></label>
      <label>列数<select aria-label="公式表格列数" value={columnCount} disabled={['cases', 'system', 'aligned', 'gathered'].includes(kind)} onChange={e => {const n = Number(e.target.value); setColumns(n); setAlignment('c'.repeat(n));}}>{Array.from({length: MAX_GRID_SIZE}, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}</select></label>
      {kind === 'array' && <label>列对齐<input aria-label="公式列对齐" value={alignment} maxLength={25} onChange={e => setAlignment(e.target.value)} placeholder="cc|c"/></label>}
    </div>
    <p className="hint">{kind === 'cases' ? '左列填表达式，右列填条件，中文条件可写 \\text{其他}。' : kind === 'aligned' ? '左列填等号左侧，右列以 = 等关系符号开头；省略左侧时填 {}。' : '每格可填 LaTeX，空白项填写 {}。Tab 跳到下一格，缩小行列会保留隐藏格内容。'}</p>
    <div className="formula-cell-scroll" tabIndex={0} aria-label="公式单元格表格">
      <div className="formula-cells" style={{gridTemplateColumns: 'repeat(' + columnCount + ', minmax(76px, 1fr))'}}>
        {cells.slice(0, rows).flatMap((row, r) => row.slice(0, columnCount).map((cell, c) => <input key={r + '-' + c} aria-label={'第' + (r + 1) + '行第' + (c + 1) + '列'} spellCheck={false} maxLength={MAX_FORMULA_LENGTH} value={cell} onChange={e => changeCell(r, c, e.target.value)}/>))}
      </div>
    </div>
    <div className="formula-grid-preview" aria-label="表格公式预览">{!error && <div dangerouslySetInnerHTML={{__html: rendered.html}}/>}{error && <p className="formula-error">{error}</p>}</div>
    <button type="button" className="secondary" disabled={!!error} onClick={() => onInsert(built.source)}>将结构插入公式</button>
    <p className="hint">插入后可继续修改源码或嵌套结构，确认整个公式后才写入笔记。</p>
  </div>;
}
