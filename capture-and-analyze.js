const puppeteer = require('puppeteer');
const fs = require('fs');
const http = require('http');

// Diretório para screenshots
const SCREENSHOT_DIR = '/tmp/ai-wizard-analysis';
const ANALYSIS_REPORT = '/tmp/ai-wizard-analysis-report.json';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Função para fazer requisições HTTP
function makeRequest(options, data) {
  return new Promise((resolve, reject) => {
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
    
    if (data) {
      req.write(JSON.stringify(data));
    }
    
    req.end();
  });
}

// Função para tirar screenshot
async function takeScreenshot(page, name, description) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${SCREENSHOT_DIR}/${name}_${timestamp}.png`;
  await page.screenshot({ path: filename, fullPage: true });
  console.log(`📸 Screenshot: ${filename}`);
  console.log(`   Descrição: ${description}`);
  return { filename, description, timestamp };
}

// Função para esperar
function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Analisar sistema completo
async function captureAndAnalyze() {
  console.log('🔍 CAPTURA E ANÁLISE COMPLETA DO AI WIZARD\n');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });
  
  // Capturar erros
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('❌ Console:', msg.text());
    }
  });
  
  const analysisReport = {
    timestamp: new Date().toISOString(),
    testType: 'Complete System Analysis',
    screenshots: [],
    apiTests: [],
    interfaceTests: [],
    findings: [],
    issues: [],
    recommendations: []
  };
  
  try {
    // ETAPA 1: Verificar servidores
    console.log('📍 ETAPA 1: Verificando servidores...');
    
    try {
      const healthResponse = await makeRequest({
        hostname: 'localhost',
        port: 8768,
        path: '/health',
        method: 'GET'
      });
      
      if (healthResponse.status === 200) {
        console.log('✅ Backend saudável');
        analysisReport.apiTests.push({
          test: 'Backend Health',
          status: 'SUCCESS',
          response: healthResponse.data
        });
      } else {
        console.log('❌ Backend não saudável');
        analysisReport.issues.push('Backend não está respondendo corretamente');
      }
    } catch (error) {
      console.log('❌ Erro no backend:', error.message);
      analysisReport.issues.push(`Backend error: ${error.message}`);
    }
    
    try {
      const frontendResponse = await fetch('http://localhost:5173');
      if (frontendResponse.ok) {
        console.log('✅ Frontend saudável');
        analysisReport.interfaceTests.push({
          test: 'Frontend Health',
          status: 'SUCCESS'
        });
      } else {
        console.log('❌ Frontend não saudável');
        analysisReport.issues.push('Frontend não está respondendo corretamente');
      }
    } catch (error) {
      console.log('❌ Erro no frontend:', error.message);
      analysisReport.issues.push(`Frontend error: ${error.message}`);
    }
    
    // ETAPA 2: Testar API completa
    console.log('\n🔌 ETAPA 2: Testando API completa...');
    
    const apiTestCases = [
      {
        name: 'Teste Simples',
        description: 'Teste básico do sistema',
        input: 'Quero fazer um projeto de IA'
      },
      {
        name: 'Teste Completo',
        description: 'Teste com informações completas',
        input: 'Fine-tuning de LLaMA 7B com LoRA para deploy em produção, orçamento de $100/hora'
      },
      {
        name: 'Teste Pesquisa',
        description: 'Teste de pesquisa avançada',
        input: 'Compare RTX 4090 vs A6000 benchmarks 2024 para Stable Diffusion XL'
      }
    ];
    
    for (const testCase of apiTestCases) {
      console.log(`\n🧪 ${testCase.name}:`);
      
      try {
        const response = await makeRequest({
          hostname: 'localhost',
          port: 8768,
          path: '/api/v1/ai-wizard/analyze',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }, {
          project_description: testCase.input,
          conversation_history: null
        });
        
        if (response.status === 200 && response.data.success) {
          console.log(`✅ Status: ${response.status}`);
          console.log(`🤖 Modelo: ${response.data.model_used}`);
          
          const result = response.data.data || response.data;
          
          // Validar novo formato
          if (result.stage) {
            console.log(`📋 Stage: ${result.stage}`);
            analysisReport.findings.push(`API usando novo formato - Stage: ${result.stage}`);
          } else {
            console.log('⚠️ Usando formato antigo');
            analysisReport.findings.push('API ainda usando formato antigo');
          }
          
          if (result.needs_more_info !== undefined) {
            console.log(`💬 Precisa mais info: ${result.needs_more_info}`);
            
            if (result.needs_more_info && result.questions) {
              console.log(`❓ Perguntas: ${result.questions.length}`);
              analysisReport.findings.push(`Sistema gerou ${result.questions.length} perguntas`);
            }
          }
          
          analysisReport.apiTests.push({
            test: testCase.name,
            status: 'SUCCESS',
            model: response.data.model_used,
            stage: result.stage || 'unknown',
            needsMoreInfo: result.needs_more_info
          });
          
        } else {
          console.log(`❌ Status: ${response.status}`);
          analysisReport.issues.push(`API test failed: ${testCase.name}`);
        }
        
      } catch (error) {
        console.log(`❌ Erro: ${error.message}`);
        analysisReport.issues.push(`API error: ${error.message}`);
      }
    }
    
    // ETAPA 3: Capturar screenshots da interface
    console.log('\n📸 ETAPA 3: Capturando screenshots da interface...');
    
    // Screenshot 1: Página inicial
    console.log('\n🏠 Capturando página inicial...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });
    const screenshot1 = await takeScreenshot(page, '01_initial_page', 'Página inicial do Dumont Cloud');
    analysisReport.screenshots.push(screenshot1);
    
    // Screenshot 2: Login
    console.log('\n🔐 Fazendo login...');
    const emailInput = await page.$('input[type="text"], input[type="email"]');
    const passwordInput = await page.$('input[type="password"]');
    const loginButton = await page.$('button[type="submit"]');
    
    if (emailInput && passwordInput && loginButton) {
      await emailInput.click();
      await emailInput.type('test@test.com');
      await passwordInput.click();
      await passwordInput.type('test123');
      await loginButton.click();
      
      console.log('📤 Login enviado');
      await wait(3000);
      
      const screenshot2 = await takeScreenshot(page, '02_after_login', 'Dashboard após login');
      analysisReport.screenshots.push(screenshot2);
      analysisReport.interfaceTests.push({
        test: 'Login Process',
        status: 'SUCCESS'
      });
    } else {
      console.log('❌ Formulário de login não encontrado');
      analysisReport.issues.push('Formulário de login não encontrado');
    }
    
    // Screenshot 3: Buscar botão AI
    console.log('\n🤖 Procurando botão AI...');
    await wait(2000);
    
    const buttons = await page.$$('button');
    let aiButtonFound = false;
    
    for (let i = 0; i < buttons.length; i++) {
      try {
        const text = await page.evaluate(el => el.textContent, buttons[i]);
        const className = await page.evaluate(el => el.className, buttons[i]);
        
        console.log(`  Botão ${i + 1}: "${text}" (class: ${className})`);
        
        if (text && (text.toLowerCase().includes('wizard') || 
                    text.toLowerCase().includes('ai'))) {
          aiButtonFound = true;
          console.log(`✅ Botão encontrado: "${text}"`);
          
          await buttons[i].click();
          await wait(3000);
          
          const screenshot3 = await takeScreenshot(page, '03_ai_wizard_opened', 'AI Wizard aberto');
          analysisReport.screenshots.push(screenshot3);
          analysisReport.interfaceTests.push({
            test: 'AI Wizard Access',
            status: 'SUCCESS'
          });
          break;
        }
      } catch (e) {
        // Continuar
      }
    }
    
    if (!aiButtonFound) {
      console.log('❌ Botão AI não encontrado');
      analysisReport.issues.push('Botão AI/Wizard não encontrado na interface');
      
      const screenshot3 = await takeScreenshot(page, '03_no_ai_button', 'Interface sem botão AI');
      analysisReport.screenshots.push(screenshot3);
    }
    
    // Screenshot 4: Verificar elementos do chat
    console.log('\n💬 Verificando elementos do chat...');
    
    const chatElements = {
      'Input de chat': 'textarea',
      'Botão enviar': 'button svg, button[type="submit"]',
      'Área de mensagens': '.prose, .message-content, .text-gray-200'
    };
    
    let chatWorking = true;
    for (const [name, selector] of Object.entries(chatElements)) {
      const found = await page.$(selector) !== null;
      console.log(`  ${found ? '✅' : '❌'} ${name}`);
      if (!found) chatWorking = false;
    }
    
    const screenshot4 = await takeScreenshot(page, '04_chat_elements', 'Elementos do chat AI Wizard');
    analysisReport.screenshots.push(screenshot4);
    
    if (chatWorking) {
      analysisReport.interfaceTests.push({
        test: 'Chat Elements',
        status: 'SUCCESS'
      });
    } else {
      analysisReport.issues.push('Elementos do chat não estão todos presentes');
    }
    
    // Screenshot 5: Testar conversa
    if (chatWorking) {
      console.log('\n📤 Testando conversa...');
      
      const textarea = await page.$('textarea');
      if (textarea) {
        await textarea.click();
        await textarea.selectText();
        await textarea.type('Teste completo do sistema - fine-tuning LLaMA 7B');
        await wait(1000);
        
        const screenshot5 = await takeScreenshot(page, '05_message_typed', 'Mensagem digitada no chat');
        analysisReport.screenshots.push(screenshot5);
        
        const sendButton = await page.$('button svg') || 
                          await page.$('button[type="submit"]') ||
                          await page.$('button');
        
        if (sendButton) {
          await sendButton.click();
          console.log('📤 Mensagem enviada');
          await wait(5000);
          
          const screenshot6 = await takeScreenshot(page, '06_response_received', 'Resposta recebida do AI');
          analysisReport.screenshots.push(screenshot6);
          
          // Verificar resposta
          const responses = await page.$$('.prose, .message-content, .text-gray-200');
          if (responses.length > 0) {
            const lastResponse = responses[responses.length - 1];
            const responseText = await page.evaluate(el => el.textContent, lastResponse);
            console.log('🤖 Resposta recebida:', responseText.substring(0, 100) + '...');
            
            analysisReport.findings.push(`Resposta do sistema: ${responseText.substring(0, 50)}...`);
            analysisReport.interfaceTests.push({
              test: 'Chat Conversation',
              status: 'SUCCESS'
            });
          } else {
            console.log('❌ Nenhuma resposta recebida');
            analysisReport.issues.push('Chat não retornou resposta');
          }
        } else {
          console.log('❌ Botão de envio não encontrado');
          analysisReport.issues.push('Botão de envio do chat não encontrado');
        }
      } else {
        console.log('❌ Input de chat não encontrado');
        analysisReport.issues.push('Input de chat não encontrado');
      }
    }
    
    // ETAPA 4: Análise final
    console.log('\n📋 ETAPA 4: Análise final...');
    
    // Contar screenshots
    console.log(`📸 Total de screenshots: ${analysisReport.screenshots.length}`);
    
    // Analisar problemas
    if (analysisReport.issues.length === 0) {
      console.log('✅ Nenhum problema crítico encontrado');
      analysisReport.findings.push('Sistema funcionando perfeitamente');
    } else {
      console.log(`⚠️ ${analysisReport.issues.length} problemas encontrados:`);
      analysisReport.issues.forEach((issue, idx) => {
        console.log(`   ${idx + 1}. ${issue}`);
      });
    }
    
    // Gerar recomendações
    if (analysisReport.issues.length > 0) {
      analysisReport.recommendations.push('Investigar e corrigir os problemas identificados');
    }
    
    if (!analysisReport.findings.includes('API usando novo formato')) {
      analysisReport.recommendations.push('Atualizar API para usar novo formato de stages');
    }
    
    if (analysisReport.issues.length === 0) {
      analysisReport.recommendations.push('Sistema pronto para produção');
    }
    
    // Salvar relatório
    fs.writeFileSync(ANALYSIS_REPORT, JSON.stringify(analysisReport, null, 2));
    console.log(`\n📋 Relatório salvo: ${ANALYSIS_REPORT}`);
    
    // Relatório final
    console.log('\n🎯 RELATÓRIO FINAL DE ANÁLISE');
    console.log('='.repeat(60));
    console.log(`✅ Screenshots capturados: ${analysisReport.screenshots.length}`);
    console.log(`✅ Testes de API: ${analysisReport.apiTests.length}`);
    console.log(`✅ Testes de interface: ${analysisReport.interfaceTests.length}`);
    console.log(`⚠️ Problemas encontrados: ${analysisReport.issues.length}`);
    console.log(`💡 Descobertas: ${analysisReport.findings.length}`);
    console.log(`📋 Recomendações: ${analysisReport.recommendations.length}`);
    
    console.log('\n📁 Screenshots em:', SCREENSHOT_DIR);
    console.log('📋 Relatório completo em:', ANALYSIS_REPORT);
    
    if (analysisReport.issues.length === 0) {
      console.log('\n🎉 SISTEMA 100% FUNCIONAL!');
    } else {
      console.log('\n⚠️ SISTEMA PRECISA DE AJUSTES');
    }
    
  } catch (error) {
    console.error('❌ Erro durante análise:', error.message);
    analysisReport.issues.push(`Analysis error: ${error.message}`);
    
    const errorScreenshot = await takeScreenshot(page, 'error_state', 'Erro durante análise');
    analysisReport.screenshots.push(errorScreenshot);
    
    fs.writeFileSync(ANALYSIS_REPORT, JSON.stringify(analysisReport, null, 2));
  } finally {
    await browser.close();
  }
}

// Executar análise
async function main() {
  await captureAndAnalyze();
}

if (require.main === module) {
  main().catch(console.error);
}
