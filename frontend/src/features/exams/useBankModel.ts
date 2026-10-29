import {useEffect,useRef,useState} from "react";
import {api} from "../../api/client";
import {useModelChange} from "../../api/modelEvents";

const empty={configured:false,vision_configured:false,model:"正在核对模型",vendor:"",endpoint:""};
export function useBankModel(token:string){
 const [value,setValue]=useState(empty);
 const generation=useRef(0);
 useEffect(()=>{const id=++generation.current;setValue(empty);void api.bankAICapabilities(token).then(v=>{if(id===generation.current)setValue({...empty,...v});}).catch(()=>{if(id===generation.current)setValue({...empty,model:"模型配置不可用"});});return()=>{generation.current++;};},[token]);
 useModelChange(token,isCurrent=>{const id=++generation.current;setValue(empty);void api.bankAICapabilities(token).then(v=>{if(isCurrent()&&id===generation.current)setValue({...empty,...v});}).catch(()=>{if(isCurrent()&&id===generation.current)setValue({...empty,model:"模型配置不可用"});});});
 return {...value,label:`${value.vendor==="deepseek"?"DeepSeek · ":""}${value.model}`};
}
