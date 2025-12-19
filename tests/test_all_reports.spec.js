// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';

// All reports from MetricsHub
const reports = [
  { tab: 'market', report: null, name: 'Mercado', file: 'report-market' },
  { tab: 'providers', report: null, name: 'Provedores', file: 'report-providers' },
  { tab: 'efficiency', report: null, name: 'Eficiência', file: 'report-efficiency' },
  { tab: 'spot', report: 'monitor', name: 'Monitor de Preços Spot', file: 'report-spot-monitor' },
  { tab: 'spot', report: 'savings', name: 'Calculadora de Economia', file: 'report-spot-savings' },
  { tab: 'spot', report: 'availability', name: 'Disponibilidade Instantânea', file: 'report-spot-availability' },
  { tab: 'spot', report: 'prediction', name: 'Previsão de Preços', file: 'report-spot-prediction' },
  { tab: 'spot', report: 'safe-windows', name: 'Janelas Seguras', file: 'report-spot-safe-windows' },
  { tab: 'spot', report: 'reliability', name: 'Score de Confiabilidade', file: 'report-spot-reliability' },
  { tab: 'spot', report: 'interruption', name: 'Taxa de Interrupção', file: 'report-spot-interruption' },
  { tab: 'spot', report: 'llm', name: 'Melhor GPU para LLM', file: 'report-spot-llm' },
  { tab: 'spot', report: 'training', name: 'Custo por Treinamento', file: 'report-spot-training' },
  { tab: 'spot', report: 'fleet', name: 'Estratégia de Fleet', file: 'report-spot-fleet' },
];

test.describe('All Reports Screenshots', () => {

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

  for (const report of reports) {
    test(`Screenshot: ${report.name}`, async ({ page }) => {
      // Build URL
      let url = `${BASE_URL}/metrics?tab=${report.tab}`;
      if (report.report) {
        url += `&report=${report.report}`;
      }

      // Navigate to the report
      await page.goto(url);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000); // Wait for data to load

      // Verify we're on the metrics page
      await expect(page.locator('.metrics-container')).toBeVisible({ timeout: 10000 });

      // Take screenshot
      await page.screenshot({
        path: `tests/screenshots/${report.file}.png`,
        fullPage: true
      });

      console.log(`Screenshot saved: ${report.file}.png`);
    });
  }

});
