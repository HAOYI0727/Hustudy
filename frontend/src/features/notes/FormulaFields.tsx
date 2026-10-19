import type {RefObject} from 'react';
import type {FormulaDraft, FormulaSlot} from './formulaAuthoring';
export function FormulaFields({draft, container, onSelect, onChange}: {
  draft: FormulaDraft; container: RefObject<HTMLDivElement | null>;
  onSelect: (slot: FormulaSlot, element: HTMLTextAreaElement) => void;
  onChange: (slot: FormulaSlot, value: string, element: HTMLTextAreaElement) => void;
}) {
  const fraction = draft.slots.length === 2 && draft.slots[0].label === '分子' && draft.slots[1].label === '分母';
  return <div className="formula-fields" ref={container}>
    <p className="hint">逐项填写，Tab 切换字段。符号按钮会插入当前字段的光标处；选中字段内容再点结构可以嵌套。</p>
    {!draft.slots.length && <p className="hint">尚无可填写字段。点击上方分数、根号等图形，或使用源码编写；已有公式可点击“识别结构”。</p>}
    <div className={'formula-field-grid' + (fraction ? ' is-fraction' : '')}>
      {draft.slots.map((slot, i) => <label key={slot.label + '-' + slot.start} className="formula-field-cell"><span><b>{i + 1}</b>{slot.label}</span>
        <textarea rows={1} aria-label={'填写 ' + slot.label} data-formula-field-start={slot.start} data-formula-field-end={slot.end} spellCheck={false} value={draft.source.slice(slot.start, slot.end)}
          onFocus={e => onSelect(slot, e.currentTarget)}
          onSelect={e => onSelect(slot, e.currentTarget)}
          onChange={e => onChange(slot, e.target.value, e.currentTarget)}/>
      </label>)}
    </div>
  </div>;
}
