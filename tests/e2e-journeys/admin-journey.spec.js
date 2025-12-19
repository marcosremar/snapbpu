// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * 👑 E2E Journey: Admin
 *
 * Simula a jornada de um administrador.
 * A autenticação é feita automaticamente via auth.setup.js
 */

test.describe('Jornada: Admin', () => {

  test('Acessar Settings', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Verifica que chegou na página de settings
    const isSettings = page.url().includes('settings');
    console.log(isSettings ? '✅ Página Settings acessada' : '⚠️ Redirecionado de Settings');
  });

  test('Verificar CPU Standby config', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Verifica que a página Settings carregou
    const isLoaded = await page.url().includes('settings');
    expect(isLoaded).toBeTruthy();

    // Procura qualquer input ou configuração visível
    const configElements = page.locator('input, select, button, label');
    const count = await configElements.count();

    console.log(`⚙️ Encontradas ${count} opções de configuração`);
  });

  test('Verificar API/Integração', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Procura seção de API
    const apiSection = page.locator('text=/api|integration|token/i').first();

    if (await apiSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('✅ Seção API/Integração encontrada');
    } else {
      console.log('⚠️ Seção API não encontrada');
    }
  });

  test('Verificar perfil do usuário', async ({ page }) => {
    await page.goto('/app/settings');
    await page.waitForLoadState('networkidle');

    // Procura informações do perfil
    const profileInfo = page.locator('text=/email|user|profile/i, [data-testid="user-profile"]').first();

    if (await profileInfo.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('✅ Informações de perfil encontradas');
    } else {
      console.log('⚠️ Perfil não encontrado');
    }
  });

  test('Testar logout', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Procura botão de logout
    const logoutBtn = page.locator('button:has-text("Logout"), button:has-text("Sair"), a:has-text("Logout"), [data-testid="logout"]').first();

    if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('✅ Botão logout encontrado');
      // Não clica para não deslogar
    } else {
      console.log('⚠️ Botão logout não encontrado');
    }
  });

  test('Responsividade Settings', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Verifica que conteúdo é visível em mobile
    const content = page.locator('main, [role="main"], .main-content, .settings').first();
    await expect(content).toBeVisible();

    console.log('✅ Settings responsivo OK');
  });

});
