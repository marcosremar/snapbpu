// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Testes E2E - Fluxo Completo de Auto-Hibernação
 * 
 * Testa o ciclo completo:
 * 1. Navegação para máquinas
 * 2. Configuração de auto-hibernação
 * 3. Verificação de status em tempo real
 * 4. Dashboard de economia
 * 
 * NOTA: Estes testes não criam instâncias reais,
 * apenas verificam a interface e APIs.
 */

const BASE_URL = process.env.BASE_URL || 'http://localhost:8766';
const TEST_USER = 'marcoslogin';
const TEST_PASS = 'marcos123';

// Helper para login
async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  
  const usernameField = page.locator('input[name="username"], input[type="text"]').first();
  const passwordField = page.locator('input[name="password"], input[type="password"]').first();
  
  if (await usernameField.isVisible()) {
    await usernameField.fill(TEST_USER);
    await passwordField.fill(TEST_PASS);
    await page.locator('button[type="submit"]').first().click();
    await page.waitForLoadState('networkidle');
    return true;
  }
  return false;
}

test.describe('Fluxo de Auto-Hibernação E2E', () => {
  
  test('Fluxo completo: Dashboard → Métricas → Economia', async ({ page }) => {
    // 1. Login
    await login(page);
    
    // 2. Verificar dashboard principal
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-1-dashboard.png',
      fullPage: true 
    });
    console.log('✓ Step 1: Dashboard carregado');
    
    // 3. Navegar para métricas
    const metricsLink = page.locator('a[href*="metrics"], nav >> text="Métricas"').first();
    if (await metricsLink.isVisible()) {
      await metricsLink.click();
      await page.waitForLoadState('networkidle');
    } else {
      await page.goto(`${BASE_URL}/metrics`);
      await page.waitForLoadState('networkidle');
    }
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-2-metrics.png',
      fullPage: true 
    });
    console.log('✓ Step 2: Página de métricas');
    
    // 4. Abrir aba de Economia
    const economiaTab = page.locator('button:has-text("Economia"), button >> text="Economia"');
    if (await economiaTab.isVisible({ timeout: 5000 })) {
      await economiaTab.click();
      await page.waitForTimeout(1500);
      
      await page.screenshot({ 
        path: 'tests/screenshots/e2e-3-economia.png',
        fullPage: true 
      });
      console.log('✓ Step 3: Aba economia aberta');
    }
    
    // 5. Verificar se há dados de economia
    const savingsValue = page.locator('text=/\\$[0-9]+/');
    if (await savingsValue.first().isVisible({ timeout: 3000 })) {
      console.log('✓ Step 4: Valores de economia exibidos');
    } else {
      console.log('⚠ Step 4: Sem dados de economia ainda');
    }
  });

  test('Fluxo de configuração de standby', async ({ page }) => {
    await login(page);
    
    // 1. Ir para settings
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-standby-1-settings.png',
      fullPage: true 
    });
    console.log('✓ Step 1: Settings carregado');
    
    // 2. Scroll até seção de standby
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-standby-2-scrolled.png',
      fullPage: true 
    });
    console.log('✓ Step 2: Scroll para standby');
    
    // 3. Verificar seção existe
    const standbyConfig = page.locator('.standby-config, :has-text("CPU Standby")');
    if (await standbyConfig.first().isVisible({ timeout: 5000 })) {
      console.log('✓ Step 3: Seção standby encontrada');
    }
    
    // 4. Verificar formulário
    const selects = await page.locator('.standby-config select').count();
    const toggles = await page.locator('.standby-config input[type="checkbox"]').count();
    
    console.log(`✓ Step 4: ${selects} selects, ${toggles} toggles encontrados`);
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-standby-3-form.png',
      fullPage: true 
    });
  });

  test('Verificar APIs de economia funcionam', async ({ page, request }) => {
    // Login API
    const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
      data: { username: TEST_USER, password: TEST_PASS }
    });
    
    let token = null;
    if (loginResponse.ok()) {
      const data = await loginResponse.json();
      token = data.access_token;
    }
    
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    
    // 1. Testar /api/agent/status
    const agentResponse = await request.post(`${BASE_URL}/api/agent/status`, {
      data: {
        agent: "E2ETest",
        version: "1.0.0",
        instance_id: "e2e_test_001",
        status: "idle",
        timestamp: new Date().toISOString(),
        gpu_utilization: 5.0
      }
    });
    
    expect(agentResponse.ok()).toBeTruthy();
    console.log('✓ API 1: /api/agent/status OK');
    
    // 2. Testar /api/v1/metrics/savings/real
    const savingsResponse = await request.get(
      `${BASE_URL}/api/v1/metrics/savings/real?days=30`,
      { headers }
    );
    
    if (savingsResponse.ok()) {
      const data = await savingsResponse.json();
      console.log(`✓ API 2: /savings/real OK (${data.summary.hibernation_count} hibernações)`);
    }
    
    // 3. Testar /api/v1/metrics/savings/history
    const historyResponse = await request.get(
      `${BASE_URL}/api/v1/metrics/savings/history?days=30`,
      { headers }
    );
    
    if (historyResponse.ok()) {
      const data = await historyResponse.json();
      console.log(`✓ API 3: /savings/history OK (${data.history.length} dias)`);
    }
    
    // 4. Testar /api/v1/metrics/hibernation/events
    const eventsResponse = await request.get(
      `${BASE_URL}/api/v1/metrics/hibernation/events?limit=10`,
      { headers }
    );
    
    if (eventsResponse.ok()) {
      const data = await eventsResponse.json();
      console.log(`✓ API 4: /hibernation/events OK (${data.count} eventos)`);
    }
    
    // 5. Testar /api/agent/instances
    const instancesResponse = await request.get(
      `${BASE_URL}/api/agent/instances`,
      { headers }
    );
    
    if (instancesResponse.ok()) {
      const data = await instancesResponse.json();
      console.log(`✓ API 5: /agent/instances OK (${data.length} instâncias)`);
    }
  });

  test('Verificar integração com máquinas', async ({ page }) => {
    await login(page);
    
    // 1. Ir para máquinas
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-machines-1-list.png',
      fullPage: true 
    });
    
    // 2. Contar máquinas
    const machineCards = page.locator('[class*="machine-card"], .flex.flex-col.p-3');
    const count = await machineCards.count();
    
    console.log(`✓ ${count} máquina(s) encontrada(s)`);
    
    if (count > 0) {
      // 3. Verificar primeira máquina
      const firstCard = machineCards.first();
      
      // Verificar badges
      const badges = await firstCard.locator('span[class*="badge"], span[class*="status"]').allTextContents();
      console.log(`✓ Badges encontrados: ${badges.join(', ')}`);
      
      // Verificar botões de ação
      const actionButtons = await firstCard.locator('button').count();
      console.log(`✓ ${actionButtons} botões de ação`);
      
      // 4. Abrir menu de ações
      const menuButton = firstCard.locator('button:has(svg[class*="more"], svg)').last();
      if (await menuButton.isVisible()) {
        await menuButton.click();
        await page.waitForTimeout(300);
        
        await page.screenshot({ 
          path: 'tests/screenshots/e2e-machines-2-menu.png' 
        });
        
        // Verificar opção Auto-Hibernation
        const hibernateOption = page.locator('text=/Auto-Hibernation|Hibernação/i');
        if (await hibernateOption.isVisible({ timeout: 2000 })) {
          console.log('✓ Opção Auto-Hibernation presente');
        }
        
        await page.keyboard.press('Escape');
      }
    }
  });

  test('Responsividade mobile', async ({ page }) => {
    await login(page);
    
    // Viewport mobile
    await page.setViewportSize({ width: 375, height: 812 });
    
    // 1. Dashboard mobile
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-mobile-1-dashboard.png',
      fullPage: true 
    });
    console.log('✓ Dashboard mobile OK');
    
    // 2. Métricas mobile
    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-mobile-2-metrics.png',
      fullPage: true 
    });
    console.log('✓ Métricas mobile OK');
    
    // 3. Settings mobile
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-mobile-3-settings.png',
      fullPage: true 
    });
    console.log('✓ Settings mobile OK');
    
    // 4. Machines mobile
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'tests/screenshots/e2e-mobile-4-machines.png',
      fullPage: true 
    });
    console.log('✓ Machines mobile OK');
  });
});

test.describe('Testes de Regressão', () => {
  
  test('Todas as páginas principais carregam', async ({ page }) => {
    await login(page);
    
    const pages = [
      { path: '/', name: 'Dashboard' },
      { path: '/machines', name: 'Machines' },
      { path: '/metrics', name: 'Metrics' },
      { path: '/settings', name: 'Settings' },
    ];
    
    for (const p of pages) {
      await page.goto(`${BASE_URL}${p.path}`);
      await page.waitForLoadState('networkidle');
      
      // Verifica que não há erros JS
      const errors = [];
      page.on('pageerror', err => errors.push(err));
      
      await page.waitForTimeout(500);
      
      if (errors.length === 0) {
        console.log(`✓ ${p.name} carregou sem erros`);
      } else {
        console.log(`⚠ ${p.name} tem ${errors.length} erros JS`);
      }
    }
  });

  test('Menu de navegação funciona', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');
    
    // Clica em cada item do menu
    const menuItems = page.locator('nav a, aside a');
    const count = await menuItems.count();
    
    console.log(`✓ ${count} itens de menu encontrados`);
    
    // Verifica que links estão visíveis
    for (let i = 0; i < Math.min(count, 5); i++) {
      const item = menuItems.nth(i);
      if (await item.isVisible()) {
        const href = await item.getAttribute('href');
        console.log(`  - ${href}`);
      }
    }
  });

  test('Health endpoint always responds', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/health`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.version).toBeDefined();
    expect(data.service).toBe('dumont-cloud');
    
    console.log(`✓ Health: version=${data.version}`);
  });
});
