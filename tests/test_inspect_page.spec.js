const { test, expect } = require('@playwright/test');

test('Inspecionar estrutura da página', async ({ page }) => {
  console.log('=== INSPECIONANDO ESTRUTURA DA PÁGINA ===\n');
  
  // 1. Acessar site
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  
  // 2. Analisar estrutura
  console.log('1. Analisando estrutura da página...');
  
  // Verificar todos os inputs
  const allInputs = await page.locator('input').all();
  console.log('   Total de inputs encontrados:', allInputs.length);
  
  for (let i = 0; i < allInputs.length; i++) {
    const input = allInputs[i];
    const type = await input.getAttribute('type');
    const placeholder = await input.getAttribute('placeholder');
    const isVisible = await input.isVisible();
    
    console.log(`   Input ${i}: type="${type}", placeholder="${placeholder}", visible=${isVisible}`);
  }
  
  // Verificar todos os botões
  const allButtons = await page.locator('button').all();
  console.log('   Total de botões encontrados:', allButtons.length);
  
  for (let i = 0; i < allButtons.length; i++) {
    const button = allButtons[i];
    const text = await button.textContent();
    const isVisible = await button.isVisible();
    
    console.log(`   Button ${i}: "${text}", visible=${isVisible}`);
  }
  
  // Verificar formulários
  const forms = await page.locator('form').all();
  console.log('   Total de formulários encontrados:', forms.length);
  
  // Verificar conteúdo da página
  const pageContent = await page.content();
  console.log('   Título da página:', await page.title());
  console.log('   URL atual:', page.url());
  
  // Procurar por elementos específicos
  const hasLogin = pageContent.includes('Login') || pageContent.includes('login');
  const hasEmail = pageContent.includes('email') || pageContent.includes('Email');
  const hasPassword = pageContent.includes('password') || pageContent.includes('Password');
  const hasUsername = pageContent.includes('username') || pageContent.includes('Username');
  
  console.log('   Tem "Login":', hasLogin);
  console.log('   Tem "Email":', hasEmail);
  console.log('   Tem "Password":', hasPassword);
  console.log('   Tem "Username":', hasUsername);
  
  // Tirar screenshot
  await page.screenshot({ path: 'screenshots/inspect-structure.png', fullPage: true });
  
  // 3. Tentar diferentes abordagens para login
  console.log('\n2. Tentando diferentes abordagens...');
  
  // Tentar encontrar inputs por placeholder
  const emailInput = await page.locator('input[placeholder*="email"], input[placeholder*="Email"], input[name*="email"]').first();
  const passInput = await page.locator('input[type="password"], input[placeholder*="password"], input[name*="password"]').first();
  
  console.log('   Input de email encontrado:', await emailInput.count() > 0 ? '✓' : '✗');
  console.log('   Input de senha encontrado:', await passInput.count() > 0 ? '✓' : '✗');
  
  if (await emailInput.count() > 0 && await passInput.count() > 0) {
    console.log('   Preenchendo formulário...');
    await emailInput.fill('marcosremar@gmail.com');
    await passInput.fill('dumont123');
    
    // Procurar botão de submit
    const submitBtn = await page.locator('button[type="submit"], input[type="submit"], button:has-text("Login")').first();
    if (await submitBtn.count() > 0) {
      await submitBtn.click();
      console.log('   Botão submit clicado');
    } else {
      await page.keyboard.press('Enter');
      console.log('   Enter pressionado');
    }
    
    await page.waitForTimeout(5000);
    
    // Verificar resultado
    const newUrl = page.url();
    console.log('   URL após tentativa:', newUrl);
    
    const hasLogout = await page.locator('text=Logout, text=Sair').count();
    console.log('   Logout encontrado após login:', hasLogout > 0 ? '✓' : '✗');
    
    await page.screenshot({ path: 'screenshots/inspect-after-login.png', fullPage: true });
  }
  
  console.log('\n=== INSPEÇÃO CONCLUÍDA ===');
});
