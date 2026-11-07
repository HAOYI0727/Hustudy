import {defineConfig, devices} from '@playwright/test';
import {fileURLToPath} from 'node:url';
const python=fileURLToPath(new URL(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python',import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ||= fileURLToPath(new URL('../.tools/playwright',import.meta.url));
export default defineConfig({
  testDir:'./tests/e2e', outputDir:fileURLToPath(new URL('../.artifacts/playwright/test-results',import.meta.url)), fullyParallel:false, workers:1, retries:0, timeout:45_000,
  reporter:'list', use:{baseURL:'http://127.0.0.1:5178',trace:'retain-on-failure',screenshot:'only-on-failure'},
  projects:[{name:'chromium',use:{...devices['Desktop Chrome'],...(process.env.HUSTUDY_E2E_CHROME_CHANNEL === 'chrome' ? {channel:'chrome'} : {})}},{name:'webkit',use:{...devices['Desktop Safari']}}],
  webServer:[
    {command:`"${python}" ../scripts/e2e_server.py`,url:'http://127.0.0.1:8056/health',timeout:60_000,reuseExistingServer:false},
    {command:`"${process.execPath}" scripts/build-office.mjs && "${process.execPath}" scripts/build-math-notices.mjs && "${process.execPath}" node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5178 --strictPort`,url:'http://127.0.0.1:5178',env:{VITE_API_BASE_URL:'http://127.0.0.1:8056/api/v1'},timeout:60_000,reuseExistingServer:false}
  ]
});
