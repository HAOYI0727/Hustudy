import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect, test} from 'vitest';
import {AIResultStatus} from '../../../src/features/ai/AIResultStatus';

test('引用校验失败不展示为平台不可用，兼容历史provider_error状态',()=>{
  const html=renderToStaticMarkup(createElement(AIResultStatus,{status:'provider_error',errorCode:'INVALID_CITATION'}));
  expect(html).toContain('引用校验失败');
  expect(html).not.toContain('模型不可用');
});

test('服务异常与成功结果保留已有状态',()=>{
  expect(renderToStaticMarkup(createElement(AIResultStatus,{status:'provider_error',errorCode:'SERVICE_BUSY'}))).toContain('服务繁忙');
  expect(renderToStaticMarkup(createElement(AIResultStatus,{status:'grounded'}))).toContain('有来源');
});

test.each(['INVALID_OUTPUT','INVALID_JSON'])('输出格式问题不误报平台不可用：%s',errorCode=>{
  const html=renderToStaticMarkup(createElement(AIResultStatus,{status:'provider_error',errorCode}));
  expect(html).toContain('输出格式不符');
  expect(html).not.toContain('模型不可用');
});
