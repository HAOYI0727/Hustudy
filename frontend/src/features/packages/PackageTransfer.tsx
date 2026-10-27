import {useEffect, useRef, useState} from 'react';
import {api,ApiError,type Course,type NoteFolder,type PackageCatalog,type PackageImportRequest,type PackageImportResult,type PackageKind,type PackagePreview,type PackageScope,type PackageSelection,type PackageSelectionPreview} from '../../api/client';
import {sessionPartition} from '../../api/query';
import {WorkspaceDialog} from '../../components/WorkspaceDialog';
import {folderOptions} from '../notes/organization';
import {PackagePicker} from './PackagePicker';
import {PackageFinalItems} from './PackageFinalItems';
import {PackagePreviewManager} from './PackagePreviewManager';
import {freezePackageSelection,PACKAGE_CATEGORIES,PACKAGE_MAX_BYTES,PACKAGE_SELECTION_LIMIT,packageSelection,safePackageFilename,selectedPackageCount} from './packageSelection';
import {readPendingPackage,savePendingPackage} from './packagePending';
import {packageDestination} from './packageDestination';
import './packages.css';

export type PackageIntent={mode:'import'|'export';kind:PackageKind;courseId?:string;folderId?:string;nonce:number};
type Props={token:string;intent:PackageIntent|null;disabled?:boolean;courses?:Course[];onClose:()=>void;onChanged:(result:PackageImportResult)=>Promise<void>;onNotice:(message:string)=>void;onError:(error:unknown)=>void;beforeCommit?:()=>boolean;samples?:{label:string;href:string;filename:string}[]};
type Operation='catalog'|'file'|'review'|'export'|'import'|'status';
type Review={data:PackageSelectionPreview;selection:PackageSelection;targetCourse:string;parentFolder:string;title:string;mergeCourse:boolean};
const countLabels:Record<string,string>={...Object.fromEntries(PACKAGE_CATEGORIES.map(item=>[item.key,item.label])),document_versions:'资料版本',versions:'资料版本',document_chunks:'原文片段',chunks:'原文片段',citations:'资料引用',note_links:'笔记双链',exam_attempts:'作答记录',mistakes:'错题',review_tasks:'复习任务',manual_transcripts:'人工补录'};
function Counts({counts}:{counts:Record<string,number>}) {return <div className="package-counts">{Object.entries(counts).filter(([key,value])=>value>0&&countLabels[key]).map(([key,value])=><span key={key}>{countLabels[key]} <strong>{value}</strong></span>)}</div>;}
function Warnings({warnings}:{warnings:string[]}) {return warnings.length?<div className="package-warnings"><strong>范围说明</strong><ul>{warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul></div>:null;}

export default function PackageTransfer({token,intent,disabled=false,courses:providedCourses,onClose,onChanged,onNotice,onError,beforeCommit,samples=[]}:Props) {
  const [current,setCurrent]=useState<PackageIntent|null>(null),[catalog,setCatalog]=useState<PackageCatalog|null>(null),[uploaded,setUploaded]=useState<PackagePreview|null>(null);
  const [selection,setSelection]=useState<PackageSelection>({}),[review,setReview]=useState<Review|null>(null),[file,setFile]=useState<File|null>(null);
  const [courseRows,setCourseRows]=useState<Course[]>(providedCourses||[]),[folderRows,setFolderRows]=useState<NoteFolder[]>([]);
  const [targetCourse,setTargetCourse]=useState(''),[parentFolder,setParentFolder]=useState(''),[title,setTitle]=useState('');
  const [mergeCourse,setMergeCourse]=useState(false);
  const [managerBusy,setManagerBusy]=useState(false);
  const [operation,setOperation]=useState<Operation|null>(null),[error,setError]=useState(''),[paused,setPaused]=useState(false),[unknown,setUnknown]=useState(false),[notFound,setNotFound]=useState(false);
  const [frozen,setFrozen]=useState<PackageImportRequest|null>(null),[result,setResult]=useState<PackageImportResult|null>(null),[downloaded,setDownloaded]=useState(false);
  const [owner,setOwner]=useState(''),[checkingOwner,setCheckingOwner]=useState(true),[ownerRevision,setOwnerRevision]=useState(0),[storageWarning,setStorageWarning]=useState('');
  const ownerRef=useRef(''),uploadedRef=useRef<PackagePreview|null>(null),pausedRef=useRef(false);
  const frozenRef=useRef<PackageImportRequest|null>(null),operationRef=useRef<Operation|null>(null),serial=useRef(0),active=useRef<{controller:AbortController;timer:number}|null>(null),input=useRef<HTMLInputElement>(null);
  const callbacks=useRef({onClose,onChanged,onNotice,onError,beforeCommit});callbacks.current={onClose,onChanged,onNotice,onError,beforeCommit};
  const open=!!intent,mode=current?.mode||intent?.mode||'import',kind=catalog?.kind||current?.kind||'course';
  const committing=operation==='import'||operation==='export',locked=!!operation||managerBusy||!!frozen||paused||checkingOwner||!owner;
  const setSessionPaused=(value:boolean)=>{pausedRef.current=value;setPaused(value);};
  const cancel=()=>{serial.current++;if(active.current){active.current.controller.abort();window.clearTimeout(active.current.timer);active.current=null;}operationRef.current=null;setOperation(null);};
  const begin=(next:Operation)=>{cancel();const controller=new AbortController(),id=serial.current;active.current={controller,timer:window.setTimeout(()=>controller.abort(),120000)};operationRef.current=next;setOperation(next);setError('');return {id,signal:controller.signal};};
  const live=(id:number)=>serial.current===id;
  const finish=(id:number)=>{if(!live(id))return;if(active.current)window.clearTimeout(active.current.timer);active.current=null;operationRef.current=null;setOperation(null);};
  const failure=(reason:unknown)=>{const message=reason instanceof Error?reason.message:'操作未完成，请重试。';setError(message);if(reason instanceof ApiError&&reason.status===401)callbacks.current.onError(reason);};
  const setPending=(value:PackageImportRequest|null)=>{frozenRef.current=value;setFrozen(value);if(!savePendingPackage(ownerRef.current,value))setStorageWarning('浏览器无法保存请求标识。请保持本页打开，核对导入结果后再刷新。');};
  const scope=(source=current):PackageScope=>({course_id:source?.courseId||'',kind:source?.kind||'course',...(source?.folderId?{folder_id:source.folderId}:{})});
  const loadCatalog=async(source:PackageIntent)=>{
    const task=begin('catalog');
    try{const next=await api.packageCatalog(token,scope(source),task.signal);if(!live(task.id))return;setCatalog(next);setSelection(packageSelection(next.items));setTitle(next.title);}
    catch(reason){if(live(task.id))failure(reason);}finally{finish(task.id);}
  };
  const reset=(source:PackageIntent)=>{cancel();setCurrent(source);setCatalog(null);setUploaded(null);setSelection({});setReview(null);setFile(null);setError('');setResult(null);setDownloaded(false);setSessionPaused(false);setUnknown(false);setNotFound(false);setTargetCourse(source.courseId||'');setParentFolder(source.folderId||'');setFolderRows([]);setTitle('');setMergeCourse(false);if(input.current)input.current.value='';if(source.mode==='export')void loadCatalog(source);};
  useEffect(()=>{if(!intent||checkingOwner||!owner)return;setSessionPaused(false);if(frozenRef.current){setCurrent(source=>({...source,...intent,mode:'import'}));return;}reset(intent);},[intent?.nonce,checkingOwner,owner]);
  useEffect(()=>{if(!open){cancel();}return()=>{};},[open]);
  useEffect(()=>()=>{serial.current++;active.current?.controller.abort();if(active.current)window.clearTimeout(active.current.timer);},[]);
  useEffect(()=>{
    let valid=true;setCheckingOwner(true);setOwner('');cancel();
    void api.me(token).then(user=>{
      if(!valid)return;
      if(ownerRef.current&&ownerRef.current!==user.id){frozenRef.current=null;setFrozen(null);setCatalog(null);setUploaded(null);uploadedRef.current=null;setResult(null);setReview(null);setFile(null);setSelection({});}
      ownerRef.current=user.id;setOwner(user.id);
      if(!frozenRef.current){const restored=readPendingPackage(user.id);if(restored){frozenRef.current=restored;setFrozen(restored);setUnknown(true);setNotFound(false);}}
      setCheckingOwner(false);
    }).catch(reason=>{if(valid){setError('暂时无法核对当前账户，请关闭窗口后重试。');callbacks.current.onError(reason);setCheckingOwner(false);}});
    return()=>{valid=false;};
  },[token,ownerRevision]);
  useEffect(()=>{
    const unauthorized=(event:Event)=>{if((event as CustomEvent).detail!==sessionPartition(token))return;if(frozenRef.current){setUnknown(true);setNotFound(false);}cancel();setSessionPaused(true);callbacks.current.onClose();};
    window.addEventListener('hustudy:unauthorized',unauthorized);return()=>window.removeEventListener('hustudy:unauthorized',unauthorized);
  },[token]);
  useEffect(()=>{
    const guard=(event:Event)=>{if(pausedRef.current)return;if(operationRef.current==='import'||frozenRef.current){event.preventDefault();setError('请先在标准包窗口核对本次导入结果，再切换工作区。');}};
    const unload=(event:BeforeUnloadEvent)=>{if(pausedRef.current)return;if(operationRef.current==='import'||frozenRef.current){event.preventDefault();event.returnValue='';}};
    window.addEventListener('hustudy:before-navigate',guard);window.addEventListener('beforeunload',unload);return()=>{window.removeEventListener('hustudy:before-navigate',guard);window.removeEventListener('beforeunload',unload);};
  },[]);
  useEffect(()=>{if(providedCourses)setCourseRows(providedCourses);},[providedCourses]);
  useEffect(()=>{
    if(!open||mode!=='import'||!catalog||(catalog.kind!=='folder'&&!mergeCourse)||paused||checkingOwner||!owner)return;
    let valid=true;
    if(providedCourses){if(!targetCourse&&providedCourses[0])setTargetCourse(providedCourses[0].id);return;}
    void api.courses(token).then(rows=>{if(!valid)return;setCourseRows(rows);if(!targetCourse&&rows[0])setTargetCourse(rows[0].id);}).catch(reason=>{if(valid)failure(reason);});
    return()=>{valid=false;};
  },[open,mode,catalog?.kind,mergeCourse,token,paused,providedCourses,checkingOwner,owner]);
  useEffect(()=>{
    if(!open||mode!=='import'||catalog?.kind!=='folder'||!targetCourse||paused)return;
    let valid=true;setFolderRows([]);
    void api.noteFolders(token,targetCourse).then(rows=>{if(valid)setFolderRows(rows);}).catch(reason=>{if(valid)failure(reason);});
    return()=>{valid=false;};
  },[open,mode,catalog?.kind,targetCourse,token,paused]);
  const inspect=async(picked:File)=>{
    if(locked)return;if(!/\.zip$/i.test(picked.name)||!picked.size||picked.size>PACKAGE_MAX_BYTES){setError('请选择非空、最多100 MiB的标准 ZIP 数据包。');return;}
    setFile(picked);setCatalog(null);setUploaded(null);setReview(null);setResult(null);setDownloaded(false);
    const task=begin('file');
    try{if(uploadedRef.current){try{await api.removePackagePreview(token,uploadedRef.current.preview_id,task.signal);}catch(reason){if(!(reason instanceof ApiError&&reason.status===404))throw reason;}if(!live(task.id))return;uploadedRef.current=null;}const next=await api.previewPackage(token,picked,task.signal);if(!live(task.id))return;uploadedRef.current=next;setUploaded(next);setCatalog(next);setSelection(packageSelection(next.items));setTitle(next.title);}
    catch(reason){if(live(task.id))failure(reason);}finally{finish(task.id);}
  };
  const discardPreview=async()=>{
    if(frozenRef.current||operationRef.current)return;
    const task=begin('file');
    try{if(uploadedRef.current){try{await api.removePackagePreview(token,uploadedRef.current.preview_id,task.signal);}catch(reason){if(!(reason instanceof ApiError&&reason.status===404))throw reason;}}if(!live(task.id))return;uploadedRef.current=null;setUploaded(null);setCatalog(null);setFile(null);setReview(null);setResult(null);setSelection({});if(input.current)input.current.value='';}
    catch(reason){if(live(task.id))failure(reason);}finally{finish(task.id);}
  };
  const changeSelection=(next:PackageSelection)=>{setSelection(next);setReview(null);setDownloaded(false);};
  const preview=async()=>{
    if(locked||!catalog||!current)return;
    if(mode==='import'&&kind==='course'&&!mergeCourse&&!title.trim()){setError('请填写新课程名称。');return;}
    if(mode==='import'&&(kind==='folder'||mergeCourse)&&!targetCourse){setError('请先创建或选择接收笔记包的课程。');return;}
    if(selectedPackageCount(selection)>PACKAGE_SELECTION_LIMIT){setError('每次最多选择3000项，请缩小范围后预览。');return;}
    const chosen=freezePackageSelection(selection),task=begin('review');setReview(null);setDownloaded(false);
    try{const data=await api.previewPackageSelection(token,{...(mode==='import'?{preview_id:uploaded!.preview_id,...packageDestination(kind,mergeCourse,title,targetCourse,parentFolder)}:scope()),selection:chosen},task.signal);if(!live(task.id))return;setReview({data,selection:chosen,targetCourse,parentFolder,title:title.trim(),mergeCourse});}
    catch(reason){if(live(task.id))failure(reason);}finally{finish(task.id);}
  };
  const complete=async(next:PackageImportResult)=>{
    setResult(next);setPending(null);setUnknown(false);setNotFound(false);callbacks.current.onNotice('标准包已导入，原有数据保留。');
    try{await callbacks.current.onChanged(next);}catch{setError('导入已完成，但列表刷新失败。请稍后刷新课程或笔记列表，无需再次导入。');}
  };
  const sendImport=async(payload:PackageImportRequest)=>{
    if(disabled||managerBusy||paused||checkingOwner||!ownerRef.current||operationRef.current||callbacks.current.beforeCommit?.()===false)return;
    setPending(payload);setUnknown(false);setNotFound(false);const task=begin('import');
    try{const next=await api.importPackage(token,payload,task.signal);if(live(task.id))await complete(next);}
    catch(reason){if(!live(task.id))return;if(reason instanceof ApiError&&reason.code==='PACKAGE_SELECTION_CHANGED'){setPending(null);setReview(null);failure(reason);return;}const uncertain=!(reason instanceof ApiError)||reason.status===0||reason.status===401||reason.status===409||reason.status===429||reason.status>=500;if(uncertain)setUnknown(true);else setPending(null);failure(reason);}
    finally{finish(task.id);}
  };
  const confirm=async()=>{
    if(!review||!current||disabled||locked)return;
    if(!/^[0-9a-f]{64}$/.test(review.data.selection_sha256)){setError('范围校验信息缺失，请重新预览后确认。');setReview(null);return;}
    if(mode==='import'){
      const payload:PackageImportRequest={preview_id:uploaded!.preview_id,request_id:crypto.randomUUID(),selection:freezePackageSelection(review.selection),expected_sha256:review.data.selection_sha256,...packageDestination(kind,review.mergeCourse,review.title,review.targetCourse,review.parentFolder)};
      await sendImport(payload);return;
    }
    const task=begin('export');
    try{const download=await api.exportPackage(token,{...scope(),selection:review.selection,expected_sha256:review.data.selection_sha256},task.signal);if(!live(task.id))return;const url=URL.createObjectURL(download.blob),link=document.createElement('a');link.href=url;link.download=safePackageFilename(download.filename);document.body.append(link);link.click();link.remove();window.setTimeout(()=>URL.revokeObjectURL(url),60000);setDownloaded(true);callbacks.current.onNotice('标准 ZIP 已生成并开始下载，可使用同格式导入。');}
    catch(reason){if(live(task.id)){if(reason instanceof ApiError&&reason.code==='PACKAGE_SELECTION_CHANGED')setReview(null);failure(reason);}}finally{finish(task.id);}
  };
  const checkImport=async()=>{
    const pending=frozenRef.current;if(!pending||operationRef.current||paused)return;const task=begin('status');setNotFound(false);
    try{const next=await api.packageImportResult(token,pending.request_id,task.signal);if(live(task.id))await complete(next);}
    catch(reason){if(!live(task.id))return;if(reason instanceof ApiError&&reason.status===404){setNotFound(true);setError('尚未查询到成功记录。可以沿用原选择和请求标识重试；若原请求仍在处理，服务端会核对同一次导入。');}else failure(reason);}
    finally{finish(task.id);}
  };
  const close=()=>{if(committing)return;cancel();callbacks.current.onClose();};
  const invalidTarget=mode==='import'&&(kind==='folder'||mergeCourse)&&(!targetCourse||!courseRows.some(row=>row.id===targetCourse)||kind==='folder'&&!!parentFolder&&!folderRows.some(row=>row.id===parentFolder));
  const canReview=!!catalog&&!locked&&selectedPackageCount(selection)>0&&!invalidTarget&&selectedPackageCount(selection)<=PACKAGE_SELECTION_LIMIT;
  const added=review?Math.max(0,selectedPackageCount(review.data.selection)-selectedPackageCount(review.selection)):0;
  return <WorkspaceDialog open={open&&!paused} title={mode==='export'?'导出标准数据包':'导入标准数据包'} onClose={close} busy={committing} className="package-transfer-dialog">
    <section className="package-transfer" aria-label="标准数据包工作区">
      <div className="package-intro"><strong>{mode==='export'?'选择范围，带走完整关联。':'先核对内容，再加入学习空间。'}</strong><p>{mode==='export'?'标准 ZIP 保留可重新导入的元数据。日常离线阅读仍可使用原“选择笔记导出”。':'支持本项目导出的课程包和笔记文件夹包，导入会新建对象，不覆盖原有内容。'}</p></div>
      {current?.courseId&&!frozen&&!result&&<div className="package-actions" aria-label="标准包操作方式"><button type="button" className="secondary" aria-pressed={mode==='import'} disabled={locked} onClick={()=>reset({...current,mode:'import'})}>导入 ZIP</button><button type="button" className="secondary" aria-pressed={mode==='export'} disabled={locked} onClick={()=>reset({...current,mode:'export'})}>导出当前范围</button></div>}
      <ol className="package-steps" aria-label="数据包处理步骤"><li className={!catalog?'current':''}>{mode==='import'?'选择 ZIP':'读取范围'}</li><li className={catalog&&!review?'current':''}>选择内容</li><li className={review?'current':''}>预览并确认</li></ol>
      {samples.length>0&&<div className="package-actions" aria-label="标准包示例下载">{samples.map(sample=><a key={sample.href} className="secondary" href={sample.href} download={sample.filename}>{sample.label}</a>)}</div>}
      {checkingOwner&&<p role="status">正在核对当前账户…</p>}
      {!checkingOwner&&!owner&&<button type="button" className="secondary" onClick={()=>setOwnerRevision(value=>value+1)}>重新核对账户</button>}
      {storageWarning&&<p role="status" className="package-warnings">{storageWarning}</p>}
      {open&&!paused&&!checkingOwner&&owner&&<PackagePreviewManager key={owner+token} token={token} owner={owner} protectedId={frozen?.preview_id} disabled={!!operation} onBusyChange={setManagerBusy} onError={onError} onRemoved={id=>{if(uploadedRef.current?.preview_id!==id)return;uploadedRef.current=null;setUploaded(null);setCatalog(null);setFile(null);setReview(null);setResult(null);setSelection({});if(input.current)input.current.value='';}}/>}
      {!checkingOwner&&owner&&mode==='import'&&!frozen&&!result&&<div className="package-file"><label>选择标准 ZIP<input ref={input} type="file" aria-label="选择标准ZIP" accept=".zip,application/zip" disabled={locked||!owner} onChange={event=>{const picked=event.target.files?.[0];if(picked)void inspect(picked);event.target.value='';}}/></label><p className="hint">ZIP最多100 MiB，展开内容最多256 MiB。课程包可新建课程或合并到已有课程；笔记文件夹包导入到现有课程，可保留层级及未归档笔记。</p>{file&&<p>{file.name} · {(file.size/1024/1024).toFixed(2)} MiB</p>}{file&&!catalog&&!operation&&<button type="button" className="secondary" onClick={()=>void inspect(file)}>重新检查文件</button>}{uploaded&&<button type="button" className="text-button" disabled={locked} onClick={()=>void discardPreview()}>移除预览</button>}</div>}
      {error&&<p role="alert" className="package-error">{error}</p>}
      {operation&&<p role="status" className="package-progress">{{catalog:'正在读取可导出的内容…',file:'正在校验 ZIP 并识别内容，尚未导入…',review:'正在核对选择与关联依赖…',export:'正在打包并下载，请稍候…',import:'正在导入，请保持窗口打开…',status:'正在核对原请求结果…'}[operation]} 单次处理最多等待120秒。</p>}
      {mode==='export'&&!catalog&&!operation&&current&&<button disabled={locked} type="button" className="secondary" onClick={()=>void loadCatalog(current)}>重新读取导出范围</button>}
      {!checkingOwner&&owner&&frozen&&<div className="package-uncertain" role="status"><strong>{unknown?'上次导入结果尚未确认':'本次导入已固定范围'}</strong><p>已保留原文件预览、目标和选择。请核对本次请求，不会自动重发或随着新选择改变范围。</p><code>请求标识：{frozen.request_id}</code>{!operation&&<div className="package-actions"><button type="button" className="primary" onClick={()=>void checkImport()}>核对导入结果</button>{notFound&&<button type="button" className="secondary" disabled={disabled} onClick={()=>void sendImport(frozen)}>重试原导入请求</button>}</div>}</div>}
      {!checkingOwner&&owner&&(result?<section className="package-result" aria-label="标准包导入结果"><h3>导入完成</h3><p>新增 {result.note_count} 篇笔记、{result.folder_count} 个文件夹。</p><Counts counts={result.counts}/><Warnings warnings={result.warnings}/><p className="hint">原有内容保持不变。关闭窗口后可在课程或笔记目录中查看。</p><button type="button" className="secondary" disabled={!!operation} onClick={()=>void discardPreview()}>移除预览并导入下一份</button></section>:catalog&&<>
        <div className="package-source"><h3>{catalog.title}</h3><span>{catalog.kind==='course'?'课程标准包':'笔记文件夹标准包'}</span></div>
        <Warnings warnings={catalog.warnings}/>
        {mode==='import'&&kind==='course'&&<fieldset className="package-destination" disabled={locked}><legend>课程包导入方式</legend><label><input type="radio" name="package-destination" checked={!mergeCourse} onChange={()=>{setMergeCourse(false);setReview(null);}}/>新建课程</label><label><input type="radio" name="package-destination" checked={mergeCourse} onChange={()=>{setMergeCourse(true);setReview(null);}}/>合并到已有课程</label><p className="hint">合并会添加所选内容的独立副本，保留目标课程名称、设置和已有资料，不覆盖原对象。</p></fieldset>}
        {mode==='import'&&kind==='course'&&!mergeCourse&&<label className="package-target">新课程名称<input aria-label="新课程名称" value={title} maxLength={200} disabled={locked} onChange={event=>{setTitle(event.target.value);setReview(null);}}/><small>仅新建课程，课程基本信息随包保留；可自行取消不需要的内容。</small></label>}
        {mode==='import'&&(kind==='folder'||mergeCourse)&&<div className="package-targets"><label>目标课程<select aria-label="标准包目标课程" value={targetCourse} disabled={locked} onChange={event=>{setTargetCourse(event.target.value);setParentFolder('');setReview(null);}}><option value="">选择接收课程</option>{courseRows.map(course=><option key={course.id} value={course.id}>{course.name}</option>)}</select></label>{kind==='folder'&&<label>放入文件夹<select aria-label="标准包目标文件夹" value={parentFolder} disabled={locked||!targetCourse} onChange={event=>{setParentFolder(event.target.value);setReview(null);}}><option value="">课程根目录（保留包内结构）</option>{folderOptions(folderRows).map(folder=><option key={folder.id} value={folder.id}>{folder.path}</option>)}</select></label>}{!courseRows.length&&<p className="hint">暂无接收课程，请先在总览创建课程。</p>}{kind==='folder'&&invalidTarget&&targetCourse&&parentFolder&&<p role="alert">所选目标文件夹尚未加载或已不可用，请核对后重新选择。</p>}</div>}
        <PackagePicker items={catalog.items} selection={selection} disabled={locked} onChange={changeSelection}/>
        {!frozen&&<button type="button" className="primary" disabled={!canReview} onClick={()=>void preview()}>预览所选内容</button>}
        {review&&<section className="package-review" aria-label="标准包确认预览"><h3>{mode==='import'?'确认导入范围':'确认导出范围'}</h3><p>{mode==='import'?(kind==='course'&&!review.mergeCourse?`新建课程：${review.title}`:`${review.mergeCourse?'合并到':'导入到'}：${courseRows.find(course=>course.id===review.targetCourse)?.name||'所选课程'}${kind==='folder'&&review.parentFolder?' / '+(folderRows.find(folder=>folder.id===review.parentFolder)?.name||'所选文件夹'):(kind==='folder'?' / 根目录':'（保留原有内容）')}`):`导出：${catalog.title}`}</p><Counts counts={review.data.counts}/>{added>0&&<p className="hint">为保持内容关系，自动补充 {added} 项依赖；下方按最终范围列出。</p>}<Warnings warnings={review.data.warnings}/><PackageFinalItems preview={review.data} original={review.selection}/><p className="hint">未选择的笔记不会自动带入，也不会沿用原笔记链接。课程包导入不执行模型、识别或后台学习任务。</p>{disabled&&<p role="status">请先保存或处理当前笔记草稿，再确认本次操作。</p>}<button type="button" className="primary" disabled={disabled||locked} onClick={()=>void confirm()}>{mode==='import'?'确认导入所选内容':'确认导出并下载ZIP'}</button>{downloaded&&<p role="status">ZIP 已生成并发起下载，可以使用“导入标准数据包”重新导入。</p>}</section>}
      </>)}
    </section>
  </WorkspaceDialog>;
}
