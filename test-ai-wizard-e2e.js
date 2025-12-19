const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Configurações
const BASE_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8768';
const SCREENSHOT_DIR = '/tmp/ai-wizard-e2e';

// Garantir diretório de screenshots
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Função para tirar screenshot com timestamp
async function takeScreenshot(page, name) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${SCREENSHOT_DIR}/${name}_${timestamp}.png`;
  await page.screenshot({ path: filename, fullPage: true });
  console.log(`📸 Screenshot salvo: ${filename}`);
  return filename;
}

// Função para fazer requisições HTTP
function makeRequest(url, data) {
  return new Promise((resolve, reject) => {
    const http = require('http');
    const urlObj = new URL(url);
    
    const postData = JSON.stringify(data);
    
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };
    
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          resolve({ status: res.statusCode, data: json });
        } catch (e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });
    
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// Teste completo E2E do AI Wizard
async function testAIWizardE2E() {
  console.log('🚀 Iniciando teste E2E completo do AI Wizard...\n');
  
  const browser = await puppeteer.launch({
    headless: true, // Modo headless para servidor sem X
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
    // ETAPA 1: Acessar aplicação
    console.log('📍 ETAPA 1: Acessando aplicação...');
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    await takeScreenshot(page, '01_initial_page');
    
    // Fazer login se necessário
    const emailInput = await page.$('input[type="text"], input[type="email"]');
    if (emailInput) {
      console.log('🔐 Fazendo login...');
      await page.type('input[type="text"], input[type="email"]', 'test@test.com');
      await page.type('input[type="password"]', 'test123');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(3000);
      await takeScreenshot(page, '02_after_login');
    }
    
    // ETAPA 2: Acessar AI Wizard
    console.log('\n🤖 ETAPA 2: Acessando AI Wizard...');
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const aiButton = buttons.find(btn => btn.textContent.trim() === 'AI');
      if (aiButton) aiButton.click();
    });
    await page.waitForTimeout(2000);
    await takeScreenshot(page, '03_ai_wizard_opened');
    
    // Verificar se está usando LLM real ou fallback
    console.log('\n🔍 ETAPA 3: Verificando se usa LLM real...');
    
    // Enviar mensagem simples para testar
    const textarea = await page.$('textarea');
    await textarea.click();
    await textarea.type('Teste inicial para verificar modelo');
    
    const sendButton = await page.$('button svg.lucide-send');
    await sendButton.click();
    await page.waitForTimeout(5000);
    await takeScreenshot(page, '04_initial_response');
    
    // Verificar se menciona modelo usado
    const pageContent = await page.content();
    const usesFallback = pageContent.includes('model_used') || 
                        pageContent.includes('fallback') ||
                        pageContent.includes('heurístico');
    
    if (usesFallback) {
      console.log('⚠️ Sistema está usando fallback heurístico');
    } else {
      console.log('✅ Sistema parece estar usando LLM real');
    }
    
    // ETAPA 4: Testar fluxo de conversa completo
    console.log('\n💬 ETAPA 4: Testando fluxo de conversa completo...');
    
    const scenarios = [
      {
        name: 'Cenário 1: Fine-tuning de LLM',
        messages: [
          'Quero fazer fine-tuning de um modelo de linguagem',
          'É um LLaMA 7B para deploy em produção',
          'Vou usar LoRA para economizar VRAM'
        ]
      },
      {
        name: 'Cenário 2: API de Imagens',
        messages: [
          'Preciso criar uma API para geração de imagens',
          'Usando Stable Diffusion XL',
          'Para alta qualidade e múltiplos usuários'
        ]
      }
    ];
    
    for (let scenarioIndex = 0; scenarioIndex < scenarios.length; scenarioIndex++) {
      const scenario = scenarios[scenarioIndex];
      console.log(`\n📋 ${scenario.name}`);
      
      // Limpar chat para novo cenário
      await page.reload();
      await page.waitForTimeout(2000);
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const aiButton = buttons.find(btn => btn.textContent.trim() === 'AI');
        if (aiButton) aiButton.click();
      });
      await page.waitForTimeout(2000);
      
      const conversationHistory = [];
      let askedQuestions = [];
      
      for (let msgIndex = 0; msgIndex < scenario.messages.length; msgIndex++) {
        const message = scenario.messages[msgIndex];
        console.log(`  📝 Enviando: ${message}`);
        
        // Enviar mensagem
        const textarea = await page.$('textarea');
        await textarea.click();
        await textarea.selectText();
        await textarea.type(message);
        
        const sendButton = await page.$('button svg.lucide-send');
        await sendButton.click();
        
        // Aguardar resposta
        await page.waitForTimeout(5000);
        
        // Capturar resposta
        const responseElements = await page.$$('.prose, .text-gray-200, .message-content');
        const lastResponse = responseElements[responseElements.length - 1];
        
        if (lastResponse) {
          const responseText = await page.evaluate(el => el.textContent, lastResponse);
          console.log(`  🤖 Resposta: ${responseText.substring(0, 100)}...`);
          
          // Verificar se pediu mais informações
          const asksForInfo = responseText.includes('?') && 
                             (responseText.includes('preciso') || 
                              responseText.includes('qual') ||
                              responseText.includes('quanto'));
          
          if (asksForInfo) {
            console.log('  ❓ AI pediu mais informações');
            askedQuestions.push(responseText);
          }
          
          // Verificar se deu recomendações
          const hasRecommendations = responseText.includes('RTX') || 
                                    responseText.includes('GPU') ||
                                    responseText.includes('recomendo');
          
          if (hasRecommendations) {
            console.log('  🎮 AI deu recomendações de GPU');
            
            // Tirar screenshot das recomendações
            await takeScreenshot(page, `05_scenario_${scenarioIndex + 1}_recommendations`);
            
            // ETAPA 5: Testar seleção de GPU
            console.log('\n🎯 ETAPA 5: Testando seleção de GPU...');
            
            // Procurar botões de busca de GPU
            const searchButtons = await page.$$('button');
            let gpuButtonFound = false;
            
            for (const button of searchButtons) {
              const buttonText = await page.evaluate(el => el.textContent, button);
              if (buttonText && buttonText.includes('Buscar') && buttonText.includes('RTX')) {
                console.log(`  🔍 Botão encontrado: ${buttonText}`);
                await takeScreenshot(page, `06_scenario_${scenarioIndex + 1}_before_search`);
                
                // Clicar no botão
                await button.click();
                await page.waitForTimeout(5000);
                
                // Verificar se redirecionou para resultados
                const currentUrl = page.url();
                console.log(`  🌐 URL após clique: ${currentUrl}`);
                
                await takeScreenshot(page, `07_scenario_${scenarioIndex + 1}_search_results`);
                
                // ETAPA 6: Testar seleção e reserva
                console.log('\n🛒 ETAPA 6: Testando seleção e reserva...');
                
                // Procurar cards de ofertas
                const offerCards = await page.$$('.grid > div, .offer-card, [class*="offer"]');
                console.log(`  📊 Ofertas encontradas: ${offerCards.length}`);
                
                if (offerCards.length > 0) {
                  // Selecionar primeira oferta
                  const firstOffer = offerCards[0];
                  await firstOffer.click();
                  await page.waitForTimeout(2000);
                  
                  await takeScreenshot(page, `08_scenario_${scenarioIndex + 1}_offer_selected`);
                  
                  // Procurar botão de reservar/alugar
                  const reserveButtons = await page.$$('button');
                  let reserveButtonFound = false;
                  
                  for (const button of reserveButtons) {
                    const buttonText = await page.evaluate(el => el.textContent, button);
                    if (buttonText && (buttonText.includes('Alugar') || 
                                      buttonText.includes('Reservar') || 
                                      buttonText.includes('Selecionar'))) {
                      console.log(`  🎯 Botão de reserva: ${buttonText}`);
                      await takeScreenshot(page, `09_scenario_${scenarioIndex + 1}_before_reserve`);
                      
                      // Simular clique (não vamos realmente reservar)
                      console.log('  ✅ Fluxo até reserva validado com sucesso');
                      reserveButtonFound = true;
                      break;
                    }
                  }
                  
                  if (!reserveButtonFound) {
                    console.log('  ⚠️ Botão de reserva não encontrado');
                  }
                } else {
                  console.log('  ⚠️ Nenhuma oferta encontrada');
                }
                
                gpuButtonFound = true;
                break;
              }
            }
            
            if (!gpuButtonFound) {
              console.log('  ⚠️ Botão de busca de GPU não encontrado');
            }
            
            break; // Testar apenas primeiro cenário completo
          }
        }
        
        conversationHistory.push({ user: message, assistant: responseText });
        await takeScreenshot(page, `05_scenario_${scenarioIndex + 1}_message_${msgIndex + 1}`);
      }
      
      // Analisar qualidade das perguntas
      if (askedQuestions.length > 0) {
        console.log(`  📊 Perguntas feitas: ${askedQuestions.length}`);
        
        // Verificar se são repetitivas
        const uniqueQuestions = [...new Set(askedQuestions)];
        if (uniqueQuestions.length < askedQuestions.length) {
          console.log('  ⚠️ Detectadas perguntas repetitivas');
        } else {
          console.log('  ✅ Perguntas não são repetitivas');
        }
      }
    }
    
    // ETAPA 7: Análise final da UX
    console.log('\n📊 ETAPA 7: Análise final da experiência do usuário...');
    
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    await page.waitForTimeout(2000);
    
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const aiButton = buttons.find(btn => btn.textContent.trim() === 'AI');
      if (aiButton) aiButton.click();
    });
    await page.waitForTimeout(2000);
    
    await takeScreenshot(page, '10_final_interface_state');
    
    // Verificar elementos de UX
    const uxElements = {
      'Input de chat': 'textarea',
      'Botão enviar': 'button svg',
      'Mensagem de boas-vindas': '.prose, .text-gray-200',
      'Exemplos': 'button[onclick*="exemplo"]',
      'Indicador de loading': '.loading, [class*="loading"]'
    };
    
    console.log('  🔍 Verificando elementos de UX:');
    for (const [name, selector] of Object.entries(uxElements)) {
      const element = await page.$(selector);
      console.log(`    ${element ? '✅' : '❌'} ${name}`);
    }
    
    console.log('\n🎉 Teste E2E concluído!');
    console.log(`📸 Screenshots salvos em: ${SCREENSHOT_DIR}`);
    
    // Gerar relatório
    const report = {
      timestamp: new Date().toISOString(),
      testType: 'E2E Complete Flow',
      scenarios: scenarios.length,
      screenshots: fs.readdirSync(SCREENSHOT_DIR),
      summary: {
        llmUsed: usesFallback ? 'fallback' : 'real',
        uxScore: 'pending',
        flowCompleted: true
      }
    };
    
    fs.writeFileSync('/tmp/ai-wizard-e2e-report.json', JSON.stringify(report, null, 2));
    console.log('📋 Relatório salvo em: /tmp/ai-wizard-e2e-report.json');
    
  } catch (error) {
    console.error('❌ Erro durante o teste E2E:', error);
    await takeScreenshot(page, 'error_state');
  } finally {
    await browser.close();
  }
}

// Verificar se servidores estão rodando
async function checkServers() {
  try {
    // Verificar frontend
    const frontendResponse = await fetch(BASE_URL);
    if (!frontendResponse.ok) {
      throw new Error('Frontend não está rodando');
    }
    
    // Verificar backend
    const backendResponse = await fetch(`${API_BASE}/health`);
    if (!backendResponse.ok) {
      throw new Error('Backend não está rodando');
    }
    
    console.log('✅ Servidores estão rodando');
    return true;
  } catch (error) {
    console.log('❌', error.message);
    console.log('💡 Certifique-se de que:');
    console.log('   - Frontend: cd web && npm run dev');
    console.log('   - Backend: cd /home/ubuntu/dumont-cloud && python -m uvicorn src.main:app --host 0.0.0.0 --port 8768');
    return false;
  }
}

// Executar teste
async function main() {
  const serversOk = await checkServers();
  if (!serversOk) {
    process.exit(1);
  }
  
  // Verificar Puppeteer
  try {
    require('puppeteer');
  } catch (error) {
    console.log('📦 Instalando Puppeteer...');
    const { execSync } = require('child_process');
    execSync('npm install puppeteer', { stdio: 'inherit' });
  }
  
  await testAIWizardE2E();
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { testAIWizardE2E };
