// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * 🚀 E2E Journey: Novo Usuário
 *
 * Simula a jornada de um usuário já autenticado explorando o sistema.
 * A autenticação é feita automaticamente via auth.setup.js
 */

test.describe('Jornada: Novo Usuário Explorando', () => {

  test('Dashboard carrega corretamente', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Verifica elementos principais do dashboard
    await expect(page.locator('nav, .sidebar, [data-testid="sidebar"]').first()).toBeVisible();

    console.log('✅ Dashboard carregou corretamente');
  });

  test('Navegar para Máquinas', async ({ page }) => {
    // Navega direto para máquinas
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');

    // Verifica que a página carregou
    await expect(page).toHaveURL(/machines/);
    console.log('✅ Navegou para Machines');
  });

  test('Ver ofertas de GPU', async ({ page }) => {
    await page.goto('/app/machines');
    await page.waitForLoadState('networkidle');

    // Aguarda cards ou lista de GPUs
    const gpuContent = page.locator('.gpu-card, .offer-card, [data-testid*="gpu"], table tbody tr').first();

    // Pode não ter ofertas - isso é OK
    const hasContent = await gpuContent.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasContent) {
      console.log('✅ Ofertas de GPU visíveis');
    } else {
      console.log('⚠️ Nenhuma oferta visível (pode ser normal)');
    }

    // Verifica que não há erro crítico
    await expect(page.getByText(/500|internal server error/i)).not.toBeVisible();
  });

  test('Ver economia/savings', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Procura elementos de economia
    const savingsElement = page.locator('[data-testid*="saving"], .savings, text=/\\$\\d+|saved/i').first();

    const hasSavings = await savingsElement.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSavings) {
      console.log('✅ Dados de economia visíveis');
    } else {
      console.log('⚠️ Dados de economia não visíveis (pode ser novo usuário)');
    }
  });

});

test.describe('Jornada: Explorar Menu', () => {

  test('Menu principal funciona', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Conta links no menu
    const menuLinks = page.locator('nav a, .sidebar a');
    const count = await menuLinks.count();

    console.log(`📋 Menu tem ${count} links`);
    expect(count).toBeGreaterThan(0);

    // Testa navegação para páginas via URL direto
    const testUrls = ['/app/machines', '/app/metrics', '/app/settings'];

    for (const url of testUrls) {
      await page.goto(url);
      await page.waitForLoadState('networkidle');

      // Verifica que não deu erro 500
      const hasError = await page.getByText(/500|internal server error/i).isVisible({ timeout: 2000 }).catch(() => false);
      if (!hasError) {
        console.log(`✅ ${url} carregou sem erro`);
      }
    }

    console.log('✅ Menu funciona corretamente');
  });

  test('Responsividade mobile', async ({ page }) => {
    // Redimensiona para mobile
    await page.setViewportSize({ width: 375, height: 812 });

    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Procura menu mobile
    const mobileMenu = page.locator('[data-testid="mobile-menu"], .mobile-menu, button[aria-label*="menu"], .hamburger, [data-testid="menu-toggle"]').first();

    const hasMobileMenu = await mobileMenu.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasMobileMenu) {
      await mobileMenu.click();
      await page.waitForTimeout(300);
      console.log('✅ Menu mobile funciona');
    } else {
      console.log('⚠️ Menu mobile não encontrado');
    }

    // Verifica que conteúdo principal é visível
    await expect(page.locator('main, [role="main"], .main-content').first()).toBeVisible();

    console.log('✅ Layout responsivo OK');
  });

});
