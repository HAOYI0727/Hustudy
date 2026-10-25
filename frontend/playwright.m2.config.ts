import {defineConfig} from '@playwright/test';
import base from './playwright.config';

// M2 verification can reuse an installed Python; no project venv is required.
const python=process.env.HUSTUDY_TEST_PYTHON || 'python';
export default defineConfig({
  ...base,
  webServer:(Array.isArray(base.webServer)?base.webServer:[base.webServer]).map((server,index)=>index===0?{
    ...server,command:`"${python}" ../scripts/e2e_server.py`,
  }:server).filter((server):server is NonNullable<typeof server>=>Boolean(server)),
});
