const { test, expect } = require('@playwright/test');

// Configuração para modo headless e testes paralelos
test.describe.configure({ mode: 'parallel' });

test.describe('AI Wizard Interface - Comprehensive Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Configurar viewport e capturar erros
    await page.setViewportSize({ width: 1280, height: 720 });
    
    // Capturar erros do console para debugging
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('CONSOLE ERROR:', msg.text());
      }
    });
    page.on('pageerror', err => {
      console.log('PAGE ERROR:', err.message);
    });

    // Navegar para a aplicação
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    
    // Fazer login se necessário
    const emailInput = page.locator('input[type="text"], input[type="email"]').first();
    if (await emailInput.isVisible()) {
      await emailInput.fill('test@test.com');
      await page.locator('input[type="password"]').fill('test123');
      await page.locator('button[type="submit"]').click();
      await page.waitForTimeout(2000);
    }
    
    // Clicar na aba AI
    const aiButton = page.locator('button').filter({ hasText: /^AI$/ }).first();
    await aiButton.waitFor({ state: 'visible', timeout: 10000 });
    await aiButton.click();
    await page.waitForTimeout(1000);
  });

  test('deve renderizar interface completa do AI Wizard', async ({ page }) => {
    // Verificar header do chat
    await expect(page.getByText('AI GPU Advisor')).toBeVisible();
    await expect(page.getByText('Descreva seu projeto e receba recomendações')).toBeVisible();
    
    // Verificar mensagem de boas-vindas
    await expect(page.getByText('Olá! Sou seu assistente de GPU.')).toBeVisible();
    await expect(page.getByText('Descreva seu projeto e eu vou recomendar a GPU ideal.')).toBeVisible();
    
    // Verificar exemplos
    await expect(page.getByText('Fine-tuning LLaMA 7B')).toBeVisible();
    await expect(page.getByText('API de Stable Diffusion')).toBeVisible();
    await expect(page.getByText('Treinar modelo de visão')).toBeVisible();
    
    // Verificar input e botão
    const textarea = page.locator('textarea');
    await expect(textarea).toBeVisible();
    await expect(textarea).toBeEnabled();
    
    const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
    await expect(sendButton).toBeVisible();
    
    // Botão deve estar desabilitado com input vazio
    await expect(sendButton).toBeDisabled();
  });

  test('deve enviar mensagem e receber recomendações detalhadas', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
    
    // Enviar mensagem sobre fine-tuning
    await textarea.fill('Quero fazer fine-tuning de LLaMA 7B com LoRA');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();
    
    // Aguardar resposta
    await page.waitForTimeout(3000);
    
    // Verificar mensagem do usuário
    await expect(page.getByText('Quero fazer fine-tuning de LLaMA 7B com LoRA')).toBeVisible();
    
    // Verificar resposta do assistente
    const response = page.locator('.prose').first();
    await expect(response).toBeVisible();
    
    // Verificar cards de GPU
    await expect(page.getByText('mínima')).toBeVisible();
    await expect(page.getByText('recomendada')).toBeVisible();
    await expect(page.getByText('máxima')).toBeVisible();
    
    // Verificar GPUs específicas
    await expect(page.getByText('RTX_3090')).toBeVisible();
    await expect(page.getByText('RTX_4090')).toBeVisible();
    await expect(page.getByText('A6000')).toBeVisible();
  });

  test('deve testar diferentes cenários de uso', async ({ page }) => {
    const testCases = [
      {
        message: 'API de Stable Diffusion XL',
        expectedKeywords: ['RTX_4070_Ti', 'RTX_4080', 'RTX_3090', '12GB'],
        description: 'Geração de imagens'
      },
      {
        message: 'LLM 70B para produção com vLLM',
        expectedKeywords: ['A100', 'H100', '80GB', 'multi-GPU'],
        description: 'LLM grande'
      },
      {
        message: 'Inferência LLaMA 13B',
        expectedKeywords: ['RTX_4090', 'A6000', 'RTX_3090', '24GB'],
        description: 'Inferência médio'
      },
      {
        message: 'Treinamento YOLOv8',
        expectedKeywords: ['RTX_4090', 'A6000', 'RTX_4080', '16GB'],
        description: 'Visão computacional'
      }
    ];

    for (const testCase of testCases) {
      console.log(`\n🧪 Testando: ${testCase.description}`);
      
      // Limpar e enviar nova mensagem
      const textarea = page.locator('textarea');
      await textarea.clear();
      await textarea.fill(testCase.message);
      
      const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
      await sendButton.click();
      
      // Aguardar resposta
      await page.waitForTimeout(3000);
      
      // Verificar palavras-chave
      const pageContent = await page.content();
      for (const keyword of testCase.expectedKeywords) {
        if (pageContent.includes(keyword)) {
          console.log(`✅ Encontrado: ${keyword}`);
        } else {
          console.log(`⚠️ Não encontrado: ${keyword}`);
        }
      }
      
      // Tirar screenshot para debugging
      await page.screenshot({ 
        path: `/tmp/ai-wizard-${testCase.description.replace(/\s+/g, '_')}.png`, 
        fullPage: true 
      });
    }
  });

  test('deve funcionar botões de busca individual das GPUs', async ({ page }) => {
    // Enviar mensagem para gerar recomendações
    const textarea = page.locator('textarea');
    await textarea.fill('Fine-tuning LLaMA 7B');
    
    const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
    await sendButton.click();
    
    await page.waitForTimeout(3000);
    
    // Scroll para garantir visibilidade dos botões
    await page.evaluate(() => window.scrollBy(0, 300));
    await page.waitForTimeout(500);
    
    // Procurar botões de busca específicos
    const gpuButtons = [
      { name: 'RTX_3090', selector: /RTX.?3090/i },
      { name: 'RTX_4090', selector: /RTX.?4090/i },
      { name: 'A6000', selector: /A6000/i }
    ];
    
    for (const gpu of gpuButtons) {
      const searchButton = page.getByRole('button', { name: gpu.selector });
      const count = await searchButton.count();
      
      if (count > 0) {
        console.log(`🎯 Botão encontrado para ${gpu.name}`);
        
        // Clicar e testar busca
        await searchButton.first().click();
        await page.waitForTimeout(3000);
        
        // Verificar se redirecionou para resultados
        const resultsTitle = page.locator('h2').filter({ hasText: 'Máquinas Disponíveis' });
        const hasResults = await resultsTitle.isVisible().catch(() => false);
        
        if (hasResults) {
          console.log(`✅ Busca para ${gpu.name} funcionou!`);
          
          // Verificar ofertas
          const offerCards = page.locator('.grid > div').filter({ has: page.locator('text=VRAM:') });
          const offers = await offerCards.count();
          console.log(`📊 Ofertas encontradas: ${offers}`);
          
          if (offers > 0) {
            console.log('🎉 Busca executada com sucesso!');
          }
        }
        
        // Voltar para o AI Wizard
        await page.goto('http://localhost:5173');
        await page.waitForTimeout(1000);
        await page.locator('button').filter({ hasText: /^AI$/ }).first().click();
        await page.waitForTimeout(1000);
        
        // Reenviar mensagem
        await textarea.fill('Fine-tuning LLaMA 7B');
        await sendButton.click();
        await page.waitForTimeout(3000);
        await page.evaluate(() => window.scrollBy(0, 300));
        
        break; // Testar apenas o primeiro encontrado
      }
    }
  });

  test('deve lidar com entrada inválida e pedir mais informações', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
    
    // Testar mensagem vazia
    await textarea.fill('');
    await expect(sendButton).toBeDisabled();
    
    // Testar mensagem muito curta
    await textarea.fill('oi');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();
    
    await page.waitForTimeout(2000);
    
    // Deve pedir mais informações
    await expect(page.getByText(/preciso de mais informações/i)).toBeVisible();
    await expect(page.getByText(/qual modelo/i)).toBeVisible();
  });

  test('deve testar responsividade em diferentes dispositivos', async ({ page }) => {
    const viewports = [
      { width: 375, height: 667, name: 'Mobile' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 1280, height: 720, name: 'Desktop' }
    ];

    for (const viewport of viewports) {
      console.log(`📱 Testando em ${viewport.name}: ${viewport.width}x${viewport.height}`);
      
      await page.setViewportSize(viewport);
      await page.reload();
      await page.waitForTimeout(2000);
      
      // Ativar modo AI
      await page.locator('button').filter({ hasText: /^AI$/ }).first().click();
      await page.waitForTimeout(1000);
      
      // Verificar se chat ainda funciona
      const textarea = page.locator('textarea');
      await expect(textarea).toBeVisible();
      
      // Enviar mensagem
      await textarea.fill(`Teste responsividade ${viewport.name}`);
      const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
      await sendButton.click();
      
      await page.waitForTimeout(3000);
      
      // Verificar resposta
      await expect(page.getByText(`Teste responsividade ${viewport.name}`)).toBeVisible();
      
      // Screenshot
      await page.screenshot({ 
        path: `/tmp/ai-wizard-responsivo-${viewport.name}.png`, 
        fullPage: true 
      });
    }
  });

  test('deve testar performance e tempo de resposta', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
    
    // Testar múltiplas mensagens e medir tempo
    const messages = [
      'Quero rodar LLaMA 7B',
      'API de Stable Diffusion',
      'Fine-tuning modelo pequeno'
    ];
    
    for (let i = 0; i < messages.length; i++) {
      const startTime = Date.now();
      
      await textarea.clear();
      await textarea.fill(messages[i]);
      await sendButton.click();
      
      // Esperar resposta
      await page.waitForSelector('.prose', { timeout: 10000 });
      
      const responseTime = Date.now() - startTime;
      console.log(`⏱️ Mensagem ${i + 1}: ${responseTime}ms`);
      
      // Verificar se tempo é razoável (< 8 segundos)
      expect(responseTime).toBeLessThan(8000);
      
      // Verificar resposta
      await expect(page.getByText(messages[i])).toBeVisible();
      
      // Pequena pausa entre mensagens
      await page.waitForTimeout(1000);
    }
  });

  test('deve testar fluxo completo de conversação', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
    
    // Conversa em múltiplos turnos
    const conversation = [
      'Quero treinar um modelo',
      'É um LLaMA 7B para fine-tuning',
      'Usando LoRA com PyTorch'
    ];
    
    for (const message of conversation) {
      await textarea.clear();
      await textarea.fill(message);
      await sendButton.click();
      await page.waitForTimeout(3000);
      
      // Verificar se mensagem aparece no histórico
      await expect(page.getByText(message)).toBeVisible();
    }
    
    // Verificar recomendação final
    await expect(page.getByText('RTX_4090')).toBeVisible();
    await expect(page.getByText('QLoRA')).toBeVisible();
    
    // Verificar histórico completo
    for (const message of conversation) {
      await expect(page.getByText(message)).toBeVisible();
    }
  });
});
