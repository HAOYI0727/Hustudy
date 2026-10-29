import type {PackageImportRequest,PackageSelection} from '../../api/client';
import {PACKAGE_CATEGORIES,PACKAGE_SELECTION_LIMIT,freezePackageSelection} from './packageSelection';

type StorageLike=Pick<Storage,'getItem'|'setItem'|'removeItem'>;
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const key=(owner:string)=>`hustudy:package-pending:v1:${owner}`;
function browserStorage():StorageLike|null {try{return typeof sessionStorage==='undefined'?null:sessionStorage;}catch{return null;}}
export function readPendingPackage(owner:string,storage:StorageLike|null=browserStorage()):PackageImportRequest|null {
  if(!uuid.test(owner)||!storage)return null;
  try {
    const text=storage.getItem(key(owner));if(!text||text.length>1024*1024)return null;
    const saved=JSON.parse(text) as Record<string,unknown>,payload=saved.request as Partial<PackageImportRequest>|undefined;
    if(saved.version!==1||!payload||!uuid.test(payload.request_id||'')||!uuid.test(payload.preview_id||'')||!payload.selection||typeof payload.selection!=='object'||Array.isArray(payload.selection))return null;
    const selection:PackageSelection={};let count=0;
    for(const [category,ids] of Object.entries(payload.selection)){
      if(!PACKAGE_CATEGORIES.some(item=>item.key===category)||!Array.isArray(ids)||ids.some(id=>typeof id!=='string'||!uuid.test(id)))return null;
      count+=ids.length;if(count>PACKAGE_SELECTION_LIMIT||new Set(ids).size!==ids.length)return null;
      selection[category as keyof PackageSelection]=ids;
    }
    if(payload.target_course_id!==undefined&&!uuid.test(payload.target_course_id)||payload.parent_folder_id!==undefined&&!uuid.test(payload.parent_folder_id)||payload.title!==undefined&&(typeof payload.title!=='string'||payload.title.length>400)||payload.expected_sha256!==undefined&&(typeof payload.expected_sha256!=='string'||!/^[0-9a-f]{64}$/.test(payload.expected_sha256)))return null;
    return requestFields({...payload,request_id:payload.request_id!,preview_id:payload.preview_id!,selection});
  }catch{return null;}
}
export function savePendingPackage(owner:string,payload:PackageImportRequest|null,storage:StorageLike|null=browserStorage()):boolean {
  if(!uuid.test(owner)||!storage)return false;
  try {if(payload)storage.setItem(key(owner),JSON.stringify({version:1,request:requestFields(payload)}));else storage.removeItem(key(owner));return true;}catch{return false;}
}
function requestFields(payload:PackageImportRequest):PackageImportRequest {
  return {request_id:payload.request_id,preview_id:payload.preview_id,selection:freezePackageSelection(payload.selection),...(payload.expected_sha256?{expected_sha256:payload.expected_sha256}:{}),...(payload.target_course_id?{target_course_id:payload.target_course_id}:{}),...(payload.parent_folder_id?{parent_folder_id:payload.parent_folder_id}:{}),...(payload.title?{title:payload.title}:{})};
}
