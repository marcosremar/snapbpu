// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8766';
const TEST_USER = 'test@test.com';
const TEST_PASSWORD = 'test123';

test('take machines page screenshot', async ({ page }) => {
  // Login
  await page.goto(`${BASE_URL}/`);
  await page.locator('input').first().fill(TEST_USER);
  await page.locator('input[type="password"]').fill(TEST_PASSWORD);
  await page.locator('button:has-text("Login")').click();
  await page.waitForTimeout(2000);

  // Go to machines
  await page.goto(`${BASE_URL}/machines`);
  await page.waitForTimeout(3000);

  // Take screenshot
  await page.screenshot({ path: 'screenshots/machines-with-providers.png', fullPage: true });

  // Check for Vast.ai badge
  const vastBadge = page.locator('text=Vast.ai');
  const vastCount = await vastBadge.count();
  console.log(`Vast.ai badges: ${vastCount}`);

  // Check for GCP badge
  const gcpBadge = page.locator('text=GCP');
  const gcpCount = await gcpBadge.count();
  console.log(`GCP badges: ${gcpCount}`);

  // Check machine cards
  const cards = page.locator('[class*="rounded-lg"][class*="border"]');
  const cardCount = await cards.count();
  console.log(`Machine cards: ${cardCount}`);
});
