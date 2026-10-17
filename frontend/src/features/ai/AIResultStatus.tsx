import { Status } from "../../components/workspace";

export function AIResultStatus({status, errorCode}: {status: string; errorCode?: string}) {
  if(errorCode==="PARTIAL_REPORT")return <span className="status status-running">部分报告</span>;
  if (status === "provider_error") {
    const labels:Record<string,string>={TIMEOUT:"请求超时",INVALID_ANSWER:"题目答案不符",INVALID_TOPICS:"知识点关联不符",INVALID_COUNT:"题目数量不符",INVALID_RUBRIC:"评分细则不符",INVALID_REFERENCE:"参考范围不符",DUPLICATE_QUESTION:"题目重复",SOURCE_UNAVAILABLE:"来源已失效",SERVICE_BUSY:"服务繁忙",RATE_LIMITED:"请求过于频繁",USAGE_LIMIT:"账户额度受限",INCOMPLETE_OUTPUT:"输出未完整结束",RESPONSE_BUDGET:"响应超出预算"};
    if(errorCode&&labels[errorCode]) return <span className="status status-failed">{labels[errorCode]}</span>;
    if (errorCode === "INVALID_CITATION") return <span className="status status-failed">引用校验失败</span>;
    if (errorCode === "INVALID_OUTPUT" || errorCode === "INVALID_JSON") return <span className="status status-failed">输出格式不符</span>;
  }
  return <Status value={status}/>;
}
