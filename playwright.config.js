const { defineConfig, devices } = require('@playwright/test');
const path = require('path');

const authFile = path.join(__dirname, 'tests/.auth/user.json');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : 2,
  reporter: [['list'], ['html', { open: 'never' }]],
  timeout: 60000,

  use: {
    headless: true,
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  projects: [
    // Setup de autenticação (roda primeiro)
    {
      name: 'setup',
      testMatch: /auth\.setup\.js/,
    },
    // Testes E2E (usam autenticação)
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
      },
      dependencies: ['setup'],
    },
  ],
});
