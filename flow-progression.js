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

// Testar progressão do fluxo completo
async function testFlowProgression() {
  console.log('🔄 TESTE DE PROGRESSÃO DO FLUXO COMPLETO\n');
  
  let conversationHistory = [];
  let currentStage = 'analysis';
  
  try {
    // ETAPA 1: ANÁLISE INICIAL
    console.log('📍 ETAPA 1: ANÁLISE INICIAL');
    console.log('Usuário: "Quero fazer um projeto de IA"');
    
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
    
    if (step1.status === 200 && step1.data.success) {
      const result1 = step1.data.data;
      console.log(`✅ Stage: ${result1.stage}`);
      console.log(`💬 Precisa mais info: ${result1.needs_more_info}`);
      
      if (result1.needs_more_info && result1.questions) {
        console.log('❓ Sistema perguntou:');
        result1.questions.forEach((q, idx) => {
          console.log(`   ${idx + 1}. ${q}`);
        });
        
        // Adicionar ao histórico
        conversationHistory.push(
          { role: 'user', content: 'Quero fazer um projeto de IA' },
          { role: 'assistant', content: JSON.stringify(result1) }
        );
        
        // ETAPA 2: RESPOSTA COMPLETA - DEVE PROGREDIR PARA RESEARCH
        console.log('\n📍 ETAPA 2: RESPOSTA COMPLETA');
        console.log('Usuário: "Fine-tuning de LLaMA 7B com LoRA para deploy em produção, orçamento de $100/hora"');
        
        const step2 = await makeRequest({
          hostname: 'localhost',
          port: 8768,
          path: '/api/v1/ai-wizard/analyze',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }, {
          project_description: 'Fine-tuning de LLaMA 7B com LoRA para deploy em produção, orçamento de $100/hora',
          conversation_history: conversationHistory
        });
        
        if (step2.status === 200 && step2.data.success) {
          const result2 = step2.data.data;
          console.log(`✅ Stage: ${result2.stage}`);
          
          if (result2.stage === 'research') {
            console.log('✅ Fluxo progrediu corretamente para RESEARCH');
            
            if (result2.research_results) {
              console.log('🔍 Resultados da pesquisa:');
              console.log(`   Findings: ${result2.research_results.findings?.substring(0, 80) || 'N/A'}...`);
              console.log(`   Benchmarks: ${result2.research_results.benchmarks?.substring(0, 80) || 'N/A'}...`);
            }
            
            // Adicionar ao histórico
            conversationHistory.push(
              { role: 'user', content: 'Fine-tuning de LLaMA 7B com LoRA para deploy em produção, orçamento de $100/hora' },
              { role: 'assistant', content: JSON.stringify(result2) }
            );
            
            // ETAPA 3: SOLICITAR OPÇÕES - DEVE PROGREDIR PARA OPTIONS
            console.log('\n📍 ETAPA 3: SOLICITAR OPÇÕES');
            console.log('Usuário: "Quero ver as opções de preço disponíveis"');
            
            const step3 = await makeRequest({
              hostname: 'localhost',
              port: 8768,
              path: '/api/v1/ai-wizard/analyze',
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              }
            }, {
              project_description: 'Quero ver as opções de preço disponíveis',
              conversation_history: conversationHistory
            });
            
            if (step3.status === 200 && step3.data.success) {
              const result3 = step3.data.data;
              console.log(`✅ Stage: ${result3.stage}`);
              
              if (result3.stage === 'options') {
                console.log('✅ Fluxo progrediu corretamente para OPTIONS');
                
                if (result3.price_options) {
                  console.log('💰 Opções de preço:');
                  result3.price_options.forEach((option, idx) => {
                    console.log(`   ${idx + 1}. ${option.tier}: ${option.price_per_hour}`);
                    console.log(`      GPUs: ${option.gpus.join(', ')}`);
                    console.log(`      Performance: ${option.performance?.substring(0, 50) || 'N/A'}...`);
                  });
                }
                
                // Adicionar ao histórico
                conversationHistory.push(
                  { role: 'user', content: 'Quero ver as opções de preço disponíveis' },
                  { role: 'assistant', content: JSON.stringify(result3) }
                );
                
                // ETAPA 4: ESCOLHER OPÇÃO - DEVE PROGREDIR PARA SELECTION
                console.log('\n📍 ETAPA 4: ESCOLHER OPÇÃO');
                console.log('Usuário: "Escolho a opção Intermediário"');
                
                const step4 = await makeRequest({
                  hostname: 'localhost',
                  port: 8768,
                  path: '/api/v1/ai-wizard/analyze',
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json'
                  }
                }, {
                  project_description: 'Escolho a opção Intermediário',
                  conversation_history: conversationHistory
                });
                
                if (step4.status === 200 && step4.data.success) {
                  const result4 = step4.data.data;
                  console.log(`✅ Stage: ${result4.stage}`);
                  
                  if (result4.stage === 'selection') {
                    console.log('✅ Fluxo progrediu corretamente para SELECTION');
                    console.log(`🎯 Modo de seleção: ${result4.selection_mode}`);
                    
                    if (result4.selection_mode === 'manual' && result4.machines) {
                      console.log('🖥️ Máquinas disponíveis:');
                      result4.machines.forEach((machine, idx) => {
                        console.log(`   ${idx + 1}. ${machine.name} - ${machine.gpu} - ${machine.price_per_hour}`);
                      });
                    }
                    
                    // Adicionar ao histórico
                    conversationHistory.push(
                      { role: 'user', content: 'Escolho a opção Intermediário' },
                      { role: 'assistant', content: JSON.stringify(result4) }
                    );
                    
                    // ETAPA 5: FINALIZAR SELEÇÃO - DEVE PROGREDIR PARA RESERVATION
                    console.log('\n📍 ETAPA 5: FINALIZAR SELEÇÃO');
                    console.log('Usuário: "Quero escolher automaticamente a melhor máquina"');
                    
                    const step5 = await makeRequest({
                      hostname: 'localhost',
                      port: 8768,
                      path: '/api/v1/ai-wizard/analyze',
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json'
                      }
                    }, {
                      project_description: 'Quero escolher automaticamente a melhor máquina',
                      conversation_history: conversationHistory
                    });
                    
                    if (step5.status === 200 && step5.data.success) {
                      const result5 = step5.data.data;
                      console.log(`✅ Stage final: ${result5.stage}`);
                      
                      if (result5.stage === 'reservation') {
                        console.log('✅ Fluxo progrediu corretamente para RESERVATION');
                        
                        if (result5.reservation) {
                          console.log(`📋 Status da reserva: ${result5.reservation.status}`);
                          console.log(`📝 Detalhes: ${result5.reservation.details?.substring(0, 80) || 'N/A'}...`);
                        }
                        
                        console.log('\n🎉 FLUXO COMPLETO FUNCIONANDO!');
                        console.log('✅ analysis → research → options → selection → reservation');
                        
                      } else {
                        console.log(`⚠️ Esperado reservation, mas recebeu: ${result5.stage}`);
                      }
                    } else {
                      console.log('❌ Erro na etapa 5');
                    }
                  } else {
                    console.log(`⚠️ Esperado selection, mas recebeu: ${result4.stage}`);
                  }
                } else {
                  console.log('❌ Erro na etapa 4');
                }
              } else {
                console.log(`⚠️ Esperado options, mas recebeu: ${result3.stage}`);
              }
            } else {
              console.log('❌ Erro na etapa 3');
            }
          } else {
            console.log(`⚠️ Esperado research, mas recebeu: ${result2.stage}`);
          }
        } else {
          console.log('❌ Erro na etapa 2');
        }
      } else {
        console.log('❌ Sistema não fez perguntas na análise inicial');
      }
    } else {
      console.log('❌ Erro na etapa 1');
    }
    
  } catch (error) {
    console.error('❌ Erro durante o teste:', error.message);
  }
}

// Executar teste
async function main() {
  await testFlowProgression();
}

if (require.main === module) {
  main().catch(console.error);
}
