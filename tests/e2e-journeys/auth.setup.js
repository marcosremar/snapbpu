// @ts-check
const { test: setup, expect } = require('@playwright/test');
const path = require('path');

const authFile = path.join(__dirname, '../.auth/user.json');

/**
 * Setup de autenticação global
 * Este setup roda UMA vez antes de todos os testes
 * e salva o estado de autenticação para reutilização
 */
setup('authenticate', async ({ page }) => {
  // 1. Vai para login
  console.log('📍 Navigating to /login');
  await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
  console.log('✅ Login page loaded');

  // 2. Aguarda o formulário carregar
  await page.waitForLoadState('networkidle');
  console.log('✅ Network idle reached');

  // 3. Preenche credenciais - o formulário usa textbox genérico
  // Primeiro textbox é Username, segundo é Password
  const usernameInput = page.getByRole('textbox').first();
  const passwordInput = page.getByRole('textbox').nth(1);
  const submitButton = page.getByRole('button', { name: /login|entrar/i });

  console.log('🔐 Filling credentials');
  await usernameInput.fill('test@test.com');
  await passwordInput.fill('test123');

  // 4. Click login e aguarda navegação
  console.log('📤 Submitting login');
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(() => {}),
    submitButton.click()
  ]);

  // Pequeno delay para garantir que a navegação completou
  await page.waitForTimeout(1000);

  const currentUrl = page.url();
  console.log('📍 Current URL after login:', currentUrl);

  // 5. Salva estado de autenticação
  await page.context().storageState({ path: authFile });

  console.log('✅ Autenticação salva em', authFile);
});
