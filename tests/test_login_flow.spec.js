const { test, expect } = require('@playwright/test');

test('Fluxo completo de login', async ({ page }) => {
  console.log('=== FLUXO COMPLETO DE LOGIN ===\n');
  
  // 1. Acessar site inicial
  console.log('1. Acessando site inicial...');
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // 2. Clicar no botão Login
  console.log('2. Procurando e clicando no botão Login...');
  const loginBtn = page.locator('button:has-text("Login")').first();
  
  if (await loginBtn.count() > 0) {
    console.log('   Botão Login encontrado: ✓');
    await loginBtn.click();
    console.log('   Botão Login clicado: ✓');
  } else {
    console.log('   Botão Login não encontrado: ✗');
    // Tentar outros seletores
    const otherLogin = page.locator('a[href*="login"], .login, #login').first();
    if (await otherLogin.count() > 0) {
      await otherLogin.click();
      console.log('   Link Login encontrado e clicado: ✓');
    }
  }
  
  await page.waitForTimeout(3000);
  
  // 3. Verificar se estamos na página de login
  console.log('3. Verificando página de login...');
  const currentUrl = page.url();
  console.log('   URL atual:', currentUrl);
  
  await page.screenshot({ path: 'screenshots/login-01-page.png', fullPage: true });
  
  // 4. Procurar formulário de login
  console.log('4. Procurando formulário de login...');
  
  // Esperar um pouco mais para a página carregar
  await page.waitForTimeout(2000);
  
  // Verificar todos os inputs novamente
  const inputs = await page.locator('input').all();
  console.log('   Inputs encontrados:', inputs.length);
  
  if (inputs.length >= 2) {
    // Preencher formulário
    for (let i = 0; i < inputs.length; i++) {
      const input = inputs[i];
      const type = await input.getAttribute('type');
      const placeholder = await input.getAttribute('placeholder');
      const isVisible = await input.isVisible();
      
      console.log(`   Input ${i}: type="${type}", placeholder="${placeholder}", visible=${isVisible}`);
    }
    
    // Tentar identificar qual é email/senha
    const emailInput = await page.locator('input[type="email"], input[name*="email"], input[placeholder*="email"]').first();
    const passInput = await page.locator('input[type="password"], input[name*="password"], input[placeholder*="password"]').first();
    
    let emailField, passField;
    
    if (await emailInput.count() > 0) {
      emailField = emailInput;
      console.log('   Campo email identificado: ✓');
    } else {
      // Usar o primeiro input visível que não seja password
      for (let i = 0; i < inputs.length; i++) {
        const type = await inputs[i].getAttribute('type');
        if (type !== 'password' && await inputs[i].isVisible()) {
          emailField = inputs[i];
          console.log(`   Campo email (input ${i}) selecionado: ✓`);
          break;
        }
      }
    }
    
    if (await passInput.count() > 0) {
      passField = passInput;
      console.log('   Campo senha identificado: ✓');
    } else {
      // Usar o primeiro input do tipo password
      for (let i = 0; i < inputs.length; i++) {
        const type = await inputs[i].getAttribute('type');
        if (type === 'password' && await inputs[i].isVisible()) {
          passField = inputs[i];
          console.log(`   Campo senha (input ${i}) selecionado: ✓`);
          break;
        }
      }
    }
    
    if (emailField && passField) {
      console.log('5. Preenchendo formulário...');
      await emailField.fill('marcosremar@gmail.com');
      await passField.fill('dumont123');
      
      await page.screenshot({ path: 'screenshots/login-02-filled.png', fullPage: true });
      
      // Procurar botão de submit
      const submitBtn = await page.locator('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Entrar")').first();
      
      if (await submitBtn.count() > 0) {
        await submitBtn.click();
        console.log('   Botão submit clicado: ✓');
      } else {
        await page.keyboard.press('Enter');
        console.log('   Enter pressionado: ✓');
      }
      
      await page.waitForTimeout(5000);
      
      // 6. Verificar resultado do login
      console.log('6. Verificando resultado do login...');
      const afterUrl = page.url();
      console.log('   URL após login:', afterUrl);
      
      await page.screenshot({ path: 'screenshots/login-03-after.png', fullPage: true });
      
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
        console.log('\n=== LOGIN BEM-SUCEDIDO ===');
        console.log('O sistema está funcionando corretamente!');
        
        // Testar busca de máquinas
        console.log('\n7. Testando busca de máquinas...');
        const buscarBtn = await page.locator('text=Buscar Máquinas, text=Buscar').first();
        if (await buscarBtn.count() > 0) {
          await buscarBtn.click();
          await page.waitForTimeout(5000);
          
          const hasError = await page.locator('text=/Erro|Falha|Algo deu errado/').count();
          const hasResults = await page.locator('text=RTX, text=NVIDIA, text=GPU').count();
          
          console.log('   Resultados da busca:', hasResults > 0 ? '✓' : '✗');
          console.log('   Erros na busca:', hasError > 0 ? '✗' : '✓');
          
          await page.screenshot({ path: 'screenshots/login-04-busca.png', fullPage: true });
        }
      }
    } else {
      console.log('   ERRO: Não foi possível identificar campos de email/senha');
    }
  } else {
    console.log('   ERRO: Formulário de login não encontrado após clicar no botão Login');
  }
  
  console.log('\n=== FLUXO DE LOGIN CONCLUÍDO ===');
});
