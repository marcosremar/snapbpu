const http = require('http');
const fs = require('fs');

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

// Teste completo do fluxo do AI Wizard via API
async function testCompleteFlow() {
  console.log('🚀 TESTE COMPLETO DO FLUXO AI WIZARD\n');
  
  const baseURL = 'http://localhost:8768';
  
  try {
    // ETAPA 1: Verificar saúde do servidor
    console.log('📍 ETAPA 1: Verificando servidor...');
    const healthResponse = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/health',
      method: 'GET'
    });
    
    if (healthResponse.status === 200) {
      console.log('✅ Servidor saudável');
    } else {
      console.log('❌ Servidor não saudável');
      return;
    }
    
    // ETAPA 2: Testar cenários completos
    console.log('\n🤖 ETAPA 2: Testando cenários completos...');
    
    const scenarios = [
      {
        name: 'Fine-tuning LLaMA 7B',
        description: 'Quero fazer fine-tuning de LLaMA 7B com LoRA para deploy em produção',
        expectedKeywords: ['training', 'RTX_4090', 'RTX_3090', 'A6000', 'QLoRA'],
        expectedWorkload: 'training'
      },
      {
        name: 'API Stable Diffusion XL',
        description: 'API de Stable Diffusion XL para alta qualidade e múltiplos usuários',
        expectedKeywords: ['inference', 'RTX_4070_Ti', 'RTX_4080', 'RTX_3090', '16GB'],
        expectedWorkload: 'inference'
      },
      {
        name: 'LLM 70B Produção',
        description: 'LLM 70B para produção com vLLM serving',
        expectedKeywords: ['inference', 'A100', 'H100', '80GB', 'multi-GPU'],
        expectedWorkload: 'inference'
      },
      {
        name: 'Treinamento YOLOv8',
        description: 'Treinamento de modelo YOLOv8 para detecção de objetos',
        expectedKeywords: ['training', 'RTX_4090', 'A6000', 'RTX_4080', '16GB'],
        expectedWorkload: 'training'
      },
      {
        name: 'Inferência LLaMA 13B',
        description: 'Quero rodar LLaMA 13B para inferência em produção',
        expectedKeywords: ['inference', 'RTX_4090', 'A6000', 'RTX_3090', '24GB'],
        expectedWorkload: 'inference'
      }
    ];
    
    let totalTests = scenarios.length;
    let passedTests = 0;
    const results = [];
    
    for (let i = 0; i < scenarios.length; i++) {
      const scenario = scenarios[i];
      console.log(`\n🧪 Cenário ${i + 1}/${totalTests}: ${scenario.name}`);
      console.log(`📝 Descrição: ${scenario.description}`);
      
      const startTime = Date.now();
      
      // Fazer requisição para o AI Wizard
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
        console.log(`⏱️ Tempo de resposta: ${responseTime}ms`);
        console.log(`🤖 Modelo: ${response.data.model_used}`);
        
        const recommendation = response.data.recommendation;
        
        // Verificar workload type
        const workloadCorrect = recommendation.workload_type === scenario.expectedWorkload;
        console.log(`💼 Workload: ${recommendation.workload_type} ${workloadCorrect ? '✅' : '❌'}`);
        
        // Verificar palavras-chave
        let foundKeywords = 0;
        const recommendationString = JSON.stringify(recommendation).toLowerCase();
        
        for (const keyword of scenario.expectedKeywords) {
          if (recommendationString.includes(keyword.toLowerCase())) {
            foundKeywords++;
            console.log(`✅ Encontrado: ${keyword}`);
          } else {
            console.log(`❌ Não encontrado: ${keyword}`);
          }
        }
        
        const score = (foundKeywords / scenario.expectedKeywords.length) * 100;
        console.log(`📊 Score: ${score.toFixed(1)}% (${foundKeywords}/${scenario.expectedKeywords.length})`);
        
        // Verificar se pede mais informações
        if (response.data.needs_more_info) {
          console.log('❓ Pediu mais informações');
        }
        
        // Salvar resultado
        const result = {
          scenario: scenario.name,
          description: scenario.description,
          status: response.status,
          responseTime,
          modelUsed: response.data.model_used,
          workloadType: recommendation.workload_type,
          score,
          keywordsFound: foundKeywords,
          totalKeywords: scenario.expectedKeywords.length,
          passed: score >= 70
        };
        
        results.push(result);
        
        if (score >= 70) {
          console.log('🎉 Cenário aprovado!');
          passedTests++;
        } else {
          console.log('⚠️ Cenário reprovado');
        }
        
        // Exibir detalhes das recomendações
        if (recommendation.min_vram_gb) {
          console.log(`🎮 VRAM mínima: ${recommendation.min_vram_gb}GB`);
        }
        
        if (recommendation.recommended_gpus && recommendation.recommended_gpus.length > 0) {
          console.log(`🎮 GPUs: ${recommendation.recommended_gpus.join(', ')}`);
        }
        
        if (recommendation.explanation) {
          console.log(`💡 Explicação: ${recommendation.explanation.substring(0, 100)}...`);
        }
        
      } else {
        console.log(`❌ Status: ${response.status}`);
        console.log(`❌ Erro: ${response.data.detail || 'Erro desconhecido'}`);
        
        results.push({
          scenario: scenario.name,
          description: scenario.description,
          status: response.status,
          passed: false,
          error: response.data.detail || 'Erro desconhecido'
        });
      }
    }
    
    // ETAPA 3: Testar casos limite
    console.log('\n🔍 ETAPA 3: Testando casos limite...');
    
    const edgeCases = [
      { name: 'Mensagem vazia', description: '' },
      { name: 'Mensagem curta', description: 'oi' },
      { name: 'Mensagem ambígua', description: 'quero uma gpu' },
      { name: 'Mensagem muito específica', description: 'Quero fazer fine-tuning de LLaMA 7B com QLoRA, batch size 32, learning rate 1e-4, por 100 epochs' }
    ];
    
    for (const edgeCase of edgeCases) {
      console.log(`\n🧪 Testando: ${edgeCase.name}`);
      
      const response = await makeRequest({
        hostname: 'localhost',
        port: 8768,
        path: '/api/v1/ai-wizard/analyze',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }, {
        project_description: edgeCase.description,
        conversation_history: null
      });
      
      if (response.status === 200) {
        console.log('✅ Respondeu corretamente');
        if (response.data.needs_more_info) {
          console.log('💬 Pediu mais informações (comportamento esperado)');
        }
      } else {
        console.log(`❌ Erro: ${response.status}`);
      }
    }
    
    // ETAPA 4: Testar conversação com histórico
    console.log('\n💬 ETAPA 4: Testando conversação com histórico...');
    
    const conversationTest = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/api/v1/ai-wizard/analyze',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    }, {
      project_description: 'Quero fazer fine-tuning de LLaMA 7B com LoRA',
      conversation_history: [
        { role: 'user', content: 'Estou procurando uma GPU para treinamento' },
        { role: 'assistant', content: 'Para treinamento, recomendo GPUs com mais VRAM' },
        { role: 'user', content: 'Qual seria a melhor opção custo-benefício?' }
      ]
    });
    
    if (conversationTest.status === 200 && conversationTest.data.success) {
      console.log('✅ Conversação com histórico funcionou');
      console.log(`🤖 Modelo: ${conversationTest.data.model_used}`);
      
      // Verificar se considera o histórico
      const recommendation = conversationTest.data.recommendation;
      if (recommendation.workload_type === 'training') {
        console.log('✅ Considerou histórico (identificou treinamento)');
      }
    } else {
      console.log('❌ Conversação com histórico falhou');
    }
    
    // ETAPA 5: Análise de qualidade
    console.log('\n📊 ETAPA 5: Análise de qualidade das respostas...');
    
    // Verificar se está usando LLM real ou fallback
    const llmResponses = results.filter(r => r.modelUsed);
    const usingFallback = llmResponses.every(r => r.modelUsed === 'fallback');
    
    if (usingFallback) {
      console.log('⚠️ Sistema está usando fallback heurístico');
      console.log('💡 Para usar LLM real, configure OPENROUTER_API_KEY válida');
    } else {
      console.log('✅ Sistema está usando LLM real');
    }
    
    // Verificar performance
    const avgResponseTime = results.reduce((sum, r) => sum + (r.responseTime || 0), 0) / results.length;
    console.log(`⏱️ Tempo médio de resposta: ${avgResponseTime.toFixed(1)}ms`);
    
    // Verificar consistência
    const workloads = results.map(r => r.workloadType).filter(Boolean);
    const uniqueWorkloads = [...new Set(workloads)];
    console.log(`🎯 Workloads detectados: ${uniqueWorkloads.join(', ')}`);
    
    // Relatório final
    console.log('\n📋 RELATÓRIO FINAL');
    console.log('='.repeat(60));
    console.log(`✅ Testes executados: ${totalTests}`);
    console.log(`✅ Testes aprovados: ${passedTests}`);
    console.log(`📊 Taxa de sucesso: ${((passedTests / totalTests) * 100).toFixed(1)}%`);
    console.log(`⏱️ Tempo médio resposta: ${avgResponseTime.toFixed(1)}ms`);
    console.log(`🤖 Modelo usado: ${usingFallback ? 'Fallback heurístico' : 'LLM real'}`);
    
    if (passedTests === totalTests) {
      console.log('🎉 TODOS OS TESTES APROVADOS!');
      console.log('💡 AI Wizard está funcionando perfeitamente.');
    } else if (passedTests >= totalTests * 0.8) {
      console.log('✅ AI Wizard está funcionando bem.');
    } else {
      console.log('⚠️ AI Wizard precisa de melhorias.');
    }
    
    // Salvar relatório detalhado
    const report = {
      timestamp: new Date().toISOString(),
      testType: 'Complete Flow API Test',
      summary: {
        totalTests,
        passedTests,
        successRate: (passedTests / totalTests) * 100,
        avgResponseTime,
        modelUsed: usingFallback ? 'fallback' : 'llm'
      },
      scenarios: results,
      edgeCases: edgeCases.length,
      conversationTest: conversationTest.status === 200,
      recommendations: [
        usingFallback ? 'Configure OPENROUTER_API_KEY para usar LLM real' : 'LLM real está funcionando',
        avgResponseTime < 100 ? 'Performance excelente' : 'Performance aceitável',
        passedTests === totalTests ? 'Sistema pronto para produção' : 'Sistema precisa de ajustes'
      ]
    };
    
    fs.writeFileSync('/tmp/ai-wizard-complete-flow-report.json', JSON.stringify(report, null, 2));
    console.log('\n📋 Relatório detalhado: /tmp/ai-wizard-complete-flow-report.json');
    
    console.log('\n🎉 TESTE COMPLETO CONCLUÍDO!');
    
  } catch (error) {
    console.error('❌ Erro durante o teste:', error.message);
  }
}

// Verificar servidor
async function checkServer() {
  try {
    const response = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/health',
      method: 'GET'
    });
    return response.status === 200;
  } catch (error) {
    return false;
  }
}

// Executar
async function main() {
  const serverRunning = await checkServer();
  if (!serverRunning) {
    console.log('❌ Servidor não está rodando em http://localhost:8768');
    console.log('💡 Inicie o servidor: cd /home/ubuntu/dumont-cloud && python -m uvicorn src.main:app --host 0.0.0.0 --port 8768');
    process.exit(1);
  }
  
  await testCompleteFlow();
}

if (require.main === module) {
  main().catch(console.error);
}
