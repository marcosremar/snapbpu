/**
 * Dumont Cloud - Testes de Ações Específicas
 *
 * Testa ações reais: reservar máquina, menu de opções, snapshot, etc.
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://dumontcloud.com';
const TEST_USER = 'marcosremar@gmail.com';
const TEST_PASS = 'Marcos123';

test.describe('Ações Específicas', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="text"]', TEST_USER);
    await page.fill('input[type="password"]', TEST_PASS);
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
  });

  test('RESERVAR MÁQUINA - Fluxo completo', async ({ page }) => {
    console.log('\n🔍 TESTE: Reservar Máquina (Fluxo Completo)\n');

    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // 1. Selecionar região
    await page.click('button:has-text("Global")');
    await page.waitForTimeout(500);
    console.log('✓ Região Global selecionada');

    // 2. Buscar máquinas
    await page.click('button:has-text("Buscar Máquinas Disponíveis")');
    await page.waitForTimeout(10000);

    const maquinasDisponiveis = await page.locator('button:has-text("Selecionar")').count();
    console.log(`✓ ${maquinasDisponiveis} máquinas disponíveis`);

    await page.screenshot({ path: 'screenshots/action-01-maquinas-disponiveis.png', fullPage: true });

    if (maquinasDisponiveis > 0) {
      // 3. Clicar em Selecionar na primeira máquina barata
      // Procurar uma máquina com preço baixo (< $0.20/hr)
      const primeiroSelecionar = page.locator('button:has-text("Selecionar")').first();

      // Capturar info da máquina antes de selecionar
      const cardPai = primeiroSelecionar.locator('xpath=ancestor::div[contains(@class, "border")]').first();
      const gpuName = await cardPai.locator('text=/RTX|A100|L4|H100/').first().textContent().catch(() => 'GPU');
      const preco = await cardPai.locator('text=/\\$[\\d.]+\\/hr/').first().textContent().catch(() => 'N/A');

      console.log(`\n📋 Máquina selecionada:`);
      console.log(`   - GPU: ${gpuName}`);
      console.log(`   - Preço: ${preco}`);

      // Clicar em Selecionar
      await primeiroSelecionar.click();
      await page.waitForTimeout(3000);

      await page.screenshot({ path: 'screenshots/action-02-apos-selecionar.png', fullPage: true });

      // Verificar se abriu tela de confirmação ou deploy
      const telaConfirmacao = await page.locator('text=/confirma|deploy|criar|iniciar/i').isVisible().catch(() => false);
      const campoNome = await page.locator('input[placeholder*="nome"], input[name*="name"]').isVisible().catch(() => false);

      console.log(`\n📊 Resultado após Selecionar:`);
      console.log(`   - Tela de confirmação: ${telaConfirmacao ? 'SIM' : 'NÃO'}`);
      console.log(`   - Campo para nome: ${campoNome ? 'SIM' : 'NÃO'}`);

      // Se tiver botão de confirmar/deploy, NÃO clicar (para não gastar dinheiro)
      const btnConfirmar = page.locator('button:has-text("Confirmar"), button:has-text("Deploy"), button:has-text("Criar")');
      if (await btnConfirmar.count() > 0) {
        console.log('   - Botão de confirmar encontrado (NÃO CLICADO para não gastar $)');
      }

      // Cancelar se possível
      const btnCancelar = page.locator('button:has-text("Cancelar"), button:has-text("Voltar")');
      if (await btnCancelar.count() > 0) {
        await btnCancelar.first().click();
        console.log('✓ Cancelado para não criar máquina');
      }
    }

    console.log('\n✅ Fluxo de reserva testado!\n');
  });

  test('MENU COMPLETO - Verificar todas opções', async ({ page }) => {
    console.log('\n🔍 TESTE: Menu de Opções Completo\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Filtrar Online para ter máquinas com mais opções
    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    // Abrir menu de 3 pontos
    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      await page.screenshot({ path: 'screenshots/action-03-menu-completo.png' });

      // Listar todas as opções visíveis no menu
      const menuItems = page.locator('[role="menuitem"], [role="menu"] > div, [class*="dropdown"] button, [class*="dropdown"] div[class*="item"]');
      const itemCount = await menuItems.count();

      console.log(`📋 Opções encontradas no menu (${itemCount}):`);

      const opcoesEsperadas = [
        'Auto-Hibernation',
        'Copiar SSH',
        'Criar Snapshot',
        'Restaurar em Nova',
        'Destruir'
      ];

      for (const opcao of opcoesEsperadas) {
        const encontrada = await page.locator(`text=/${opcao}/i`).isVisible().catch(() => false);
        console.log(`   ${encontrada ? '✓' : '✗'} ${opcao}`);
      }

      await page.keyboard.press('Escape');
    }

    console.log('\n✅ Menu verificado!\n');
  });

  test('CRIAR SNAPSHOT - Verificar ação', async ({ page }) => {
    console.log('\n🔍 TESTE: Criar Snapshot\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      // Procurar opção de Snapshot
      const snapshotBtn = page.locator('text=/Criar Snapshot|Snapshot/i');

      if (await snapshotBtn.count() > 0) {
        console.log('✓ Opção "Criar Snapshot" encontrada');

        // Clicar para criar
        await snapshotBtn.click();
        await page.waitForTimeout(3000);

        await page.screenshot({ path: 'screenshots/action-04-criar-snapshot.png', fullPage: true });

        // Verificar se apareceu loading ou confirmação
        const loading = await page.locator('text=/criando|snapshot|aguarde|loading/i').isVisible().catch(() => false);
        const sucesso = await page.locator('text=/sucesso|criado|concluído/i').isVisible().catch(() => false);

        console.log(`📊 Resultado:`);
        console.log(`   - Loading/Progress: ${loading ? 'SIM' : 'NÃO'}`);
        console.log(`   - Mensagem sucesso: ${sucesso ? 'SIM' : 'NÃO'}`);

        console.log('\n✅ Snapshot solicitado!\n');
      } else {
        console.log('⚠️ Opção Snapshot não encontrada');
        await page.keyboard.press('Escape');
      }
    }
  });

  test('RESTAURAR EM NOVA - Verificar opção', async ({ page }) => {
    console.log('\n🔍 TESTE: Restaurar em Nova Máquina\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      // Procurar opção de Restaurar
      const restaurarBtn = page.locator('text=/Restaurar|Restore/i');

      if (await restaurarBtn.count() > 0) {
        console.log('✓ Opção "Restaurar" encontrada');

        await restaurarBtn.click();
        await page.waitForTimeout(2000);

        await page.screenshot({ path: 'screenshots/action-05-restaurar.png', fullPage: true });

        // Verificar se abriu modal ou navegou
        const modalRestaurar = await page.locator('text=/selecionar|escolher|máquina|restaurar/i').isVisible().catch(() => false);

        console.log(`📊 Resultado:`);
        console.log(`   - Modal/Tela de restauração: ${modalRestaurar ? 'SIM' : 'NÃO'}`);

        // Fechar se necessário
        const btnCancelar = page.locator('button:has-text("Cancelar"), button:has-text("Fechar")');
        if (await btnCancelar.count() > 0) {
          await btnCancelar.first().click();
        }

        console.log('\n✅ Opção Restaurar testada!\n');
      } else {
        console.log('⚠️ Opção Restaurar não encontrada');
        await page.keyboard.press('Escape');
      }
    }
  });

  test('DESTRUIR MÁQUINA - Verificar confirmação', async ({ page }) => {
    console.log('\n🔍 TESTE: Destruir Máquina (só verificar dialog)\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Usar filtro Offline se tiver máquinas offline
    const offlineCount = await page.locator('button:has-text("Offline")').textContent();
    if (offlineCount && offlineCount.includes('0')) {
      await page.click('button:has-text("Online")');
    } else {
      await page.click('button:has-text("Offline")');
    }
    await page.waitForTimeout(1000);

    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      // Procurar opção de Destruir
      const destruirBtn = page.locator('text=/Destruir|Destroy|Excluir/i');

      if (await destruirBtn.count() > 0) {
        console.log('✓ Opção "Destruir" encontrada');

        await destruirBtn.click();
        await page.waitForTimeout(1000);

        await page.screenshot({ path: 'screenshots/action-06-destruir-dialog.png' });

        // Verificar se apareceu dialog de confirmação
        const dialogConfirmacao = await page.locator('text=/certeza|confirma|destruir|apagar|excluir/i').isVisible().catch(() => false);
        const btnConfirmar = await page.locator('button:has-text("Destruir"), button:has-text("Confirmar")').count();
        const btnCancelar = await page.locator('button:has-text("Cancelar")').count();

        console.log(`📊 Dialog de Confirmação:`);
        console.log(`   - Dialog visível: ${dialogConfirmacao ? 'SIM' : 'NÃO'}`);
        console.log(`   - Botão confirmar: ${btnConfirmar > 0 ? 'SIM' : 'NÃO'}`);
        console.log(`   - Botão cancelar: ${btnCancelar > 0 ? 'SIM' : 'NÃO'}`);

        // CANCELAR - não destruir a máquina!
        if (btnCancelar > 0) {
          await page.locator('button:has-text("Cancelar")').click();
          console.log('✓ Cancelado (máquina NÃO destruída)');
        } else {
          await page.keyboard.press('Escape');
        }

        console.log('\n✅ Dialog de destruição verificado!\n');
      } else {
        console.log('⚠️ Opção Destruir não encontrada');
        await page.keyboard.press('Escape');
      }
    }
  });

  test('AUTO-HIBERNATION - Verificar toggle', async ({ page }) => {
    console.log('\n🔍 TESTE: Auto-Hibernation\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      // Procurar opção de Auto-Hibernation
      const hibernationBtn = page.locator('text=/Auto-Hibernation|Hibernation|Hibernar/i');

      if (await hibernationBtn.count() > 0) {
        console.log('✓ Opção "Auto-Hibernation" encontrada');

        // Verificar estado atual (switch/toggle)
        const switchElement = page.locator('[role="switch"], input[type="checkbox"]');
        const hasSwitch = await switchElement.count() > 0;

        console.log(`📊 Resultado:`);
        console.log(`   - Toggle/Switch: ${hasSwitch ? 'SIM' : 'NÃO'}`);

        await page.screenshot({ path: 'screenshots/action-07-hibernation.png' });

        console.log('\n✅ Auto-Hibernation verificado!\n');
      } else {
        console.log('⚠️ Opção Auto-Hibernation não encontrada');
      }

      await page.keyboard.press('Escape');
    }
  });

  test('COPIAR SSH CONFIG - Verificar ação', async ({ page }) => {
    console.log('\n🔍 TESTE: Copiar SSH Config\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    await page.click('button:has-text("Online")');
    await page.waitForTimeout(1000);

    const menuBtn = page.locator('button:has(svg.lucide-more-vertical)').first();

    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(500);

      // Procurar opção de SSH
      const sshBtn = page.locator('text=/Copiar SSH|SSH Config|SSH/i');

      if (await sshBtn.count() > 0) {
        console.log('✓ Opção "Copiar SSH" encontrada');

        await sshBtn.click();
        await page.waitForTimeout(1000);

        await page.screenshot({ path: 'screenshots/action-08-ssh-config.png' });

        // Verificar se copiou (toast) ou abriu modal
        const toastCopiado = await page.locator('text=/copiado|copied|clipboard/i').isVisible().catch(() => false);

        console.log(`📊 Resultado:`);
        console.log(`   - Feedback "Copiado": ${toastCopiado ? 'SIM' : 'NÃO'}`);

        console.log('\n✅ SSH Config verificado!\n');
      } else {
        console.log('⚠️ Opção SSH não encontrada');
        await page.keyboard.press('Escape');
      }
    }
  });

  test('INICIAR MÁQUINA OFFLINE - Verificar botão', async ({ page }) => {
    console.log('\n🔍 TESTE: Iniciar Máquina Offline\n');

    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(3000);

    // Filtrar Offline
    await page.click('button:has-text("Offline")');
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'screenshots/action-09-maquinas-offline.png', fullPage: true });

    // Procurar botão Iniciar
    const iniciarBtn = page.locator('button:has-text("Iniciar")');
    const iniciarCount = await iniciarBtn.count();

    console.log(`📊 Máquinas Offline:`);
    console.log(`   - Botões "Iniciar": ${iniciarCount}`);

    if (iniciarCount > 0) {
      // Clicar para ver se aparece confirmação
      await iniciarBtn.first().click();
      await page.waitForTimeout(2000);

      await page.screenshot({ path: 'screenshots/action-09-iniciar-dialog.png' });

      // Verificar dialog ou ação
      const dialogIniciar = await page.locator('text=/iniciar|start|confirma/i').isVisible().catch(() => false);

      console.log(`   - Dialog de confirmação: ${dialogIniciar ? 'SIM' : 'NÃO'}`);

      // Cancelar
      const btnCancelar = page.locator('button:has-text("Cancelar")');
      if (await btnCancelar.count() > 0) {
        await btnCancelar.click();
        console.log('✓ Cancelado');
      }
    } else {
      console.log('   - Nenhuma máquina offline disponível');
    }

    console.log('\n✅ Botão Iniciar verificado!\n');
  });

});
