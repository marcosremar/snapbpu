// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';

test.describe('Spot Reports Page Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    // Fill login form - using text input (not email type)
    await page.fill('input[type="text"]', 'test@test.com');
    await page.fill('input[type="password"]', 'test123');

    // Click login button
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForURL(/\/(dashboard|machines|metrics)?$/i, { timeout: 15000 });
    await page.waitForLoadState('networkidle');
  });

  test('should load GPU Metrics page', async ({ page }) => {
    // Navigate to metrics page
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.locator('h1:has-text("Métricas de GPU")')).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/metrics-page.png', fullPage: true });
  });

  test('should show all tabs including Spot Reports', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check all tabs are visible
    await expect(page.locator('button:has-text("Mercado")')).toBeVisible();
    await expect(page.locator('button:has-text("Provedores")')).toBeVisible();
    await expect(page.locator('button:has-text("Eficiência")')).toBeVisible();
    await expect(page.locator('button:has-text("Spot Reports")')).toBeVisible();

    // Take screenshot of tabs
    await page.screenshot({ path: 'tests/screenshots/metrics-tabs.png' });
  });

  test('should navigate to Spot Reports tab and show components', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click on Spot Reports tab
    await page.click('button:has-text("Spot Reports")');
    await page.waitForTimeout(3000); // Wait for data to load

    // Check that Spot Reports section title is visible
    await expect(page.locator('h2:has-text("Relatórios Spot")')).toBeVisible({ timeout: 10000 });

    // Take screenshot of Spot Reports tab
    await page.screenshot({ path: 'tests/screenshots/spot-reports-tab.png', fullPage: true });
  });

  test('should show Spot Monitor component', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click on Spot Reports tab
    await page.click('button:has-text("Spot Reports")');
    await page.waitForTimeout(5000);

    // Check for Spot Monitor card
    const spotMonitor = page.locator('.spot-card:has-text("Monitor de Preços Spot")');
    await expect(spotMonitor).toBeVisible({ timeout: 15000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/spot-monitor.png', fullPage: true });
  });

  test('should show multiple Spot components', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click on Spot Reports tab
    await page.click('button:has-text("Spot Reports")');
    await page.waitForTimeout(5000); // Wait for all components to load

    // Check for various Spot components (they may show "loading" or actual data)
    const spotCards = page.locator('.spot-card');
    const count = await spotCards.count();
    console.log(`Found ${count} spot cards`);

    // We expect at least some cards to be visible
    expect(count).toBeGreaterThan(0);

    // Take full page screenshot
    await page.screenshot({ path: 'tests/screenshots/spot-reports-full.png', fullPage: true });
  });

  test('should show Market tab with data', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Market tab should be active by default
    // Check for market summary cards or empty state
    const summaryCards = page.locator('.summary-card, .market-summary-grid, .empty-state');
    await expect(summaryCards.first()).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/market-tab.png', fullPage: true });
  });

  test('should show Providers tab with data', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click on Providers tab
    await page.click('button:has-text("Provedores")');
    await page.waitForTimeout(3000);

    // Check for providers table or empty state
    const providersSection = page.locator('.providers-section, .providers-table, .empty-state');
    await expect(providersSection.first()).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/providers-tab.png', fullPage: true });
  });

  test('should show Efficiency tab with data', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click on Efficiency tab
    await page.click('button:has-text("Eficiência")');
    await page.waitForTimeout(3000);

    // Check for efficiency grid or empty state
    const efficiencySection = page.locator('.efficiency-section, .efficiency-grid, .empty-state');
    await expect(efficiencySection.first()).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/efficiency-tab.png', fullPage: true });
  });

  test('should have working filters', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check filter controls
    const gpuFilter = page.locator('select.filter-select').first();
    await expect(gpuFilter).toBeVisible();

    // Check time range filter chips
    const timeChips = page.locator('.filter-chip');
    const chipCount = await timeChips.count();
    expect(chipCount).toBeGreaterThan(0);

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/filters.png' });
  });

});
