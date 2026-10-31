import {useEffect,useState,type CSSProperties} from "react";
import {Icon} from "../../components/Icon";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {useAppearance} from "./AppearanceProvider";
import {accentPresets,defaultAppearance,defaultTypography,FONT_SIZE_MAX,FONT_SIZE_MIN,FONT_SIZE_STEP,type Appearance,type TypographyPreference} from "./preferences";
function Options<K extends keyof Appearance>({title,field,options}:{title:string;field:K;options:{value:Appearance[K];label:string;description:string}[]}){
  const {value,update}=useAppearance();
  return <fieldset className="appearance-options"><legend>{title}</legend><div>{options.map(option=><label key={option.value} className={value[field]===option.value?"is-selected":""}><input type="radio" name={`appearance-${field}`} checked={value[field]===option.value} onChange={()=>update({...value,[field]:option.value})}/><span><strong>{option.label}</strong><small>{option.description}</small></span></label>)}</div></fieldset>;
}
function TypographyOptions<K extends keyof TypographyPreference>({title,field,options}:{title:string;field:K;options:{value:TypographyPreference[K];label:string;description:string}[]}){
  const {typography,updateTypography}=useAppearance();
  return <fieldset className="appearance-options"><legend>{title}</legend><div>{options.map(option=><label key={String(option.value)} className={typography[field]===option.value?"is-selected":""}><input type="radio" name={`typography-${field}`} checked={typography[field]===option.value} onChange={()=>updateTypography({...typography,[field]:option.value})}/><span><strong>{option.label}</strong><small>{option.description}</small></span></label>)}</div></fieldset>;
}
function TypographySize(){
  const {typography,updateTypography}=useAppearance();
  return <fieldset className="appearance-size-control"><legend>字体大小</legend><div className="appearance-size-row"><input type="range" aria-label="全站字体大小" min={FONT_SIZE_MIN} max={FONT_SIZE_MAX} step={FONT_SIZE_STEP} value={typography.size} onChange={event=>updateTypography({...typography,size:Number(event.target.value)})}/><output aria-live="polite">{typography.size}px</output></div><p>调整普通界面、标题、按钮和说明文字的基础字号；资料原件、代码、公式和阅读器字号独立保留。</p></fieldset>;
}
export default function AppearancePanel(){
  const {value,error,update,retry,typographyError,retryTypography,updateTypography}=useAppearance();
  const [open,setOpen]=useState(false),[custom,setCustom]=useState(value.customColor),[invalid,setInvalid]=useState("");
  useEffect(()=>setCustom(value.customColor),[value.customColor]);
  useEffect(()=>{const expire=()=>setOpen(false);window.addEventListener("hustudy:unauthorized",expire);return()=>window.removeEventListener("hustudy:unauthorized",expire);},[]);
  return <><button className="appearance-trigger secondary" aria-label="外观与布局" onClick={()=>setOpen(true)}><Icon name="palette" size={17}/><span>外观</span><i aria-hidden="true"/></button>
    <WorkspaceDialog open={open} title="外观与布局" className="appearance-dialog" onClose={()=>setOpen(false)}>
      <div className="appearance-intro"><span className="appearance-eyebrow">MAKE ROOM FOR YOUR MIND</span><h3>让学习空间，合你的心意。</h3><p>选择喜欢的色调、字体与留白，调整会立即应用，学习内容保持原位。</p></div>
      {error&&<p role="alert" className="appearance-error">{error}<button className="text-button" onClick={retry}>重试保存当前外观</button></p>}
      {typographyError&&<p role="alert" className="appearance-error">{typographyError}<button className="text-button" onClick={retryTypography}>重试保存字体设置</button></p>}
      <div className="appearance-layout"><div className="appearance-controls">
        <fieldset className="appearance-colors"><legend>主题色调</legend><p>全站卡片、导航、按钮与工具统一使用这一主色，以深浅区分层次。</p><div>{accentPresets.map(preset=><button key={preset.id} className={value.accent===preset.id?"is-selected":""} aria-pressed={value.accent===preset.id} onClick={()=>{setInvalid("");update({...value,accent:preset.id});}} style={{"--swatch":preset.color} as CSSProperties}><span className="appearance-swatch">{value.accent===preset.id&&<Icon name="check" size={16}/>}</span><span>{preset.name}</span></button>)}</div></fieldset>
        <form className="appearance-custom" onSubmit={event=>{event.preventDefault();if(!/^#[\da-f]{6}$/i.test(custom)){setInvalid("请输入完整的颜色值，例如 #6255C5");return;}setInvalid("");update({...value,accent:"custom",customColor:custom.toLowerCase()});}}>
          <label className="appearance-color-picker">自定色<input type="color" aria-label="选择自定主题色" value={value.customColor} onChange={event=>{setInvalid("");update({...value,accent:"custom",customColor:event.target.value});}}/></label>
          <label className="appearance-hex">颜色值<input aria-label="自定主题色值" value={custom} maxLength={7} spellCheck={false} onChange={event=>setCustom(event.target.value)}/></label><button className="secondary">应用自定色</button>
        </form>{invalid&&<p className="appearance-error" role="alert">{invalid}</p>}
        {value.accent==="custom"&&<p className="appearance-help">选定颜色用于点缀；按钮和文字会自动调整明暗，以保持可读。</p>}
        <TypographyOptions title="字体风格" field="font" options={[{value:"heiti",label:"黑体",description:"中文清晰利落，适合快速浏览"},{value:"songti",label:"宋体",description:"中文端正耐读，适合长文阅读"},{value:"kaiti",label:"楷体",description:"中文舒展有手稿感，适合思考"}]}/>
        <TypographySize/>
        <Options title="页面基调" field="surface" options={[{value:"cloud",label:"云白",description:"明亮、干净、轻盈"},{value:"paper",label:"暖纸",description:"温暖柔和的纸张底色"},{value:"mist",label:"柔雾",description:"清淡的灰青色背景"}]}/>
        <Options title="导航风格" field="navigation" options={[{value:"light",label:"浅色导航",description:"轻巧、融入工作台"},{value:"dark",label:"深色导航",description:"沉稳、清晰分区"}]}/>
        <Options title="界面密度" field="density" options={[{value:"comfortable",label:"舒适留白",description:"更从容地阅读和浏览"},{value:"compact",label:"紧凑排列",description:"在同屏放下更多信息"}]}/>
        <Options title="内容宽度" field="width" options={[{value:"wide",label:"舒展布局",description:"充分利用大屏空间"},{value:"focused",label:"聚焦布局",description:"收拢内容，视线更集中"}]}/>
    </div><aside className="appearance-preview" aria-label="当前外观预览"><span className="appearance-eyebrow">YOUR STUDY SPACE</span><div className="appearance-preview-window" aria-hidden="true"><div className="appearance-preview-rail"><span>H</span><i/><i/><i/><i/></div><div className="appearance-preview-page"><span className="appearance-preview-topline"/><div className="appearance-preview-hero"><small>每一步，都连着理解</small><strong>留一点空间，<br/>给新的想法。</strong><span className="appearance-preview-action">继续学习 <Icon name="arrow" size={12}/></span></div><div className="appearance-preview-cards"><span><Icon name="file"/><i/><i/></span><span><Icon name="notes"/><i/><i/></span></div><div className="appearance-preview-lines"><i/><i/><i/></div></div></div><h4>属于你的学习节奏</h4><p>清晰的层级，适度的留白。<br/>让资料、理解与练习自然连接。</p><div className="appearance-preview-status"><span/>即刻应用 · 仅当前浏览器</div><p className="appearance-help">偏好不会随账户备份或跨设备同步。原件、图片和资料阅读字号保持原样。</p></aside></div><footer className="appearance-footer"><p>仅此浏览器 · 即刻应用，不改变学习内容</p><div><button className="secondary" onClick={()=>{setInvalid("");update({...defaultAppearance});updateTypography({...defaultTypography});}}>恢复默认外观</button><button className="primary" onClick={()=>setOpen(false)}>完成设置</button></div></footer>
    </WorkspaceDialog></>;
}
