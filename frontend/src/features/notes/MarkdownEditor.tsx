import {useEffect, useReducer, useRef, useState, type RefObject} from 'react';
import type {NoteSummary} from '../../api/client';
import {NotePreview} from '../../components/knowledge';
import {Icon, type IconName} from '../../components/Icon';
import {NotesDialog} from './NotesDialog';
import {FormulaEditor} from './FormulaEditor';
import {formulaSelection, insertFormula, type FormulaSelection} from './formulaEditing';
import {continueList, formatMarkdown, markdownOutline, type MarkdownCommand, type Edit} from './markdownEditing';

export function MarkdownEditor({value, onChange, textarea, preview, setPreview, token, notes, onNote, onSave, assetRevision, focused, setFocused, onImage, active = true}: {
  value: string; onChange: (text: string) => void; textarea: RefObject<HTMLTextAreaElement | null>; preview: boolean; setPreview: (value: boolean) => void;
  token: string; notes: NoteSummary[]; onNote: (note: NoteSummary) => void; onSave: () => void; assetRevision: number; focused: boolean; setFocused: (value: boolean) => void;
  onImage?: () => void; active?: boolean;
}) {
  const [split, setSplit] = useState(false), [find, setFind] = useState(''), [findStatus, setFindStatus] = useState('');
  const [formula, setFormula] = useState<{base: string; selection: FormulaSelection} | null>(null);
  const [formulaSuspended, setFormulaSuspended] = useState(false);
  useEffect(() => {
    const suspend = () => setFormulaSuspended(true);
    window.addEventListener('hustudy:notes-session-expired', suspend);
    return () => window.removeEventListener('hustudy:notes-session-expired', suspend);
  }, []);
  const history = useRef({past: [] as string[], present: value, future: [] as string[]});
  const [, redraw] = useReducer(x => x + 1, 0);
  useEffect(() => {
    const h = history.current;
    if (value !== h.present) {
      h.past.push(h.present); h.present = value; h.future = [];
      while (h.past.length > 50 || h.past.reduce((sum, text) => sum + text.length, 0) > 5 * 1024 * 1024) h.past.shift();
      redraw();
    }
  }, [value]);
  useEffect(() => {
    if (!focused) return;
    const old = document.body.style.overflow; document.body.style.overflow = 'hidden';
    const escape = (event: KeyboardEvent) => {if (event.key === 'Escape' && !document.querySelector('dialog[open]')) setFocused(false);};
    window.addEventListener('keydown', escape);
    return () => {document.body.style.overflow = old; window.removeEventListener('keydown', escape);};
  }, [focused]);
  const position = (start: number, end = start, scroll = false) => {
    window.requestAnimationFrame(() => {const el = textarea.current; if (!el) return; el.focus(); el.setSelectionRange(start, end); if (scroll) el.scrollTop = Math.max(0, value.slice(0,start).split('\n').length - 3) * parseFloat(getComputedStyle(el).lineHeight || '24');});
  };
  const apply = (edit: Edit) => {onChange(edit.text); position(edit.start, edit.end);};
  const format = (command: MarkdownCommand) => {setPreview(false); const el = textarea.current; apply(formatMarkdown(value, el?.selectionStart ?? value.length, el?.selectionEnd ?? value.length, command));};
  const openFormula = () => {setFormulaSuspended(false); if (formula) return; const el = textarea.current; setFormula({base: value, selection: formulaSelection(value, el?.selectionStart ?? value.length, el?.selectionEnd ?? value.length)});};
  const undo = (redo = false) => {
    const h = history.current, from = redo ? h.future : h.past, to = redo ? h.past : h.future;
    if (!from.length) return;
    to.push(h.present); h.present = from.pop()!; onChange(h.present); redraw();
  };
  const findNext = () => {
    if (!find) return;
    setPreview(false); const from = textarea.current?.selectionEnd ?? 0;
    const haystack = value.toLocaleLowerCase(), needle = find.toLocaleLowerCase();
    let index = haystack.indexOf(needle, from); if (index < 0) index = haystack.indexOf(needle);
    if (index < 0) setFindStatus('未找到匹配内容'); else {setFindStatus(`已定位到第 ${value.slice(0,index).split('\n').length} 行`); position(index, index + find.length, true);}
  };
  const groups: [MarkdownCommand, string, IconName][][] = [
    [['bold','加粗','bold'],['italic','斜体','italic'],['heading','二级标题','heading'],['strike','删除线','strike']],
    [['ordered','有序列表','ordered'],['list','无序列表','list'],['task','任务列表','task'],['quote','引用块','quote']],
    [['code','行内代码','code'],['fence','代码块','braces'],['link','链接','link'],['table','表格','table'],['rule','分隔线','rule']],
  ];
  const shortcuts: Partial<Record<MarkdownCommand,string>> = {bold: 'Ctrl/Cmd+B', italic: 'Ctrl/Cmd+I', link: 'Ctrl/Cmd+K'};
  return <div className="note-markdown-editor">
    <div className="writing-toolbar note-format-toolbar" role="group" aria-label="Markdown 格式工具">
      {groups.map((group, index) => <div className="note-format-group" key={index}>{group.map(([command,label,icon]) => <button key={command} type="button" className="secondary note-icon-tool" aria-label={label} title={label + (shortcuts[command] ? ` · ${shortcuts[command]}` : '')} onMouseDown={e => e.preventDefault()} onClick={() => format(command)}><Icon name={icon}/></button>)}</div>)}
      <div className="note-format-group">
        {onImage && <button type="button" className="secondary note-icon-tool" aria-label="插入图片与双链" title="插入图片与双链" onMouseDown={e => e.preventDefault()} onClick={onImage}><Icon name="image"/></button>}
        <button type="button" className="secondary note-icon-tool note-formula-tool" aria-label="公式编辑器" title="公式编辑器 · Ctrl/Cmd+Shift+M" onClick={event => {event.currentTarget.focus({preventScroll: true}); openFormula();}}><Icon name="formula"/></button>
      </div>
      <div className="note-format-group">
        <button type="button" className="secondary note-icon-tool" aria-label="撤销" title="撤销 · Ctrl/Cmd+Z" disabled={!history.current.past.length} onClick={() => undo()}><Icon name="undo"/></button><button type="button" className="secondary note-icon-tool" aria-label="重做" title="重做 · Ctrl/Cmd+Shift+Z" disabled={!history.current.future.length} onClick={() => undo(true)}><Icon name="redo"/></button>
      </div>
      <div className="note-format-group note-view-tools">
        <button type="button" className="secondary note-icon-tool" aria-label="分屏预览" title="分屏预览" aria-pressed={split} onClick={() => {setSplit(!split); setPreview(false);}}><Icon name="split"/></button>
        <button type="button" className="secondary note-icon-tool" aria-label={focused ? '退出专注' : '专注编辑'} title={focused ? '退出专注 · Esc' : '专注编辑'} aria-pressed={focused} onClick={() => setFocused(!focused)}><Icon name={focused ? 'collapse' : 'expand'}/></button>
      </div>
    </div>
    <div className="note-editor-navigation">
      <label>大纲<select aria-label="笔记大纲" value="" onChange={e => {if (e.target.value !== '') {setPreview(false); position(Number(e.target.value), Number(e.target.value), true);}}}><option value="">跳转到标题…</option>{markdownOutline(value).map(h => <option key={h.offset} value={h.offset}>{'　'.repeat(h.level - 1)}{h.label}</option>)}</select></label>
      <label>查找<input aria-label="查找正文" value={find} onChange={e => setFind(e.target.value)} onKeyDown={e => {if (e.key === 'Enter' && !e.nativeEvent.isComposing) {e.preventDefault(); findNext();}}}/></label><button className="text-button" disabled={!find} onClick={findNext}>下一个匹配</button><small role="status">{findStatus}</small>
    </div>
    <div className={`note-editor-panes ${split ? 'split' : ''}`}>
      {(!preview || split) && <textarea ref={textarea} aria-label="Markdown 正文" className="knowledge-text" placeholder="记录概念、例子和未解决的问题…" value={value} onChange={e => onChange(e.target.value)} rows={18} onKeyDown={e => {
        if (e.nativeEvent.isComposing) return;
        if (e.ctrlKey || e.metaKey) {
          const key = e.key.toLowerCase();
          if (key === 's') {e.preventDefault(); onSave();}
          else if (key === 'e') {e.preventDefault(); setPreview(!preview);}
          else if (key === 'z') {e.preventDefault(); undo(e.shiftKey);}
          else if (key === 'y') {e.preventDefault(); undo(true);}
          else if (key === 'm' && e.shiftKey) {e.preventDefault(); openFormula();}
          else if (['b','i','k'].includes(key)) {e.preventDefault(); format(key === 'b' ? 'bold' : key === 'i' ? 'italic' : 'link');}
        } else if (e.key === 'Tab') {e.preventDefault(); format(e.shiftKey ? 'outdent' : 'indent');}
        else if (e.key === 'Enter' && !e.shiftKey && e.currentTarget.selectionStart === e.currentTarget.selectionEnd) {const edit = continueList(value, e.currentTarget.selectionStart); if (edit) {e.preventDefault(); apply(edit);}}
      }}/>}
      {active && (preview || split) && <div className="note-live-preview" aria-label="笔记实时预览"><NotePreview key={assetRevision} content={value} token={token} notes={notes} onNote={onNote}/></div>}
    </div>
    <div className="note-editor-status"><span>Markdown</span><span>{value.length.toLocaleString()} 字符</span><details><summary>快捷键与帮助</summary><p>选中文字后点图标应用格式；悬停可看中文说明。Ctrl/Cmd+B 加粗、I 斜体、K 链接、S 保存、Z 撤销、Shift+M 编辑公式；列表回车续写，Tab 缩进，Esc 退出专注。把光标放在已有公式内，点 Σ 即可修改。</p></details></div>
    <NotesDialog className="formula-dialog" open={!!formula && !formulaSuspended} title="公式编辑器" onClose={() => setFormula(null)}>{formula && <FormulaEditor selection={formula.selection} stale={formula.base !== value} onCancel={() => setFormula(null)} onInsert={(source, display) => {if (formula.base !== value) return; setPreview(false); apply(insertFormula(value, formula.selection, source, display)); setFormula(null);}}/>}</NotesDialog>
  </div>;
}
