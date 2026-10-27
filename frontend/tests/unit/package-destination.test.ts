import {describe,expect,it} from 'vitest';
import {packageDestination} from '../../src/features/packages/packageDestination';

describe('标准包导入目的',()=>{
  it('新建课程仅使用明确名称，不误带上次选中的课程或目录',()=>{
    expect(packageDestination('course',false,' 新课程 ','old-course','old-folder')).toEqual({title:'新课程'});
  });
  it('合并课程保留目标身份，不发送覆盖名称或笔记目录字段',()=>{
    expect(packageDestination('course',true,'包内原课程','target-course','old-folder')).toEqual({target_course_id:'target-course'});
  });
  it('文件夹包可放入指定父目录，根目录不发送空UUID',()=>{
    expect(packageDestination('folder',false,'包内标题','target-course','parent')).toEqual({target_course_id:'target-course',parent_folder_id:'parent'});
    expect(packageDestination('folder',false,'包内标题','target-course','')).toEqual({target_course_id:'target-course'});
  });
});
