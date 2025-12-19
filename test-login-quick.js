const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  console.log('1. Acessando landing page...');
  await page.goto('https://dumontcloud.com/', { waitUntil: 'networkidle' });
  
  console.log('2. Clicando em Login...');
  await page.click('button:has-text("Login"), .nav-login');
  await page.waitForTimeout(1000);
  
  console.log('3. Preenchendo credenciais...');
  await page.fill('input[type="text"], input[placeholder*="email"]', 'marcosremar@gmail.com');
  await page.fill('input[type="password"]', 'dumont123');
  
  console.log('4. Submetendo...');
  
  // Capturar resposta da API
  page.on('response', response => {
    if (response.url().includes('/api/auth/login')) {
      console.log('   API Response:', response.status());
      response.json().then(data => console.log('   Data:', JSON.stringify(data)));
    }
  });
  
  await page.click('button[type="submit"], .form-submit');
  await page.waitForTimeout(3000);
  
  console.log('5. URL atual:', page.url());
  
  // Verificar se há erro visível
  const errorText = await page.locator('.form-error, .alert-error, .error').textContent().catch(() => null);
  if (errorText) {
    console.log('   ERRO VISÍVEL:', errorText);
  }
  
  await browser.close();
  console.log('Teste concluído!');
})();
