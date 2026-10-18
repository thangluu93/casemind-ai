import {defineConfig} from '@playwright/test';
export default defineConfig({testDir: './e2e', workers: 1, use: {baseURL: process.env.CASEMIND_TEST_URL || 'http://127.0.0.1:8080', browserName: 'chromium', launchOptions: {executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}, viewport: {width: 1440, height: 900}}, reporter: 'list'});
