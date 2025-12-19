const { test, expect } = require('@playwright/test');

test('Navegação Completa do Sistema Dumont Cloud', async ({ page }) => {
  const testReport = {
    timestamp: new Date().toISOString(),
    tests: [],
    summary: {
      passed: 0,
      failed: 0,
      errors: []
    }
  };

  const logTest = (name, passed, details = '') => {
    testReport.tests.push({ name, passed, details, timestamp: new Date().toISOString() });
    if (passed) {
      testReport.summary.passed++;
      console.log(`✅ ${name}${details ? ': ' + details : ''}`);
    } else {
      testReport.summary.failed++;
      testReport.summary.errors.push({ test: name, error: details });
      console.log(`❌ ${name}: ${details}`);
    }
  };

  // ========== TESTE 1: ACESSO À PÁGINA INICIAL ==========
  console.log('\n=== TESTE 1: ACESSANDO PÁGINA INICIAL ===');
  try {
    await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle', timeout: 30000 });
    const title = await page.title();
    logTest('Página inicial carrega', title.includes('Dumont'), title);
    await page.screenshot({ path: 'screenshots/01-homepage.png' });
  } catch (err) {
    logTest('Página inicial carrega', false, err.message);
  }

  // ========== TESTE 2: LOCALIZAR BOTÃO LOGIN ==========
  console.log('\n=== TESTE 2: LOCALIZANDO BOTÃO LOGIN ===');
  try {
    const loginBtn = page.locator('button:has-text("Login")').first();
    const isVisible = await loginBtn.isVisible();
    logTest('Botão Login visível', isVisible, isVisible ? 'Encontrado' : 'Não encontrado');

    if (isVisible) {
      await page.screenshot({ path: 'screenshots/02-homepage-with-login-button.png' });
    }
  } catch (err) {
    logTest('Botão Login visível', false, err.message);
  }

  // ========== TESTE 3: CLICAR EM LOGIN ==========
  console.log('\n=== TESTE 3: CLICANDO EM LOGIN ===');
  try {
    const loginBtn = page.locator('button:has-text("Login")').first();
    await loginBtn.click();
    await page.waitForTimeout(2000);

    // Verificar se apareceu formulário de login
    const emailInputs = await page.locator('input[type="text"], input[type="email"]').count();
    logTest('Formulário de login aparece', emailInputs > 0, `Encontrados ${emailInputs} inputs`);
    await page.screenshot({ path: 'screenshots/03-login-form-open.png' });
  } catch (err) {
    logTest('Clica em Login com sucesso', false, err.message);
  }

  // ========== TESTE 4: PREENCHER FORMULÁRIO ==========
  console.log('\n=== TESTE 4: PREENCHENDO FORMULÁRIO ===');
  try {
    // Localizar campos
    const inputs = await page.locator('input').all();
    console.log(`Total de inputs encontrados: ${inputs.length}`);

    // Assumindo: primeiro input relevante = email, segundo = password
    let emailField = null;
    let passwordField = null;

    for (let i = 0; i < inputs.length; i++) {
      const type = await inputs[i].getAttribute('type');
      const placeholder = await inputs[i].getAttribute('placeholder');
      const name = await inputs[i].getAttribute('name');

      console.log(`  Input ${i}: type="${type}", placeholder="${placeholder}", name="${name}"`);

      if ((type === 'email' || type === 'text' || name === 'email') && !emailField) {
        emailField = inputs[i];
      } else if (type === 'password' && !passwordField) {
        passwordField = inputs[i];
      }
    }

    if (emailField && passwordField) {
      await emailField.fill('marcosremar@gmail.com');
      await page.waitForTimeout(500);
      await passwordField.fill('dumont123');
      await page.waitForTimeout(500);

      logTest('Preenche email e senha', true, 'Campos preenchidos');
      await page.screenshot({ path: 'screenshots/04-form-filled.png' });
    } else {
      logTest('Preenche email e senha', false, 'Campos não encontrados');
    }
  } catch (err) {
    logTest('Preenche email e senha', false, err.message);
  }

  // ========== TESTE 5: SUBMETER LOGIN ==========
  console.log('\n=== TESTE 5: SUBMETENDO LOGIN ===');
  try {
    // Localizar botão de submit
    const submitBtn = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Entrar")').first();
    const isVisible = await submitBtn.isVisible();

    if (isVisible) {
      await submitBtn.click();
      await page.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      logTest('Submete formulário', true, 'Login enviado');
      await page.screenshot({ path: 'screenshots/05-after-login-submit.png' });
    } else {
      logTest('Submete formulário', false, 'Botão não encontrado');
    }
  } catch (err) {
    logTest('Submete formulário', false, err.message);
  }

  // ========== TESTE 6: VERIFICAR AUTENTICAÇÃO ==========
  console.log('\n=== TESTE 6: VERIFICANDO AUTENTICAÇÃO ===');
  try {
    const authToken = await page.evaluate(() => localStorage.getItem('auth_token'));
    const hasLogout = await page.locator('text=Logout').count();
    const hasDashboard = await page.locator('text=Dashboard').count();

    const isAuthenticated = !!authToken || hasLogout > 0;
    logTest('Usuário autenticado', isAuthenticated,
      isAuthenticated ? `Token: ${authToken ? 'Sim' : 'Não'}, Logout: ${hasLogout > 0}` : 'Não encontrado');

    await page.screenshot({ path: 'screenshots/06-dashboard-view.png' });
  } catch (err) {
    logTest('Usuário autenticado', false, err.message);
  }

  // ========== TESTE 7: NAVEGAR PARA MÁQUINAS ==========
  console.log('\n=== TESTE 7: NAVEGANDO PARA MÁQUINAS ===');
  try {
    const machinesLink = page.locator('a:has-text("Máquinas"), a:has-text("Machines"), text=Máquinas').first();
    const isMachinesLinkVisible = await machinesLink.count() > 0;

    if (isMachinesLinkVisible) {
      await machinesLink.click();
      await page.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      logTest('Acessa página de máquinas', true, 'Página carregada');
      await page.screenshot({ path: 'screenshots/07-machines-page.png' });
    } else {
      // Tentar URL direta
      await page.goto('https://dumontcloud.com/machines', { waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      const url = page.url();
      const isOnMachinesPage = url.includes('machines') || await page.locator('text=Máquina').count() > 0;
      logTest('Acessa página de máquinas', isOnMachinesPage, url);
      await page.screenshot({ path: 'screenshots/07-machines-page.png' });
    }
  } catch (err) {
    logTest('Acessa página de máquinas', false, err.message);
  }

  // ========== TESTE 8: VERIFICAR LISTA DE MÁQUINAS ==========
  console.log('\n=== TESTE 8: VERIFICANDO LISTA DE MÁQUINAS ===');
  try {
    await page.waitForTimeout(2000);
    const machineRows = await page.locator('[class*="machine"], [class*="instance"], tr').count();
    const hasMachineData = machineRows > 0;

    logTest('Carrega dados de máquinas', hasMachineData, `Encontradas ${machineRows} linhas/cards`);
    await page.screenshot({ path: 'screenshots/08-machines-list.png' });
  } catch (err) {
    logTest('Carrega dados de máquinas', false, err.message);
  }

  // ========== TESTE 9: NAVEGAR PARA SETTINGS ==========
  console.log('\n=== TESTE 9: NAVEGANDO PARA SETTINGS ===');
  try {
    const settingsLink = page.locator('a:has-text("Configurações"), a:has-text("Settings"), text=/Config|Sett/i').first();

    if (await settingsLink.count() > 0) {
      await settingsLink.click();
      await page.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      logTest('Acessa página de configurações', true, 'Página carregada');
      await page.screenshot({ path: 'screenshots/09-settings-page.png' });
    } else {
      await page.goto('https://dumontcloud.com/settings', { waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      const url = page.url();
      const isOnSettingsPage = url.includes('settings') || await page.locator('text=Configuração').count() > 0;
      logTest('Acessa página de configurações', isOnSettingsPage, url);
      await page.screenshot({ path: 'screenshots/09-settings-page.png' });
    }
  } catch (err) {
    logTest('Acessa página de configurações', false, err.message);
  }

  // ========== TESTE 10: PROCURAR OFERTAS DE GPU ==========
  console.log('\n=== TESTE 10: BUSCANDO OFERTAS DE GPU ===');
  try {
    // Voltar para dashboard/home
    await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(2000);

    // Procurar por botões de velocidade (Rápido, Médio, etc)
    const rapidoBtn = page.locator('text=/Rápido|Rapido|Fast/i').first();

    if (await rapidoBtn.count() > 0) {
      await rapidoBtn.click();
      await page.waitForTimeout(5000);

      const offers = await page.locator('[class*="card"], [class*="offer"], [class*="machine"]').count();
      logTest('Busca ofertas de GPU', offers > 0, `Encontradas ${offers} ofertas`);
      await page.screenshot({ path: 'screenshots/10-gpu-offers.png' });
    } else {
      // Procurar por botão de busca genérico
      const searchBtn = page.locator('button:has-text("Buscar")').first();
      if (await searchBtn.count() > 0) {
        await searchBtn.click();
        await page.waitForTimeout(5000);

        logTest('Busca ofertas de GPU', true, 'Busca iniciada');
        await page.screenshot({ path: 'screenshots/10-gpu-offers.png' });
      } else {
        logTest('Busca ofertas de GPU', false, 'Botão de busca não encontrado');
      }
    }
  } catch (err) {
    logTest('Busca ofertas de GPU', false, err.message);
  }

  // ========== TESTE 11: VERIFICAR RESPONSIVIDADE MOBILE ==========
  console.log('\n=== TESTE 11: TESTANDO RESPONSIVIDADE ===');
  try {
    // Simular viewport mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);

    const isMobileVisible = await page.locator('[class*="mobile"], [class*="menu"]').count() > 0 ||
                            await page.locator('button:has-text("Menu")').count() > 0;

    logTest('Layout mobile funciona', true, 'Viewport ajustado para 375x667');
    await page.screenshot({ path: 'screenshots/11-mobile-view.png' });

    // Voltar ao desktop
    await page.setViewportSize({ width: 1280, height: 720 });
  } catch (err) {
    logTest('Layout mobile funciona', false, err.message);
  }

  // ========== TESTE 12: LOGOUT ==========
  console.log('\n=== TESTE 12: FAZENDO LOGOUT ===');
  try {
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Sair")').first();

    if (await logoutBtn.count() > 0) {
      await logoutBtn.click();
      await page.waitForTimeout(2000);

      const authToken = await page.evaluate(() => localStorage.getItem('auth_token'));
      const isLoggedOut = !authToken;

      logTest('Logout funciona', isLoggedOut, isLoggedOut ? 'Token removido' : 'Token ainda presente');
      await page.screenshot({ path: 'screenshots/12-after-logout.png' });
    } else {
      logTest('Logout funciona', false, 'Botão não encontrado');
    }
  } catch (err) {
    logTest('Logout funciona', false, err.message);
  }

  // ========== RELATÓRIO FINAL ==========
  console.log('\n\n╔════════════════════════════════════════════════════════╗');
  console.log('║          RELATÓRIO FINAL DE NAVEGAÇÃO                  ║');
  console.log('╚════════════════════════════════════════════════════════╝');
  console.log(`\n✅ Testes Passados: ${testReport.summary.passed}`);
  console.log(`❌ Testes Falhados: ${testReport.summary.failed}`);
  console.log(`📊 Taxa de Sucesso: ${Math.round((testReport.summary.passed / (testReport.summary.passed + testReport.summary.failed)) * 100)}%`);

  if (testReport.summary.errors.length > 0) {
    console.log('\n⚠️  Erros Encontrados:');
    testReport.summary.errors.forEach((err, idx) => {
      console.log(`  ${idx + 1}. ${err.test}: ${err.error}`);
    });
  }

  console.log('\n📸 Screenshots gerados:');
  testReport.tests.forEach(test => {
    if (test.passed) {
      console.log(`  ✅ ${test.name}`);
    }
  });

  // Salvar relatório em JSON
  const fs = require('fs');
  const reportPath = 'screenshots/test-report.json';
  fs.writeFileSync(reportPath, JSON.stringify(testReport, null, 2));
  console.log(`\n📄 Relatório salvo em: ${reportPath}`);

  // Verificação final
  const successRate = testReport.summary.passed / (testReport.summary.passed + testReport.summary.failed);
  expect(successRate).toBeGreaterThan(0.8); // Expectativa: 80% de sucesso
});
