const { test, expect } = require('@playwright/test');

test('Verificação final da busca de ofertas', async ({ page }) => {
  const apiCalls = [];

  page.on('request', req => {
    if (req.url().includes('/api/')) {
      const headers = req.headers();
      apiCalls.push({
        type: 'REQUEST',
        url: req.url(),
        method: req.method(),
        hasAuth: !!headers['authorization']
      });
    }
  });

  page.on('response', async res => {
    if (res.url().includes('/api/')) {
      let body = '';
      try { body = await res.text(); } catch(e) {}
      apiCalls.push({
        type: 'RESPONSE',
        url: res.url(),
        status: res.status(),
        body: body.substring(0, 200)
      });
    }
  });

  // 1. Limpar storage e fazer login fresco
  await page.goto('https://dumontcloud.com');
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'networkidle' });

  console.log('=== Fazendo login ===');

  // Esperar a página de login carregar
  await page.waitForSelector('input', { timeout: 10000 });

  // Pegar todos os inputs
  const inputs = await page.locator('input').all();
  console.log('Inputs encontrados:', inputs.length);

  if (inputs.length >= 2) {
    // Primeiro input é username, segundo é password
    await inputs[0].fill('marcosremar@gmail.com');
    await inputs[1].fill('dumont123');

    await page.screenshot({ path: 'screenshots/final-01-login-filled.png' });

    // Clicar no botão Login
    await page.locator('button:has-text("Login")').click();

    // Esperar navegação ou dashboard aparecer
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'screenshots/final-02-after-login.png' });
  }

  // 2. Verificar se logou com sucesso
  const url = page.url();
  console.log('URL atual:', url);

  // Verificar tokens no localStorage
  const authToken = await page.evaluate(() => localStorage.getItem('auth_token'));
  const oldToken = await page.evaluate(() => localStorage.getItem('token'));
  console.log('auth_token:', authToken ? 'PRESENTE (' + authToken.substring(0,30) + '...)' : 'AUSENTE');
  console.log('token (antigo):', oldToken ? 'PRESENTE' : 'AUSENTE');

  // Verificar se está no Dashboard (tem navbar, Logout, etc)
  const hasLogout = await page.locator('text=Logout').count();
  const hasDashboard = await page.locator('text=Dashboard').count();
  console.log('Tem Logout:', hasLogout > 0);
  console.log('Tem Dashboard:', hasDashboard > 0);

  if (hasLogout === 0) {
    console.log('ERRO: Login falhou - não encontrou botão Logout');
    await page.screenshot({ path: 'screenshots/final-error-login.png', fullPage: true });
    throw new Error('Login falhou');
  }

  // 3. Clicar em um tier de velocidade para buscar
  await page.waitForTimeout(1000);

  // Procurar por cards de velocidade
  const rapidoCard = page.locator('text=Rapido').first();
  if (await rapidoCard.count() > 0) {
    console.log('=== Clicando em Rapido ===');
    await rapidoCard.click();
    await page.waitForTimeout(5000);
  }

  // 4. Relatório das chamadas API
  console.log('\n=== RELATORIO DE API CALLS ===');
  apiCalls.forEach(c => {
    if (c.type === 'REQUEST') {
      console.log('OUT ' + c.method + ' ' + c.url + ' [Auth: ' + (c.hasAuth ? 'SIM' : 'NAO') + ']');
    } else {
      console.log('IN ' + c.status + ' ' + c.url);
      if (c.status !== 200) {
        console.log('   Body: ' + c.body);
      }
    }
  });

  // 5. Verificar se há erro na página
  const errorEl = page.locator('text=/Algo deu errado|Falha ao buscar/i').first();
  if (await errorEl.count() > 0) {
    console.log('\nERRO DETECTADO NA PAGINA');
    await page.screenshot({ path: 'screenshots/final-check-error.png', fullPage: true });
    throw new Error('Erro de busca ainda presente na página');
  } else {
    console.log('\nSUCESSO - Nenhum erro detectado na pagina');
    await page.screenshot({ path: 'screenshots/final-check-success.png', fullPage: true });
  }
});
