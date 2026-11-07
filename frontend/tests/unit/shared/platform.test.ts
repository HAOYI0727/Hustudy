import {afterEach, expect, test, vi} from 'vitest';
import {parseWorkspace, workspaceHref} from '../../../src/features/platform/routing';
import {clearSessionQueries, queryClient, sessionPartition} from '../../../src/api/query';
import {api, ApiError} from '../../../src/api/client';
import {onlineManager} from '@tanstack/react-query';
const course='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', documentId='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', versionId='cccccccc-cccc-cccc-cccc-cccccccccccc', chunkId='dddddddd-dddd-dddd-dddd-dddddddddddd';
afterEach(()=>{clearSessionQueries();onlineManager.setOnline(true);vi.unstubAllGlobals();});
test('资料历史版本、定位和预览页可完整往返 URL',()=>{
  const target={documentId,versionId,chunkId,previewPage:3};
  const url=new URL(workspaceHref('materials',course,{material:target}),'http://localhost');
  expect(parseWorkspace(url.pathname,url.search)).toEqual({section:'materials',courseId:course,noteId:undefined,mistakeId:undefined,material:target,invalid:false});
  expect(workspaceHref('notes',course,{noteId:chunkId})).toContain('note='+chunkId);
});
test.each(['/alien?course=broken','/materials?document='+documentId,'/notes?course=','/materials?document='+documentId+'&version='+versionId+'&page=-1'])('坏地址被标记而不转成业务 ID: %s',address=>{
  const url=new URL(address,'http://localhost');expect(parseWorkspace(url.pathname,url.search).invalid).toBe(true);
});

test('错题子页面地址支持往返且拒绝无效题目ID',()=>{
 const url=new URL(workspaceHref('review',course,{mistakeId:chunkId}),'http://localhost');
 expect(parseWorkspace(url.pathname,url.search)).toMatchObject({section:'review',mistakeId:chunkId,invalid:false});
 expect(parseWorkspace('/review','?mistake=bad').invalid).toBe(true);
});
test('原文回看错题的只读计划入口可刷新恢复，拒绝错误模式及缺少错题的地址',()=>{
 const url=new URL(workspaceHref('review',course,{mistakeId:chunkId,reviewMode:'plan'}),'http://localhost');
 expect(parseWorkspace(url.pathname,url.search)).toMatchObject({section:'review',mistakeId:chunkId,reviewMode:'plan',invalid:false});
 for(const address of ['/review?review=plan','/review?mistake='+chunkId+'&review=wrong','/notes?mistake='+chunkId+'&review=plan']){
  const bad=new URL(address,'http://localhost');expect(parseWorkspace(bad.pathname,bad.search).invalid).toBe(true);
 }
 expect(workspaceHref('notes',course,{mistakeId:chunkId,reviewMode:'plan'})).not.toContain('review=');
 expect(workspaceHref('review',course,{mistakeId:chunkId})).not.toContain('review=');
});
test('令牌不进入 query key，退出清理所有会话数据',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>Response.json([])));
  await api.courses('private-first-token');
  expect(JSON.stringify(queryClient.getQueryCache().getAll().map(x=>x.queryKey))).not.toContain('private-first-token');
  expect(sessionPartition('a')).not.toBe(sessionPartition('b'));
  clearSessionQueries();expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
});
test('重叠同会话 GET 去重，后续读取重新授权，另一账户独立读取',async()=>{
  let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
  const fetcher=vi.fn(async()=>{await gate;return Response.json([]);});vi.stubGlobal('fetch',fetcher);
  const a=api.courses('one'),b=api.courses('one'),c=api.courses('two');
  expect(fetcher).toHaveBeenCalledTimes(2);release();await Promise.all([a,b,c]);
  await api.courses('one');expect(fetcher).toHaveBeenCalledTimes(3);
});
test('401 与变更失败均不自动重试，保留后端错误',async()=>{
  const fetcher=vi.fn(async()=>Response.json({error:{message:'expired',code:'AUTH_REQUIRED'}},{status:401}));vi.stubGlobal('fetch',fetcher);
  await expect(api.courses('expired')).rejects.toBeInstanceOf(ApiError);
  expect(fetcher).toHaveBeenCalledTimes(1);
  await expect(api.createCourse('expired','课程','')).rejects.toMatchObject({status:401,code:'AUTH_REQUIRED'});
  expect(fetcher).toHaveBeenCalledTimes(2);
});
test('成功变更使本会话数据失效，下载 Blob 不写入 query cache',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>Response.json([])));
  await api.courses('one');await api.courses('two');
  await api.createCourse('one','课程','');
  const one=queryClient.getQueryCache().find({exact:false,queryKey:['api',sessionPartition('one'),'/courses']});
  const two=queryClient.getQueryCache().find({exact:false,queryKey:['api',sessionPartition('two'),'/courses']});
  expect(one?.state.isInvalidated).toBe(true);expect(two?.state.isInvalidated).toBe(false);
  const size=queryClient.getQueryCache().getAll().length;
  await api.downloadAccountArchive('one',course);expect(queryClient.getQueryCache().getAll()).toHaveLength(size);
});

test('写入后刷新不合并到写入前仍在途的旧列表请求',async()=>{
  let release!:(value:Response)=>void;
  const pending=new Promise<Response>(resolve=>{release=resolve;});
  const fetcher=vi.fn().mockImplementationOnce(()=>pending).mockResolvedValueOnce(Response.json({id:course})).mockResolvedValueOnce(Response.json([{id:course,name:'新课程'}]));
  vi.stubGlobal('fetch',fetcher);
  const old=api.courses('one');await api.createCourse('one','新课程','');
  const fresh=await api.courses('one');expect(fresh[0].name).toBe('新课程');expect(fetcher).toHaveBeenCalledTimes(3);
  release(Response.json([]));expect(await old).toEqual([]);
});

test('显式学习记录离线立即失败，恢复联网不自动重放',async()=>{
  onlineManager.setOnline(false);
  const fetcher=vi.fn().mockRejectedValue(new TypeError('offline'));
  vi.stubGlobal('fetch',fetcher);
  await expect(api.learningRecords('one',course,'all','',0)).rejects.toMatchObject({status:0});
  expect(fetcher).toHaveBeenCalledTimes(1);
  onlineManager.setOnline(true);
  await Promise.resolve();
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
});

test('关闭学习记录传递真实取消信号，下一次显式读取独立发起',async()=>{
  const controller=new AbortController();
  const fetcher=vi.fn((_url:string,options:RequestInit)=>new Promise<Response>((_resolve,reject)=>{
    options.signal?.addEventListener('abort',()=>reject(new DOMException('cancelled','AbortError')),{once:true});
  }));
  vi.stubGlobal('fetch',fetcher);
  const pending=api.learningRecords('one',course,'note','',0,controller.signal);
  expect(fetcher.mock.calls[0][1].signal).toBe(controller.signal);
  controller.abort();await expect(pending).rejects.toMatchObject({status:0});
  vi.stubGlobal('fetch',vi.fn(async()=>Response.json({course_id:course,items:[]})));
  await expect(api.learningRecords('one',course,'note','',0)).resolves.toMatchObject({course_id:course});
});

test('浏览器判断外网离线时仍可读取可达的本机API',async()=>{
  onlineManager.setOnline(false);
  const fetcher=vi.fn(async()=>Response.json([{id:course,name:'本机课程'}]));
  vi.stubGlobal('fetch',fetcher);
  await expect(api.courses('one')).resolves.toMatchObject([{id:course}]);
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test('本机API连接失败立即报告，联网后不自动重放失败读取',async()=>{
  onlineManager.setOnline(false);
  const fetcher=vi.fn().mockRejectedValue(new TypeError('offline'));
  vi.stubGlobal('fetch',fetcher);
  await expect(api.courses('one')).rejects.toMatchObject({status:0,message:expect.stringContaining('暂时无法连接学习服务')});
  onlineManager.setOnline(true);await Promise.resolve();
  expect(fetcher).toHaveBeenCalledTimes(1);
});
