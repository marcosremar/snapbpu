// @ts-check
const { test, expect } = require('@playwright/test');
const path = require('path');

const authFile = path.join(__dirname, '.auth/user.json');

test('authenticate', async ({ page }) => {
  console.log('\n🔐 Setting up authentication...\n');

  // Listen to console for debugging
  page.on('console', msg => {
    if (msg.text().includes('App.jsx') || msg.text().includes('login') || msg.text().includes('error')) {
      console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`);
    }
  });

  // Check if we should use demo mode (default is REAL mode now)
  const useDemoMode = process.env.USE_DEMO_MODE === 'true';

  if (useDemoMode) {
    console.log('📍 DEMO MODE: Using demo app (no auth required)\n');

    // Navigate directly to demo app
    await page.goto('/demo-app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    console.log('✅ Demo mode loaded');
  } else {
    console.log('📍 REAL MODE: Logging in with credentials\n');

    // Navigate to login page
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    console.log('📍 On login page');

    // Fill in credentials
    const username = process.env.TEST_USER_EMAIL || 'test@test.com';
    const password = process.env.TEST_USER_PASSWORD || 'test123';

    console.log(`📧 Using username: ${username}`);

    // Find username input (first textbox)
    const usernameInput = page.locator('input[name="username"], input[type="text"], input[type="email"]').first();
    await usernameInput.fill(username);
    console.log('✅ Username filled');

    // Find password input
    const passwordInput = page.locator('input[type="password"]');
    await passwordInput.fill(password);
    console.log('✅ Password filled');

    // Click login button
    const loginButton = page.locator('button:has-text("Entrar"), button:has-text("Login")');
    console.log('🔍 Looking for login button...');
    await expect(loginButton).toBeVisible({ timeout: 5000 });
    console.log('✅ Login button found');

    await loginButton.click();
    console.log('🔑 Credentials submitted');

    // Wait a bit for the request to complete
    await page.waitForTimeout(3000);

    // Check current URL
    const currentUrl = page.url();
    console.log(`📍 Current URL after submit: ${currentUrl}`);

    // Wait for redirect to /app (not /demo-app)
    if (!currentUrl.includes('/app')) {
      console.log('⏳ Waiting for redirect to /app...');
      await page.waitForURL('**/app**', { timeout: 15000 });
    }

    console.log('✅ Logged in successfully');
  }

  console.log(`📍 Current URL: ${page.url()}`);

  // MANTER DEMO MODE para ter dados mockados
  // Mesmo no "modo real", precisamos de demo_mode=true para o backend retornar dados
  console.log('🔧 Garantindo demo_mode=true para dados mockados...');
  await page.evaluate(() => {
    localStorage.setItem('demo_mode', 'true');
  });
  console.log('✅ demo_mode habilitado (dados mockados disponíveis)');

  // Close welcome modal if present
  const skipButton = page.locator('text="Pular tudo"');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
    await page.waitForTimeout(500);
    console.log('✅ Closed welcome modal');
  }

  // Save signed-in state
  await page.context().storageState({ path: authFile });
  console.log(`💾 Auth state saved to ${authFile}\n`);
});
