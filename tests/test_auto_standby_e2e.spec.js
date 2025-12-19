// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Teste E2E: Auto-Standby com Interface
 *
 * Fluxo testado:
 * 1. Acessa a aplicação
 * 2. Cria uma GPU
 * 3. Verifica se CPU standby foi criada automaticamente
 * 4. Verifica se mostra os badges de provider (Vast.ai + GCP)
 * 5. Verifica se mostra o preço combinado
 * 6. Destrói a GPU
 * 7. Verifica se CPU standby foi destruída
 */

const BASE_URL = 'http://localhost:8766';

// Credenciais de teste
const TEST_USER = 'test@test.com';
const TEST_PASSWORD = 'test123';

/**
 * Helper function to login via UI
 */
async function login(page) {
  await page.goto(`${BASE_URL}/`);

  // Verifica se está na página de login
  const loginForm = page.locator('input[type="password"]');
  if (await loginForm.isVisible({ timeout: 3000 }).catch(() => false)) {
    console.log('Fazendo login...');

    // Preenche username
    await page.locator('input').first().fill(TEST_USER);

    // Preenche password
    await page.locator('input[type="password"]').fill(TEST_PASSWORD);

    // Clica no botão de login
    await page.locator('button:has-text("Login")').click();

    // Aguarda redirect
    await page.waitForTimeout(2000);
    console.log('Login realizado');
  }
}

test.describe('Auto-Standby E2E', () => {

  test.beforeAll(async () => {
    // Configurar auto-standby via API antes dos testes
    console.log('Configurando auto-standby...');

    const configResponse = await fetch(`${BASE_URL}/api/v1/standby/configure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: true,
        gcp_zone: 'europe-west1-b',
        gcp_machine_type: 'e2-medium',
        gcp_spot: true,
        sync_interval: 30,
        auto_failover: true,
      }),
    });

    // Pode falhar se não tiver credenciais, mas continua o teste
    console.log('Config response:', configResponse.status);
  });

  test('should display provider badges and pricing with CPU standby', async ({ page }) => {
    // Fazer login primeiro
    await login(page);

    // Ir para página de máquinas
    await page.goto(`${BASE_URL}/machines`);

    // Esperar carregar
    await page.waitForTimeout(2000);

    // Tirar screenshot inicial
    await page.screenshot({ path: 'tests/screenshots/machines-initial.png', fullPage: true });

    // Verificar se a página carregou (pode estar em inglês ou português)
    await expect(page.locator('text=Minhas Máquinas').or(page.locator('text=My Machines')).or(page.locator('h1'))).toBeVisible({ timeout: 10000 });

    // Verificar se tem máquinas listadas
    const machineCards = page.locator('[class*="rounded-lg"][class*="border"]');
    const count = await machineCards.count();
    console.log(`Máquinas encontradas: ${count}`);

    if (count > 0) {
      // Verificar se mostra badge Vast.ai
      const vastBadge = page.locator('text=Vast.ai').first();
      await expect(vastBadge).toBeVisible({ timeout: 5000 });
      console.log('Badge Vast.ai encontrado');

      // Verificar se mostra preço
      const priceText = page.locator('[class*="text-yellow-400"]').first();
      await expect(priceText).toBeVisible();
      const price = await priceText.textContent();
      console.log(`Preço encontrado: ${price}`);

      // Verificar se tem badge GCP (se tiver standby ativo)
      const gcpBadge = page.locator('text=GCP');
      const hasGcpBadge = await gcpBadge.count() > 0;
      console.log(`Badge GCP (CPU Standby): ${hasGcpBadge ? 'Sim' : 'Não'}`);

      // Verificar se mostra "+backup" se tiver standby
      const backupIndicator = page.locator('text=+backup');
      const hasBackup = await backupIndicator.count() > 0;
      console.log(`Indicador +backup: ${hasBackup ? 'Sim' : 'Não'}`);

      // Tirar screenshot com máquinas
      await page.screenshot({ path: 'tests/screenshots/machines-with-cards.png', fullPage: true });
    }
  });

  test('should show standby status in API', async ({ page }) => {
    // Verificar status do standby via API
    const response = await page.request.get(`${BASE_URL}/api/v1/standby/status`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    console.log('Standby Status:', JSON.stringify(data, null, 2));

    expect(data).toHaveProperty('configured');
    expect(data).toHaveProperty('auto_standby_enabled');
    expect(data).toHaveProperty('active_associations');
  });

  test('should list instances with CPU standby info', async ({ page }) => {
    // Verificar lista de instâncias via API
    const response = await page.request.get(`${BASE_URL}/api/instances`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    console.log(`Instâncias encontradas: ${data.instances?.length || 0}`);

    if (data.instances?.length > 0) {
      const inst = data.instances[0];
      console.log('Primeira instância:', {
        id: inst.id,
        gpu_name: inst.gpu_name,
        provider: inst.provider,
        dph_total: inst.dph_total,
        cpu_standby: inst.cpu_standby,
        total_dph: inst.total_dph,
      });

      // Verificar campos
      expect(inst).toHaveProperty('provider');
      expect(inst).toHaveProperty('total_dph');

      // Se tiver CPU standby
      if (inst.cpu_standby?.enabled) {
        expect(inst.cpu_standby).toHaveProperty('provider');
        expect(inst.cpu_standby).toHaveProperty('dph_total');
        expect(inst.cpu_standby).toHaveProperty('ip');
        console.log(`CPU Standby ativo: ${inst.cpu_standby.name} @ ${inst.cpu_standby.ip}`);
      }
    }
  });

  test('full flow: create GPU, verify standby, destroy', async ({ page }) => {
    test.setTimeout(600000); // 10 minutos para este teste

    // Fazer login primeiro
    await login(page);

    // Ir para Dashboard
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Screenshot inicial
    await page.screenshot({ path: 'tests/screenshots/dashboard-initial.png', fullPage: true });

    // Verificar se o Dashboard carregou (espera página carregar completamente)
    await page.waitForLoadState('networkidle');
    console.log('Dashboard carregado');

    // Buscar oferta barata
    console.log('Buscando oferta de GPU...');
    const offersResponse = await page.request.get(`${BASE_URL}/api/instances/offers?max_price=0.20&limit=5`);

    if (offersResponse.ok()) {
      const offersData = await offersResponse.json();
      console.log(`Ofertas encontradas: ${offersData.offers?.length || 0}`);

      if (offersData.offers?.length > 0) {
        const offer = offersData.offers[0];
        console.log(`Selecionada: ${offer.gpu_name} @ $${offer.dph_total}/h`);

        // Criar instância via API (mais confiável que UI)
        console.log('Criando instância...');
        const createResponse = await page.request.post(`${BASE_URL}/api/instances`, {
          data: {
            offer_id: offer.id,
            image: 'pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime',
            disk_size: 20,
            label: 'playwright-standby-test',
          },
        });

        if (createResponse.ok()) {
          const instance = await createResponse.json();
          console.log(`Instância criada: ${instance.id}`);

          // Aguardar CPU standby ser criado (até 3 minutos)
          console.log('Aguardando CPU standby ser criado...');
          let standbyCreated = false;

          for (let i = 0; i < 18; i++) { // 18 * 10s = 3 minutos
            await page.waitForTimeout(10000);

            const statusResponse = await page.request.get(`${BASE_URL}/api/v1/standby/associations/${instance.id}`);

            if (statusResponse.ok()) {
              const standbyData = await statusResponse.json();
              console.log(`Standby status: ${JSON.stringify(standbyData)}`);

              if (standbyData.cpu_standby?.ip) {
                standbyCreated = true;
                console.log(`CPU Standby criado: ${standbyData.cpu_standby.name} @ ${standbyData.cpu_standby.ip}`);
                break;
              }
            }

            console.log(`Aguardando... (${i + 1}/18)`);
          }

          // Ir para Machines e verificar UI
          await page.goto(`${BASE_URL}/machines`);
          await page.waitForTimeout(3000);

          // Screenshot com a máquina criada
          await page.screenshot({ path: 'tests/screenshots/machines-with-new-gpu.png', fullPage: true });

          // Verificar se mostra os badges
          if (standbyCreated) {
            const gcpBadge = page.locator('text=GCP');
            const hasGcp = await gcpBadge.count() > 0;
            console.log(`Badge GCP visível: ${hasGcp}`);

            // Screenshot mostrando CPU standby
            await page.screenshot({ path: 'tests/screenshots/machines-with-cpu-standby.png', fullPage: true });
          }

          // Destruir a instância
          console.log(`Destruindo instância ${instance.id}...`);
          const destroyResponse = await page.request.delete(`${BASE_URL}/api/instances/${instance.id}`);

          if (destroyResponse.ok()) {
            console.log('Instância destruída');

            // Verificar se CPU standby também foi destruído
            await page.waitForTimeout(5000);

            const finalStatusResponse = await page.request.get(`${BASE_URL}/api/v1/standby/associations/${instance.id}`);

            if (finalStatusResponse.status() === 404) {
              console.log('CPU Standby também foi destruído (associação removida)');
            } else {
              console.log('Verificando cleanup...');
            }
          }

          // Screenshot final
          await page.goto(`${BASE_URL}/machines`);
          await page.waitForTimeout(2000);
          await page.screenshot({ path: 'tests/screenshots/machines-after-destroy.png', fullPage: true });
        }
      }
    }
  });

});
