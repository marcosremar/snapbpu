const puppeteer = require('puppeteer');
const fs = require('fs');

// Diretório para screenshots
const SCREENSHOT_DIR = '/tmp/ai-wizard-interfaces';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Função para esperar
function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Capturar screenshots de cada interface
async function captureInterfaces() {
  console.log('📸 CAPTURANDO SCREENSHOTS DE CADA INTERFACE\n');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });
  
  const screenshots = [];
  
  try {
    // ETAPA 1: Página inicial
    console.log('📍 ETAPA 1: Página inicial...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });
    await wait(2000);
    
    const screenshot1 = await page.screenshot({ 
      path: `${SCREENSHOT_DIR}/01_initial_page.png`, 
      fullPage: true 
    });
    screenshots.push({
      name: 'Página Inicial',
      file: '01_initial_page.png',
      description: 'Tela de login/entrada do sistema'
    });
    console.log('✅ Página inicial capturada');
    
    // ETAPA 2: Dashboard após login
    console.log('\n📍 ETAPA 2: Dashboard após login...');
    
    const emailInput = await page.$('input[type="text"], input[type="email"]');
    const passwordInput = await page.$('input[type="password"]');
    const loginButton = await page.$('button[type="submit"]');
    
    if (emailInput && passwordInput && loginButton) {
      await emailInput.click();
      await emailInput.type('test@test.com');
      await passwordInput.click();
      await passwordInput.type('test123');
      await loginButton.click();
      
      console.log('📤 Login realizado');
      await wait(3000);
      
      const screenshot2 = await page.screenshot({ 
        path: `${SCREENSHOT_DIR}/02_dashboard.png`, 
        fullPage: true 
      });
      screenshots.push({
        name: 'Dashboard',
        file: '02_dashboard.png',
        description: 'Dashboard principal após login'
      });
      console.log('✅ Dashboard capturado');
    }
    
    // ETAPA 3: AI Wizard - Abertura
    console.log('\n📍 ETAPA 3: AI Wizard - Abertura...');
    
    const buttons = await page.$$('button');
    let aiButtonFound = false;
    
    for (let i = 0; i < buttons.length; i++) {
      try {
        const text = await page.evaluate(el => el.textContent, buttons[i]);
        
        if (text && text.toLowerCase().includes('wizard')) {
          aiButtonFound = true;
          console.log(`✅ Botão encontrado: "${text}"`);
          await buttons[i].click();
          await wait(3000);
          break;
        }
      } catch (e) {
        // Continuar
      }
    }
    
    if (aiButtonFound) {
      const screenshot3 = await page.screenshot({ 
        path: `${SCREENSHOT_DIR}/03_ai_wizard_opened.png`, 
        fullPage: true 
      });
      screenshots.push({
        name: 'AI Wizard Aberto',
        file: '03_ai_wizard_opened.png',
        description: 'AI Wizard aberto e pronto para uso'
      });
      console.log('✅ AI Wizard aberto capturado');
    }
    
    // ETAPA 4: Chat - Estado inicial
    console.log('\n📍 ETAPA 4: Chat - Estado inicial...');
    
    const screenshot4 = await page.screenshot({ 
      path: `${SCREENSHOT_DIR}/04_chat_initial.png`, 
      fullPage: true 
    });
    screenshots.push({
      name: 'Chat Inicial',
      file: '04_chat_initial.png',
      description: 'Chat do AI Wizard em estado inicial'
    });
    console.log('✅ Chat inicial capturado');
    
    // ETAPA 5: Chat - Após primeira mensagem
    console.log('\n📍 ETAPA 5: Chat - Após primeira mensagem...');
    
    // Tentar encontrar e usar o campo de input
    const inputSelectors = [
      'textarea',
      'input[type="text"]',
      'div[contenteditable="true"]',
      '.prose p',
      'div[class*="input"]',
      'div[class*="chat"] input'
    ];
    
    let inputFound = false;
    for (const selector of inputSelectors) {
      try {
        const element = await page.$(selector);
        if (element) {
          const isVisible = await page.evaluate(el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && 
                   style.visibility !== 'hidden' && 
                   style.opacity !== '0';
          }, element);
          
          if (isVisible) {
            console.log(`✅ Input encontrado com: ${selector}`);
            await element.click();
            await wait(500);
            await element.type('Quero fazer um projeto de IA');
            
            // Tentar enviar
            const sendButton = await page.$('button svg') || 
                              await page.$('button[type="submit"]') ||
                              await page.$('button');
            
            if (sendButton) {
              await sendButton.click();
              console.log('📤 Mensagem enviada');
              await wait(3000);
              
              const screenshot5 = await page.screenshot({ 
                path: `${SCREENSHOT_DIR}/05_chat_with_response.png`, 
                fullPage: true 
              });
              screenshots.push({
                name: 'Chat com Resposta',
                file: '05_chat_with_response.png',
                description: 'Chat após enviar mensagem e receber resposta'
              });
              console.log('✅ Chat com resposta capturado');
            }
            
            inputFound = true;
            break;
          }
        }
      } catch (e) {
        // Continuar
      }
    }
    
    if (!inputFound) {
      console.log('⚠️ Input não encontrado, capturando estado atual');
      const screenshot5 = await page.screenshot({ 
        path: `${SCREENSHOT_DIR}/05_chat_no_input.png`, 
        fullPage: true 
      });
      screenshots.push({
        name: 'Chat Sem Input',
        file: '05_chat_no_input.png',
        description: 'Chat sem campo de input identificado'
      });
    }
    
    // ETAPA 6: Análise de elementos da interface
    console.log('\n📍 ETAPA 6: Análise de elementos da interface...');
    
    const interfaceAnalysis = await page.evaluate(() => {
      const elements = {
        buttons: document.querySelectorAll('button').length,
        inputs: document.querySelectorAll('input, textarea').length,
        links: document.querySelectorAll('a').length,
        images: document.querySelectorAll('img').length,
        divs: document.querySelectorAll('div').length,
        textElements: document.querySelectorAll('p, span, h1, h2, h3, h4, h5, h6').length
      };
      
      const problematicElements = [];
      
      // Procurar elementos com problemas potenciais
      document.querySelectorAll('*').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.position === 'fixed' || style.position === 'absolute') {
          if (style.zIndex && parseInt(style.zIndex) > 1000) {
            problematicElements.push({
              tag: el.tagName,
              class: el.className,
              zIndex: style.zIndex,
              position: style.position
            });
          }
        }
      });
      
      return {
        elementCount: elements,
        problematicElements: problematicElements,
        viewportSize: {
          width: window.innerWidth,
          height: window.innerHeight
        }
      };
    });
    
    console.log('📊 Análise da interface:');
    console.log(`   Botões: ${interfaceAnalysis.elementCount.buttons}`);
    console.log(`   Inputs: ${interfaceAnalysis.elementCount.inputs}`);
    console.log(`   Links: ${interfaceAnalysis.elementCount.links}`);
    console.log(`   Imagens: ${interfaceAnalysis.elementCount.images}`);
    console.log(`   Divs: ${interfaceAnalysis.elementCount.divs}`);
    console.log(`   Textos: ${interfaceAnalysis.elementCount.textElements}`);
    console.log(`   Elementos problemáticos: ${interfaceAnalysis.problematicElements.length}`);
    
    // ETAPA 7: Capturar diferentes resoluções
    console.log('\n📍 ETAPA 7: Testando responsividade...');
    
    const resolutions = [
      { width: 1920, height: 1080, name: 'Desktop HD' },
      { width: 1366, height: 768, name: 'Desktop Médio' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 375, height: 667, name: 'Mobile' }
    ];
    
    for (const resolution of resolutions) {
      console.log(`📱 Testando ${resolution.name} (${resolution.width}x${resolution.height})`);
      await page.setViewport({ width: resolution.width, height: resolution.height });
      await wait(1000);
      
      const filename = `06_responsive_${resolution.name.toLowerCase().replace(' ', '_')}.png`;
      await page.screenshot({ 
        path: `${SCREENSHOT_DIR}/${filename}`, 
        fullPage: true 
      });
      
      screenshots.push({
        name: `Responsivo - ${resolution.name}`,
        file: filename,
        description: `Interface em ${resolution.name}`
      });
    }
    
    // Salvar análise completa
    const analysisReport = {
      timestamp: new Date().toISOString(),
      screenshots: screenshots,
      interfaceAnalysis: interfaceAnalysis,
      recommendations: []
    };
    
    // Gerar recomendações baseadas na análise
    if (interfaceAnalysis.elementCount.inputs === 0) {
      analysisReport.recommendations.push('CRÍTICO: Nenhum campo de input encontrado na interface');
    }
    
    if (interfaceAnalysis.problematicElements.length > 0) {
      analysisReport.recommendations.push('ATENÇÃO: Elementos com z-index muito alto podem causar interferência');
    }
    
    if (interfaceAnalysis.elementCount.buttons > 20) {
      analysisReport.recommendations.push('UX: Muitos botões podem confundir o usuário');
    }
    
    fs.writeFileSync(`${SCREENSHOT_DIR}/interface-analysis.json`, JSON.stringify(analysisReport, null, 2));
    
    console.log('\n📋 RELATÓRIO DE CAPTURA');
    console.log('='.repeat(50));
    console.log(`📸 Screenshots capturados: ${screenshots.length}`);
    console.log(`📊 Análise completa: salva`);
    console.log(`📁 Diretório: ${SCREENSHOT_DIR}`);
    
    console.log('\n📋 Screenshots capturados:');
    screenshots.forEach((shot, idx) => {
      console.log(`   ${idx + 1}. ${shot.name} - ${shot.file}`);
      console.log(`      ${shot.description}`);
    });
    
    if (analysisReport.recommendations.length > 0) {
      console.log('\n⚠️ RECOMENDAÇÕES IDENTIFICADAS:');
      analysisReport.recommendations.forEach((rec, idx) => {
        console.log(`   ${idx + 1}. ${rec}`);
      });
    }
    
    console.log('\n🎯 PRÓXIMO PASSO: Analisar screenshots e implementar melhorias');
    
  } catch (error) {
    console.error('❌ Erro durante captura:', error.message);
  } finally {
    await browser.close();
  }
}

// Executar captura
async function main() {
  await captureInterfaces();
}

if (require.main === module) {
  main().catch(console.error);
}
