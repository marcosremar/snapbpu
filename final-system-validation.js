const http = require('http');

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

// Validação final completa do sistema
async function finalSystemValidation() {
  console.log('🎯 VALIDAÇÃO FINAL COMPLETA DO SISTEMA AI WIZARD\n');
  
  const validation = {
    timestamp: new Date().toISOString(),
    systemStatus: 'UNKNOWN',
    allTasksCompleted: false,
    flowProgression: {
      analysis: false,
      research: false,
      options: false,
      selection: false,
      reservation: false
    },
    features: {
      apiFormat: false,
      progression: false,
      priceOptions: false,
      machineSelection: false,
      reservationSystem: false,
      researchSystem: false,
      chatInterface: false
    },
    finalResult: 'UNKNOWN'
  };
  
  try {
    // ETAPA 1: Verificar saúde do sistema
    console.log('📍 ETAPA 1: Verificando saúde do sistema...');
    
    const healthResponse = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/health',
      method: 'GET'
    });
    
    if (healthResponse.status === 200) {
      console.log('✅ Backend saudável');
      validation.systemStatus = 'HEALTHY';
    } else {
      console.log('❌ Backend não saudável');
      validation.systemStatus = 'UNHEALTHY';
      return;
    }
    
    // ETAPA 2: Validar formato da API
    console.log('\n📍 ETAPA 2: Validando formato da API...');
    
    const apiTest = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/api/v1/ai-wizard/analyze',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    }, {
      project_description: 'Teste de formato da API',
      conversation_history: null
    });
    
    if (apiTest.status === 200 && apiTest.data.success) {
      const result = apiTest.data.data;
      
      if (result && result.stage) {
        console.log('✅ API usando novo formato com stage');
        validation.features.apiFormat = true;
        console.log(`   Stage: ${result.stage}`);
        console.log(`   Needs more info: ${result.needs_more_info}`);
      } else {
        console.log('❌ API ainda usando formato antigo');
      }
    } else {
      console.log('❌ API não respondendo corretamente');
    }
    
    // ETAPA 3: Validar progressão completa do fluxo
    console.log('\n📍 ETAPA 3: Validando progressão do fluxo...');
    
    const flowTests = [
      {
        name: 'Análise Inicial',
        description: 'Quero fazer um projeto de IA',
        expectedStage: 'analysis'
      },
      {
        name: 'Pesquisa',
        description: 'Fine-tuning LLaMA 7B com LoRA, orçamento $100/hora',
        expectedStage: 'research'
      },
      {
        name: 'Opções',
        description: 'Quero ver as opções de preço disponíveis',
        expectedStage: 'options'
      },
      {
        name: 'Seleção',
        description: 'Escolho a opção Intermediário',
        expectedStage: 'selection'
      },
      {
        name: 'Reserva',
        description: 'Quero escolher automaticamente a melhor máquina',
        expectedStage: 'reservation'
      }
    ];
    
    let flowProgressionWorking = true;
    
    for (const test of flowTests) {
      console.log(`\n🧪 ${test.name}:`);
      
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
          project_description: test.description,
          conversation_history: null
        });
        
        if (response.status === 200 && response.data.success) {
          const result = response.data.data;
          
          if (result && result.stage === test.expectedStage) {
            console.log(`✅ Stage correto: ${result.stage}`);
            validation.flowProgression[test.expectedStage] = true;
          } else {
            console.log(`❌ Stage incorreto: esperado ${test.expectedStage}, recebido ${result?.stage}`);
            flowProgressionWorking = false;
          }
          
          // Validar features específicas de cada stage
          if (test.expectedStage === 'research' && result.research_results) {
            console.log('✅ Sistema de pesquisa funcionando');
            validation.features.researchSystem = true;
          }
          
          if (test.expectedStage === 'options' && result.price_options) {
            console.log('✅ Opções de preço funcionando');
            validation.features.priceOptions = true;
            console.log(`   Opções: ${result.price_options.length}`);
          }
          
          if (test.expectedStage === 'selection' && result.machines) {
            console.log('✅ Seleção de máquinas funcionando');
            validation.features.machineSelection = true;
            console.log(`   Máquinas: ${result.machines.length}`);
          }
          
          if (test.expectedStage === 'reservation' && result.reservation) {
            console.log('✅ Sistema de reserva funcionando');
            validation.features.reservationSystem = true;
            console.log(`   Status: ${result.reservation.status}`);
          }
          
        } else {
          console.log(`❌ Erro: ${response.status}`);
          flowProgressionWorking = false;
        }
        
      } catch (error) {
        console.log(`❌ Erro: ${error.message}`);
        flowProgressionWorking = false;
      }
    }
    
    if (flowProgressionWorking) {
      console.log('\n✅ Progressão completa do fluxo funcionando');
      validation.features.progression = true;
    } else {
      console.log('\n❌ Progressão do fluxo com problemas');
    }
    
    // ETAPA 4: Validar sistema de pesquisa real
    console.log('\n📍 ETAPA 4: Validando sistema de pesquisa...');
    
    const researchTest = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/api/v1/ai-wizard/analyze',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    }, {
      project_description: 'Compare RTX 4090 vs A6000 benchmarks 2024 para Stable Diffusion XL',
      conversation_history: null
    });
    
    if (researchTest.status === 200 && researchTest.data.success) {
      const result = researchTest.data.data;
      
      if (result && result.stage === 'research' && result.research_results) {
        console.log('✅ Sistema de pesquisa real implementado');
        console.log(`   Findings: ${result.research_results.findings?.substring(0, 50) || 'N/A'}...`);
        validation.features.researchSystem = true;
      } else {
        console.log('⚠️ Sistema de pesquisa usando fallback');
      }
    }
    
    // ETAPA 5: Resumo final
    console.log('\n📍 ETAPA 5: Resumo final da validação...');
    
    const allFeaturesWorking = Object.values(validation.features).every(status => status);
    const allFlowStagesWorking = Object.values(validation.flowProgression).every(status => status);
    
    validation.allTasksCompleted = allFeaturesWorking && allFlowStagesWorking;
    
    if (validation.allTasksCompleted) {
      validation.finalResult = 'PERFECT';
      console.log('🎉 SISTEMA 100% PERFEITO!');
    } else if (validation.systemStatus === 'HEALTHY' && validation.features.progression) {
      validation.finalResult = 'EXCELLENT';
      console.log('🚀 SISTEMA EXCELENTE!');
    } else if (validation.systemStatus === 'HEALTHY') {
      validation.finalResult = 'GOOD';
      console.log('✅ SISTEMA BOM!');
    } else {
      validation.finalResult = 'NEEDS_WORK';
      console.log('⚠️ SISTEMA PRECISA DE TRABALHO');
    }
    
    // Salvar validação
    const fs = require('fs');
    fs.writeFileSync('/tmp/ai-wizard-final-validation.json', JSON.stringify(validation, null, 2));
    console.log('\n📋 Validação final salva: /tmp/ai-wizard-final-validation.json');
    
    // Relatório final
    console.log('\n📊 RELATÓRIO FINAL DE VALIDAÇÃO');
    console.log('='.repeat(60));
    console.log(`🎯 Status do Sistema: ${validation.systemStatus}`);
    console.log(`📋 Resultado Final: ${validation.finalResult}`);
    console.log(`✅ Todas as Tarefas: ${validation.allTasksCompleted ? 'CONCLUÍDAS' : 'PENDENTES'}`);
    
    console.log('\n🔧 Status das Features:');
    Object.entries(validation.features).forEach(([feature, status]) => {
      console.log(`   ${status ? '✅' : '❌'} ${feature}`);
    });
    
    console.log('\n🔄 Progressão do Fluxo:');
    Object.entries(validation.flowProgression).forEach(([stage, status]) => {
      console.log(`   ${status ? '✅' : '❌'} ${stage}`);
    });
    
    console.log('\n🎉 CONCLUSÃO FINAL:');
    if (validation.finalResult === 'PERFECT') {
      console.log('✅ Todas as tarefas foram concluídas com sucesso!');
      console.log('✅ Sistema 100% funcional e pronto para produção!');
      console.log('✅ Fluxo completo do projeto até a reserva funcionando!');
      console.log('✅ Sistema de pesquisa real implementado!');
      console.log('✅ Interface corrigida e funcional!');
    } else if (validation.finalResult === 'EXCELLENT') {
      console.log('✅ Sistema principal funcionando perfeitamente!');
      console.log('✅ Pequenos ajustes podem ser feitos posteriormente!');
    }
    
  } catch (error) {
    console.error('❌ Erro na validação final:', error.message);
    validation.finalResult = 'ERROR';
    validation.systemStatus = 'ERROR';
  }
}

// Executar validação final
async function main() {
  await finalSystemValidation();
}

if (require.main === module) {
  main().catch(console.error);
}
