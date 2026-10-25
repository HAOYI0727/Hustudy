import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,test} from 'vitest';
import type {AIExecution} from '../../src/api/client';
import {ExecutionSummary} from '../../src/features/ai/ExecutionSummary';
import {AIResultStatus} from '../../src/features/ai/AIResultStatus';

const initial:AIExecution={budget_seconds:120,max_structure_repairs:0,repairs_used:0,total_calls:0,window_number:1,window_calls:0,window_call_limit:1,window_started_at:null,deadline_at:null,remaining_seconds:120,phase:'awaiting_dispatch'};

test('预算预览默认不修复，派发前排队不消耗窗口',()=>{
  const html=renderToStaticMarkup(createElement(ExecutionSummary,{execution:initial}));
  expect(html).toContain('未授权格式修复');
  expect(html).toContain('120秒');expect(html).toContain('排队不计时');
});
test('授权修复次数和剩余预算如实显示，续跑不重置总额度',()=>{
  const execution={...initial,max_structure_repairs:2,repairs_used:1,total_calls:3,window_number:2,window_calls:1,window_call_limit:3,window_started_at:'2026-10-24T00:00:00Z',remaining_seconds:40,phase:'repairing'};
  const html=renderToStaticMarkup(createElement(ExecutionSummary,{execution,pending:true}));
  expect(html).toContain('已用格式修复1/2次');expect(html).toContain('剩余约40秒');
  expect(html).toContain('正在进行已授权');expect(html).toContain('已完成批次');
});
test('旧历史缺执行字段可读，预算错误不误报模型不可用',()=>{
  expect(renderToStaticMarkup(createElement(ExecutionSummary,{}))).toBe('');
  const html=renderToStaticMarkup(createElement(AIResultStatus,{status:'provider_error',errorCode:'TASK_BUDGET_EXCEEDED'}));
  expect(html).toContain('处理预算已用尽');expect(html).not.toContain('模型不可用');
});
