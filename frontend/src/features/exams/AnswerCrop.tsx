import {BankImage} from "../../api/client";
import {useState} from "react";
import {BankFigure,CropPicker} from "./BankImages";

export function AnswerCrop({token,courseId,assetId,originalId,sources=[],disabled,onSave,onDelete}:{
  token:string;courseId:string;assetId:string;originalId?:string;sources?:BankImage[];disabled:boolean;onSave:(box:number[],sourceId:string)=>Promise<void>;onDelete:()=>Promise<void>;
}){
  const [open,setOpen]=useState(false),[crop,setCrop]=useState([0,0,100,100]);
  const pages=sources.some(source=>source.asset_id===(originalId||assetId))?sources:[...sources,{asset_id:originalId||assetId,alt:"原图"}];
  const [page,setPage]=useState(Math.max(0,pages.findIndex(source=>source.asset_id===(originalId||assetId))));
  const sourceId=pages[page]?.asset_id||originalId||assetId;
  const box=crop.map(value=>value/100);
  const valid=box.every(Number.isFinite)&&box[0]>=0&&box[1]>=0&&box[2]>0&&box[3]>0&&box[0]+box[2]<=1&&box[1]+box[3]<=1;
  return <div className="panel">
    <button type="button" className="secondary" disabled={disabled} onClick={()=>setOpen(value=>!value)}>{open?"收起裁剪":"裁剪答案图片"}</button>
    <button type="button" className="danger-button" disabled={disabled} onClick={()=>{if(window.confirm("删除这张答案图片？文字答案会保留。"))void onDelete();}}>删除答案图片</button>
    {open&&<fieldset disabled={disabled}>
      <p>在图片上拖动框选需要保留的答案区域，保存后替换本题这张图片。</p>
      <div className="bank-actions"><button type="button" className="secondary" disabled={page===0} onClick={()=>{setPage(page-1);setCrop([0,0,100,100]);}}>上一页</button><span>{pages[page]?.alt||"原页"} · {page+1}/{pages.length}</span><button type="button" className="secondary" disabled={page+1>=pages.length} onClick={()=>{setPage(page+1);setCrop([0,0,100,100]);}}>下一页</button></div>
      <CropPicker token={token} courseId={courseId} assetId={sourceId} crop={crop} onChange={setCrop}/>
      <details><summary>精确调整裁剪范围</summary><div className="bank-fields">{["左侧 %","顶部 %","宽度 %","高度 %"].map((label,index)=><label key={label}>{label}<input type="number" min={0} max={100} step={0.1} value={crop[index]} onChange={event=>setCrop(values=>values.map((value,i)=>i===index?Number(event.target.value):value))}/></label>)}</div></details>
      {valid?<BankFigure token={token} courseId={courseId} image={{asset_id:sourceId,box,alt:"答案裁剪预览"}}/>:<p role="alert">裁剪范围须在图片内，宽高不能为零。</p>}
      <div className="bank-actions"><button type="button" className="secondary" onClick={()=>setCrop([0,0,100,100])}>重置范围</button><button type="button" className="primary" disabled={!valid||disabled} onClick={()=>void onSave(box,sourceId)}>保存答案裁剪</button></div>
    </fieldset>}
  </div>;
}
