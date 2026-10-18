import {defineConfig} from '@playwright/test';

const port = Number(process.env.CASEMIND_OFFLINE_PORT || '8081');
export default defineConfig({
  testDir: './e2e',
  outputDir: '../plans/261010-2218-investigator-workspace-replan/reports/browser-tests',
  testMatch: 'workspace-offline.spec.ts',
  workers: 1,
  timeout: 60_000,
  reporter: 'list',
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    browserName: 'chromium',
    launchOptions: process.env.CASEMIND_BROWSER_PATH
      ? {executablePath: process.env.CASEMIND_BROWSER_PATH}
      : {executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'},
    viewport: {width: 1440, height: 900},
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'PYTHONPATH=backend ./.venv/bin/python tests/offline_workspace_server.py',
    cwd: '..',
    env: {CASEMIND_CLOUD: 'false', CASEMIND_SESSION_SECRET: '', CASEMIND_GOOGLE_CLIENT_ID: '', CASEMIND_INVESTIGATOR_SUBJECTS: ''},
    url: `http://127.0.0.1:${port}/api/health`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
