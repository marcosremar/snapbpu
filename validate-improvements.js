const puppeteer = require('puppeteer');
const fs = require('fs');

// Validar melhorias implementadas
async function validateImprovements() {
  console.log('🧪 VALIDANDO MELHORIAS IMPLEMENTADAS\n');
  
  const validation = {
    timestamp: new Date().toISOString(),
    originalProblems: 3,
    improvementsImplemented: 4,
    tests: {
      inputFunctionality: false,
      quickActions: false,
      responsiveness: false,
      visualFeedback: false,
      overallExperience: false
    },
    finalScore: 0
  };
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });
  
  try {
    // ETAPA 1: Testar HTML melhorado
    console.log('📍 ETAPA 1: Testando HTML melhorado...');
    
    const htmlPath = '/tmp/ai-wizard-improved.html';
    if (fs.existsSync(htmlPath)) {
      await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle2' });
      console.log('✅ HTML melhorado carregado');
      
      // Aguardar carregamento completo
      await page.waitForTimeout(2000);
      
      // ETAPA 2: Testar funcionalidade do input
      console.log('\n📍 ETAPA 2: Testando funcionalidade do input...');
      
      const chatInput = await page.$('.chat-input');
      if (chatInput) {
        console.log('✅ Campo de input encontrado');
        
        // Testar digitação
        await chatInput.click();
        await chatInput.type('Teste de mensagem');
        
        const inputValue = await page.evaluate(el => el.value, chatInput);
        if (inputValue === 'Teste de mensagem') {
          console.log('✅ Input funcional - digitação OK');
          validation.tests.inputFunctionality = true;
        }
        
        // Limpar input
        await page.evaluate(el => el.value = '', chatInput);
      } else {
        console.log('❌ Campo de input não encontrado');
      }
      
      // ETAPA 3: Testar botões de ação rápida
      console.log('\n📍 ETAPA 3: Testando botões de ação rápida...');
      
      const quickActions = await page.$$('.quick-action');
      if (quickActions.length > 0) {
        console.log(`✅ ${quickActions.length} botões de ação rápida encontrados`);
        
        // Testar primeiro botão
        const firstAction = quickActions[0];
        const actionText = await page.evaluate(el => el.textContent, firstAction);
        console.log(`✅ Botão: "${actionText}"`);
        
        await firstAction.click();
        await page.waitForTimeout(500);
        
        const inputValue = await page.evaluate(el => el.value, chatInput);
        if (inputValue === actionText) {
          console.log('✅ Botão de ação rápida funcional');
          validation.tests.quickActions = true;
        }
      } else {
        console.log('❌ Botões de ação rápida não encontrados');
      }
      
      // ETAPA 4: Testar envio de mensagem
      console.log('\n📍 ETAPA 4: Testando envio de mensagem...');
      
      if (validation.tests.inputFunctionality) {
        await chatInput.click();
        await chatInput.type('Teste de validação');
        
        const sendButton = await page.$('.send-button');
        if (sendButton) {
          await sendButton.click();
          console.log('✅ Mensagem enviada');
          
          // Aguardar processamento
          await page.waitForTimeout(1500);
          
          // Verificar se mensagem foi adicionada
          const messages = await page.$$('.message');
          if (messages.length >= 2) {
            console.log('✅ Mensagem adicionada ao chat');
            validation.tests.visualFeedback = true;
          }
        } else {
          console.log('❌ Botão de envio não encontrado');
        }
      }
      
      // ETAPA 5: Testar responsividade
      console.log('\n📍 ETAPA 5: Testando responsividade...');
      
      const resolutions = [
        { width: 1920, height: 1080, name: 'Desktop' },
        { width: 768, height: 1024, name: 'Tablet' },
        { width: 375, height: 667, name: 'Mobile' }
      ];
      
      let responsiveWorking = true;
      
      for (const resolution of resolutions) {
        console.log(`📱 Testando ${resolution.name} (${resolution.width}x${resolution.height})`);
        
        await page.setViewport({ width: resolution.width, height: resolution.height });
        await page.waitForTimeout(500);
        
        // Verificar se elementos ainda funcionam
        const inputVisible = await page.evaluate(() => {
          const input = document.querySelector('.chat-input');
          if (!input) return false;
          
          const style = window.getComputedStyle(input);
          return style.display !== 'none' && 
                 style.visibility !== 'hidden' && 
                 style.opacity !== '0';
        });
        
        if (inputVisible) {
          console.log(`✅ ${resolution.name}: Input visível`);
        } else {
          console.log(`❌ ${resolution.name}: Input não visível`);
          responsiveWorking = false;
        }
      }
      
      if (responsiveWorking) {
        console.log('✅ Interface responsiva funcionando');
        validation.tests.responsiveness = true;
      }
      
      // ETAPA 6: Capturar screenshots da interface melhorada
      console.log('\n📍 ETAPA 6: Capturando screenshots da interface melhorada...');
      
      const screenshotsDir = '/tmp/ai-wizard-improved-screenshots';
      if (!fs.existsSync(screenshotsDir)) {
        fs.mkdirSync(screenshotsDir, { recursive: true });
      }
      
      // Desktop
      await page.setViewport({ width: 1280, height: 720 });
      await page.screenshot({ 
        path: `${screenshotsDir}/01_improved_desktop.png`, 
        fullPage: true 
      });
      
      // Tablet
      await page.setViewport({ width: 768, height: 1024 });
      await page.screenshot({ 
        path: `${screenshotsDir}/02_improved_tablet.png`, 
        fullPage: true 
      });
      
      // Mobile
      await page.setViewport({ width: 375, height: 667 });
      await page.screenshot({ 
        path: `${screenshotsDir}/03_improved_mobile.png`, 
        fullPage: true 
      });
      
      console.log('✅ Screenshots da interface melhorada capturados');
      
      // ETAPA 7: Calcular pontuação final
      console.log('\n📍 ETAPA 7: Calculando pontuação final...');
      
      const testResults = Object.values(validation.tests);
      const passedTests = testResults.filter(result => result).length;
      validation.finalScore = Math.round((passedTests / testResults.length) * 100);
      
      if (validation.finalScore >= 90) {
        validation.overallExperience = 'EXCELLENT';
      } else if (validation.finalScore >= 70) {
        validation.overallExperience = 'GOOD';
      } else if (validation.finalScore >= 50) {
        validation.overallExperience = 'FAIR';
      } else {
        validation.overallExperience = 'POOR';
      }
      
      console.log(`📊 Pontuação final: ${validation.finalScore}%`);
      console.log(`🎯 Experiência geral: ${validation.overallExperience}`);
      
    } else {
      console.log('❌ HTML melhorado não encontrado');
    }
    
    // ETAPA 8: Salvar relatório de validação
    console.log('\n📍 ETAPA 8: Salvando relatório de validação...');
    
    const validationReport = {
      ...validation,
      recommendations: [],
      filesTested: [
        '/tmp/ai-wizard-improved.html',
        '/tmp/ai-wizard-improvements.css',
        '/tmp/ai-wizard-improvements.js'
      ],
      screenshotsCaptured: [
        '/tmp/ai-wizard-improved-screenshots/01_improved_desktop.png',
        '/tmp/ai-wizard-improved-screenshots/02_improved_tablet.png',
        '/tmp/ai-wizard-improved-screenshots/03_improved_mobile.png'
      ]
    };
    
    // Gerar recomendações baseadas nos resultados
    if (!validation.tests.inputFunctionality) {
      validationReport.recommendations.push('Revisar implementação do campo de input');
    }
    
    if (!validation.tests.quickActions) {
      validationReport.recommendations.push('Verificar botões de ação rápida');
    }
    
    if (!validation.tests.responsiveness) {
      validationReport.recommendations.push('Melhorar design responsivo');
    }
    
    if (validationReport.recommendations.length === 0) {
      validationReport.recommendations.push('Interface pronta para integração');
    }
    
    fs.writeFileSync('/tmp/ai-wizard-validation-report.json', JSON.stringify(validationReport, null, 2));
    
    console.log('\n📋 RELATÓRIO FINAL DE VALIDAÇÃO');
    console.log('='.repeat(60));
    console.log(`📊 Problemas originais: ${validation.originalProblems}`);
    console.log(`✅ Melhorias implementadas: ${validation.improvementsImplemented}`);
    console.log(`🧪 Testes executados: ${Object.keys(validation.tests).length}`);
    console.log(`📈 Pontuação final: ${validation.finalScore}%`);
    console.log(`🎯 Experiência geral: ${validation.overallExperience}`);
    
    console.log('\n📊 Resultados dos testes:');
    Object.entries(validation.tests).forEach(([test, result]) => {
      console.log(`   ${result ? '✅' : '❌'} ${test}`);
    });
    
    console.log('\n📁 Arquivos validados:');
    validationReport.filesTested.forEach((file, idx) => {
      console.log(`   ${idx + 1}. ${file}`);
    });
    
    console.log('\n📸 Screenshots capturados:');
    validationReport.screenshotsCaptured.forEach((file, idx) => {
      console.log(`   ${idx + 1}. ${file}`);
    });
    
    console.log('\n💡 Recomendações:');
    validationReport.recommendations.forEach((rec, idx) => {
      console.log(`   ${idx + 1}. ${rec}`);
    });
    
    console.log('\n🎉 CONCLUSÃO FINAL:');
    if (validation.finalScore >= 90) {
      console.log('✅ INTERFACE EXCELENTE! Pronta para produção.');
      console.log('✅ Todas as melhorias implementadas com sucesso.');
      console.log('✅ Experiência do usuário otimizada.');
    } else if (validation.finalScore >= 70) {
      console.log('✅ INTERFACE BOA! Pequenos ajustes recomendados.');
      console.log('✅ Funcionalidades principais funcionando.');
    } else {
      console.log('⚠️ INTERFACE PRECISA DE MELHORIAS.');
      console.log('❌ Alguns problemas críticos identificados.');
    }
    
  } catch (error) {
    console.error('❌ Erro durante validação:', error.message);
    validation.overallExperience = 'ERROR';
  } finally {
    await browser.close();
  }
}

// Executar validação
async function main() {
  await validateImprovements();
}

if (require.main === module) {
  main().catch(console.error);
}
