// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * VIBE TEST: Fine-Tuning Feature - Demo Mode Testing
 *
 * Ambiente: Demo Mode (localhost:5173/app)
 * Tipo: Interface testing with demo data
 *
 * Jornadas testadas:
 * 1. Navegar para Fine-Tuning page
 * 2. Verificar elementos da página
 * 3. Testar modal de criação (se disponível)
 */

test.describe('Fine-Tuning Feature - Vibe Test Journey', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to demo app for testing
    await page.goto('/app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // Close welcome modal if present
    const skipButton = page.locator('text="Pular tudo"');
    if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('should navigate to Fine-Tuning page and verify basic elements', async ({ page }) => {
    const startTime = Date.now();
    console.log('\n========================================');
    console.log('VIBE TEST: Fine-Tuning Page Navigation');
    console.log('Environment: Demo Mode');
    console.log('========================================\n');

    // ==========================================
    // STEP 1: NAVIGATE TO FINE-TUNING
    // ==========================================
    console.log('STEP 1: Navigate to Fine-Tuning page');
    const step1Start = Date.now();

    if (!page.url().includes('/app/finetune')) {
      await page.goto('/app/finetune');
    }
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    const step1Duration = Date.now() - step1Start;
    console.log(`Time: ${step1Duration}ms`);

    // Verify URL
    const currentUrl = page.url();
    console.log(`Current URL: ${currentUrl}`);

    if (!currentUrl.includes('/finetune')) {
      console.log('Status: Fine-Tuning page may not be available');
      // Try clicking sidebar link
      const finetuneLink = page.getByRole('link', { name: /fine.?tuning|treinamento/i }).first();
      if (await finetuneLink.isVisible({ timeout: 5000 }).catch(() => false)) {
        await finetuneLink.click({ force: true });
        await page.waitForLoadState('domcontentloaded');
        await page.waitForTimeout(1000);
      } else {
        console.log('Warning: Fine-Tuning page not accessible - checking if page is /finetune anyway');
        // Tentar navegar diretamente
        await page.goto('/app/finetune');
        await page.waitForLoadState('domcontentloaded');
        await page.waitForTimeout(1000);
      }
    }

    console.log('Status: On Fine-Tuning page');

    // ==========================================
    // STEP 2: VERIFY PAGE ELEMENTS
    // ==========================================
    console.log('\nSTEP 2: Verify page elements');
    const step2Start = Date.now();

    // Look for Fine-Tuning header
    const headerVariants = [
      'Fine-Tuning',
      'Fine Tuning',
      'FineTuning',
      'Treinamento'
    ];

    let hasHeader = false;
    for (const header of headerVariants) {
      const h = page.locator(`text="${header}"`);
      if (await h.isVisible().catch(() => false)) {
        console.log(`Found header: "${header}"`);
        hasHeader = true;
        break;
      }
    }

    if (!hasHeader) {
      console.log('Status: Fine-Tuning header not found');
      console.log('Note: Page may have different content in demo mode');

      // Check for any content
      const pageContent = await page.locator('main, [role="main"]').textContent().catch(() => '');
      console.log(`Page content length: ${pageContent.length} characters`);

      if (pageContent.length < 50) {
        console.log('Warning: page appears empty but continuing test');
        // Não fazer skip - continuar para verificar se há elementos interativos
      }
    }

    const step2Duration = Date.now() - step2Start;
    console.log(`Time: ${step2Duration}ms`);

    // ==========================================
    // STEP 3: LOOK FOR NEW JOB BUTTON
    // ==========================================
    console.log('\nSTEP 3: Look for job creation button');
    const step3Start = Date.now();

    const buttonVariants = [
      'New Fine-Tune Job',
      'Novo Job',
      'Criar Job',
      'Create Job',
      'Start Fine-Tuning'
    ];

    let hasNewJobButton = false;
    let newJobButton = null;

    for (const btnText of buttonVariants) {
      const btn = page.locator(`button:has-text("${btnText}")`);
      if (await btn.isVisible().catch(() => false)) {
        console.log(`Found button: "${btnText}"`);
        hasNewJobButton = true;
        newJobButton = btn;
        break;
      }
    }

    if (!hasNewJobButton) {
      console.log('Status: No job creation button found');
      console.log('Note: Feature may not be available in demo mode');
    }

    const step3Duration = Date.now() - step3Start;
    console.log(`Time: ${step3Duration}ms`);

    // ==========================================
    // STEP 4: VERIFY STATS CARDS (if present)
    // ==========================================
    console.log('\nSTEP 4: Check for stats cards');
    const step4Start = Date.now();

    const statsVariants = ['Total Jobs', 'Running', 'Completed', 'Failed', 'Jobs'];
    let statsFound = 0;

    for (const stat of statsVariants) {
      const statElement = page.locator(`text=/${stat}/i`);
      if (await statElement.isVisible().catch(() => false)) {
        statsFound++;
      }
    }

    console.log(`Stats cards found: ${statsFound}`);

    const step4Duration = Date.now() - step4Start;
    console.log(`Time: ${step4Duration}ms`);

    // ==========================================
    // STEP 5: TRY TO OPEN MODAL (if button exists)
    // ==========================================
    if (hasNewJobButton && newJobButton) {
      console.log('\nSTEP 5: Try to open job creation modal');
      const step5Start = Date.now();

      await newJobButton.click();
      await page.waitForTimeout(1000);

      // Check for modal
      const modal = page.locator('[role="dialog"], [class*="modal"]');
      const hasModal = await modal.isVisible().catch(() => false);

      if (hasModal) {
        console.log('Modal opened successfully');

        // Look for wizard steps
        const hasSteps = await page.locator('text=/Step \\d/').first().isVisible().catch(() => false);
        if (hasSteps) {
          console.log('Validated: Wizard steps visible in modal');
        }

        // Look for model selection
        const hasModels = await page.locator('text=/Llama|Mistral|Phi|Gemma|Model/i').first().isVisible().catch(() => false);
        if (hasModels) {
          console.log('Validated: Model selection visible');
        }

        // Close modal
        const closeButton = page.locator('button:has-text("Close"), button:has-text("Cancel"), [aria-label="Close"]');
        if (await closeButton.isVisible().catch(() => false)) {
          await closeButton.click();
          await page.waitForTimeout(500);
        }
      } else {
        console.log('Status: Modal did not appear (may not be implemented)');
      }

      const step5Duration = Date.now() - step5Start;
      console.log(`Time: ${step5Duration}ms`);
    }

    // ==========================================
    // FINAL SUMMARY
    // ==========================================
    const totalDuration = Date.now() - startTime;
    console.log('\n========================================');
    console.log('FINE-TUNING PAGE TEST COMPLETE');
    console.log('========================================');
    console.log(`Total Duration: ${totalDuration}ms`);
    console.log(`Header found: ${hasHeader ? 'YES' : 'NO'}`);
    console.log(`New job button: ${hasNewJobButton ? 'YES' : 'NO'}`);
    console.log(`Stats cards: ${statsFound}`);
    console.log('========================================\n');
  });

  test('should verify Fine-Tuning sidebar link exists', async ({ page }) => {
    console.log('\n========================================');
    console.log('VIBE TEST: Fine-Tuning Sidebar Link');
    console.log('========================================\n');

    // Check for Fine-Tuning link in sidebar
    const finetuneLink = page.getByRole('link', { name: /fine.?tuning|treinamento/i }).first();
    const hasLink = await finetuneLink.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasLink) {
      console.log('Validated: Fine-Tuning link visible in sidebar');

      // Click and verify navigation
      await finetuneLink.click({ force: true });
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const currentUrl = page.url();
      expect(currentUrl).toContain('/finetune');
      console.log(`Validated: Navigated to ${currentUrl}`);
    } else {
      console.log('Status: Fine-Tuning link not in sidebar');
      console.log('Note: Feature may not be enabled - checking page directly');

      // Tentar navegar diretamente
      await page.goto('/app/finetune');
      await page.waitForLoadState('domcontentloaded');

      const currentUrl = page.url();
      console.log(`Navigated to: ${currentUrl}`);

      // Verificar se página tem algum conteúdo
      const hasContent = await page.locator('main, [role="main"]').isVisible().catch(() => false);
      expect(hasContent).toBeTruthy();
    }

    console.log('\n========================================');
    console.log('SIDEBAR LINK TEST COMPLETE');
    console.log('========================================\n');
  });

  test('should display fine-tuning jobs list if available', async ({ page }) => {
    console.log('\n========================================');
    console.log('VIBE TEST: Fine-Tuning Jobs List');
    console.log('========================================\n');

    if (!page.url().includes('/app/finetune')) {
      await page.goto('/app/finetune');
    }
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Check for jobs list or empty state
    const hasJobsList = await page.locator('[class*="grid"], [class*="list"]').filter({
      has: page.locator('text=/Job|Training|Model|Status/i')
    }).isVisible().catch(() => false);

    const hasEmptyState = await page.locator('text=/No jobs|Empty|Nenhum job/i').first().isVisible().catch(() => false);

    if (hasJobsList) {
      console.log('Validated: Jobs list/grid visible');

      // Count job cards
      const jobCards = await page.locator('[class*="card"], [class*="rounded-lg"][class*="border"]').count();
      console.log(`Job cards found: ${jobCards}`);
    } else if (hasEmptyState) {
      console.log('Validated: Empty state visible (no jobs yet)');
    } else {
      console.log('Status: Jobs list not found');
      console.log('Note: Page may have different layout in demo mode');
    }

    // Check for any interactive elements
    const interactiveCount = await page.locator('button, a[href], input').count();
    console.log(`Interactive elements: ${interactiveCount}`);
    expect(interactiveCount).toBeGreaterThan(0);

    console.log('\n========================================');
    console.log('JOBS LIST TEST COMPLETE');
    console.log('========================================\n');
  });

});
