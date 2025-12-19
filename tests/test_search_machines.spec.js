const { test, expect } = require('@playwright/test');

test('Login e busca de máquinas', async ({ page }) => {
  // Capturar requests
  const apiCalls = [];
  page.on('response', async res => {
    if (res.url().includes('/api/')) {
      let body = '';
      try { body = await res.text(); } catch(e) {}
      apiCalls.push({ 
        url: res.url(), 
        status: res.status(),
        body: body.substring(0, 200)
      });
    }
  });

  console.log('=== 1. Acessando site ===');
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  
  console.log('=== 2. Fazendo login ===');
  // Preencher username e password
  await page.fill('input[type="text"], input:first-of-type', 'marcosremar@gmail.com');
  await page.fill('input[type="password"]', 'dumont123');
  await page.screenshot({ path: 'screenshots/search-01-login.png' });
  
  // Clicar em Login
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'screenshots/search-02-after-login.png' });
  
  // Verificar token
  const token = await page.evaluate(() => localStorage.getItem('token'));
  console.log('Token:', token ? 'OK (' + token.substring(0, 30) + '...)' : 'NENHUM');
  
  // Verificar URL atual
  console.log('URL atual:', page.url());
  
  console.log('=== 3. Navegando para busca ===');
  // Se não estiver no dashboard, ir para ele
  if (!page.url().includes('dashboard')) {
    await page.goto('https://dumontcloud.com/dashboard', { waitUntil: 'networkidle' });
  }
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'screenshots/search-03-dashboard.png' });
  
  console.log('=== 4. Clicando em buscar ===');
  // Procurar botão de buscar
  const searchBtn = page.locator('button:has-text("Buscar GPUs")').first();
  if (await searchBtn.count() > 0) {
    await searchBtn.click();
    console.log('Clicou em Buscar GPUs');
  } else {
    // Tentar outros seletores
    const altBtn = page.locator('button:has-text("Buscar"), button:has-text("Search")').first();
    if (await altBtn.count() > 0) {
      await altBtn.click();
      console.log('Clicou em botão alternativo');
    } else {
      console.log('Botão de busca não encontrado');
    }
  }
  
  await page.waitForTimeout(5000);
  await page.screenshot({ path: 'screenshots/search-04-result.png', fullPage: true });
  
  console.log('\n=== API Calls ===');
  apiCalls.forEach(c => {
    console.log(`${c.status} ${c.url}`);
    if (c.status >= 400) {
      console.log(`  Body: ${c.body}`);
    }
  });
  
  // Verificar se há erros visíveis
  const pageContent = await page.content();
  if (pageContent.includes('Falha ao buscar') || pageContent.includes('erro')) {
    console.log('\n=== ERRO DETECTADO NA PÁGINA ===');
    const errorEl = await page.locator('text=/Falha|erro|error/i').first().textContent().catch(() => '');
    console.log('Texto de erro:', errorEl);
  }
});
