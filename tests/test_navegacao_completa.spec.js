const { test, expect } = require('@playwright/test');

test('Navegação completa pelo Dumont Cloud', async ({ page }) => {
  console.log('=== NAVEGAÇÃO COMPLETA - DUMONT CLOUD ===\n');
  
  // Configurar timeout maior
  test.setTimeout(120000);
  
  // 1. Acessar site
  console.log('1. Acessando o site...');
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // Verificar se estamos na página de login
  const pageContent = await page.content();
  const hasLoginForm = pageContent.includes('Login') || pageContent.includes('login');
  console.log('   Formulário de login encontrado:', hasLoginForm ? '✓' : '✗');
  
  await page.screenshot({ path: 'screenshots/completo-01-initial.png', fullPage: true });
  
  // 2. Tentar login
  console.log('2. Tentando fazer login...');
  
  // Esperar inputs carregarem
  await page.waitForSelector('input', { timeout: 15000 });
  
  // Pegar todos os inputs visíveis
  const inputs = await page.locator('input:visible').all();
  console.log('   Inputs encontrados:', inputs.length);
  
  if (inputs.length >= 2) {
    // Preencher formulário
    await inputs[0].click();
    await inputs[0].fill('marcosremar@gmail.com');
    await inputs[1].click();
    await inputs[1].fill('dumont123');
    
    console.log('   Formulário preenchido: ✓');
    await page.screenshot({ path: 'screenshots/completo-02-form-filled.png', fullPage: true });
    
    // Procurar e clicar no botão de login
    const loginBtn = page.locator('button:has-text("Login"), button[type="submit"], input[type="submit"]').first();
    if (await loginBtn.count() > 0) {
      await loginBtn.click();
      console.log('   Botão Login clicado: ✓');
    } else {
      // Tentar enviar com Enter
      await page.keyboard.press('Enter');
      console.log('   Enter pressionado: ✓');
    }
    
    // Esperar processamento
    await page.waitForTimeout(5000);
    
    // 3. Verificar resultado do login
    console.log('3. Verificando resultado do login...');
    const currentUrl = page.url();
    console.log('   URL após login:', currentUrl);
    
    await page.screenshot({ path: 'screenshots/completo-03-after-login.png', fullPage: true });
    
    // Verificar elementos pós-login
    const logoutBtn = await page.locator('text=Logout, text=Sair').count();
    const dashboardTitle = await page.locator('text=Dashboard, h1:has-text("Dashboard")').count();
    const userEmail = await page.locator('text=marcosremar@gmail.com').count();
    
    console.log('   Botão Logout:', logoutBtn > 0 ? '✓' : '✗');
    console.log('   Dashboard:', dashboardTitle > 0 ? '✓' : '✗');
    console.log('   Email do usuário:', userEmail > 0 ? '✓' : '✗');
    
    const isLoggedIn = logoutBtn > 0 || dashboardTitle > 0 || userEmail > 0;
    console.log('   Status login:', isLoggedIn ? '✓ SUCESSO' : '✗ FALHOU');
    
    if (isLoggedIn) {
      // 4. Testar funcionalidades principais
      console.log('4. Testando funcionalidades principais...');
      
      // 4.1 Testar busca de GPUs
      console.log('   4.1 Testando busca de GPUs...');
      const buscarBtn = await page.locator('text=Buscar Máquinas, text=Buscar').first();
      if (await buscarBtn.count() > 0) {
        await buscarBtn.click();
        await page.waitForTimeout(5000);
        
        const hasError = await page.locator('text=/Erro|Falha|Algo deu errado/').count();
        const hasResults = await page.locator('text=RTX, text=NVIDIA, text=GPU').count();
        
        console.log('       Resultados da busca:', hasResults > 0 ? '✓' : '✗');
        console.log('       Erros na busca:', hasError > 0 ? '✗' : '✓');
        
        await page.screenshot({ path: 'screenshots/completo-04-busca-gpus.png', fullPage: true });
      }
      
      // 4.2 Testar página Machines
      console.log('   4.2 Testando página Machines...');
      const machinesLink = await page.locator('a[href*="machines"], text= Máquinas').first();
      if (await machinesLink.count() > 0) {
        await machinesLink.click();
        await page.waitForTimeout(3000);
        
        const machinesPage = await page.locator('text= Máquinas, h1:has-text("Máquinas")').count();
        console.log('       Página Machines:', machinesPage > 0 ? '✓' : '✗');
        
        await page.screenshot({ path: 'screenshots/completo-05-machines.png', fullPage: true });
      }
      
      // 4.3 Testar página Settings
      console.log('   4.3 Testando página Settings...');
      const settingsLink = await page.locator('a[href*="settings"], text= Configurações').first();
      if (await settingsLink.count() > 0) {
        await settingsLink.click();
        await page.waitForTimeout(3000);
        
        const settingsPage = await page.locator('text= Configurações, h1:has-text("Settings")').count();
        console.log('       Página Settings:', settingsPage > 0 ? '✓' : '✗');
        
        await page.screenshot({ path: 'screenshots/completo-06-settings.png', fullPage: true });
      }
      
      // 5. Logout
      console.log('5. Fazendo logout...');
      const logoutLink = await page.locator('text=Logout, text=Sair').first();
      if (await logoutLink.count() > 0) {
        await logoutLink.click();
        await page.waitForTimeout(3000);
        
        const backToLogin = await page.locator('input').count();
        console.log('   Logout realizado:', backToLogin > 0 ? '✓' : '✗');
        
        await page.screenshot({ path: 'screenshots/completo-07-logout.png', fullPage: true });
      }
    }
  } else {
    console.log('   ERRO: Formulário de login não encontrado');
    await page.screenshot({ path: 'screenshots/completo-erro-sem-form.png', fullPage: true });
  }
  
  console.log('\n=== NAVEGAÇÃO CONCLUÍDA ===');
});
