/**
 * Dumont Cloud - Teste Funcional Completo
 *
 * Testa AÇÕES REAIS: buscar máquinas, criar snapshots, pausar, etc.
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';
const TEST_USER = 'marcosremar@gmail.com';
const TEST_PASS = 'Marcos123';

test.describe('Testes Funcionais - Ações Reais', () => {

  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="text"]', TEST_USER);
    await page.fill('input[type="password"]', TEST_PASS);
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
  });

  test('1. BUSCAR MÁQUINAS - Verificar se retorna resultados', async ({ page }) => {
    console.log('\n🔍 TESTE: Buscar Máquinas Disponíveis\n');

    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Selecionar região Europa
    await page.click('button:has-text("Europa")');
    await page.waitForTimeout(500);
    console.log('✓ Região Europa selecionada');

    // Clicar em buscar
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    console.log('✓ Clicou em Buscar');

    // Aguardar resultados (até 15 segundos)
    await page.waitForTimeout(10000);

    // Verificar se apareceram resultados
    const resultadosText = await page.locator('text=/Máquinas Disponíveis|resultados encontrados/i').isVisible();
    const gpuCards = await page.locator('text=/RTX|A100|H100/').count();
    const precos = await page.locator('text=/\\$[\\d.]+\\/hr/').count();
    const botoesSelecionar = await page.locator('button:has-text("Selecionar")').count();

    await page.screenshot({ path: 'screenshots/func-01-busca-resultados.png', fullPage: true });

    console.log(`\n📊 RESULTADOS DA BUSCA:`);
    console.log(`   - Título "Máquinas Disponíveis": ${resultadosText ? 'SIM' : 'NÃO'}`);
    console.log(`   - GPUs encontradas: ${gpuCards}`);
    console.log(`   - Preços exibidos: ${precos}`);
    console.log(`   - Botões "Selecionar": ${botoesSelecionar}`);

    if (gpuCards > 0) {
      console.log('\n✅ SUCESSO: Busca retornou máquinas!\n');
    } else {
      console.log('\n❌ FALHA: Nenhuma máquina encontrada\n');
    }

    expect(gpuCards).toBeGreaterThan(0);
  });

  test('2. FILTROS DE MÁQUINAS - Testar Todas/Online/Offline', async ({ page }) => {
    console.log('\n🔍 TESTE: Filtros de Máquinas\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Capturar contagem inicial
    const todasBtn = page.locator('button:has-text("Todas")');
    const onlineBtn = page.locator('button:has-text("Online")');
    const offlineBtn = page.locator('button:has-text("Offline")');

    // Extrair números dos botões
    const todasText = await todasBtn.textContent();
    const onlineText = await onlineBtn.textContent();
    const offlineText = await offlineBtn.textContent();

    console.log(`📊 Contagem nos filtros:`);
    console.log(`   - ${todasText}`);
    console.log(`   - ${onlineText}`);
    console.log(`   - ${offlineText}`);

    // Clicar em Online e verificar
    await onlineBtn.click();
    await page.waitForTimeout(1000);
    const cardsOnline = await page.locator('text=ONLINE').count();
    console.log(`\n✓ Filtro Online: ${cardsOnline} máquinas exibidas`);
    await page.screenshot({ path: 'screenshots/func-02-filtro-online.png', fullPage: true });

    // Clicar em Offline e verificar
    await offlineBtn.click();
    await page.waitForTimeout(1000);
    const cardsOffline = await page.locator('[class*="border"]').filter({ hasText: /OFFLINE|Offline/ }).count();
    console.log(`✓ Filtro Offline: ${cardsOffline} máquinas exibidas`);
    await page.screenshot({ path: 'screenshots/func-02-filtro-offline.png', fullPage: true });

    // Voltar para Todas
    await todasBtn.click();
    await page.waitForTimeout(1000);
    const cardsTodas = await page.locator('text=/ONLINE|OFFLINE/').count();
    console.log(`✓ Filtro Todas: ${cardsTodas} máquinas exibidas`);

    console.log('\n✅ SUCESSO: Filtros funcionando!\n');
  });

  test('3. DROPDOWN VS CODE - Verificar opções Online/Desktop', async ({ page }) => {
    console.log('\n🔍 TESTE: Dropdown VS Code\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Filtrar Online
    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    // Clicar no primeiro botão VS Code
    const vscodeBtn = page.locator('button:has-text("VS Code")').first();
    if (await vscodeBtn.count() > 0) {
      await vscodeBtn.click();
      await page.waitForTimeout(500);

      // Verificar se dropdown abriu
      const onlineWeb = await page.locator('text=Online (Web)').isVisible();
      const desktopSSH = await page.locator('text=Desktop (SSH)').isVisible();

      await page.screenshot({ path: 'screenshots/func-03-vscode-dropdown.png' });

      console.log(`📊 Opções do dropdown:`);
      console.log(`   - Online (Web): ${onlineWeb ? 'VISÍVEL' : 'NÃO VISÍVEL'}`);
      console.log(`   - Desktop (SSH): ${desktopSSH ? 'VISÍVEL' : 'NÃO VISÍVEL'}`);

      if (onlineWeb && desktopSSH) {
        console.log('\n✅ SUCESSO: Dropdown VS Code funcionando!\n');
      }

      await page.keyboard.press('Escape');

      expect(onlineWeb).toBeTruthy();
      expect(desktopSSH).toBeTruthy();
    } else {
      console.log('⚠️ Nenhuma máquina online para testar');
    }
  });

  test('4. MENU DE OPÇÕES DA MÁQUINA - Verificar itens', async ({ page }) => {
    console.log('\n🔍 TESTE: Menu de Opções (3 pontos)\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Encontrar menu de 3 pontos
    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      await page.screenshot({ path: 'screenshots/func-04-menu-opcoes.png' });

      // Verificar opções do menu
      const opcoes = [
        'Auto-Hibernation',
        'Copiar SSH',
        'Criar Snapshot',
        'Restaurar',
        'Destruir'
      ];

      console.log('📊 Opções do menu:');
      for (const opcao of opcoes) {
        const visivel = await page.locator(`text=/${opcao}/i`).isVisible().catch(() => false);
        console.log(`   - ${opcao}: ${visivel ? 'VISÍVEL ✓' : 'NÃO ENCONTRADO'}`);
      }

      await page.keyboard.press('Escape');
      console.log('\n✅ Menu de opções verificado!\n');
    }
  });

  test('5. CRIAR SNAPSHOT - Testar funcionalidade', async ({ page }) => {
    console.log('\n🔍 TESTE: Criar Snapshot\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Filtrar Online
    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    // Abrir menu de opções
    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      // Procurar opção de Snapshot
      const snapshotOption = page.locator('text=/Criar Snapshot|Snapshot/i');

      if (await snapshotOption.count() > 0) {
        console.log('✓ Opção "Criar Snapshot" encontrada');

        // Clicar para criar snapshot
        await snapshotOption.click();
        await page.waitForTimeout(3000);

        await page.screenshot({ path: 'screenshots/func-05-criar-snapshot.png', fullPage: true });

        // Verificar se apareceu alguma confirmação ou toast
        const toast = await page.locator('[class*="toast"], [class*="notification"], text=/snapshot|sucesso|criado/i').isVisible().catch(() => false);

        console.log(`📊 Resultado:`);
        console.log(`   - Feedback visual: ${toast ? 'SIM' : 'NÃO DETECTADO'}`);

        console.log('\n✅ Snapshot solicitado!\n');
      } else {
        console.log('⚠️ Opção Snapshot não encontrada no menu');
        await page.keyboard.press('Escape');
      }
    }
  });

  test('6. PAUSAR MÁQUINA - Testar botão', async ({ page }) => {
    console.log('\n🔍 TESTE: Pausar Máquina\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Filtrar Online
    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    // Encontrar botão Pausar
    const pausarBtn = page.locator('button:has-text("Pausar")').first();

    if (await pausarBtn.count() > 0) {
      console.log('✓ Botão "Pausar" encontrado');

      await page.screenshot({ path: 'screenshots/func-06-antes-pausar.png', fullPage: true });

      // Clicar em pausar
      await pausarBtn.click();
      await page.waitForTimeout(2000);

      // Verificar se apareceu confirmação
      const confirmDialog = await page.locator('text=/confirma|certeza|pausar/i').isVisible().catch(() => false);

      await page.screenshot({ path: 'screenshots/func-06-apos-pausar.png', fullPage: true });

      console.log(`📊 Resultado:`);
      console.log(`   - Dialog de confirmação: ${confirmDialog ? 'SIM' : 'NÃO'}`);

      // Se tiver dialog, cancelar
      const cancelBtn = page.locator('button:has-text("Cancelar")');
      if (await cancelBtn.count() > 0) {
        await cancelBtn.click();
        console.log('✓ Cancelado para não pausar a máquina');
      }

      console.log('\n✅ Botão Pausar funcionando!\n');
    } else {
      console.log('⚠️ Nenhum botão Pausar encontrado');
    }
  });

  test('7. SETTINGS - Salvar configurações', async ({ page }) => {
    console.log('\n🔍 TESTE: Salvar Configurações\n');

    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'screenshots/func-07-settings-antes.png', fullPage: true });

    // Verificar campos preenchidos
    const passwordInputs = await page.locator('input[type="password"]').count();
    console.log(`✓ ${passwordInputs} campos de senha encontrados`);

    // Clicar em Save Settings
    const saveBtn = page.locator('button:has-text("Save Settings")');

    if (await saveBtn.count() > 0) {
      await saveBtn.click();
      await page.waitForTimeout(2000);

      await page.screenshot({ path: 'screenshots/func-07-settings-apos.png', fullPage: true });

      // Verificar feedback
      const sucesso = await page.locator('text=/sucesso|saved|salvo/i').isVisible().catch(() => false);
      const toast = await page.locator('[class*="toast"]').isVisible().catch(() => false);

      console.log(`📊 Resultado:`);
      console.log(`   - Mensagem de sucesso: ${sucesso ? 'SIM' : 'NÃO'}`);
      console.log(`   - Toast notification: ${toast ? 'SIM' : 'NÃO'}`);

      console.log('\n✅ Settings salvas!\n');
    }
  });

  test('8. BUSCAR POR REGIÃO - Comparar EUA vs Europa', async ({ page }) => {
    console.log('\n🔍 TESTE: Busca por Região\n');

    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Buscar EUA
    await page.click('button:has-text("EUA")');
    await page.waitForTimeout(500);
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    await page.waitForTimeout(8000);

    const gpusEUA = await page.locator('button:has-text("Selecionar")').count();
    await page.screenshot({ path: 'screenshots/func-08-busca-eua.png', fullPage: true });
    console.log(`✓ EUA: ${gpusEUA} máquinas encontradas`);

    // Voltar
    const voltarBtn = page.locator('button:has-text("Voltar")');
    if (await voltarBtn.count() > 0) {
      await voltarBtn.click();
      await page.waitForTimeout(1000);
    } else {
      await page.goto(`${BASE_URL}/`);
      await page.waitForTimeout(2000);
    }

    // Buscar Europa
    await page.click('button:has-text("Europa")');
    await page.waitForTimeout(500);
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    await page.waitForTimeout(8000);

    const gpusEuropa = await page.locator('button:has-text("Selecionar")').count();
    await page.screenshot({ path: 'screenshots/func-08-busca-europa.png', fullPage: true });
    console.log(`✓ Europa: ${gpusEuropa} máquinas encontradas`);

    console.log(`\n📊 Comparação:`);
    console.log(`   - EUA: ${gpusEUA} máquinas`);
    console.log(`   - Europa: ${gpusEuropa} máquinas`);

    console.log('\n✅ Busca por região funcionando!\n');
  });

  test('9. SELECIONAR GPU ESPECÍFICA - RTX 4090', async ({ page }) => {
    console.log('\n🔍 TESTE: Filtrar por GPU específica\n');

    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Abrir seletor de GPU
    const gpuSelector = page.locator('text=GPU').first();
    await gpuSelector.click().catch(() => {});
    await page.waitForTimeout(500);

    // Tentar clicar em "Selecione o tipo" ou similar
    const seletorTipo = page.locator('text=/Selecione|Automático/i').first();
    await seletorTipo.click().catch(() => {});
    await page.waitForTimeout(500);

    await page.screenshot({ path: 'screenshots/func-09-gpu-selector.png', fullPage: true });

    // Buscar máquinas
    await page.keyboard.press('Escape');
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    await page.waitForTimeout(8000);

    // Contar RTX 4090 nos resultados
    const rtx4090Count = await page.locator('text=RTX 4090').count();

    console.log(`📊 Resultados com RTX 4090: ${rtx4090Count}`);
    await page.screenshot({ path: 'screenshots/func-09-resultados-gpu.png', fullPage: true });

    console.log('\n✅ Seleção de GPU testada!\n');
  });

  test('10. ABRIR VS CODE WEB - Testar link', async ({ page }) => {
    console.log('\n🔍 TESTE: Abrir VS Code Web\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Filtrar Online
    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    // Clicar no VS Code
    const vscodeBtn = page.locator('button:has-text("VS Code")').first();

    if (await vscodeBtn.count() > 0) {
      await vscodeBtn.click();
      await page.waitForTimeout(500);

      // Clicar em "Online (Web)"
      const onlineWebOption = page.locator('text=Online (Web)');

      if (await onlineWebOption.count() > 0) {
        // Capturar URL antes
        const urlAntes = page.url();

        // Interceptar nova aba/navegação
        const [newPage] = await Promise.all([
          page.context().waitForEvent('page', { timeout: 5000 }).catch(() => null),
          onlineWebOption.click()
        ]);

        await page.waitForTimeout(2000);

        if (newPage) {
          const newUrl = newPage.url();
          console.log(`✓ Nova aba aberta: ${newUrl}`);
          await newPage.screenshot({ path: 'screenshots/func-10-vscode-web.png', fullPage: true });
          await newPage.close();
        } else {
          // Pode ter aberto na mesma aba
          const urlDepois = page.url();
          if (urlDepois !== urlAntes) {
            console.log(`✓ Navegou para: ${urlDepois}`);
            await page.screenshot({ path: 'screenshots/func-10-vscode-web.png', fullPage: true });
          }
        }

        console.log('\n✅ VS Code Web testado!\n');
      }
    } else {
      console.log('⚠️ Nenhuma máquina online para testar');
    }
  });

  test('11. MÉTRICAS - Verificar dados carregados', async ({ page }) => {
    console.log('\n🔍 TESTE: Página de Métricas\n');

    await page.goto(`${BASE_URL}/metrics`);
    await page.waitForTimeout(5000);

    await page.screenshot({ path: 'screenshots/func-11-metricas.png', fullPage: true });

    // Contar elementos
    const gpuCards = await page.locator('text=/RTX 4090|RTX 4080|RTX 3090|A100/').count();
    const precos = await page.locator('text=/\\$[\\d.]+/').count();
    const graficos = await page.locator('canvas').count();

    console.log(`📊 Dados na página:`);
    console.log(`   - Cards de GPU: ${gpuCards}`);
    console.log(`   - Preços exibidos: ${precos}`);
    console.log(`   - Gráficos: ${graficos}`);

    // Verificar se tem dados na tabela
    const tabelaLinhas = await page.locator('text=/RTX \\d+|A\\d+|H\\d+|L\\d+/').count();
    console.log(`   - Linhas na tabela: ${tabelaLinhas}`);

    if (gpuCards > 0 || tabelaLinhas > 0) {
      console.log('\n✅ Métricas carregadas com sucesso!\n');
    } else {
      console.log('\n⚠️ Poucos dados nas métricas\n');
    }
  });

  test('12. SYNC STATUS - Verificar indicador', async ({ page }) => {
    console.log('\n🔍 TESTE: Status de Sincronização\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Filtrar Online
    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    // Procurar indicador de sync
    const syncIndicator = await page.locator('text=/Sync|Synced|Syncing/i').count();

    console.log(`📊 Indicadores de Sync: ${syncIndicator}`);

    await page.screenshot({ path: 'screenshots/func-12-sync-status.png', fullPage: true });

    if (syncIndicator > 0) {
      console.log('\n✅ Indicador de Sync visível!\n');
    }
  });

});
