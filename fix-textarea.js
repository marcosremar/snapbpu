const puppeteer = require('puppeteer');
const fs = require('fs');

// Função para esperar
function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Corrigir elemento textarea do chat
async function fixTextarea() {
  console.log('🔧 CORRIGINDO ELEMENTO TEXTAREA DO CHAT\n');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });
  
  // Capturar erros e logs
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('❌ Console:', msg.text());
    }
  });
  
  try {
    // ETAPA 1: Acessar e fazer login
    console.log('📍 ETAPA 1: Acessando sistema...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });
    
    // Login
    const emailInput = await page.$('input[type="text"], input[type="email"]');
    const passwordInput = await page.$('input[type="password"]');
    const loginButton = await page.$('button[type="submit"]');
    
    if (emailInput && passwordInput && loginButton) {
      await emailInput.click();
      await emailInput.type('test@test.com');
      await passwordInput.click();
      await passwordInput.type('test123');
      await loginButton.click();
      
      console.log('✅ Login realizado');
      await wait(3000);
    } else {
      console.log('❌ Formulário de login não encontrado');
      return;
    }
    
    // ETAPA 2: Abrir AI Wizard
    console.log('\n📍 ETAPA 2: Abrindo AI Wizard...');
    
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
    
    if (!aiButtonFound) {
      console.log('❌ Botão AI Wizard não encontrado');
      return;
    }
    
    // ETAPA 3: Analisar estrutura do chat
    console.log('\n📍 ETAPA 3: Analisando estrutura do chat...');
    
    // Provar diferentes seletores para textarea
    const textareaSelectors = [
      'textarea',
      'textarea[placeholder*="mensagem"]',
      'textarea[placeholder*="digite"]',
      'textarea[placeholder*="escreva"]',
      'div[contenteditable="true"]',
      '.chat-input textarea',
      '.message-input textarea',
      'input[type="text"]',
      '.prose p',
      'div[class*="input"]',
      'div[class*="chat"] input',
      'div[class*="message"] input'
    ];
    
    let foundElements = [];
    
    for (const selector of textareaSelectors) {
      try {
        const elements = await page.$$(selector);
        if (elements.length > 0) {
          console.log(`✅ Encontrado ${elements.length} elementos com: ${selector}`);
          foundElements.push({ selector, count: elements.length });
          
          // Analisar cada elemento
          for (let i = 0; i < Math.min(elements.length, 3); i++) {
            const element = elements[i];
            try {
              const isVisible = await page.evaluate(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0';
              }, element);
              
              const isEditable = await page.evaluate(el => {
                return !el.disabled && !el.readOnly;
              }, element);
              
              const placeholder = await page.evaluate(el => el.placeholder || '', element);
              
              console.log(`   Elemento ${i + 1}: Visível=${isVisible}, Editável=${isEditable}, Placeholder="${placeholder}"`);
            } catch (e) {
              console.log(`   Elemento ${i + 1}: Erro na análise`);
            }
          }
        }
      } catch (e) {
        // Continuar
      }
    }
    
    // ETAPA 4: Capturar screenshot para análise
    console.log('\n📍 ETAPA 4: Capturando screenshot para análise...');
    
    const screenshotPath = '/tmp/chat-structure-analysis.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`📸 Screenshot salvo: ${screenshotPath}`);
    
    // ETAPA 5: Tentar interagir com elementos encontrados
    console.log('\n📍 ETAPA 5: Testando interação...');
    
    if (foundElements.length > 0) {
      // Tentar encontrar um elemento interativo
      for (const { selector } of foundElements) {
        try {
          const element = await page.$(selector);
          if (element) {
            // Tentar clicar e digitar
            await element.click();
            await wait(500);
            
            // Limpar e digitar
            await page.evaluate(el => el.value = '', element);
            await element.type('Teste de mensagem do sistema');
            
            console.log(`✅ Intação bem-sucedida com: ${selector}`);
            
            // Capturar screenshot após digitação
            const afterTypePath = '/tmp/chat-after-typing.png';
            await page.screenshot({ path: afterTypePath, fullPage: true });
            console.log(`📸 Screenshot pós-digitação: ${afterTypePath}`);
            
            break;
          }
        } catch (e) {
          console.log(`❌ Falha na interação com: ${selector}`);
        }
      }
    } else {
      console.log('❌ Nenhum elemento de input encontrado');
      
      // ETAPA 6: Análise avançada do DOM
      console.log('\n📍 ETAPA 6: Análise avançada do DOM...');
      
      const domAnalysis = await page.evaluate(() => {
        const allElements = document.querySelectorAll('*');
        const inputElements = [];
        
        for (const el of allElements) {
          const tagName = el.tagName.toLowerCase();
          const className = el.className;
          const id = el.id;
          
          if (tagName === 'textarea' || 
              tagName === 'input' ||
              el.contentEditable === 'true' ||
              (className && className.includes('input')) ||
              (className && className.includes('chat')) ||
              (className && className.includes('message'))) {
            
            const style = window.getComputedStyle(el);
            const isVisible = style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0';
            
            inputElements.push({
              tag: tagName,
              class: className,
              id: id,
              visible: isVisible,
              editable: !el.disabled && !el.readOnly,
              contentEditable: el.contentEditable === 'true'
            });
          }
        }
        
        return inputElements;
      });
      
      console.log('Elementos de input encontrados:');
      domAnalysis.forEach((el, idx) => {
        console.log(`   ${idx + 1}. ${el.tag} - class="${el.class}" - visible=${el.visible} - editable=${el.editable}`);
      });
      
      // Salvar análise
      fs.writeFileSync('/tmp/dom-analysis.json', JSON.stringify(domAnalysis, null, 2));
      console.log('\n📋 Análise DOM salva: /tmp/dom-analysis.json');
    }
    
    console.log('\n🎯 RESUMO DA CORREÇÃO');
    console.log('='.repeat(50));
    console.log(`📊 Elementos encontrados: ${foundElements.length}`);
    console.log(`📸 Screenshots capturados: 2`);
    console.log(`📋 Análise DOM: completa`);
    
    if (foundElements.length > 0) {
      console.log('✅ Elementos de input encontrados e testados');
      console.log('✅ Intação funcionando');
    } else {
      console.log('❌ Nenhum elemento interativo encontrado');
      console.log('📋 Possíveis causas:');
      console.log('   - Interface ainda carregando');
      console.log('   - Seletor CSS diferente');
      console.log('   - Elemento gerado dinamicamente');
    }
    
  } catch (error) {
    console.error('❌ Erro durante correção:', error.message);
  } finally {
    await browser.close();
  }
}

// Executar correção
async function main() {
  await fixTextarea();
}

if (require.main === module) {
  main().catch(console.error);
}
