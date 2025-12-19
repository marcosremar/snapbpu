const { test, expect } = require('@playwright/test');

test('Login and Logout Functionality - Complete Flow', async ({ page }) => {
  console.log('\n=== INICIANDO TESTE DE LOGIN E LOGOUT ===\n');

  // Setup: Capture console logs
  page.on('console', msg => console.log(`[CONSOLE] ${msg.type()}: ${msg.text()}`));

  // STEP 1: Navigate to home and log in
  console.log('--- STEP 1: Login Flow ---');
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle', timeout: 30000 });

  // Click login button
  const loginBtn = page.locator('button:has-text("Login")').first();
  await loginBtn.click();
  await page.waitForTimeout(500);

  // Fill form
  const emailInput = page.locator('input[type="email"]').first();
  const passwordInput = page.locator('input[type="password"]').first();
  await emailInput.fill('marcosremar@gmail.com');
  await passwordInput.fill('123456');
  await page.waitForTimeout(300);

  // Submit form via JavaScript click to ensure React handler is called
  await page.evaluate(() => {
    const btn = document.querySelector('button[type="submit"]');
    if (btn) btn.click();
  });

  // Wait for login to complete
  console.log('Waiting for login API response...');
  await page.waitForTimeout(3000);

  // Verify token was saved
  const token = await page.evaluate(() => localStorage.getItem('auth_token'));
  console.log(`Token saved to localStorage: ${token ? 'YES' : 'NO'}`);
  expect(token).toBeTruthy();

  // Navigate to /app to access dashboard
  console.log('\n--- STEP 2: Navigate to Dashboard ---');
  await page.goto('https://dumontcloud.com/app', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(2000);

  // Verify we're on the dashboard and can see logout button
  const logoutBtn = page.locator('button:has-text("Logout")').first();
  const logoutBtnCount = await logoutBtn.count();
  console.log(`Logout button visible: ${logoutBtnCount > 0 ? 'YES' : 'NO'}`);
  expect(logoutBtnCount).toBeGreaterThan(0);

  // STEP 3: Test logout
  console.log('\n--- STEP 3: Logout Flow ---');
  console.log('Clicking logout button...');
  await logoutBtn.click();
  await page.waitForTimeout(2000);

  // Verify token was removed
  const tokenAfterLogout = await page.evaluate(() => localStorage.getItem('auth_token'));
  console.log(`Token after logout: ${tokenAfterLogout ? 'STILL PRESENT' : 'REMOVED'}`);
  expect(tokenAfterLogout).toBeNull();

  // Verify we're redirected
  const url = page.url();
  console.log(`URL after logout: ${url}`);
  const isRedirected = url.includes('login') || url === 'https://dumontcloud.com/';
  expect(isRedirected).toBeTruthy();

  console.log('\n✅ LOGIN AND LOGOUT TEST PASSED\n');
});
