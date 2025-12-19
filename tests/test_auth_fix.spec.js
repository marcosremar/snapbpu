const { test, expect } = require('@playwright/test');

test('Verificar busca de ofertas com auth_token', async ({ page }) => {
  const apiCalls = [];
  
  page.on('response', async res => {
    if (res.url().includes('/api/')) {
      let body = '';
      try { body = await res.text(); } catch(e) {}
      apiCalls.push({ url: res.url(), status: res.status(), body: body.substring(0, 300) });
    }
  });

  // 1. Login
  console.log('=== Fazendo login ===');
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  
  const emailField = page.locator('input[type="email"]').first();
  if (await emailField.count() > 0) {
    await emailField.fill('marcosremar@gmail.com');
    await page.locator('input[type="password"]').first().fill('dumont123');
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(3000);
  }

  // 2. Verificar token
  const authToken = await page.evaluate(() => localStorage.getItem('auth_token'));
  console.log('auth_token:', authToken ? authToken.substring(0, 50) + '...' : 'NENHUM');

  // 3. Clicar em um tier para buscar
  const tier = page.locator('text=Rapido').first();
  if (await tier.count() > 0) {
    await tier.click();
    await page.waitForTimeout(5000);
  }

  // 4. Log das chamadas
  console.log('\n=== API Calls ===');
  apiCalls.forEach(c => console.log(`${c.status} ${c.url}\n  Body: ${c.body}`));
  
  await page.screenshot({ path: 'screenshots/auth-fix-test.png', fullPage: true });
});
