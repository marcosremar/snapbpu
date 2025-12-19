const { test } = require('@playwright/test');

test('Debug Login Completo', async ({ page }) => {
  console.log('\n=== DEBUG LOGIN COMPLETO ===\n');

  // Passo 1: Ir para homepage
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  console.log('1. Homepage carregada');

  // Passo 2: Abrir modal de login
  await page.locator('button:has-text("Login")').click();
  await page.waitForTimeout(1000);
  console.log('2. Modal aberto');

  // Passo 3: Preencher formulário
  const inputs = await page.locator('input').all();
  await inputs[1].fill('marcosremar@gmail.com');
  await inputs[2].fill('123456');
  console.log('3. Formulario preenchido');

  // Passo 4: Monitor localStorage antes de submit
  await page.evaluate(() => {
    if (typeof console !== 'undefined') {
      console.log('localStorage antes:', Object.keys(localStorage));
    }
  });

  // Passo 5: Submit
  console.log('4. Submitando formulario');
  await page.evaluate(() => {
    const overlay = document.querySelector('.login-modal-overlay');
    if (overlay) overlay.style.pointerEvents = 'none';
  });

  const submitBtn = await page.locator('button[type="submit"]').first();
  await submitBtn.click({ force: true });
  await page.waitForTimeout(3000);

  // Passo 6: Verificar localStorage após
  const tokens = await page.evaluate(() => {
    return Object.keys(localStorage);
  });
  console.log(`5. localStorage contém: ${tokens.join(', ')}`);

  // Passo 7: Verificar URL
  console.log(`6. URL atual: ${page.url()}`);

  // Passo 8: Tentar acessar /app
  await page.goto('https://dumontcloud.com/app', { waitUntil: 'networkidle' });
  console.log(`7. URL apos /app: ${page.url()}`);

  // Passo 9: Procurar Logout
  const logout = page.locator('button:has-text("Logout")');
  const logoutCount = await logout.count();
  console.log(`8. Logout encontrado: ${logoutCount > 0 ? 'SIM' : 'NAO'}`);

  console.log('\n=== FIM DEBUG ===\n');
});
