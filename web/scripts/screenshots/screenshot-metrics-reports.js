import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

const metricsReports = [
  { name: 'metrics-market', path: '/demo-app/metrics?tab=market' },
  { name: 'metrics-providers', path: '/demo-app/metrics?tab=providers' },
  { name: 'metrics-efficiency', path: '/demo-app/metrics?tab=efficiency' },
  { name: 'metrics-spot-monitor', path: '/demo-app/metrics?tab=spot&report=monitor' },
  { name: 'metrics-spot-savings', path: '/demo-app/metrics?tab=spot&report=savings' },
  { name: 'metrics-spot-availability', path: '/demo-app/metrics?tab=spot&report=availability' },
  { name: 'metrics-spot-prediction', path: '/demo-app/metrics?tab=spot&report=prediction' },
  { name: 'metrics-spot-safe-windows', path: '/demo-app/metrics?tab=spot&report=safe-windows' },
  { name: 'metrics-spot-reliability', path: '/demo-app/metrics?tab=spot&report=reliability' },
  { name: 'metrics-spot-interruption', path: '/demo-app/metrics?tab=spot&report=interruption' },
  { name: 'metrics-spot-llm', path: '/demo-app/metrics?tab=spot&report=llm' },
  { name: 'metrics-spot-training', path: '/demo-app/metrics?tab=spot&report=training' },
  { name: 'metrics-spot-fleet', path: '/demo-app/metrics?tab=spot&report=fleet' },
];

async function screenshotMetricsReports() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  console.log('Taking screenshots of all metrics reports...\n');

  for (const report of metricsReports) {
    try {
      const url = `${BASE_URL}${report.path}`;
      console.log(`📸 ${report.name}: ${url}`);

      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(2000);

      await page.screenshot({
        path: `/tmp/${report.name}.png`,
        fullPage: true
      });

      console.log(`   ✅ Saved: /tmp/${report.name}.png`);
    } catch (err) {
      console.log(`   ❌ Error: ${err.message}`);
    }
  }

  console.log('\n✅ All metrics screenshots completed!');
  await browser.close();
}

screenshotMetricsReports();
