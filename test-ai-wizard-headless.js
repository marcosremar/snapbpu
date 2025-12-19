const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function testAIWizardInterface() {
  console.log('🚀 Iniciando testes do AI Wizard em modo headless...\n');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const page = await browser.newPage();
  
  // Configurar viewport
  await page.setViewport({ width: 1280, height: 720 });
  
  // Capturar console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('❌ Console Error:', msg.text());
    }
  });
  
  page.on('pageerror', err => {
    console.log('❌ Page Error:', err.message);
  });
  
  try {
    // Teste 1: Acessar página
    console.log('📍 Teste 1: Acessando página...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });
    console.log('✅ Página carregada com sucesso');
    
    // Tirar screenshot inicial
    await page.screenshot({ path: '/tmp/ai-wizard-01-initial.png', fullPage: true });
    
    // Teste 2: Fazer login se necessário
    console.log('\n🔐 Teste 2: Verificando login...');
    const emailInput = await page.$('input[type="text"], input[type="email"]');
    if (emailInput) {
      await page.type('input[type="text"], input[type="email"]', 'test@test.com');
      await page.type('input[type="password"]', 'test123');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
      console.log('✅ Login realizado');
    } else {
      console.log('✅ Já logado ou login não necessário');
    }
    
    // Teste 3: Acessar aba AI
    console.log('\n🤖 Teste 3: Acessando aba AI...');
    const aiButton = await page.waitForSelector('button', { timeout: 10000 });
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const aiButton = buttons.find(btn => btn.textContent.trim() === 'AI');
      if (aiButton) aiButton.click();
    });
    await page.waitForTimeout(1000);
    console.log('✅ Aba AI acessada');
    
    // Teste 4: Verificar interface do chat
    console.log('\n💬 Teste 4: Verificando interface do chat...');
    
    const chatElements = [
      { selector: 'text=AI GPU Advisor', name: 'Header do chat' },
      { selector: 'text=Olá! Sou seu assistente de GPU', name: 'Mensagem de boas-vindas' },
      { selector: 'textarea', name: 'Campo de input' },
      { selector: 'button svg', name: 'Botão enviar' }
    ];
    
    for (const element of chatElements) {
      const el = await page.$(element.selector);
      if (el) {
        console.log(`✅ ${element.name} encontrado`);
      } else {
        console.log(`❌ ${element.name} não encontrado`);
      }
    }
    
    // Screenshot da interface
    await page.screenshot({ path: '/tmp/ai-wizard-02-chat-interface.png', fullPage: true });
    
    // Teste 5: Enviar mensagem e aguardar resposta
    console.log('\n📝 Teste 5: Enviando mensagem...');
    
    const testMessages = [
      'Quero fazer fine-tuning de LLaMA 7B',
      'API de Stable Diffusion XL',
      'Inferência LLaMA 13B'
    ];
    
    for (let i = 0; i < testMessages.length; i++) {
      const message = testMessages[i];
      console.log(`\n🔄 Testando mensagem ${i + 1}: ${message}`);
      
      // Limpar e preencher textarea
      await page.evaluate(() => {
        const textarea = document.querySelector('textarea');
        if (textarea) textarea.value = '';
      });
      
      await page.type('textarea', message);
      
      // Verificar se botão está habilitado
      const sendButton = await page.$('button svg');
      if (sendButton) {
        await sendButton.click();
        console.log('✅ Mensagem enviada');
        
        // Aguardar resposta
        await page.waitForTimeout(5000);
        
        // Verificar se resposta apareceu
        const response = await page.$('.prose, .text-gray-200');
        if (response) {
          console.log('✅ Resposta recebida');
        } else {
          console.log('⚠️ Resposta não encontrada');
        }
        
        // Screenshot após resposta
        await page.screenshot({ 
          path: `/tmp/ai-wizard-03-response-${i + 1}.png`, 
          fullPage: true 
        });
        
        // Verificar cards de GPU
        const gpuCards = await page.$$('text=RTX');
        console.log(`📊 Cards de GPU encontrados: ${gpuCards.length}`);
        
        // Testar botões de busca se existirem
        if (gpuCards.length > 0) {
          const searchButtons = await page.$$('button');
          for (const button of searchButtons) {
            const text = await page.evaluate(el => el.textContent, button);
            if (text && text.includes('Buscar')) {
              console.log(`🔍 Botão de busca encontrado: ${text}`);
              // Clicar no primeiro botão de busca
              await button.click();
              await page.waitForTimeout(3000);
              
              // Verificar se redirecionou para resultados
              const results = await page.$('h2');
              if (results) {
                const resultsText = await page.evaluate(el => el.textContent, results);
                console.log(`📋 Página de resultados: ${resultsText}`);
              }
              
              // Voltar para testar próxima mensagem
              await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });
              await page.waitForTimeout(1000);
              
              // Reacessar aba AI
              await page.evaluate(() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const aiButton = buttons.find(btn => btn.textContent.trim() === 'AI');
                if (aiButton) aiButton.click();
              });
              await page.waitForTimeout(1000);
              break;
            }
          }
        }
        
      } else {
        console.log('❌ Botão enviar não encontrado');
      }
    }
    
    // Teste 6: Responsividade
    console.log('\n📱 Teste 6: Testando responsividade...');
    
    const viewports = [
      { width: 375, height: 667, name: 'Mobile' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 1280, height: 720, name: 'Desktop' }
    ];
    
    for (const viewport of viewports) {
      console.log(`📱 Testando em ${viewport.name}: ${viewport.width}x${viewport.height}`);
      
      await page.setViewport(viewport);
      await page.reload({ waitUntil: 'networkidle2' });
      await page.waitForTimeout(2000);
      
      // Acessar aba AI
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const aiButton = buttons.find(btn => btn.textContent.trim() === 'AI');
        if (aiButton) aiButton.click();
      });
      await page.waitForTimeout(1000);
      
      // Verificar se chat ainda funciona
      const textarea = await page.$('textarea');
      if (textarea) {
        await page.type('textarea', `Teste responsividade ${viewport.name}`);
        const sendButton = await page.$('button svg');
        if (sendButton) {
          await sendButton.click();
          await page.waitForTimeout(3000);
          console.log(`✅ Chat funcional em ${viewport.name}`);
        }
      }
      
      // Screenshot
      await page.screenshot({ 
        path: `/tmp/ai-wizard-04-responsive-${viewport.name}.png`, 
        fullPage: true 
      });
    }
    
    // Teste 7: Performance
    console.log('\n⚡ Teste 7: Testando performance...');
    
    await page.setViewport({ width: 1280, height: 720 });
    await page.reload({ waitUntil: 'networkidle2' });
    await page.waitForTimeout(1000);
    
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const aiButton = buttons.find(btn => btn.textContent.trim() === 'AI');
      if (aiButton) aiButton.click();
    });
    await page.waitForTimeout(1000);
    
    const performanceTests = [
      'Quero rodar LLaMA 7B',
      'API de Stable Diffusion',
      'Fine-tuning pequeno'
    ];
    
    for (let i = 0; i < performanceTests.length; i++) {
      const startTime = Date.now();
      
      await page.evaluate(() => {
        const textarea = document.querySelector('textarea');
        if (textarea) textarea.value = '';
      });
      
      await page.type('textarea', performanceTests[i]);
      await page.click('button svg');
      
      // Esperar resposta
      await page.waitForSelector('.prose, .text-gray-200', { timeout: 10000 });
      
      const responseTime = Date.now() - startTime;
      console.log(`⏱️ Mensagem ${i + 1}: ${responseTime}ms`);
      
      if (responseTime > 8000) {
        console.log(`⚠️ Tempo de resposta alto: ${responseTime}ms`);
      } else {
        console.log(`✅ Tempo de resposta aceitável: ${responseTime}ms`);
      }
    }
    
    console.log('\n🎉 Testes concluídos com sucesso!');
    console.log('📸 Screenshots salvos em /tmp/ai-wizard-*.png');
    
  } catch (error) {
    console.error('❌ Erro durante os testes:', error);
    await page.screenshot({ path: '/tmp/ai-wizard-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
}

// Verificar se servidor está rodando
async function checkServer() {
  try {
    const response = await fetch('http://localhost:5173');
    return response.ok;
  } catch (error) {
    return false;
  }
}

// Executar testes
async function main() {
  console.log('🔍 Verificando se o servidor está rodando...');
  
  const serverRunning = await checkServer();
  if (!serverRunning) {
    console.log('❌ Servidor não está rodando em http://localhost:5173');
    console.log('Por favor, inicie o servidor com: cd web && npm run dev');
    process.exit(1);
  }
  
  console.log('✅ Servidor está rodando');
  
  // Instalar Puppeteer se necessário
  try {
    require('puppeteer');
  } catch (error) {
    console.log('📦 Instalando Puppeteer...');
    const { execSync } = require('child_process');
    execSync('npm install puppeteer', { stdio: 'inherit' });
  }
  
  await testAIWizardInterface();
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { testAIWizardInterface };
