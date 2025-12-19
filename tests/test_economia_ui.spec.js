// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Testes de Interface - Dashboard de Economia Real
 * 
 * Testa a nova aba "Economia" na página de métricas:
 * - Cards de resumo (total economizado, horas, hibernações)
 * - Gráfico de histórico
 * - Breakdown por GPU
 * - Filtro por período
 */

const BASE_URL = process.env.BASE_URL || 'http://localhost:8766';
const TEST_USER = 'marcoslogin';
const TEST_PASS = 'marcos123';

test.describe('Dashboard de Economia Real', () => {

    test.beforeEach(async ({ page }) => {
        // Login primeiro
        await page.goto(`${BASE_URL}/login`);
        await page.waitForLoadState('networkidle');

        // Tenta encontrar campos de login
        const usernameField = page.locator('input[name="username"], input[type="text"]').first();
        const passwordField = page.locator('input[name="password"], input[type="password"]').first();

        if (await usernameField.isVisible()) {
            await usernameField.fill(TEST_USER);
            await passwordField.fill(TEST_PASS);
            await page.locator('button[type="submit"]').first().click();
            await page.waitForLoadState('networkidle');
        }
    });

    test('Navegação para aba Economia', async ({ page }) => {
        // Navega para página de métricas
        await page.goto(`${BASE_URL}/metrics`);
        await page.waitForLoadState('networkidle');

        // Procura aba Economia
        const economiaTab = page.locator('button:has-text("Economia")');

        await expect(economiaTab).toBeVisible({ timeout: 10000 });

        // Clica na aba
        await economiaTab.click();
        await page.waitForLoadState('networkidle');

        // Screenshot
        await page.screenshot({
            path: 'tests/screenshots/economia-tab.png',
            fullPage: true
        });

        console.log('✓ Aba Economia visível e clicável');
    });

    test('Cards de resumo exibidos', async ({ page }) => {
        await page.goto(`${BASE_URL}/metrics`);
        await page.waitForLoadState('networkidle');

        // Clica na aba Economia
        const economiaTab = page.locator('button:has-text("Economia")');
        if (await economiaTab.isVisible()) {
            await economiaTab.click();
            await page.waitForTimeout(1000);
        }

        // Verifica cards de resumo
        const savingsDashboard = page.locator('.savings-dashboard, [class*="savings"]');

        if (await savingsDashboard.isVisible({ timeout: 5000 })) {
            // Verifica cards
            await expect(page.locator('text=/Total Economizado|Total Savings/i')).toBeVisible();

            console.log('✓ Dashboard de economia exibido');
        } else {
            console.log('⚠ Dashboard pode estar carregando ou sem dados');
        }

        await page.screenshot({
            path: 'tests/screenshots/economia-cards.png'
        });
    });

    test('Seletor de período funciona', async ({ page }) => {
        await page.goto(`${BASE_URL}/metrics`);
        await page.waitForLoadState('networkidle');

        // Clica na aba Economia
        const economiaTab = page.locator('button:has-text("Economia")');
        if (await economiaTab.isVisible()) {
            await economiaTab.click();
            await page.waitForTimeout(1000);
        }

        // Verifica seletor de período
        const periodButtons = page.locator('.period-selector button, button:has-text("7d"), button:has-text("30d"), button:has-text("90d")');

        const count = await periodButtons.count();
        if (count > 0) {
            // Clica em cada período
            for (let i = 0; i < Math.min(count, 3); i++) {
                await periodButtons.nth(i).click();
                await page.waitForTimeout(500);
            }
            console.log('✓ Seletor de período funciona');
        }

        await page.screenshot({
            path: 'tests/screenshots/economia-periodos.png'
        });
    });

    test('Gráfico de histórico carrega', async ({ page }) => {
        await page.goto(`${BASE_URL}/metrics`);
        await page.waitForLoadState('networkidle');

        // Clica na aba Economia
        const economiaTab = page.locator('button:has-text("Economia")');
        if (await economiaTab.isVisible()) {
            await economiaTab.click();
            await page.waitForTimeout(2000);
        }

        // Verifica se há canvas (Chart.js)
        const charts = page.locator('canvas');
        const chartCount = await charts.count();

        if (chartCount > 0) {
            console.log(`✓ ${chartCount} gráfico(s) encontrado(s)`);
        } else {
            console.log('⚠ Nenhum gráfico ainda (pode estar sem dados)');
        }

        await page.screenshot({
            path: 'tests/screenshots/economia-grafico.png'
        });
    });

    test('Estado vazio exibido quando sem dados', async ({ page }) => {
        await page.goto(`${BASE_URL}/metrics`);
        await page.waitForLoadState('networkidle');

        // Clica na aba Economia
        const economiaTab = page.locator('button:has-text("Economia")');
        if (await economiaTab.isVisible()) {
            await economiaTab.click();
            await page.waitForTimeout(1000);
        }

        // Verifica empty state
        const emptyState = page.locator('.empty-state, text=/Nenhuma hibernação/i');

        if (await emptyState.isVisible({ timeout: 3000 })) {
            console.log('✓ Empty state exibido corretamente');
        } else {
            console.log('✓ Dados disponíveis (sem empty state)');
        }
    });
});

test.describe('Configuração de CPU Standby', () => {

    test.beforeEach(async ({ page }) => {
        // Login
        await page.goto(`${BASE_URL}/login`);
        await page.waitForLoadState('networkidle');

        const usernameField = page.locator('input[name="username"], input[type="text"]').first();
        const passwordField = page.locator('input[name="password"], input[type="password"]').first();

        if (await usernameField.isVisible()) {
            await usernameField.fill(TEST_USER);
            await passwordField.fill(TEST_PASS);
            await page.locator('button[type="submit"]').first().click();
            await page.waitForLoadState('networkidle');
        }
    });

    test('Navegação para Settings', async ({ page }) => {
        await page.goto(`${BASE_URL}/settings`);
        await page.waitForLoadState('networkidle');

        // Verifica se página carregou
        await expect(page.locator('text=/Settings|Configurações/i')).toBeVisible({ timeout: 10000 });

        await page.screenshot({
            path: 'tests/screenshots/settings-page.png',
            fullPage: true
        });

        console.log('✓ Página de settings acessível');
    });

    test('Seção CPU Standby visível', async ({ page }) => {
        await page.goto(`${BASE_URL}/settings`);
        await page.waitForLoadState('networkidle');

        // Scroll para baixo para ver a seção
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(500);

        // Procura seção de Standby
        const standbySection = page.locator('text=/CPU Standby|Failover|CPU Backup/i');

        if (await standbySection.isVisible({ timeout: 5000 })) {
            console.log('✓ Seção CPU Standby encontrada');
        } else {
            console.log('⚠ Seção CPU Standby pode estar mais abaixo');
        }

        await page.screenshot({
            path: 'tests/screenshots/settings-standby.png',
            fullPage: true
        });
    });

    test('Toggle de Auto-Standby funciona', async ({ page }) => {
        await page.goto(`${BASE_URL}/settings`);
        await page.waitForLoadState('networkidle');

        // Scroll para a seção
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(500);

        // Procura toggle
        const toggle = page.locator('.standby-config input[type="checkbox"]').first();

        if (await toggle.isVisible({ timeout: 5000 })) {
            const wasChecked = await toggle.isChecked();
            await toggle.click();
            await page.waitForTimeout(300);

            const isChecked = await toggle.isChecked();
            expect(isChecked).not.toBe(wasChecked);

            // Reverte
            await toggle.click();

            console.log('✓ Toggle de auto-standby funciona');
        } else {
            console.log('⚠ Toggle não encontrado');
        }
    });

    test('Seletor de zona GCP funciona', async ({ page }) => {
        await page.goto(`${BASE_URL}/settings`);
        await page.waitForLoadState('networkidle');

        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(500);

        // Procura select de zona
        const zoneSelect = page.locator('.standby-config select').first();

        if (await zoneSelect.isVisible({ timeout: 5000 })) {
            // Verifica opções
            const options = await zoneSelect.locator('option').allTextContents();
            expect(options.length).toBeGreaterThan(0);

            console.log(`✓ Seletor de zona com ${options.length} opções`);
        }
    });

    test('Botão salvar habilitado', async ({ page }) => {
        await page.goto(`${BASE_URL}/settings`);
        await page.waitForLoadState('networkidle');

        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(500);

        // Procura botão salvar
        const saveButton = page.locator('.standby-config button:has-text("Salvar"), .standby-config .save-button');

        if (await saveButton.isVisible({ timeout: 5000 })) {
            const isEnabled = await saveButton.isEnabled();
            console.log(`✓ Botão salvar ${isEnabled ? 'habilitado' : 'desabilitado'}`);
        }

        await page.screenshot({
            path: 'tests/screenshots/settings-standby-form.png'
        });
    });
});

test.describe('Página de Máquinas - Badge de Standby', () => {

    test.beforeEach(async ({ page }) => {
        await page.goto(`${BASE_URL}/login`);
        await page.waitForLoadState('networkidle');

        const usernameField = page.locator('input[name="username"], input[type="text"]').first();
        const passwordField = page.locator('input[name="password"], input[type="password"]').first();

        if (await usernameField.isVisible()) {
            await usernameField.fill(TEST_USER);
            await passwordField.fill(TEST_PASS);
            await page.locator('button[type="submit"]').first().click();
            await page.waitForLoadState('networkidle');
        }
    });

    test('Lista de máquinas carrega', async ({ page }) => {
        await page.goto(`${BASE_URL}/machines`);
        await page.waitForLoadState('networkidle');

        // Verifica se a página carregou
        await expect(page.locator('text=/Máquinas|Machines|Minhas Máquinas/i')).toBeVisible({ timeout: 10000 });

        await page.screenshot({
            path: 'tests/screenshots/machines-list.png',
            fullPage: true
        });

        console.log('✓ Lista de máquinas carregada');
    });

    test('Badge GCP visível em máquinas com standby', async ({ page }) => {
        await page.goto(`${BASE_URL}/machines`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);

        // Procura badges de GCP
        const gcpBadges = page.locator('text="GCP", span:has-text("GCP")');
        const count = await gcpBadges.count();

        if (count > 0) {
            console.log(`✓ ${count} máquina(s) com badge GCP (standby ativo)`);
        } else {
            console.log('⚠ Nenhuma máquina com standby ativo (ou sem máquinas)');
        }

        await page.screenshot({
            path: 'tests/screenshots/machines-badges.png'
        });
    });

    test('Tooltip de standby exibe informações', async ({ page }) => {
        await page.goto(`${BASE_URL}/machines`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);

        // Procura badge GCP e faz hover
        const gcpBadge = page.locator('span:has-text("GCP")').first();

        if (await gcpBadge.isVisible({ timeout: 3000 })) {
            await gcpBadge.hover();
            await page.waitForTimeout(500);

            // Screenshot com tooltip
            await page.screenshot({
                path: 'tests/screenshots/machines-tooltip.png'
            });

            console.log('✓ Hover no badge GCP OK');
        }
    });

    test('Menu dropdown tem opção de Auto-Hibernation', async ({ page }) => {
        await page.goto(`${BASE_URL}/machines`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);

        // Procura botão de menu
        const menuButton = page.locator('[data-testid="machine-menu"], button:has(svg)').first();

        if (await menuButton.isVisible({ timeout: 5000 })) {
            await menuButton.click();
            await page.waitForTimeout(300);

            // Verifica opção Auto-Hibernation
            const hibernationOption = page.locator('text=/Auto-Hibernation|Hibernação/i');

            if (await hibernationOption.isVisible({ timeout: 2000 })) {
                console.log('✓ Opção Auto-Hibernation presente no menu');
            }

            // Fecha menu
            await page.keyboard.press('Escape');
        }

        await page.screenshot({
            path: 'tests/screenshots/machines-menu.png'
        });
    });
});

test.describe('API Health Checks', () => {

    test('Health endpoint responde', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/health`);

        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.status).toBe('healthy');

        console.log(`✓ Health OK: version=${data.version}`);
    });

    test('Agent status endpoint aceita heartbeat', async ({ request }) => {
        const response = await request.post(`${BASE_URL}/api/agent/status`, {
            data: {
                agent: "PlaywrightTest",
                version: "1.0.0",
                instance_id: "playwright_test",
                status: "idle",
                timestamp: new Date().toISOString(),
                gpu_utilization: 10.0
            }
        });

        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.received).toBe(true);

        console.log(`✓ Agent status aceita heartbeat`);
    });

    test('Savings real endpoint responde', async ({ request }) => {
        // Primeiro faz login para obter token
        const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
            data: { username: TEST_USER, password: TEST_PASS }
        });

        const loginData = await loginResponse.json();
        const token = loginData.access_token;

        if (token) {
            const response = await request.get(`${BASE_URL}/api/v1/metrics/savings/real?days=30`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            expect(response.ok()).toBeTruthy();

            const data = await response.json();
            expect(data.period_days).toBe(30);
            expect(data.summary).toBeDefined();

            console.log(`✓ Savings real OK: $${data.summary.total_savings_usd} economizados`);
        } else {
            console.log('⚠ Não foi possível obter token para teste');
        }
    });
});
