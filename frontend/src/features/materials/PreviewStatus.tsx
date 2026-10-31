import {useEffect,useRef,useState} from 'react';
import {api, type PreviewCapabilities, type Version} from '../../api/client';
import {Icon} from '../../components/Icon';

export function PreviewStatus({token,version,openFailed,onQueued,onError,onNotice}:{token:string;version:Version;openFailed?:boolean;onQueued:()=>Promise<unknown>;onError:(reason:unknown)=>void;onNotice:(message:string)=>void}) {
  const [capability,setCapability]=useState<PreviewCapabilities>();
  const [checking,setChecking]=useState(false),[busy,setBusy]=useState(false),[failed,setFailed]=useState(false);
  const active=useRef(true);
  const office=/\.(pptx|docx)$/i.test(version.original_filename);
  const supported=office || /\.pdf$/i.test(version.original_filename);
  const pending=['QUEUED','RUNNING'].includes(version.preview_status);
  const nativeOnly=office && ['TEXT_ONLY','PENDING'].includes(version.preview_status);
  const check=async()=>{
    setChecking(true);
    try {const data=await api.materialCapabilities(token);if(active.current){setCapability(data);setFailed(false);}}
    catch(reason){if(active.current){setFailed(true);onError(reason);}}
    finally{if(active.current)setChecking(false);}
  };
  useEffect(()=>{active.current=true;if(office)void check();return()=>{active.current=false;};},[token,office]);
  const retry=async()=>{
    if(busy)return;setBusy(true);
    try {await api.requestPreview(token,version.id);if(active.current){await onQueued();onNotice('预览任务已入队，无需重新上传；完成后可打开兼容 PDF 预览；原格式预览可直接使用');}}
    catch(reason){if(active.current)onError(reason);}
    finally{if(active.current)setBusy(false);}
  };
  if(!supported)return <p className="hint">该资料采用文本阅读；PDF、PPTX、DOCX可按原页预览。</p>;
  if(version.preview_status==='SUCCEEDED'&&!openFailed)return <p className="hint">{office?'可直接打开原格式预览；兼容 PDF 仅在需要按页核对或截图时按需生成。':'原始PDF已就绪，可打开“PDF 预览”；扫描页也可查看。'}</p>;
  return <section className="preview-recovery" aria-label="预览诊断与恢复">
    <div className="preview-recovery-heading"><Icon name="preview"/><strong>{office?'兼容预览诊断':'原始PDF预览'}</strong></div>
    <p>{pending?'预览任务尚未完成，状态会自动更新；原格式与文本阅读不受影响。':nativeOnly?'原格式预览已可用；尚未生成兼容 PDF，只有在需要按页核对或截图时才需生成。':version.preview_error || '当前尚无可用预览，可以检查环境后重试。'}</p>
    {office && <p className="hint">{checking?'正在检查本机转换环境…':capability?.message || (failed?'环境检查失败，可点击重新检查。':'尚未检测转换器。')}</p>}
    <div className="preview-recovery-actions">
      {office && <button className="secondary" disabled={checking||busy} onClick={()=>void check()}><Icon name="refresh" size={15}/>重新检查环境</button>}
      {!pending && <button className="secondary" disabled={busy||checking||(office&&!capability?.office_available)} onClick={()=>void retry()}><Icon name="refresh" size={15}/>{busy?'正在提交…':version.preview_status==='CANCELLED'?'恢复预览':nativeOnly?'生成兼容 PDF':'重试预览'}</button>}
      {office && capability && !capability.office_available && <a className="link-button" href={capability.installation_url} target="_blank" rel="noreferrer">LibreOffice 官方下载 ↗</a>}
    </div>
    {!pending && <small>重试沿用原任务次数上限。也可在本机将课件另存为PDF，再导入资料库。</small>}
  </section>;
}
