const { test, expect } = require('@playwright/test');

test('Token Persistence Debug - Step by Step', async ({ page }) => {
  console.log('\n=== INICIANDO DEBUG DE PERSISTÊNCIA DE TOKEN ===\n');

  // Capture all network requests
  const requestLogs = [];
  const responseLogs = [];

  page.on('request', request => {
    requestLogs.push({
      url: request.url(),
      method: request.method(),
      headers: request.allHeaders(),
      postData: request.postData()
    });
  });

  page.on('response', response => {
    responseLogs.push({
      url: response.url(),
      status: response.status(),
      statusText: response.statusText(),
      headers: response.headers()
    });
  });

  // Capture console messages
  page.on('console', msg => {
    console.log(`[CONSOLE] ${msg.type()}: ${msg.text()}`);
  });

  // STEP 1: Navigate to homepage
  console.log('\n--- STEP 1: Navigating to homepage ---');
  await page.goto('https://dumontcloud.com', {
    waitUntil: 'networkidle',
    timeout: 30000
  });
  console.log('✓ Homepage loaded');
  console.log(`Current URL: ${page.url()}`);

  // Check initial localStorage state
  const initialStorage = await page.evaluate(() => {
    return {
      keys: Object.keys(localStorage),
      auth_token: localStorage.getItem('auth_token'),
      token: localStorage.getItem('token'),
      sessionStorage: Object.keys(sessionStorage)
    };
  });
  console.log('Initial localStorage state:', JSON.stringify(initialStorage, null, 2));

  // STEP 2: Click login button
  console.log('\n--- STEP 2: Clicking login button ---');
  const loginBtn = page.locator('button:has-text("Login")').first();
  const isVisible = await loginBtn.isVisible();
  console.log(`Login button visible: ${isVisible}`);

  if (isVisible) {
    await loginBtn.click();
    await page.waitForTimeout(1000);
    console.log('✓ Login button clicked');
  }

  // STEP 3: Fill form
  console.log('\n--- STEP 3: Filling login form ---');
  const emailInput = page.locator('input[type="email"]').first();
  const passwordInput = page.locator('input[type="password"]').first();

  await emailInput.fill('marcosremar@gmail.com');
  await passwordInput.fill('123456');
  console.log('✓ Form filled with credentials');

  // STEP 4: Monitor what happens during submit
  console.log('\n--- STEP 4: Submitting form and monitoring ---');

  // Intercept the login API call
  const loginPromise = page.waitForResponse(response =>
    response.url().includes('/api/auth/login') || response.url().includes('/api/v1/auth/login')
  );

  // Submit the form
  const submitBtn = page.locator('button[type="submit"]').first();
  await submitBtn.click();
  console.log('✓ Submit button clicked');

  // Wait for the API response
  try {
    const loginResponse = await loginPromise;
    console.log(`\n✓ Login API responded with status ${loginResponse.status()}`);

    const responseBody = await loginResponse.json();
    console.log('API Response:', JSON.stringify(responseBody, null, 2));

    if (responseBody.token) {
      console.log(`✓ Token received from API: ${responseBody.token.substring(0, 50)}...`);
    } else {
      console.log('⚠ No token in API response!');
    }
  } catch (e) {
    console.log(`⚠ Login API call not intercepted: ${e.message}`);
  }

  // STEP 5: Check localStorage immediately after submit
  console.log('\n--- STEP 5: Checking localStorage after submit ---');
  await page.waitForTimeout(500);

  const afterSubmitStorage = await page.evaluate(() => {
    console.log('[BROWSER] Checking localStorage from browser context');
    console.log('[BROWSER] localStorage keys:', Object.keys(localStorage));
    console.log('[BROWSER] auth_token value:', localStorage.getItem('auth_token'));

    return {
      keys: Object.keys(localStorage),
      auth_token: localStorage.getItem('auth_token'),
      token: localStorage.getItem('token'),
      sessionStorage_keys: Object.keys(sessionStorage),
      sessionStorage_token: sessionStorage.getItem('auth_token')
    };
  });
  console.log('After submit storage state:', JSON.stringify(afterSubmitStorage, null, 2));

  // STEP 6: Wait for navigation
  console.log('\n--- STEP 6: Waiting for navigation ---');
  await page.waitForTimeout(2000);
  console.log(`Current URL: ${page.url()}`);

  // STEP 7: Check localStorage again after waiting
  console.log('\n--- STEP 7: Final localStorage check ---');
  const finalStorage = await page.evaluate(() => {
    return {
      keys: Object.keys(localStorage),
      auth_token: localStorage.getItem('auth_token'),
      token: localStorage.getItem('token'),
      sessionStorage_keys: Object.keys(sessionStorage),
      sessionStorage_token: sessionStorage.getItem('auth_token')
    };
  });
  console.log('Final storage state:', JSON.stringify(finalStorage, null, 2));

  // STEP 8: Check if we can see Dashboard elements
  console.log('\n--- STEP 8: Looking for Dashboard elements ---');
  const dashboardElements = await page.locator('text=Dashboard').count();
  const logoutElements = await page.locator('button:has-text("Logout")').count();
  console.log(`Dashboard elements found: ${dashboardElements}`);
  console.log(`Logout buttons found: ${logoutElements}`);

  // STEP 9: Try to access /app directly
  console.log('\n--- STEP 9: Attempting to access /app directly ---');
  await page.goto('https://dumontcloud.com/app', {
    waitUntil: 'networkidle',
    timeout: 10000
  }).catch(() => console.log('Navigation to /app timed out'));

  console.log(`URL after /app navigation: ${page.url()}`);

  const appStorage = await page.evaluate(() => {
    return {
      auth_token: localStorage.getItem('auth_token'),
      sessionStorage_token: sessionStorage.getItem('auth_token')
    };
  });
  console.log('Storage on /app page:', JSON.stringify(appStorage, null, 2));

  // Print request/response summary
  console.log('\n=== NETWORK REQUEST/RESPONSE SUMMARY ===');
  const loginRequests = requestLogs.filter(r => r.url.includes('/auth/login'));
  const loginResponses = responseLogs.filter(r => r.url.includes('/auth/login'));

  console.log(`\nLogin API Requests: ${loginRequests.length}`);
  loginRequests.forEach((req, i) => {
    console.log(`  [${i}] ${req.method} ${req.url}`);
    if (req.postData) {
      try {
        const data = JSON.parse(req.postData);
        console.log(`       Body: ${JSON.stringify(data)}`);
      } catch (e) {
        console.log(`       Body: ${req.postData}`);
      }
    }
  });

  console.log(`\nLogin API Responses: ${loginResponses.length}`);
  loginResponses.forEach((res, i) => {
    console.log(`  [${i}] ${res.status} ${res.statusText} ${res.url}`);
  });

  console.log('\n=== FIM DEBUG ===\n');

  // Always pass - this is a debug test
  expect(true).toBe(true);
});
