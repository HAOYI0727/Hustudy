import type {AIExecution} from "../../api/client";

export function ExecutionSummary({execution,pending=false}:{execution?:AIExecution|null;pending?:boolean}) {
  if(!execution)return null;
  return <div className="ai-privacy-card" aria-label="本次处理预算">
    <strong>本次确认处理窗口：{execution.budget_seconds}秒</strong>
    <p>已调用{execution.total_calls}次 · 已用格式修复{execution.repairs_used}/{execution.max_structure_repairs}次</p>
    <p className="hint">当前第{execution.window_number}个窗口，已调用{execution.window_calls}/{execution.window_call_limit}次。
      {!execution.window_started_at?"首次派发才开始计时，派发前排队不计时。":pending?`窗口剩余约${Math.ceil(execution.remaining_seconds)}秒，跨批等待也计时。`:"预算到期会停止，已完成部分保留。"}
      {execution.phase==="repairing"&&"正在进行已授权的格式修复。"}
      {execution.phase==="needs_continue"&&"剩余时间不足以容纳此前观察到的单批耗时，未派发下一批；确认后可继续。"}
    </p>
    <p className="hint">{execution.max_structure_repairs?`已授权最多${execution.max_structure_repairs}次格式修复；计入最多${execution.window_call_limit}次调用及同一窗口预算。`:"未授权格式修复，格式错误不会自动再发。"}已完成批次不重发；停止后仅明确确认才继续新窗口。</p>
  </div>;
}
