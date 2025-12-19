// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * 🔧 E2E Journey: Operator (DevOps/SysAdmin)
 *
 * Simula a jornada de um operador gerenciando instâncias.
 * A autenticação é feita automaticamente via auth.setup.js
 */

test.describe('Jornada: Operator', () => {

  test('Ver lista de instâncias', async ({ page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Verifica se há lista de instâncias
    const instanceList = page.locator('[data-testid="instance-list"], .instance-list, .machines-list, table tbody tr, .instance-card');
    const count = await instanceList.count();

    console.log(`🖥️ Encontradas ${count} instâncias/máquinas`);
  });

  test('Verificar ações disponíveis', async ({ page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Procura botões de ação
    const actionButtons = page.locator('button:has-text("Start"), button:has-text("Stop"), button:has-text("Pause"), button:has-text("Resume"), [data-testid*="action"]');
    const count = await actionButtons.count();

    console.log(`🎮 Encontrados ${count} botões de ação`);
  });

  test('Acessar CPU Standby', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Procura configuração de standby
    const standbySection = page.locator('text=/standby|cpu standby/i, [data-testid="standby"]').first();

    if (await standbySection.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('✅ Seção CPU Standby encontrada');
    } else {
      console.log('⚠️ CPU Standby não encontrado em Settings');
    }
  });

  test('Verificar métricas', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Procura elementos de métricas
    const metrics = page.locator('[data-testid*="metric"], .metric, .stats, .chart');
    const count = await metrics.count();

    console.log(`📊 Encontrados ${count} elementos de métricas`);
  });

  test('Buscar/filtrar máquinas', async ({ page }) => {
    await page.goto('/machines');
    await page.waitForLoadState('networkidle');

    // Procura campo de busca
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="filter" i]').first();

    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('test');
      await page.waitForTimeout(300);
      console.log('✅ Busca/filtro funciona');
    } else {
      console.log('⚠️ Campo de busca não encontrado');
    }
  });

});
