import {useState} from "react";
import {api,Asset,BankImage} from "../../api/client";
import {BankImageEditor} from "./BankImages";
import {NotesDialog} from "../notes/NotesDialog";

type GroupItem={id:string;revision:number;preferred_asset_id?:string;images:BankImage[];sources:BankImage[]};
export function GroupImageTools({token,courseId,id,disabled,onSaved,onError,libraryImages}:{
  token:string;courseId:string;id:string;disabled:boolean;onSaved:(revisions:Record<string,number>,images:BankImage[])=>Promise<void>;onError:(error:unknown)=>void;libraryImages:Asset[];
}){
  const [group,setGroup]=useState<GroupItem[]|null>(null),[images,setImages]=useState<BankImage[]>([]),[busy,setBusy]=useState(false);
  return <div className="panel">
    <button className="secondary" disabled={disabled||busy} onClick={async()=>{
      setBusy(true);
      try{
        const items=await api.bankImageGroup(token,id);
        setGroup(items);
        setImages(Array.from(new Map(items.flatMap(q=>q.images).map(i=>[i.asset_id+JSON.stringify(i.box),i])).values()));
      }catch(error){onError(error);}finally{setBusy(false);}
    }}>编辑本大题截图与插图</button>
    <NotesDialog open={Boolean(group)} title="大题截图与插图" onClose={()=>{if(!busy&&window.confirm("关闭插图窗口？未保存修改将丢弃。"))setGroup(null);}}>
      {group&&<><BankImageEditor preferredAssetId={group.find(item=>item.id===id)?.preferred_asset_id} libraryImages={libraryImages} token={token} courseId={courseId} sources={Array.from(new Map(group.flatMap(q=>q.sources).map(i=>[i.asset_id+JSON.stringify(i.box),i])).values())} images={images} onChange={setImages} busy={busy} onWorking={setBusy}/>
      <button className="primary" disabled={busy||images.length>8} onClick={async()=>{
        setBusy(true);
        try{const saved=await api.saveBankImageGroup(token,id,{images,revisions:Object.fromEntries(group.map(q=>[q.id,q.revision]))});setGroup(null);await onSaved(saved.revisions,images);}
        catch(error){onError(error);}finally{setBusy(false);}
      }}>保存本大题插图</button></>}
    </NotesDialog>
  </div>;
}

export function AnswerImageTools({token,courseId,sources,busy,onWorking,onInsert,libraryImages=[],label="输入图片（参考答案）",preferredAssetId,questionId}:{
  libraryImages?:Asset[];token:string;courseId:string;sources:BankImage[];busy:boolean;onWorking:(busy:boolean)=>void;onInsert:(markdown:string,origins:Record<string,string>)=>void|Promise<void>;label?:string;preferredAssetId?:string;questionId?:string;
}){
  const [open,setOpen]=useState(false),[images,setImages]=useState<BankImage[]>([]),[working,setWorking]=useState(false),[error,setError]=useState("");
  const [allSources,setAllSources]=useState<BankImage[]|null>(null);
  const workingChanged=(value:boolean)=>{setWorking(value);onWorking(value);};
  return <><button type="button" className="secondary" disabled={busy||working} onClick={async()=>{
    setImages([]);setError("");
    if(questionId){
      workingChanged(true);
      try{const group=await api.bankImageGroup(token,questionId);setAllSources(group[0]?.sources||sources);setOpen(true);}
      catch(error){setError(error instanceof Error?error.message:"原页读取失败");}
      finally{workingChanged(false);}
    }else{setAllSources(null);setOpen(true);}
  }}>{label}</button>
    <NotesDialog open={open} title="输入参考答案图片" onClose={()=>{if(!working)setOpen(false);}}>
      <p>上传答案图片、选用插图库图片，或从对应原页框选答案。插入后保存本题校正。</p>
      <BankImageEditor preferredAssetId={preferredAssetId||sources[0]?.asset_id} purpose="answer" libraryImages={libraryImages} token={token} courseId={courseId} sources={allSources||sources} images={images} onChange={setImages} busy={busy||working} onWorking={workingChanged}/>
      {error&&<p role="alert">{error}</p>}
      <button className="primary" disabled={busy||working||!images.length} onClick={async()=>{
        workingChanged(true);setError("");
        try{
          const snippets=[];const origins:Record<string,string>={};
          for(const image of images){
            const blob=await api.bankIllustration(token,courseId,image);
            const asset=await api.uploadAsset(token,courseId,new File([blob],"参考答案.png",{type:blob.type||"image/png"}),"参考答案截图");
            origins[asset.id]=image.asset_id;
            snippets.push(`![[asset:${asset.id}|参考答案截图]]`);
          }
          await onInsert(snippets.join("\n\n"),origins);setOpen(false);
        }catch(e){setError(e instanceof Error?e.message:"插入失败");}
        finally{workingChanged(false);}
      }}>插入参考答案</button>
    </NotesDialog>
  </>;
}
