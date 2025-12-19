const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';

test('Capture efficiency tab layout', async ({ page }) => {
  // Login to production site
  await page.goto(`${BASE_URL}/login`);
  await page.locator('input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin123');
  await page.click('button:has-text("Login")');

  // Wait for redirect to dashboard
  await page.waitForTimeout(3000);

  // Go to Metrics > Efficiency tab
  await page.goto(`${BASE_URL}/metrics?tab=efficiency`);

  // Wait for the page to load and data to render
  await page.waitForTimeout(4000);

  // Take screenshot
  await page.screenshot({
    path: 'screenshots/review/efficiency-new-layout.png',
    fullPage: true
  });

  console.log('Screenshot saved: screenshots/review/efficiency-new-layout.png');
});
