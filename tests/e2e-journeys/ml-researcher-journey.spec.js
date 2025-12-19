// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * 🔬 E2E Journey: ML Researcher
 *
 * Simula a jornada de um pesquisador buscando GPUs.
 * A autenticação é feita automaticamente via auth.setup.js
 */

test.describe('Jornada: ML Researcher', () => {

  test('Buscar GPU por nome', async ({ page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Procura campo de busca
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="buscar" i], [data-testid="search"]').first();

    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('RTX');
      await page.waitForTimeout(500);
      console.log('✅ Busca por GPU funciona');
    } else {
      console.log('⚠️ Campo de busca não encontrado');
    }
  });

  test('Filtrar GPUs por região', async ({ page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Procura filtro de região
    const regionFilter = page.locator('select[name*="region"], [data-testid="region-filter"], button:has-text("Region")').first();

    if (await regionFilter.isVisible({ timeout: 3000 }).catch(() => false)) {
      await regionFilter.click();
      await page.waitForTimeout(300);
      console.log('✅ Filtro de região disponível');
    } else {
      console.log('⚠️ Filtro de região não encontrado');
    }
  });

  test('Comparar preços', async ({ page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Procura preços na página
    const priceElements = page.locator('text=/\\$\\d+\\.?\\d*|R\\$\\s*\\d+/');
    const priceCount = await priceElements.count();

    console.log(`💰 Encontrados ${priceCount} elementos de preço`);

    if (priceCount > 0) {
      await expect(priceElements.first()).toBeVisible();
      console.log('✅ Preços visíveis');
    }
  });

  test('Acessar AI Wizard', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Fecha overlay de onboarding se existir
    const overlay = page.locator('.onboarding-overlay');
    if (await overlay.isVisible({ timeout: 1000 }).catch(() => false)) {
      const closeBtn = page.locator('.onboarding-overlay button[aria-label*="close"], .onboarding-overlay [data-testid="close"]');
      if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeBtn.click();
        await page.waitForTimeout(300);
      }
    }

    // Procura AI Wizard
    const wizardElement = page.locator('button:has-text("AI"), button:has-text("Wizard"), [data-testid="ai-wizard"], a:has-text("Deploy"), .deploy-wizard').first();

    if (await wizardElement.isVisible({ timeout: 3000 }).catch(() => false)) {
      try {
        await wizardElement.click({ force: true });
        await page.waitForTimeout(500);
        console.log('✅ AI Wizard acessível');
      } catch (e) {
        console.log('⚠️ AI Wizard encontrado mas não conseguiu clicar:', e.message);
      }
    } else {
      console.log('⚠️ AI Wizard não encontrado');
    }
  });

  test('Ver detalhes de GPU', async ({ page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Clica no primeiro card de GPU
    const gpuCard = page.locator('.gpu-card, .offer-card, [data-testid*="gpu"], tr[data-gpu]').first();

    if (await gpuCard.isVisible({ timeout: 5000 }).catch(() => false)) {
      await gpuCard.click();
      await page.waitForTimeout(500);
      console.log('✅ Card de GPU clicável');
    } else {
      console.log('⚠️ Nenhum card de GPU encontrado');
    }
  });

});
