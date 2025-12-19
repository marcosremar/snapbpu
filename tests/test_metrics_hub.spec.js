// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';

test.describe('Metrics Hub Page Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    // Fill login form
    await page.fill('input[type="text"]', 'test@test.com');
    await page.fill('input[type="password"]', 'test123');

    // Click login button
    await page.click('button[type="submit"]');

    // Wait for redirect
    await page.waitForURL(/\/(dashboard|machines|metrics)?$/i, { timeout: 15000 });
    await page.waitForLoadState('networkidle');
  });

  test('should load Metrics Hub page from menu', async ({ page }) => {
    // Click on Métricas in the menu
    await page.click('a[href="/metrics-hub"]');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check page title
    await expect(page.locator('h1:has-text("Central de Métricas")')).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/metrics-hub.png', fullPage: true });
  });

  test('should show all metric categories', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics-hub`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check for category sections
    await expect(page.locator('h2:has-text("Visão Geral")')).toBeVisible();
    await expect(page.locator('h2:has-text("Relatórios Spot")')).toBeVisible();
    await expect(page.locator('h2:has-text("Confiabilidade")')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/metrics-hub-categories.png', fullPage: true });
  });

  test('should show metric cards with descriptions', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics-hub`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check for some specific metric cards
    await expect(page.locator('.metric-card:has-text("Mercado de GPUs")')).toBeVisible();
    await expect(page.locator('.metric-card:has-text("Monitor de Preços Spot")')).toBeVisible();
    await expect(page.locator('.metric-card:has-text("Calculadora de Economia")')).toBeVisible();
    await expect(page.locator('.metric-card:has-text("Melhor GPU para LLM")')).toBeVisible();

    // Count total metric cards
    const cardCount = await page.locator('.metric-card').count();
    console.log(`Found ${cardCount} metric cards`);
    expect(cardCount).toBeGreaterThanOrEqual(10);

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/metrics-hub-cards.png', fullPage: true });
  });

  test('should navigate to GPU Metrics page when clicking card', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics-hub`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click on "Mercado de GPUs" card
    await page.click('.metric-card:has-text("Mercado de GPUs")');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Should be on metrics page
    await expect(page).toHaveURL(/\/metrics/);
    await expect(page.locator('h1:has-text("Métricas de GPU")')).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/metrics-from-hub.png', fullPage: true });
  });

  test('should navigate to Spot Reports when clicking Spot card', async ({ page }) => {
    await page.goto(`${BASE_URL}/metrics-hub`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click on "Monitor de Preços Spot" card (first Spot report card)
    await page.click('.metric-card:has-text("Monitor de Preços Spot")');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Should be on metrics page with spot tab
    await expect(page).toHaveURL(/\/metrics.*tab=spot/);

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/spot-from-hub.png', fullPage: true });
  });

});
