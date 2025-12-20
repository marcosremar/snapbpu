import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

const pages = [
  { name: 'landing', path: '/' },
  { name: 'login', path: '/login' },
  { name: 'dashboard', path: '/demo-app' },
  { name: 'machines', path: '/demo-app/machines' },
  { name: 'settings', path: '/demo-app/settings' },
  { name: 'metrics-hub', path: '/demo-app/metrics-hub' },
  { name: 'metrics', path: '/demo-app/metrics' },
  { name: 'savings', path: '/demo-app/savings' },
  { name: 'failover-report', path: '/demo-app/failover-report' },
  { name: 'finetune', path: '/demo-app/finetune' },
  { name: 'advisor', path: '/demo-app/advisor' },
  { name: 'docs', path: '/demo-docs' },
];

async function screenshotAllPages() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  console.log('Taking screenshots of all pages...\n');

  for (const pageInfo of pages) {
    try {
      const url = `${BASE_URL}${pageInfo.path}`;
      console.log(`📸 ${pageInfo.name}: ${url}`);

      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(1500);

      await page.screenshot({
        path: `/tmp/page-${pageInfo.name}.png`,
        fullPage: true
      });

      console.log(`   ✅ Saved: /tmp/page-${pageInfo.name}.png`);
    } catch (err) {
      console.log(`   ❌ Error: ${err.message}`);
    }
  }

  console.log('\n✅ All screenshots completed!');
  await browser.close();
}

screenshotAllPages();
