const { test, expect } = require('@playwright/test');

test('Navegação completa pelo sistema Dumont Cloud', async ({ page }) => {
  const report = {
    login: null,
    dashboard: null,
    machines: null,
    metrics: null,
    settings: null,
    logout: null,
    errors: [],
    suggestions: []
  };

  // Interceptar erros de console
  page.on('console', msg => {
    if (msg.type() === 'error') {
      report.errors.push(`Console Error: ${msg.text()}`);
    }
  });

  // Interceptar erros de página
  page.on('pageerror', error => {
    report.errors.push(`Page Error: ${error.message}`);
  });

  console.log('\n' + '='.repeat(60));
  console.log('TESTE DE NAVEGAÇÃO - DUMONT CLOUD');
  console.log('='.repeat(60));

  // ============================================
  // 1. LOGIN
  // ============================================
  console.log('\n[1/6] TESTANDO LOGIN...');

  await page.goto('https://dumontcloud.com');
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'networkidle' });

  await page.waitForSelector('input', { timeout: 10000 });
  const inputs = await page.locator('input').all();

  if (inputs.length >= 2) {
    await inputs[0].fill('marcosremar@gmail.com');
    await inputs[1].fill('dumont123');
    await page.locator('button:has-text("Login")').click();
    await page.waitForTimeout(3000);

    const hasLogout = await page.locator('text=Logout').count();
    if (hasLogout > 0) {
      report.login = 'OK - Login realizado com sucesso';
      console.log('   ✓ Login realizado com sucesso');
    } else {
      report.login = 'FALHOU - Não redirecionou para Dashboard';
      console.log('   ✗ Login falhou');
    }
  }

  await page.screenshot({ path: 'screenshots/nav-01-after-login.png' });

  // ============================================
  // 2. DASHBOARD
  // ============================================
  console.log('\n[2/6] TESTANDO DASHBOARD...');

  const dashboardChecks = {
    hasMap: await page.locator('svg, canvas, [class*="map"]').count() > 0,
    hasSpeedTiers: await page.locator('text=Lento').count() > 0,
    hasSearchButton: await page.locator('text=/Buscar/i').count() > 0,
    hasRegionFilter: await page.locator('text=EUA').count() > 0 || await page.locator('text=Europa').count() > 0,
  };

  console.log('   - Mapa/região:', dashboardChecks.hasMap ? '✓' : '✗');
  console.log('   - Tiers de velocidade:', dashboardChecks.hasSpeedTiers ? '✓' : '✗');
  console.log('   - Botão de busca:', dashboardChecks.hasSearchButton ? '✓' : '✗');
  console.log('   - Filtro de região:', dashboardChecks.hasRegionFilter ? '✓' : '✗');

  // Testar busca de ofertas
  const rapidoCard = page.locator('text=Rapido').first();
  if (await rapidoCard.count() > 0) {
    await rapidoCard.click();
    await page.waitForTimeout(1000);

    // Clicar no botão de buscar
    const searchBtn = page.locator('text=/Buscar Máquinas/i').first();
    if (await searchBtn.count() > 0) {
      await searchBtn.click();
      await page.waitForTimeout(5000);

      const hasError = await page.locator('text=/Algo deu errado|Falha ao buscar/i').count();
      const hasResults = await page.locator('text=/RTX|A100|H100|GPU/i').count();

      if (hasError > 0) {
        report.dashboard = 'ERRO - Falha ao buscar ofertas';
        console.log('   ✗ Erro ao buscar ofertas');
        report.errors.push('Dashboard: Erro ao buscar ofertas de GPU');
      } else if (hasResults > 0) {
        report.dashboard = 'OK - Dashboard funcional, ofertas carregaram';
        console.log('   ✓ Ofertas carregaram com sucesso');
      } else {
        report.dashboard = 'OK - Dashboard funcional (sem ofertas disponíveis)';
        console.log('   ~ Dashboard OK mas sem ofertas disponíveis');
      }
    }
  }

  await page.screenshot({ path: 'screenshots/nav-02-dashboard.png', fullPage: true });

  // ============================================
  // 3. MACHINES
  // ============================================
  console.log('\n[3/6] TESTANDO PÁGINA MACHINES...');

  await page.locator('text=Machines').first().click();
  await page.waitForTimeout(3000);

  const machinesChecks = {
    hasError: await page.locator('text=/Algo deu errado|Erro ao buscar/i').count() > 0,
    hasMachineList: await page.locator('[class*="machine"], [class*="card"], [class*="instance"]').count() > 0,
    hasNoMachines: await page.locator('text=/Nenhuma máquina|No machines/i').count() > 0,
  };

  if (machinesChecks.hasError) {
    report.machines = 'ERRO - Falha ao carregar máquinas';
    console.log('   ✗ Erro ao carregar máquinas');
    report.errors.push('Machines: Erro ao buscar lista de máquinas');
  } else if (machinesChecks.hasMachineList) {
    // Contar máquinas
    const machineCount = await page.locator('text=/running|stopped|loading/i').count();
    report.machines = `OK - ${machineCount} máquina(s) encontrada(s)`;
    console.log(`   ✓ ${machineCount} máquina(s) encontrada(s)`);
  } else if (machinesChecks.hasNoMachines) {
    report.machines = 'OK - Nenhuma máquina ativa';
    console.log('   ~ Nenhuma máquina ativa');
  } else {
    report.machines = 'OK - Página carregou';
    console.log('   ✓ Página carregou');
  }

  await page.screenshot({ path: 'screenshots/nav-03-machines.png', fullPage: true });

  // ============================================
  // 4. MÉTRICAS
  // ============================================
  console.log('\n[4/6] TESTANDO PÁGINA MÉTRICAS...');

  const metricsLink = page.locator('text=Métricas').first();
  if (await metricsLink.count() > 0) {
    await metricsLink.click();
    await page.waitForTimeout(3000);

    const metricsChecks = {
      hasError: await page.locator('text=/Algo deu errado|Erro/i').count() > 0,
      hasCharts: await page.locator('svg, canvas, [class*="chart"]').count() > 0,
      hasMetricsData: await page.locator('text=/economia|savings|cost/i').count() > 0,
    };

    if (metricsChecks.hasError) {
      report.metrics = 'ERRO - Falha ao carregar métricas';
      console.log('   ✗ Erro ao carregar métricas');
    } else {
      report.metrics = 'OK - Página de métricas carregou';
      console.log('   ✓ Página de métricas carregou');
    }
  } else {
    report.metrics = 'N/A - Link não encontrado';
    console.log('   ~ Link de Métricas não encontrado');
  }

  await page.screenshot({ path: 'screenshots/nav-04-metrics.png', fullPage: true });

  // ============================================
  // 5. SETTINGS
  // ============================================
  console.log('\n[5/6] TESTANDO PÁGINA SETTINGS...');

  await page.locator('text=Settings').first().click();
  await page.waitForTimeout(3000);

  const settingsChecks = {
    hasError: await page.locator('text=/Algo deu errado|Erro/i').count() > 0,
    hasForm: await page.locator('input, select, textarea').count() > 0,
    hasApiKey: await page.locator('text=/API Key|Vast/i').count() > 0,
  };

  if (settingsChecks.hasError) {
    report.settings = 'ERRO - Falha ao carregar settings';
    console.log('   ✗ Erro ao carregar settings');
  } else if (settingsChecks.hasForm) {
    report.settings = 'OK - Página de configurações carregou';
    console.log('   ✓ Página de configurações carregou');
    console.log('   - Campos de configuração:', settingsChecks.hasApiKey ? '✓ API Key visível' : '~ API Key não visível');
  } else {
    report.settings = 'OK - Página carregou (sem formulários)';
    console.log('   ~ Página carregou sem formulários');
  }

  await page.screenshot({ path: 'screenshots/nav-05-settings.png', fullPage: true });

  // ============================================
  // 6. LOGOUT
  // ============================================
  console.log('\n[6/6] TESTANDO LOGOUT...');

  const logoutBtn = page.locator('text=Logout').first();
  if (await logoutBtn.count() > 0) {
    await logoutBtn.click();
    await page.waitForTimeout(2000);

    const hasLoginForm = await page.locator('button:has-text("Login")').count() > 0;
    if (hasLoginForm) {
      report.logout = 'OK - Logout realizado com sucesso';
      console.log('   ✓ Logout realizado com sucesso');
    } else {
      report.logout = 'FALHOU - Não voltou para tela de login';
      console.log('   ✗ Não voltou para tela de login');
    }
  }

  await page.screenshot({ path: 'screenshots/nav-06-logout.png' });

  // ============================================
  // RELATÓRIO FINAL
  // ============================================
  console.log('\n' + '='.repeat(60));
  console.log('RELATÓRIO FINAL');
  console.log('='.repeat(60));
  console.log('\nRESULTADOS:');
  console.log('  Login:', report.login);
  console.log('  Dashboard:', report.dashboard);
  console.log('  Machines:', report.machines);
  console.log('  Métricas:', report.metrics);
  console.log('  Settings:', report.settings);
  console.log('  Logout:', report.logout);

  if (report.errors.length > 0) {
    console.log('\nERROS ENCONTRADOS:');
    report.errors.forEach((e, i) => console.log(`  ${i + 1}. ${e}`));
  } else {
    console.log('\nNenhum erro encontrado!');
  }

  console.log('\n' + '='.repeat(60));

  // Falhar o teste se houver erros críticos
  const criticalErrors = [report.login, report.dashboard, report.machines].filter(r => r && r.startsWith('ERRO'));
  if (criticalErrors.length > 0) {
    throw new Error(`Erros críticos encontrados: ${criticalErrors.join(', ')}`);
  }
});
