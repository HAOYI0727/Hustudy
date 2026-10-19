import {useEffect, useRef, useState} from 'react';

// Web Speech types are not included in every TypeScript DOM version.
type SpeechResult = {isFinal: boolean; 0: {transcript: string}};
type Recognition = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: {results: ArrayLike<SpeechResult>}) => void) | null;
  onerror: ((event: {error: string}) => void) | null;
  onend: (() => void) | null;
  start: () => void; stop: () => void; abort: () => void;
};
type SpeechWindow = Window & {SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition};
const messages: Record<string, string> = {
  'not-allowed': '麦克风权限被拒绝。请在浏览器地址栏允许麦克风，然后重新开始。',
  'service-not-allowed': '浏览器语音服务不可用，请尝试其他支持语音识别的浏览器。',
  'audio-capture': '未找到可用麦克风，请检查连接或是否被其他程序占用。',
  network: '无法连接浏览器的语音识别服务，请检查网络。已识别文字保留，可编辑后插入。',
  'no-speech': '没有听到清晰语音，请靠近麦克风后重新开始。',
  'language-not-supported': '此浏览器语音服务不支持所选语言，请切换语言。',
};

export function SpeechInput({open, disabled, onInsert}: {open: boolean; disabled: boolean; onInsert: (text: string) => boolean}) {
  const [text, setText] = useState(''), [interim, setInterim] = useState('');
  const [active, setActive] = useState(false), [status, setStatus] = useState('点击开始后说话，文字会实时显示。');
  const [error, setError] = useState(''), [lang, setLang] = useState('zh-CN'), [consent, setConsent] = useState(false);
  const recognition = useRef<Recognition | null>(null), timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const currentText = useRef(text); currentText.current = text;
  const Constructor = (window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition;
  const stop = () => {if (recognition.current) {setStatus('正在完成最后一句…'); recognition.current.stop();}};
  const release = () => {
    clearTimeout(timer.current);
    const session = recognition.current; recognition.current = null;
    if (session) {session.onresult = null; session.onerror = null; session.onend = null; session.abort();}
  };
  useEffect(() => {if (!open) {release(); setActive(false); setInterim('');} return release;}, [open]);
  useEffect(() => {
    const leave = (event: Event) => {if (active || (currentText.current.trim() && !window.confirm('语音文字尚未插入正文，确定离开并放弃吗？'))) event.preventDefault();};
    const unload = (event: BeforeUnloadEvent) => {if (active || currentText.current.trim()) {event.preventDefault(); event.returnValue = '';}};
    window.addEventListener('hustudy:before-navigate', leave); window.addEventListener('hustudy:before-material-change', leave); window.addEventListener('beforeunload', unload);
    return () => {window.removeEventListener('hustudy:before-navigate', leave); window.removeEventListener('hustudy:before-material-change', leave); window.removeEventListener('beforeunload', unload);};
  }, [active]);
  const start = () => {
    if (!Constructor || disabled || !consent || recognition.current) return;
    setError(''); setInterim(''); setActive(true); setStatus('正在听写…');
    const session = new Constructor(), prefix = text ? text + '\n' : '';
    recognition.current = session; session.lang = lang; session.continuous = true; session.interimResults = true;
    session.onresult = event => {
      if (recognition.current !== session) return;
      let final = '', pending = '';
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) final += result[0].transcript; else pending += result[0].transcript;
      }
      // Rebuild this session's result list: browsers can update the same result repeatedly.
      setText(prefix + final); setInterim(pending);
      if (prefix.length + final.length + pending.length > 30000) {setError('本次语音输入已达3万字，请先插入正文。'); session.stop();}
    };
    session.onerror = event => {if (recognition.current === session && event.error !== 'aborted') setError(messages[event.error] || '语音识别失败，已识别文字保留，请重试。');};
    session.onend = () => {
      if (recognition.current !== session) return;
      clearTimeout(timer.current); recognition.current = null; setActive(false); setInterim(''); setStatus('听写已停止。可以修改文字、继续听写或插入正文。');
    };
    try {session.start(); timer.current = setTimeout(() => session.stop(), 300000);}
    catch {release(); setActive(false); setError('无法启动语音服务，请检查麦克风权限或更换浏览器。');}
  };
  return <section className="note-speech-input">
    <p>说话时在这里实时转成文字，核对后插入笔记光标处。每次最长5分钟。</p>
    {!Constructor && <p role="alert">当前浏览器不支持网页语音识别。可换用支持此功能的浏览器，或在正文框使用系统的语音输入。</p>}
    <p className="hint">语音由浏览器提供的服务识别，浏览器可能将音频发送到其在线服务；这不使用智谱API，也不保证离线可用。</p>
    <label className="speech-consent"><input type="checkbox" checked={consent} disabled={active} onChange={event => setConsent(event.target.checked)}/>允许本次使用浏览器语音服务</label>
    <div className="note-folder-actions"><label>听写语言<select aria-label="听写语言" value={lang} disabled={active} onChange={event => setLang(event.target.value)}><option value="zh-CN">普通话</option><option value="en-US">英语</option></select></label>
      <button className="primary" disabled={!Constructor || disabled || !consent} onClick={active ? stop : start}>{active ? '停止语音输入' : '开始语音输入'}</button>
    </div>
    <p role="status">{status}</p>{error && <p role="alert">{error}</p>}
    {interim && <p className="speech-interim" aria-label="正在识别">{interim}</p>}
    <label>语音文字<textarea aria-label="语音识别文字" rows={9} value={text} disabled={active} onChange={event => setText(event.target.value)}/></label>
    <div className="note-folder-actions"><button className="primary" disabled={active || disabled || !text.trim()} onClick={() => {if (onInsert(text.trim())) {setText(''); setInterim('');}}}>插入正文</button><button disabled={active || !text} onClick={() => {if (window.confirm('清空本次语音文字？')) setText('');}}>清空文字</button></div>
    <p className="hint">关闭窗口会停止听写，已识别文字保留。临时识别中的文字需等待确认后才能插入。</p>
  </section>;
}
