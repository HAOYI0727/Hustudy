import {useEffect,useRef} from 'react';
import {sessionPartition} from './query';
/** Selection changes refresh capabilities without remounting a workspace or losing drafts. */
export function useModelChange(token:string,onChange:(isCurrent:()=>boolean)=>void){
  const callback=useRef(onChange),generation=useRef(0);callback.current=onChange;
  useEffect(()=>{const change=(event:Event)=>{if((event as CustomEvent).detail===sessionPartition(token)){const current=++generation.current;callback.current(()=>current===generation.current);}};window.addEventListener('hustudy:model-changed',change);return()=>{generation.current++;window.removeEventListener('hustudy:model-changed',change);};},[token]);
}
