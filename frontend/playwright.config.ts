import {defineConfig, devices} from '@playwright/test';
import {fileURLToPath} from 'node:url';
process.env.PLAYWRIGHT_BROWSERS_PATH ||= fileURLToPath(new URL('../.tools/playwright',import.meta.url));
export default defineConfig({
  testDir:'./tests/e2e', fullyParallel:false, workers:1, retries:0, timeout:45_000,
  reporter:'list', use:{baseURL:'http://127.0.0.1:5178',trace:'retain-on-failure',screenshot:'only-on-failure'},
  projects:[{name:'chromium',use:{...devices['Desktop Chrome'],...(process.env.HUSTUDY_E2E_CHROME_CHANNEL === 'chrome' ? {channel:'chrome'} : {})}},{name:'webkit',use:{...devices['Desktop Safari']}}],
  webServer:[
    {command:'../.venv/bin/python ../scripts/e2e_server.py',url:'http://127.0.0.1:8056/health',timeout:60_000,reuseExistingServer:false},
    {command:'npm run dev -- --host 127.0.0.1 --port 5178 --strictPort',url:'http://127.0.0.1:5178',env:{VITE_API_BASE_URL:'http://127.0.0.1:8056/api/v1'},timeout:60_000,reuseExistingServer:false}
  ]
});
