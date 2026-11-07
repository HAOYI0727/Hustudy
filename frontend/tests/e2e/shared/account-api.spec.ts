import {test,expect} from '@playwright/test';

for(const width of [390,1440])test(`个人API双账户保存清除隔离 ${width}px`,async({browser,request})=>{
  test.setTimeout(90000);
  const base='http://127.0.0.1:8056/api/v1';
  const accounts=[];
  for(const suffix of ['a','b']){
    const username='personal_api_'+suffix+crypto.randomUUID().replaceAll('-','');
    const auth=await(await request.post(base+'/auth/register',{data:{username,password:'Test-password-2026'}})).json();
    const context=await browser.newContext({viewport:{width,height:1000}});
    await context.addInitScript(({token,username})=>{localStorage.setItem('hustudy_token',token);localStorage.setItem('hustudy_user',username);},{token:auth.access_token,username});
    const page=await context.newPage();await page.goto('/api-connect');
    await expect(page.getByRole('button',{name:'保存API配置',exact:true})).toBeDisabled();
    accounts.push({page,context,headers:{Authorization:'Bearer '+auth.access_token}});
  }
  const [a,b]=accounts;
  try{
    await a.page.getByLabel('智谱API Key',{exact:true}).fill('synthetic-browser-account-A');
    await a.page.getByRole('combobox',{name:'使用的模型',exact:true}).selectOption('glm-5.3-flash');
    await a.page.getByRole('button',{name:'保存API配置',exact:true}).click();
    await expect(a.page.getByText('已保存，尚未测试',{exact:true})).toBeVisible();
    await expect(a.page.getByLabel('智谱API Key',{exact:true})).toHaveValue('');
    await b.page.reload();
    await expect(b.page.getByText('未配置',{exact:true})).toBeVisible();
    await b.page.getByLabel('智谱API Key',{exact:true}).fill('synthetic-browser-account-B');
    await b.page.getByRole('combobox',{name:'使用的模型',exact:true}).selectOption('glm-4.7-flash');
    await b.page.getByRole('button',{name:'保存API配置',exact:true}).click();
    await expect(b.page.getByText('已保存，尚未测试',{exact:true})).toBeVisible();
    const statusA=await(await request.get(base+'/api-connection',{headers:a.headers})).json();
    const statusB=await(await request.get(base+'/api-connection',{headers:b.headers})).json();
    expect(statusA.scope).toBe('account');expect(statusB.scope).toBe('account');
    expect(statusA.model).toBe('glm-5.3-flash');expect(statusB.model).toBe('glm-4.7-flash');
    expect(JSON.stringify([statusA,statusB])).not.toContain('synthetic-browser');
    b.page.once('dialog',dialog=>dialog.accept());
    await b.page.getByRole('button',{name:'清除配置',exact:true}).click();
    await expect(b.page.getByText('未配置',{exact:true})).toBeVisible();
    await a.page.reload();await expect(a.page.getByText('已保存，尚未测试',{exact:true})).toBeVisible();
    await expect(a.page.getByText(/其他账户需要分别保存自己的API Key/)).toBeVisible();
    expect(await a.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    expect(await b.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }finally{for(const account of accounts)await account.context.close();}
});
