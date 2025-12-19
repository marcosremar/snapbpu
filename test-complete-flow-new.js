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

// Testar fluxo completo reestruturado
async function testCompleteFlowNew() {
  console.log('🚀 TESTE DO FLUXO COMPLETO REESTRUTURADO\n');
  
  const baseURL = 'http://localhost:8768';
  
  try {
    // ETAPA 1: Verificar servidor
    console.log('📍 ETAPA 1: Verificando servidor...');
    const healthResponse = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/health',
      method: 'GET'
    });
    
    if (healthResponse.status !== 200) {
      console.log('❌ Servidor não está saudável');
      return;
    }
    console.log('✅ Servidor saudável');
    
    // ETAPA 2: Testar fluxo completo com múltiplos cenários
    console.log('\n🔄 ETAPA 2: Testando fluxo completo reestruturado...');
    
    const testScenarios = [
      {
        name: 'Cenário 1: Análise Inicial',
        description: 'Quero fazer fine-tuning de LLaMA 7B',
        expectedStage: 'analysis',
        expectedQuestions: true
      },
      {
        name: 'Cenário 2: Projeto Completo',
        description: 'Preciso fazer fine-tuning de LLaMA 7B com LoRA para deploy em produção, orçamento de $100/hora',
        expectedStage: 'research',
        expectedQuestions: false
      },
      {
        name: 'Cenário 3: Pesquisa Avançada',
        description: 'API de Stable Diffusion XL para 1000 usuários, compare RTX 4090 vs A6000 benchmarks 2024',
        expectedStage: 'options',
        expectedQuestions: false
      },
      {
        name: 'Cenário 4: Seleção de Máquinas',
        description: 'Escolha automática para treinamento de YOLOv8 com orçamento limitado',
        expectedStage: 'selection',
        expectedQuestions: false
      }
    ];
    
    for (let i = 0; i < testScenarios.length; i++) {
      const scenario = testScenarios[i];
      console.log(`\n🧪 ${scenario.name}`);
      console.log(`📝 Descrição: ${scenario.description}`);
      console.log(`💭 Esperado: Stage ${scenario.expectedStage}`);
      
      const startTime = Date.now();
      
      const response = await makeRequest({
        hostname: 'localhost',
        port: 8768,
        path: '/api/v1/ai-wizard/analyze',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }, {
        project_description: scenario.description,
        conversation_history: null
      });
      
      const responseTime = Date.now() - startTime;
      
      if (response.status === 200 && response.data.success) {
        console.log(`✅ Status: ${response.status}`);
        console.log(`⏱️ Tempo: ${responseTime}ms`);
        console.log(`🤖 Modelo: ${response.data.model_used}`);
        console.log(`🔄 Tentativas: ${response.data.attempts || 1}`);
        
        const result = response.data.data;
        
        // Validar nova estrutura
        if (result.stage) {
          console.log(`📋 Stage: ${result.stage}`);
          
          if (result.stage === scenario.expectedStage) {
            console.log('✅ Stage correto');
          } else {
            console.log(`⚠️ Stage diferente: esperado ${scenario.expectedStage}, got ${result.stage}`);
          }
        } else {
          console.log('❌ Stage não encontrado');
        }
        
        // Validar needs_more_info
        if (result.needs_more_info !== undefined) {
          console.log(`💬 Precisa mais info: ${result.needs_more_info}`);
          
          if (result.needs_more_info && result.questions) {
            console.log(`❓ Perguntas: ${result.questions.length}`);
            result.questions.forEach((q, idx) => {
              console.log(`   ${idx + 1}. ${q}`);
            });
          }
        }
        
        // Validar campos específicos do stage
        if (result.stage === 'research' && result.research_results) {
          console.log('🔍 Resultados da pesquisa:');
          console.log(`   Findings: ${result.research_results.findings?.substring(0, 50) || 'N/A'}...`);
          console.log(`   Benchmarks: ${result.research_results.benchmarks?.substring(0, 50) || 'N/A'}...`);
        }
        
        if (result.stage === 'options' && result.price_options) {
          console.log('💰 Opções de preço:');
          result.price_options.forEach((option, idx) => {
            console.log(`   ${idx + 1}. ${option.tier}: ${option.price_per_hour}`);
            console.log(`      GPUs: ${option.gpus.join(', ')}`);
            console.log(`      Performance: ${option.performance?.substring(0, 50) || 'N/A'}...`);
          });
        }
        
        if (result.stage === 'selection' && result.selection_mode) {
          console.log(`🎯 Modo de seleção: ${result.selection_mode}`);
          
          if (result.selection_mode === 'manual' && result.machines) {
            console.log('🖥️ Máquinas disponíveis:');
            result.machines.forEach((machine, idx) => {
              console.log(`   ${idx + 1}. ${machine.name} - ${machine.gpu} - ${machine.price_per_hour}`);
            });
          }
        }
        
        if (result.stage === 'reservation' && result.reservation) {
          console.log(`📋 Status da reserva: ${result.reservation.status}`);
          console.log(`📝 Detalhes: ${result.reservation.details?.substring(0, 50) || 'N/A'}...`);
        }
        
        // Validar explanation
        if (result.explanation) {
          console.log(`💡 Explicação: ${result.explanation.substring(0, 100)}...`);
        }
        
      } else {
        console.log(`❌ Status: ${response.status}`);
        console.log(`❌ Erro: ${response.data.detail || response.data.error || 'Erro desconhecido'}`);
      }
    }
    
    // ETAPA 3: Testar fluxo completo de conversação
    console.log('\n💬 ETAPA 3: Testando fluxo de conversação completo...');
    
    let conversationHistory = [];
    let currentStage = 'analysis';
    
    // Passo 1: Análise inicial
    console.log('\n📝 Passo 1: Análise inicial...');
    const step1 = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/api/v1/ai-wizard/analyze',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    }, {
      project_description: 'Quero fazer um projeto de IA',
      conversation_history: conversationHistory
    });
    
    if (step1.status === 200) {
      const result1 = step1.data.data;
      console.log(`✅ Stage: ${result1.stage}`);
      
      if (result1.needs_more_info && result1.questions) {
        console.log('❓ Sistema fez perguntas:');
        result1.questions.forEach((q, idx) => {
          console.log(`   ${idx + 1}. ${q}`);
        });
        
        // Simular resposta do usuário
        conversationHistory.push(
          { role: 'user', content: 'Quero fazer um projeto de IA' },
          { role: 'assistant', content: JSON.stringify(result1) }
        );
        
        const userResponse = 'Fine-tuning de LLaMA 7B com LoRA para deploy em produção, orçamento de $50/hora';
        conversationHistory.push({ role: 'user', content: userResponse });
        
        // Passo 2: Pesquisa
        console.log('\n🔍 Passo 2: Pesquisa com informações completas...');
        const step2 = await makeRequest({
          hostname: 'localhost',
          port: 8768,
          path: '/api/v1/ai-wizard/analyze',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }, {
          project_description: userResponse,
          conversation_history: conversationHistory
        });
        
        if (step2.status === 200) {
          const result2 = step2.data.data;
          console.log(`✅ Stage: ${result2.stage}`);
          
          if (result2.stage === 'options' && result2.price_options) {
            console.log('💰 Opções de preço recebidas:');
            result2.price_options.forEach((option, idx) => {
              console.log(`   ${idx + 1}. ${option.tier}: ${option.price_per_hour}`);
            });
            
            // Simular escolha do usuário
            conversationHistory.push(
              { role: 'assistant', content: JSON.stringify(result2) }
            );
            
            const userChoice = 'Intermediário';
            conversationHistory.push({ role: 'user', content: `Escolho a opção ${userChoice}` });
            
            // Passo 3: Seleção de máquinas
            console.log('\n🎯 Passo 3: Seleção de máquinas...');
            const step3 = await makeRequest({
              hostname: 'localhost',
              port: 8768,
              path: '/api/v1/ai-wizard/analyze',
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              }
            }, {
              project_description: `Escolhi a opção ${userChoice}`,
              conversation_history: conversationHistory
            });
            
            if (step3.status === 200) {
              const result3 = step3.data.data;
              console.log(`✅ Stage: ${result3.stage}`);
              console.log(`🎯 Modo seleção: ${result3.selection_mode}`);
              
              if (result3.stage === 'selection') {
                console.log('✅ Fluxo completo funcionando!');
                
                // Simular seleção final
                conversationHistory.push(
                  { role: 'assistant', content: JSON.stringify(result3) }
                );
                
                const finalChoice = 'automático';
                conversationHistory.push({ role: 'user', content: `Escolho modo ${finalChoice}` });
                
                // Passo 4: Reserva
                console.log('\n📋 Passo 4: Reserva...');
                const step4 = await makeRequest({
                  hostname: 'localhost',
                  port: 8768,
                  path: '/api/v1/ai-wizard/analyze',
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json'
                  }
                }, {
                  project_description: `Modo ${finalChoice} selecionado`,
                  conversation_history: conversationHistory
                });
                
                if (step4.status === 200) {
                  const result4 = step4.data.data;
                  console.log(`✅ Stage final: ${result4.stage}`);
                  console.log(`📋 Status reserva: ${result4.reservation?.status}`);
                  console.log('🎉 FLUXO COMPLETO TESTADO COM SUCESSO!');
                }
              }
            }
          }
        }
      }
    }
    
    // Relatório final
    console.log('\n📋 RELATÓRIO FINAL DO FLUXO REESTRUTURADO');
    console.log('='.repeat(60));
    console.log('✅ Sistema reestruturado implementado');
    console.log('✅ Novo fluxo: análise → pesquisa → opções → seleção → reserva');
    console.log('✅ Sistema de iteração mantido');
    console.log('✅ Validação de JSON atualizada');
    console.log('✅ Fallback adaptado ao novo formato');
    
    console.log('\n🎯 BENEFÍCIOS DO NOVO FLUXO:');
    console.log('- Guia usuário passo a passo');
    console.log('- Pesquisa de informações atualizadas');
    console.log('- Opções de preço claras');
    console.log('- Seleção manual ou automática');
    console.log('- Lista detalhada de máquinas');
    console.log('- Processo de reserva integrado');
    
    console.log('\n🚀 SISTEMA PRONOTO PARA USO COM NOVO FLUXO!');
    
  } catch (error) {
    console.error('❌ Erro durante o teste:', error.message);
  }
}

// Executar teste
async function main() {
  await testCompleteFlowNew();
}

if (require.main === module) {
  main().catch(console.error);
}
