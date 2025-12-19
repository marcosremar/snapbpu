const { test, expect } = require('@playwright/test');

test('Debug Token Persistence', async ({ page }) => {
  console.log('\n=== DEBUG TOKEN PERSISTENCE ===\n');

  // 1. Ir para homepage
  await page.goto('https://dumontcloud.com', { waitUntil: 'networkidle' });
  console.log('1. Acessado homepage');

  // 2. Verificar token antes do login
  let token = await page.evaluate(() => localStorage.getItem('auth_token'));
  console.log(`2. Token ANTES do login: ${token ? 'EXISTE' : 'NAO EXISTE'}`);

  // 3. Clicar em Login
  await page.locator('button:has-text("Login")').first().click();
  await page.waitForTimeout(1000);
  console.log('3. Modal de login aberto');

  // 4. Preencher formulário
  const inputs = await page.locator('input').all();
  await inputs[1].fill('marcosremar@gmail.com');
  await inputs[2].fill('dumont123');
  console.log('4. Formulario preenchido');

  // 5. Submit do formulário
  await page.evaluate(() => {
    const overlay = document.querySelector('.login-modal-overlay');
    if (overlay) overlay.style.pointerEvents = 'none';
  });

  await page.locator('button[type="submit"]').click({ force: true });

  // 6. Aguardar processamento
  await page.waitForTimeout(2000);

  // 7. Verificar token após login
  token = await page.evaluate(() => localStorage.getItem('auth_token'));
  console.log(`5. Token APOS login: ${token ? 'EXISTE (' + token.substring(0, 30) + '...)' : 'NAO EXISTE'}`);

  // 8. Verificar localStorage completo
  const storage = await page.evaluate(() => {
    const keys = Object.keys(localStorage);
    return keys.map(k => `${k}=${localStorage.getItem(k).substring(0, 30)}`);
  });
  console.log(`6. localStorage contém: ${storage.join(', ')}`);

  // 9. Verificar se está em /app
  await page.waitForTimeout(500);
  const url = page.url();
  console.log(`7. URL atual: ${url}`);

  // 10. Tentar acessar /app manualmente
  await page.goto('https://dumontcloud.com/app', { waitUntil: 'networkidle' });
  const finalUrl = page.url();
  console.log(`8. URL apos ir para /app: ${finalUrl}`);

  // 11. Procurar Logout
  const logoutBtn = page.locator('button:has-text("Logout")');
  const logoutCount = await logoutBtn.count();
  console.log(`9. Botao Logout encontrado: ${logoutCount > 0 ? 'SIM' : 'NAO'}`);

  if (logoutCount > 0) {
    const isVisible = await logoutBtn.isVisible();
    console.log(`   Logout visivel: ${isVisible}`);
  }

  // 12. Screenshot final
  await page.screenshot({ path: 'screenshots/debug-token.png' });
  console.log('10. Screenshot salvo\n');
});
