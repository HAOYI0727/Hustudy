import {memo, useDeferredValue, useId, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {renderFormula, MAX_FORMULA_LENGTH} from '../../components/mathRendering';
import {formulaInsertionError, type FormulaSelection} from './formulaEditing';
import {formulaCategories, formulaRecipes, searchFormulaRecipes, type FormulaRecipe} from './formulaCatalog';
import {expandFormulaSnippet, formulaGuide, insertFormulaSnippet, replaceFormulaRange, updateFormulaSource, type FormulaDraft, type FormulaSlot} from './formulaAuthoring';
import {FormulaGridBuilder} from './FormulaGridBuilder';
import {FormulaQuickTools} from './FormulaQuickTools';
import {FormulaFields} from './FormulaFields';
import {recoverFormulaSlots, refreshFormulaSlots, formulaDomOffset, formulaSourceOffset} from './formulaStructure';
import './formulaEditor.css';

const RecipeButton = memo(function RecipeButton({recipe, onInsert}: {recipe: FormulaRecipe; onInsert: (recipe: FormulaRecipe) => void}) {
  const source = expandFormulaSnippet(recipe.snippet).source;
  const rendered = useMemo(() => renderFormula(source, !!recipe.display), [source, recipe.display]);
  return <button type="button" className="secondary formula-recipe" aria-label={'插入' + recipe.label + '模板'} title={recipe.label + '\n' + source} onClick={() => onInsert(recipe)}>
    <span aria-hidden="true" dangerouslySetInnerHTML={{__html: rendered.html}}/><small>{recipe.label}</small>
  </button>;
});
type Snapshot = {draft: FormulaDraft; display: boolean; start: number; end: number};
export function FormulaEditor({selection, stale, onCancel, onInsert}: {
  selection: FormulaSelection; stale: boolean; onCancel: () => void; onInsert: (source: string, display: boolean) => void;
}) {
  const [draft, setDraft] = useState<FormulaDraft>(() => ({source: selection.source, slots: recoverFormulaSlots(selection.source)})), [display, setDisplay] = useState(selection.display);
  const [fields, setFields] = useState(false), [recent, setRecent] = useState<string[]>([]);
  const fieldsContainer = useRef<HTMLDivElement>(null);
  const fieldTarget = useRef<{slot: FormulaSlot; element: HTMLTextAreaElement} | null>(null);
  const [panel, setPanel] = useState('library'), [category, setCategory] = useState('common'), [query, setQuery] = useState('');
  const [limit, setLimit] = useState(60), [tip, setTip] = useState('先选择模板，再逐项修改；也可以直接编写 LaTeX。');
  const [undo, setUndo] = useState<Snapshot[]>([]), [redo, setRedo] = useState<Snapshot[]>([]);
  const input = useRef<HTMLTextAreaElement>(null), cursor = useRef({start: selection.source.length, end: selection.source.length});
  const pendingFocus = useRef<(() => void) | null>(null);
  useLayoutEffect(() => {
    const focus = pendingFocus.current; pendingFocus.current = null; focus?.();
  });
  // Existing controls can focus immediately; changed values must commit first.
  // Do not leave an animation-frame callback that can overwrite subsequent typing.
  const afterCommit = (focus: () => void, ready = false) => {
    pendingFocus.current = ready ? null : focus;
    if (ready) focus();
  };
  const source = draft.source, deferred = useDeferredValue(source), helpId = useId();
  const result = useMemo(() => renderFormula(deferred, display), [deferred, display]);
  const entries = useMemo(() => searchFormulaRecipes(query, category), [query, category]);
  const focusRange = (start: number, end: number, raw = source) => {
    fieldTarget.current = null;
    cursor.current = {start, end};
    afterCommit(() => {
      input.current?.focus({preventScroll: true});
      input.current?.setSelectionRange(formulaDomOffset(raw, start), formulaDomOffset(raw, end));
      cursor.current = {start, end};
    }, input.current?.value === raw.replace(/\r\n/g, '\n'));
  };
  const focusField = (start: number, end: number, raw = source) => {
    cursor.current = {start, end};
    const findField = () => fieldsContainer.current?.querySelector<HTMLTextAreaElement>('[data-formula-field-start="' + start + '"][data-formula-field-end="' + end + '"]');
    afterCommit(() => {
      const element = findField();
      if (element) {element.focus({preventScroll: true}); element.select(); cursor.current = {start, end};}
      else focusRange(start, end, raw);
    }, findField()?.value === raw.slice(start, end).replace(/\r\n/g, '\n'));
  };
  const snapshot = (): Snapshot => ({draft, display, ...cursor.current});
  const change = (next: FormulaDraft, block = display, start?: number, end = start) => {
    setUndo(previous => [...previous, snapshot()].slice(-80)); setRedo([]);
    setDraft(next); setDisplay(block);
    if (start !== undefined) focusRange(start, end ?? start, next.source);
  };
  const restore = (direction: 'undo' | 'redo') => {
    const stack = direction === 'undo' ? undo : redo, previous = stack[stack.length - 1];
    if (!previous) return;
    if (direction === 'undo') {setUndo(stack.slice(0, -1)); setRedo(items => [...items, snapshot()].slice(-80));}
    else {setRedo(stack.slice(0, -1)); setUndo(items => [...items, snapshot()].slice(-80));}
    setDraft(previous.draft); setDisplay(previous.display); focusRange(previous.start, previous.end, previous.draft.source);
  };
  const insertRecipe = (recipe: FormulaRecipe, graphic = false) => {
    const target = fieldTarget.current, structured = recipe.snippet.includes('«');
    // WebKit can omit React's select notification after a controlled value update.
    // Read the actual field selection before an action, then explicitly retain the restored caret.
    if (target?.element.isConnected) {
      const slot = draft.slots.find(item => item.start === target.slot.start && item.label === target.slot.label);
      if (slot) selectField(slot, target.element);
    }
    const edit = insertFormulaSnippet(draft, cursor.current.start, cursor.current.end, recipe.snippet);
    const block = recipe.display || display || !!formulaInsertionError(edit.draft.source, false);
    setRecent(previous => [recipe.id, ...previous.filter(id => id !== recipe.id)].slice(0, 12));
    if (target && !structured) {
      change(edit.draft, block);
      cursor.current = {start: edit.start, end: edit.end};
      afterCommit(() => {
        if (!target.element.isConnected) {focusRange(edit.start, edit.end, edit.draft.source); return;}
        target.element.focus({preventScroll: true});
        const field = edit.draft.source.slice(target.slot.start, target.slot.end + edit.draft.source.length - source.length);
        target.element.setSelectionRange(formulaDomOffset(field, edit.start - target.slot.start), formulaDomOffset(field, edit.end - target.slot.start));
        fieldTarget.current = {slot: {...target.slot, end: target.slot.end + edit.draft.source.length - source.length}, element: target.element};
        cursor.current = {start: edit.start, end: edit.end};
      });
    } else if (structured && (fields || graphic)) {
      setFields(true); change(edit.draft, block); focusField(edit.start, edit.end, edit.draft.source);
    } else change(edit.draft, block, edit.start, edit.end);
    setTip(recipe.label + '：' + (recipe.help || '点击参数按钮可定位，选中参数后可嵌套其他结构。'));
  };
  const insertRaw = (text: string) => {
    const start = cursor.current.start, end = cursor.current.end;
    change(replaceFormulaRange(draft, start, end, text), true, start + text.length);
    setTip('结构已插入，可修改源码，或选中其中的表达式再嵌套模板。');
  };
  const selectSlot = (slot: FormulaSlot) => focusRange(slot.start, slot.end);
  const nextSlot = (direction: number) => {
    if (!draft.slots.length) return;
    const index = draft.slots.findIndex(slot => slot.start === cursor.current.start && slot.end === cursor.current.end);
    const after = draft.slots.findIndex(slot => slot.start >= cursor.current.end);
    const next = index >= 0 ? (index + direction + draft.slots.length) % draft.slots.length
      : direction > 0 ? (after < 0 ? 0 : after) : (after <= 0 ? draft.slots.length - 1 : after - 1);
    const slot = draft.slots[next];
    if (fieldTarget.current) focusField(slot.start, slot.end); else selectSlot(slot);
  };
  const selectField = (slot: FormulaSlot, element: HTMLTextAreaElement, value = source.slice(slot.start, slot.end)) => {
    fieldTarget.current = {slot, element};
    cursor.current = {start: slot.start + formulaSourceOffset(value, element.selectionStart), end: slot.start + formulaSourceOffset(value, element.selectionEnd)};
  };
  const editField = (slot: FormulaSlot, value: string, element: HTMLTextAreaElement) => {
    change(replaceFormulaRange(draft, slot.start, slot.end, value));
    selectField({...slot, end: slot.start + value.length}, element, value);
  };
  const recognize = () => {
    const next = refreshFormulaSlots(draft);
    setDraft(next); setFields(true);
    setTip(next.slots.length ? '已识别 ' + next.slots.length + ' 个可填写字段，源码保持不变。' : '此写法没有可恢复的明确字段，源码完整保留。可继续直接编辑或插入图形结构。');
  };
  const error = selection.blocked ? '当前位置是代码，请关闭窗口，将光标移到正文后再插入公式。' : stale ? '正文已更新，请关闭窗口后重新打开公式，以免覆盖新内容。' : formulaInsertionError(source, display) || result.error;
  return <div className="formula-editor formula-workspace">
    <div className="formula-mode" role="group" aria-label="公式排版">
      <button type="button" className="secondary" aria-pressed={!display} onClick={() => change(draft, false)}>行内公式 <small>随文字排列</small></button>
      <button type="button" className="secondary" aria-pressed={display} onClick={() => change(draft, true)}>独立公式 <small>单独居中</small></button>
    </div>
    <FormulaQuickTools recent={recent} onInsert={recipe => insertRecipe(recipe, true)}/>
    <div className="formula-workspace-columns">
      <section className="formula-library" aria-label="公式工具箱">
        <div className="formula-panels" role="group" aria-label="公式工具切换">
          {[['library', '∑', '符号与模板'], ['grid', '▦', '矩阵 / 多行'], ['guide', '?', '语法速查']].map(([id, icon, label]) => <button type="button" className="secondary" key={id} aria-pressed={panel === id} onClick={() => setPanel(id)}><span aria-hidden="true">{icon}</span> {label}</button>)}
        </div>
        <div hidden={panel !== 'library'}>
          <label className="formula-search">搜索全部 {formulaRecipes.length} 项<input type="search" aria-label="搜索公式符号与模板" value={query} onChange={e => {setQuery(e.target.value); setLimit(60);}} placeholder="名称、符号或命令，如 积分 / alpha"/></label>
          <label className="formula-category">分类<select aria-label="公式分类" value={category} onChange={e => {setCategory(e.target.value); setQuery(''); setLimit(60);}}><option value="common">☆ 常用</option>{formulaCategories.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
          <p className="hint">{query ? '搜索所有分类 · ' + entries.length + ' 项' : formulaCategories.find(c => c[0] === category)?.[2] || '从常用结构开始，选中文字可以继续嵌套。'}</p>
          <div className="formula-catalog-scroll">
            <div className={'formula-catalog-grid' + (entries.length > 8 && entries.every(recipe => !recipe.snippet.includes('«')) ? ' is-symbol-palette' : '')} role="group" aria-label="公式模板">{entries.slice(0, limit).map(recipe => <RecipeButton key={recipe.id} recipe={recipe} onInsert={insertRecipe}/>)}</div>
            {!entries.length && <p className="hint">没有匹配项，试试中文名称或 LaTeX 命令，也可以直接编辑源码。</p>}
            {entries.length > limit && <button type="button" className="secondary" onClick={() => setLimit(limit + 60)}>显示更多（剩余 {entries.length - limit} 项）</button>}
          </div>
        </div>
        <div hidden={panel !== 'grid'}><FormulaGridBuilder onInsert={insertRaw}/></div>
        <div hidden={panel !== 'guide'} className="formula-guide">
          {formulaGuide.map(item => <details key={item.title}><summary>{item.title}</summary><p>{item.text}</p><code>{item.example}</code><button type="button" className="secondary" onClick={() => insertRaw(item.example)}>插入此示例</button></details>)}
        </div>
      </section>
      <section className={'formula-composer' + (fields ? ' has-fields' : '')} aria-label="公式编写">
        <div className="formula-edit-actions">
          <strong>编写公式</strong>
          <button type="button" className="secondary" aria-label="撤销公式编辑" title="Ctrl / Cmd + Z" disabled={!undo.length} onClick={() => restore('undo')}>↶</button>
          <button type="button" className="secondary" aria-label="重做公式编辑" title="Ctrl / Cmd + Shift + Z" disabled={!redo.length} onClick={() => restore('redo')}>↷</button>
          <button type="button" className="secondary" onClick={() => focusRange(0, source.length)}>选择整个公式</button>
          <button type="button" className="secondary" title="在当前公式后继续输入" onClick={() => focusRange(source.length, source.length)}>移到公式末尾 →</button>
        </div>
        <div className="formula-preview" aria-label="公式实时预览" aria-busy={deferred !== source}><small>实时预览</small>{!result.error && <div className="formula-rendered" dangerouslySetInnerHTML={{__html: result.html}}/>}{error && <p className="formula-error" role="status">{error}</p>}</div>
        <div className="formula-field-controls" role="group" aria-label="结构填写工具">
          <button type="button" className="secondary" aria-pressed={fields} onClick={() => {if (!fields) setDraft(refreshFormulaSlots(draft)); setFields(!fields); fieldTarget.current = null;}}>填写参数</button>
          <button type="button" className="secondary" onClick={recognize}>识别结构</button>
          <button type="button" className="secondary" disabled={!draft.slots.length} onClick={() => nextSlot(-1)}>← 上一项</button>
          <button type="button" className="secondary" disabled={!draft.slots.length} onClick={() => nextSlot(1)}>下一项 →</button>
        </div>
        {fields && <div onKeyDown={e => {
          if (e.altKey && ['ArrowDown', 'ArrowUp'].includes(e.key)) {e.preventDefault(); nextSlot(e.key === 'ArrowDown' ? 1 : -1);}
          if ((e.ctrlKey || e.metaKey) && ['z', 'y'].includes(e.key.toLowerCase())) {e.preventDefault(); restore(e.key.toLowerCase() === 'y' || e.shiftKey ? 'redo' : 'undo');}
        }}><FormulaFields draft={draft} container={fieldsContainer} onSelect={selectField} onChange={editField}/></div>}
        <label className="formula-source-label">LaTeX 公式<textarea autoFocus ref={input} aria-label="LaTeX 公式" spellCheck={false} rows={6} value={source}
          onFocus={() => {fieldTarget.current = null;}}
          onSelect={e => {cursor.current = {start: formulaSourceOffset(source, e.currentTarget.selectionStart), end: formulaSourceOffset(source, e.currentTarget.selectionEnd)};}}
          onChange={e => {change(updateFormulaSource(draft, e.target.value)); cursor.current = {start: e.target.selectionStart, end: e.target.selectionEnd};}}
          onKeyDown={e => {
            if ((e.ctrlKey || e.metaKey) && ['z', 'y'].includes(e.key.toLowerCase())) {e.preventDefault(); restore(e.key.toLowerCase() === 'y' || e.shiftKey ? 'redo' : 'undo');}
            if (e.altKey && ['ArrowDown', 'ArrowUp'].includes(e.key)) {e.preventDefault(); nextSlot(e.key === 'ArrowDown' ? 1 : -1);}
          }} placeholder="例如：\frac{a}{b} + x^2" aria-describedby={helpId}/></label>
        <div className="formula-source-help" id={helpId}><span>只填写公式，无需 $ 边界。</span><span>{source.length} / {MAX_FORMULA_LENGTH}</span></div>
        {!!draft.slots.length && !fields && <div className="formula-parameters" role="group" aria-label="公式参数">
          <div className="formula-parameter-heading"><small>定位源码中的参数 · Alt + ↑ / ↓</small></div>
          <div className="formula-parameter-list">{draft.slots.map((slot, i) => <button type="button" className="secondary" key={slot.start + '-' + slot.end + '-' + i} onClick={() => selectSlot(slot)} aria-label={'编辑参数 ' + slot.label} title={source.slice(slot.start, slot.end)}>{slot.label}<code>{source.slice(slot.start, slot.end) || '空'}</code></button>)}</div>
        </div>}
        <p className="hint formula-tip">{tip}</p>
      </section>
    </div>
    <footer className="formula-actions"><span className="hint">{selection.existing ? '确认后替换当前公式，可撤销。' : '确认后插入正文，可撤销。'}窗口内操作尚未写入笔记。</span><button type="button" className="secondary" onClick={onCancel}>取消</button><button type="button" className="primary" disabled={!!error || deferred !== source} onClick={() => onInsert(source, display)}>{selection.existing ? '更新公式' : '插入公式'}</button></footer>
  </div>;
}
