const { test, expect } = require('@playwright/test');

test('Navegação simples pelo Dumont Cloud', async ({ page }) => {
  console.log('=== INICIANDO NAVEGAÇÃO PELO DUMONT CLOUD ===\n');
  
  // 1. Login
  console.log('1. Fazendo login...');
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  
  // Esperar e preencher formulário de login
  await page.waitForSelector('input', { timeout: 10000 });
  const inputs = await page.locator('input').all();
  
  if (inputs.length >= 2) {
    await inputs[0].fill('marcosremar@gmail.com');
    await inputs[1].fill('dumont123');
    await page.locator('button:has-text("Login")').click();
    await page.waitForTimeout(3000);
  }
  
  // 2. Verificar Dashboard
  console.log('2. Verificando Dashboard...');
  const url = page.url();
  console.log('   URL atual:', url);
  
  const hasLogout = await page.locator('text=Logout').count();
  const hasDashboard = await page.locator('text=Dashboard').count();
  
  console.log('   Tem Logout:', hasLogout > 0 ? '✓' : '✗');
  console.log('   Tem Dashboard:', hasDashboard > 0 ? '✓' : '✗');
  
  if (hasLogout > 0) {
    // 3. Testar busca de máquinas
    console.log('3. Testando busca de máquinas...');
    
    // Procurar botão de busca
    const buscarBtn = page.locator('text=Buscar Máquinas Disponíveis').first();
    if (await buscarBtn.count() > 0) {
      console.log('   Botão de busca encontrado: ✓');
      await buscarBtn.click();
      await page.waitForTimeout(5000);
      
      // Verificar se aparece resultado ou mensagem
      const hasResults = await page.locator('text=RTX').count();
      const hasError = await page.locator('text=/Erro|Falha/i').count();
      
      console.log('   Resultados encontrados:', hasResults > 0 ? '✓' : '✗');
      console.log('   Erros:', hasError > 0 ? '✗ (ERRO)' : '✓ (SEM ERROS)');
      
      await page.screenshot({ path: 'screenshots/navegacao-busca.png', fullPage: true });
    } else {
      console.log('   Botão de busca não encontrado: ✗');
    }
    
    // 4. Navegar para página Machines
    console.log('4. Navegando para página Machines...');
    const machinesLink = page.locator('a[href*="machines"], text= Máquinas').first();
    if (await machinesLink.count() > 0) {
      await machinesLink.click();
      await page.waitForTimeout(3000);
      
      const machinesTitle = await page.locator('text= Máquinas|h1:has-text("Máquinas")').count();
      console.log('   Página Machines carregada:', machinesTitle > 0 ? '✓' : '✗');
      
      await page.screenshot({ path: 'screenshots/navegacao-machines.png', fullPage: true });
    } else {
      console.log('   Link para Machines não encontrado: ✗');
    }
    
    // 5. Testar Metrics
    console.log('5. Testando página Metrics...');
    const metricsLink = page.locator('a[href*="metrics"], text= Métricas').first();
    if (await metricsLink.count() > 0) {
      await metricsLink.click();
      await page.waitForTimeout(3000);
      
      const metricsContent = await page.locator('text=CPU|GPU|Memória').count();
      console.log('   Página Metrics carregada:', metricsContent > 0 ? '✓' : '✗');
      
      await page.screenshot({ path: 'screenshots/navegacao-metrics.png', fullPage: true });
    } else {
      console.log('   Link para Metrics não encontrado: ✗');
    }
    
    // 6. Logout
    console.log('6. Fazendo logout...');
    await page.locator('text=Logout').click();
    await page.waitForTimeout(2000);
    
    const backToLogin = await page.locator('input').count();
    console.log('   Voltou para login:', backToLogin > 0 ? '✓' : '✗');
  }
  
  console.log('\n=== NAVEGAÇÃO CONCLUÍDA ===');
});
