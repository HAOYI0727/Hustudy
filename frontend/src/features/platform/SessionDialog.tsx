import {Alert, Modal} from 'antd';
import {AuthScreen} from './index';

export default function SessionDialog({username,onSuccess,onExit}:{username:string;onSuccess:(token:string,username:string)=>void;onExit:()=>void}) {
  return <Modal open title="登录已过期 · 保留当前工作" closable={false} mask={{closable:false}} keyboard={false} footer={null} width={480}>
    {username ? <AuthScreen expectedUsername={username} message="当前页面和未保存内容仍保留在此窗口。请登录原账户后继续；失败的保存或模型请求不会自动重发。" onSuccess={onSuccess}/> : <Alert type="warning" title="无法确定原账户，请先复制需要保留的内容，再退出重新登录。"/>}
    <button className="text-button reauth-exit" onClick={onExit}>退出账户（离开前检查未保存内容）</button>
  </Modal>;
}
