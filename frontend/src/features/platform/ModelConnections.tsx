import {useEffect,useRef,useState} from 'react';
import {api,type ModelConnections as Connections,type ModelProfile} from '../../api/client';
import {sessionPartition} from '../../api/query';
import {NotesDialog} from '../notes/NotesDialog';
import './model-connections.css';

function announce(token:string){window.dispatchEvent(new CustomEvent('hustudy:model-changed',{detail:sessionPartition(token)}));}
export type ModelProbe = {
  partition: string;
  revision: number;
  profileId: string;
  connected: boolean;
  message: string;
  testedAt: string;
};
export function useConnections(token:string,onError:(error:unknown)=>void){
  const [data,setData]=useState<Connections|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const owner=useRef(token),callbacks=useRef(onError),epoch=useRef(0),loadSerial=useRef(0);owner.current=token;callbacks.current=onError;
  useEffect(()=>{let live=true;epoch.current++;setData(null);setError('');setBusy(false);
    const load=()=>{const serial=++loadSerial.current;void api.modelConnections(token).then(value=>{if(!value.builtin||!Array.isArray(value.profiles))throw new Error("模型配置响应无法核对，请刷新重试");if(live&&serial===loadSerial.current)setData(value);}).catch(e=>{if(live&&serial===loadSerial.current){setError(e instanceof Error?e.message:'模型列表读取失败');callbacks.current(e);}});};
    const changed=(event:Event)=>{if((event as CustomEvent).detail===sessionPartition(token))load();};
    load();window.addEventListener('hustudy:model-changed',changed);return()=>{live=false;epoch.current++;loadSerial.current++;window.removeEventListener('hustudy:model-changed',changed);};
  },[token]);
  const run=async(work:()=>Promise<Connections>,after?:()=>void)=>{if(busy)return;const current=epoch.current;const live=()=>owner.current===token&&current===epoch.current;loadSerial.current++;setBusy(true);setError('');try{const next=await work();if(!live())return;setData(next);after?.();announce(token);}catch(e){if(live()){setError(e instanceof Error?e.message:'配置未完成');callbacks.current(e);}}finally{if(live())setBusy(false);}};
  return {data,busy,error,run};
}

export function ModelControl({token,onError,disabled=false}:{token:string;onError:(error:unknown)=>void;disabled?:boolean}){
  const {data,busy,error,run}=useConnections(token,onError),[open,setOpen]=useState(false);
  useEffect(()=>{const expired=(e:Event)=>{if((e as CustomEvent).detail===sessionPartition(token))setOpen(false);};window.addEventListener('hustudy:unauthorized',expired);return()=>window.removeEventListener('hustudy:unauthorized',expired);},[token]);
  return <div className="model-control"><label>AI模型<select aria-label="当前AI模型" value={data?.active||''} disabled={disabled||busy||!data} onChange={e=>{const id=e.target.value;void run(()=>api.selectModelConnection(token,data!.revision,id||null));}}>
    <option value="">{data?`智谱 · ${data.builtin.model}${data.builtin.configured?'':'（未配置）'}`:'正在读取模型…'}</option>{data?.profiles.map(p=><option key={p.id} value={p.id} disabled={!p.configured}>{p.name} · {p.model}</option>)}</select></label><button className="secondary" disabled={disabled||busy} onClick={()=>setOpen(true)}>配置更多模型</button>
    {error&&<span role="alert" className="hint">{error}</span>}
    <NotesDialog open={open} title="模型接入与选择" className="model-settings-dialog" onClose={()=>{if(window.dispatchEvent(new Event('hustudy:before-material-change',{cancelable:true})))setOpen(false);}}>{open&&<ModelSettings token={token} onError={onError}/>}</NotesDialog>
  </div>;
}

const fresh={name:'DeepSeek',vendor:'deepseek' as 'deepseek'|'compatible',endpoint:'https://api.deepseek.com/chat/completions',model:'deepseek-flash',vision:false,thinking:false,json_mode:true};
export function ModelSettings({token,onError}:{token:string;onError:(error:unknown)=>void}){
  const {data,busy,error,run}=useConnections(token,onError);
  const [form,setForm]=useState({...fresh}),[editing,setEditing]=useState<string>(),[key,setKey]=useState(''),[dirty,setDirty]=useState(false),[consent,setConsent]=useState(false),[probing,setProbing]=useState(false),[message,setMessage]=useState('');
  const active=data?.profiles.find(p=>p.id===data.active);
  const probeEpoch=useRef(0);
  useEffect(()=>{probeEpoch.current++;setProbing(false);setConsent(false);return()=>{probeEpoch.current++;};},[token,data?.revision,data?.active]);
  const reset=()=>{setEditing(undefined);setForm({...fresh});setKey('');setDirty(false);setConsent(false);};
  useEffect(()=>{const guard=(e:Event)=>{if(busy||probing||dirty&&!window.confirm('模型配置尚未保存，确认放弃本次修改？'))e.preventDefault();};window.addEventListener('hustudy:before-navigate',guard);window.addEventListener('hustudy:before-material-change',guard);return()=>{window.removeEventListener('hustudy:before-navigate',guard);window.removeEventListener('hustudy:before-material-change',guard);};},[dirty,busy,probing]);
  const edit=(profile:ModelProfile)=>{if(dirty&&!window.confirm('放弃未保存的模型配置修改？'))return;setEditing(profile.id);setForm({name:profile.name,vendor:profile.vendor,model:profile.model,endpoint:profile.endpoint,vision:profile.vision,thinking:profile.thinking,json_mode:profile.json_mode});setKey('');setDirty(false);setMessage('');};
  const update=(change:Partial<typeof fresh>)=>{setForm(v=>({...v,...change}));setDirty(true);setConsent(false);};
  return <section className="model-settings" aria-label="高级模型接入">
    <h3>其他模型与兼容接口</h3><p>原智谱页面继续保留。这里可保存多份模型配置，并为笔记、AI学习和题库选择当前模型。切换后请重新核对发送预览。</p>
    {error&&<p role="alert">{error}<button className="text-button" onClick={()=>announce(token)}>刷新模型列表</button></p>}
    <div className="model-profile-list"><article><div><strong>原智谱配置</strong><p>{data?.builtin.model} · {data?.builtin.configured?'已配置':'请在原智谱页面保存密钥'}</p></div><button className="secondary" disabled={busy||!data||!data.active} onClick={()=>void run(()=>api.selectModelConnection(token,data!.revision,null))}>{!data?.active?'正在使用':'使用智谱'}</button></article>
    {data?.profiles.map(p=><article key={p.id}><div><strong>{p.name}{data.active===p.id?' · 正在使用':''}</strong><p>{p.model} · {p.vision?'支持图片':'文字'}{p.thinking?' · 深度思考':''}</p><small>{p.endpoint}</small></div><div><button className="secondary" disabled={busy||data.active===p.id} onClick={()=>void run(()=>api.selectModelConnection(token,data.revision,p.id))}>使用此模型</button><button className="text-button" disabled={busy} onClick={()=>edit(p)}>编辑配置</button><button className="text-button" disabled={busy||data.active===p.id} onClick={()=>{if(window.confirm(`删除“${p.name}”的模型配置？`))void run(()=>api.removeModelConnection(token,data.revision,p.id),()=>{if(editing===p.id)reset();});}}>删除配置</button></div></article>)}</div>
    <form onSubmit={e=>{e.preventDefault();if(!data)return;void run(()=>api.saveModelConnection(token,{...form,revision:data.revision,...(editing?{id:editing}:{}),...(key.trim()?{key:key.trim()}:{})}),()=>{reset();setMessage('模型配置已保存。可点击“使用此模型”后测试连接。');});}}>
      <h4>{editing?'编辑模型配置':'新增模型配置'}</h4><fieldset disabled={busy||probing||!data}>
      <div className="model-form-grid"><label>接口类型<select aria-label="模型接口类型" value={form.vendor} onChange={e=>update(e.target.value==='deepseek'?{...fresh}:{vendor:'compatible',name:'兼容模型',endpoint:'',model:'',thinking:false})}><option value="deepseek">DeepSeek 官方</option><option value="compatible">Chat Completions 兼容接口</option></select></label>
      <label>配置名称<input aria-label="模型配置名称" maxLength={60} required value={form.name} onChange={e=>update({name:e.target.value})}/></label>
      <label>模型 ID<input aria-label="模型ID" maxLength={128} required value={form.model} list="known-note-ai-models" onChange={e=>update({model:e.target.value})}/><datalist id="known-note-ai-models"><option value="deepseek-flash"/><option value="deepseek-v4-pro"/></datalist></label>
      <label>API Key<input type="password" aria-label="其他模型API Key" autoComplete="off" value={key} maxLength={512} required={!editing} placeholder={editing?'留空保留这份配置的原密钥':'粘贴此服务商的密钥'} onChange={e=>{setKey(e.target.value);setDirty(true);}}/></label></div>
      <label>完整接口地址<input type="url" aria-label="模型接口地址" required maxLength={500} value={form.endpoint} placeholder="https://服务商/chat/completions" onChange={e=>update({endpoint:e.target.value})}/></label>
      <p className="hint">兼容JSON对话接口；需填写服务商实际模型ID。允许主机：{data?.allowed_hosts.join('、')}。其他部署地址由管理员授权后使用。</p>
      <div className="model-options"><label><input type="checkbox" checked={form.vision} onChange={e=>update({vision:e.target.checked})}/>模型支持图片输入</label><label><input type="checkbox" checked={form.thinking} disabled={form.vendor!=='deepseek'} onChange={e=>update({thinking:e.target.checked})}/>DeepSeek深度思考</label><label><input type="checkbox" checked={form.json_mode} onChange={e=>update({json_mode:e.target.checked})}/>接口支持JSON输出参数</label></div>
      <p className="hint">图片能力需与所填模型一致；未启用时拒绝图片调用。模型可能按量计费，额度以服务商为准。密钥仅在后端按账户加密保存，不回显或导出。</p>
      <div className="model-actions"><button className="primary" type="submit">保存其他模型配置</button>{editing&&<button className="secondary" type="button" onClick={reset}>取消编辑</button>}</div></fieldset>
    </form>
    <section><h4>测试当前所选模型</h4><p>{active?`${active.name} · ${active.model}`:`原智谱 · ${data?.builtin.model||''}`}</p><p className="hint">测试使用当前所选模型已保存的配置。</p><label className="model-consent"><input type="checkbox" checked={consent} disabled={busy||probing} onChange={e=>setConsent(e.target.checked)}/>同意发送极短“连接测试”文本，可能消耗少量额度，不发送课程或笔记。</label><button className="secondary" disabled={!data||busy||probing||!consent} onClick={async()=>{if(!data)return;const current=probeEpoch.current;setProbing(true);setMessage('');try{const result=await api.testModelConnection(token,data.revision,data.active);if(current===probeEpoch.current){
      setMessage((result.connected?'连接成功：':'连接未通过：')+result.message);
      if(data.active){
        const detail:ModelProbe={partition:sessionPartition(token),revision:data.revision,profileId:data.active,connected:result.connected,message:result.message,testedAt:new Date().toISOString()};
        window.dispatchEvent(new CustomEvent('hustudy:model-probed',{detail}));
      }
    }}catch(e){if(current===probeEpoch.current){setMessage(e instanceof Error?e.message:'测试未完成');onError(e);}}finally{if(current===probeEpoch.current){setProbing(false);setConsent(false);}}}}>{probing?'正在测试…':'测试所选模型'}</button></section>
    {message&&<p role="status">{message}</p>}
  </section>;
}
