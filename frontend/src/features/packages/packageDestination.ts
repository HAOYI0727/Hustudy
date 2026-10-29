import type {PackageImportRequest,PackageKind} from '../../api/client';

export function packageDestination(kind:PackageKind,mergeCourse:boolean,title:string,targetCourse:string,parentFolder:string):Pick<PackageImportRequest,'title'|'target_course_id'|'parent_folder_id'> {
  if(kind==='course'&&!mergeCourse)return {title:title.trim()};
  return {target_course_id:targetCourse,...(kind==='folder'&&parentFolder?{parent_folder_id:parentFolder}:{})};
}
