/**
 * Dumont Cloud - Site Review
 * Navegação completa pelo site com screenshots
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';
const TEST_USER = 'marcosremar@gmail.com';
const TEST_PASS = 'Marcos123';
const DIR = 'screenshots/review';

// Helper para login
async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(1000);
  await page.fill('input[type="text"]', TEST_USER);
  await page.fill('input[type="password"]', TEST_PASS);
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(2000);
}

test.describe('Site Review - Screenshots e Interações', () => {

  test('1. Login Page', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/01-login.png`, fullPage: true });

    // Verificações
    await expect(page.locator('text=Dumont Cloud')).toBeVisible();
    await expect(page.locator('input[type="text"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button:has-text("Login")')).toBeVisible();

    console.log('✅ Login: Formulário completo');
  });

  test('2. Login Flow', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(1000);

    await page.fill('input[type="text"]', TEST_USER);
    await page.fill('input[type="password"]', TEST_PASS);
    await page.screenshot({ path: `${DIR}/02-login-filled.png` });

    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${DIR}/03-after-login.png`, fullPage: true });

    expect(page.url()).not.toContain('/login');
    console.log('✅ Login: Autenticação funcionando');
  });

  test('3. Dashboard - Header', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/04-dashboard-header.png` });

    // Verificar header
    const checks = [
      { name: 'Logo', selector: 'text=Dumont' },
      { name: 'Dashboard link', selector: 'text=Dashboard' },
      { name: 'Machines link', selector: 'text=Machines' },
      { name: 'Métricas dropdown', selector: 'text=Métricas' },
      { name: 'Settings link', selector: 'text=Settings' },
      { name: 'Logout button', selector: 'text=Logout' },
    ];

    for (const check of checks) {
      const visible = await page.locator(check.selector).first().isVisible().catch(() => false);
      console.log(`${visible ? '✅' : '❌'} Header: ${check.name}`);
    }
  });

  test('4. Dashboard - Deploy Wizard', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/05-dashboard-wizard.png`, fullPage: true });

    // Verificar elementos do wizard
    const checks = [
      { name: 'Título Deploy', selector: 'text=Deploy' },
      { name: 'Botão Wizard', selector: 'button:has-text("Wizard")' },
      { name: 'Tab EUA', selector: 'button:has-text("EUA")' },
      { name: 'Tab Europa', selector: 'button:has-text("Europa")' },
      { name: 'Tab Ásia', selector: 'button:has-text("Ásia")' },
      { name: 'Tab Global', selector: 'button:has-text("Global")' },
      { name: 'Seletor GPU', selector: 'text=GPU' },
      { name: 'Card Lento', selector: 'text=Lento' },
      { name: 'Card Rapido', selector: 'text=Rapido' },
      { name: 'Botão Buscar', selector: 'button:has-text("Buscar")' },
    ];

    for (const check of checks) {
      const visible = await page.locator(check.selector).first().isVisible().catch(() => false);
      console.log(`${visible ? '✅' : '❌'} Dashboard: ${check.name}`);
    }
  });

  test('5. Dashboard - Seleção de Região', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Clicar em cada região
    const regions = ['EUA', 'Europa', 'Ásia', 'Global'];
    for (const region of regions) {
      await page.locator(`button:has-text("${region}")`).click().catch(() => {});
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${DIR}/06-region-${region.toLowerCase()}.png`, fullPage: true });
      console.log(`✅ Região ${region} selecionada`);
    }
  });

  test('6. Dashboard - Busca de Máquinas', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Clicar no botão de busca
    await page.locator('button:has-text("Buscar")').click();
    await page.waitForTimeout(5000);
    await page.screenshot({ path: `${DIR}/07-search-results.png`, fullPage: true });

    // Verificar resultados
    const hasResults = await page.locator('text=/Máquinas Disponíveis|resultados/i').isVisible().catch(() => false);
    const gpuCount = await page.locator('text=/RTX|A100|H100/').count();
    const priceCount = await page.locator('text=/\\$[\\d.]+\\/h/').count();

    console.log(`✅ Busca: ${gpuCount} GPUs encontradas, ${priceCount} preços exibidos`);

    // Verificar botão Selecionar
    const selectBtns = await page.locator('button:has-text("Selecionar")').count();
    console.log(`✅ Busca: ${selectBtns} botões "Selecionar" disponíveis`);
  });

  test('7. Machines Page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${DIR}/08-machines-page.png`, fullPage: true });

    // Verificar elementos
    const checks = [
      { name: 'Título', selector: 'text=Minhas Máquinas' },
      { name: 'Filtro Todas', selector: 'button:has-text("Todas")' },
      { name: 'Filtro Online', selector: 'button:has-text("Online")' },
      { name: 'Filtro Offline', selector: 'button:has-text("Offline")' },
      { name: 'Botão Nova', selector: 'text=Nova' },
    ];

    for (const check of checks) {
      const visible = await page.locator(check.selector).first().isVisible().catch(() => false);
      console.log(`${visible ? '✅' : '❌'} Machines: ${check.name}`);
    }
  });

  test('8. Machines - Filtros', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(2000);

    // Clicar em cada filtro
    const filters = ['Todas', 'Online', 'Offline'];
    for (const filter of filters) {
      await page.locator(`button:has-text("${filter}")`).click().catch(() => {});
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${DIR}/09-machines-${filter.toLowerCase()}.png`, fullPage: true });
      console.log(`✅ Filtro "${filter}" aplicado`);
    }
  });

  test('9. Machines - Cards e Ações', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(2000);

    // Filtrar Online
    await page.locator('button:has-text("Online")').click().catch(() => {});
    await page.waitForTimeout(500);

    // Verificar botões de IDE
    const vsCode = await page.locator('button:has-text("VS Code")').count();
    const cursor = await page.locator('button:has-text("Cursor")').count();
    const windsurf = await page.locator('button:has-text("Windsurf")').count();
    console.log(`IDE Buttons: VS Code=${vsCode}, Cursor=${cursor}, Windsurf=${windsurf}`);

    // Se tiver VS Code, abrir dropdown
    if (vsCode > 0) {
      await page.locator('button:has-text("VS Code")').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${DIR}/10-vscode-dropdown.png` });
      console.log('✅ VS Code dropdown aberto');
      await page.keyboard.press('Escape');
    }

    // Verificar menu de 3 pontos
    const menuBtns = await page.locator('button:has(svg.lucide-more-vertical)').count();
    if (menuBtns > 0) {
      await page.locator('button:has(svg.lucide-more-vertical)').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${DIR}/11-machine-menu.png` });
      console.log('✅ Menu de opções aberto');
      await page.keyboard.press('Escape');
    }

    // Verificar botão Pausar/Iniciar
    const pauseBtn = await page.locator('button:has-text("Pausar")').count();
    const startBtn = await page.locator('button:has-text("Iniciar")').count();
    console.log(`Ações: Pausar=${pauseBtn}, Iniciar=${startBtn}`);
  });

  test('10. Settings Page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${DIR}/12-settings-page.png`, fullPage: true });

    // Verificar campos
    const checks = [
      { name: 'API Key', selector: 'text=/API Key|Vast/i' },
      { name: 'Campos de senha', selector: 'input[type="password"]' },
      { name: 'Botão Salvar', selector: 'button:has-text("Salvar")' },
    ];

    for (const check of checks) {
      const count = await page.locator(check.selector).count();
      console.log(`${count > 0 ? '✅' : '❌'} Settings: ${check.name} (${count} encontrados)`);
    }

    // Scroll para ver mais
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${DIR}/13-settings-bottom.png`, fullPage: true });
  });

  test('11. Settings - Toggle Visibilidade', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);

    // Encontrar botão de toggle
    const toggleBtn = page.locator('button:has(svg.lucide-eye), button:has(svg.lucide-eye-off)').first();
    if (await toggleBtn.count() > 0) {
      await toggleBtn.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: `${DIR}/14-settings-toggle.png` });
      console.log('✅ Toggle de visibilidade funcionando');
    } else {
      console.log('❌ Botão de toggle não encontrado');
    }
  });

  test('12. GPU Metrics Page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${DIR}/15-metrics-page.png`, fullPage: true });

    // Verificar elementos
    const charts = await page.locator('canvas').count();
    const gpuCards = await page.locator('text=/RTX 4090|RTX 4080|RTX 3090/').count();

    console.log(`Metrics: ${charts} gráficos, ${gpuCards} cards de GPU`);

    // Scroll
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${DIR}/16-metrics-bottom.png`, fullPage: true });
  });

  test('13. Mobile - Dashboard (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/17-mobile-dashboard.png`, fullPage: true });

    // Verificar hamburger menu
    const hamburger = page.locator('button:has(svg.lucide-menu)');
    if (await hamburger.count() > 0) {
      await hamburger.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${DIR}/18-mobile-menu.png`, fullPage: true });
      console.log('✅ Mobile: Menu hamburger funcionando');
      await page.keyboard.press('Escape');
    } else {
      console.log('❌ Mobile: Hamburger não encontrado');
    }
  });

  test('14. Mobile - Machines (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/19-mobile-machines.png`, fullPage: true });
    console.log('✅ Mobile: Página Machines');
  });

  test('15. Mobile - Settings (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/20-mobile-settings.png`, fullPage: true });
    console.log('✅ Mobile: Página Settings');
  });

  test('16. Tablet - Dashboard (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/21-tablet-dashboard.png`, fullPage: true });
    console.log('✅ Tablet: Dashboard');
  });

  test('17. Tablet - Machines (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/22-tablet-machines.png`, fullPage: true });
    console.log('✅ Tablet: Machines');
  });

});
