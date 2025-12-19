const { test, expect } = require('@playwright/test');

test('Debug busca de ofertas', async ({ page }) => {
  // Interceptar requisições de rede
  const requests = [];
  const responses = [];
  
  page.on('request', req => {
    if (req.url().includes('/api/')) {
      requests.push({ url: req.url(), method: req.method() });
    }
  });
  
  page.on('response', res => {
    if (res.url().includes('/api/')) {
      responses.push({ url: res.url(), status: res.status() });
    }
  });
  
  page.on('console', msg => {
    console.log('CONSOLE:', msg.type(), msg.text());
  });

  // 1. Ir para o site
  console.log('=== Acessando dumontcloud.com ===');
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'screenshots/debug-01-initial.png' });
  
  // 2. Verificar se está logado
  const isLoggedIn = await page.locator('text=Logout').count() > 0 || 
                      await page.locator('text=Dashboard').count() > 0;
  console.log('Está logado:', isLoggedIn);
  
  // 3. Se não estiver logado, fazer login
  if (!isLoggedIn) {
    console.log('=== Fazendo login ===');
    
    // Procurar campo de email
    const emailField = page.locator('input[type="email"], input[name="email"], input[placeholder*="mail"]').first();
    const passwordField = page.locator('input[type="password"]').first();
    
    if (await emailField.count() > 0) {
      await emailField.fill('marcosremar@gmail.com');
      await passwordField.fill('dumont123');
      await page.screenshot({ path: 'screenshots/debug-02-login-filled.png' });
      
      // Clicar no botão de login
      const loginBtn = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Entrar")').first();
      await loginBtn.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'screenshots/debug-03-after-login.png' });
    }
  }
  
  // 4. Ir para Dashboard/busca de máquinas
  console.log('=== Verificando página atual ===');
  console.log('URL:', page.url());
  await page.screenshot({ path: 'screenshots/debug-04-current-page.png' });
  
  // 5. Verificar localStorage token
  const token = await page.evaluate(() => localStorage.getItem('token'));
  console.log('Token no localStorage:', token ? token.substring(0, 50) + '...' : 'NENHUM');
  
  // 6. Procurar botão de buscar máquinas
  console.log('=== Procurando botão de buscar ===');
  const searchBtn = page.locator('button:has-text("Buscar"), button:has-text("Search"), button:has-text("Pesquisar")').first();
  if (await searchBtn.count() > 0) {
    console.log('Botão encontrado, clicando...');
    await searchBtn.click();
    await page.waitForTimeout(5000);
    await page.screenshot({ path: 'screenshots/debug-05-after-search.png' });
  }
  
  // 7. Log das requisições/respostas
  console.log('\n=== Requisições API ===');
  requests.forEach(r => console.log(`  ${r.method} ${r.url}`));
  
  console.log('\n=== Respostas API ===');
  responses.forEach(r => console.log(`  ${r.status} ${r.url}`));
  
  // 8. Verificar se há erro na página
  const errorText = await page.locator('text=/erro|error|falha|failed/i').first().textContent().catch(() => null);
  if (errorText) {
    console.log('\n=== Erro encontrado ===');
    console.log(errorText);
  }
  
  // Screenshot final
  await page.screenshot({ path: 'screenshots/debug-06-final.png', fullPage: true });
});
