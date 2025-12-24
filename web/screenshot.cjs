const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ 
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();
  
  // Ir para login primeiro
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  
  // Setar tema dark ANTES de qualquer navegação adicional
  await page.evaluate(() => {
    localStorage.setItem('theme', 'dark');
    document.documentElement.classList.add('dark');
  });
  
  // Reload para aplicar tema
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  
  // Clicar no link de demonstração
  await page.click('text=Demonstração');
  await page.waitForTimeout(3000);
  
  await page.screenshot({ path: '/tmp/dashboard-dark.png', fullPage: true });
  await browser.close();
  console.log('Screenshot saved');
})();
