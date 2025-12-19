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

// Testes da API do AI Wizard
async function testAIWizardAPI() {
  console.log('🚀 Iniciando testes do AI Wizard API em modo headless...\n');
  
  const baseURL = 'http://localhost:8768';
  
  try {
    // Teste 1: Verificar saúde do servidor
    console.log('📍 Teste 1: Verificando saúde do servidor...');
    const healthResponse = await makeRequest({
      hostname: 'localhost',
      port: 8768,
      path: '/health',
      method: 'GET'
    });
    
    if (healthResponse.status === 200) {
      console.log('✅ Servidor está saudável');
    } else {
      console.log('❌ Servidor não está saudável:', healthResponse.status);
      return;
    }
    
    // Teste 2: Testar diferentes cenários do AI Wizard
    console.log('\n🤖 Teste 2: Testando API do AI Wizard...');
    
    const testCases = [
      {
        name: 'Fine-tuning LLaMA 7B',
        description: 'Quero fazer fine-tuning de LLaMA 7B com LoRA',
        expected: ['training', 'RTX_4090', 'RTX_3090', 'A6000', 'QLoRA']
      },
      {
        name: 'Inferência LLaMA 13B',
        description: 'Quero rodar LLaMA 13B para inferência',
        expected: ['inference', 'RTX_4090', 'A6000', 'RTX_3090', '24GB']
      },
      {
        name: 'API Stable Diffusion',
        description: 'API de Stable Diffusion XL',
        expected: ['inference', 'RTX_4070_Ti', 'RTX_4080', 'RTX_3090', '12GB']
      },
      {
        name: 'LLM 70B Produção',
        description: 'LLM 70B para produção com vLLM',
        expected: ['inference', 'A100', 'H100', '80GB', 'multi-GPU']
      },
      {
        name: 'Treinamento YOLOv8',
        description: 'Treinamento YOLOv8',
        expected: ['training', 'RTX_4090', 'A6000', 'RTX_4080', '16GB']
      }
    ];
    
    let passedTests = 0;
    let totalTests = testCases.length;
    
    for (let i = 0; i < testCases.length; i++) {
      const testCase = testCases[i];
      console.log(`\n🧪 Teste ${i + 1}/${totalTests}: ${testCase.name}`);
      console.log(`📝 Descrição: ${testCase.description}`);
      
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
        project_description: testCase.description,
        conversation_history: null
      });
      
      const responseTime = Date.now() - startTime;
      
      if (response.status === 200 && response.data.success) {
        console.log(`✅ Status: ${response.status}`);
        console.log(`⏱️ Tempo de resposta: ${responseTime}ms`);
        
        const recommendation = response.data.recommendation;
        
        // Verificar palavras-chave esperadas
        let foundKeywords = 0;
        const recommendationString = JSON.stringify(recommendation).toLowerCase();
        
        for (const keyword of testCase.expected) {
          if (recommendationString.includes(keyword.toLowerCase())) {
            foundKeywords++;
            console.log(`✅ Palavra-chave encontrada: ${keyword}`);
          } else {
            console.log(`⚠️ Palavra-chave não encontrada: ${keyword}`);
          }
        }
        
        const score = (foundKeywords / testCase.expected.length) * 100;
        console.log(`📊 Score: ${score.toFixed(1)}% (${foundKeywords}/${testCase.expected.length})`);
        
        if (score >= 70) {
          console.log('🎉 Teste aprovado!');
          passedTests++;
        } else {
          console.log('⚠️ Teste parcialmente aprovado');
        }
        
        // Exibir detalhes da recomendação
        if (recommendation.workload_type) {
          console.log(`💼 Tipo de workload: ${recommendation.workload_type}`);
        }
        
        if (recommendation.gpu_options && recommendation.gpu_options.length > 0) {
          console.log(`🎮 GPUs recomendadas: ${recommendation.gpu_options.map(g => g.gpu).join(', ')}`);
        }
        
        if (recommendation.model_info) {
          console.log(`📋 Modelo: ${recommendation.model_info.name || 'N/A'}`);
        }
        
      } else {
        console.log(`❌ Status: ${response.status}`);
        console.log(`❌ Erro: ${response.data.detail || 'Erro desconhecido'}`);
      }
    }
    
    // Teste 3: Testar casos limite
    console.log('\n🔍 Teste 3: Testando casos limite...');
    
    const edgeCases = [
      {
        name: 'Mensagem vazia',
        description: '',
        expectError: false
      },
      {
        name: 'Mensagem curta',
        description: 'oi',
        expectError: false
      },
      {
        name: 'Mensagem muito longa',
        description: 'Quero '.repeat(1000) + 'treinar um modelo',
        expectError: false
      }
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
    
    // Teste 4: Testar conversação com histórico
    console.log('\n💬 Teste 4: Testando conversação com histórico...');
    
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
        { role: 'assistant', content: 'Para treinamento, recomendo GPUs com mais VRAM' }
      ]
    });
    
    if (conversationTest.status === 200 && conversationTest.data.success) {
      console.log('✅ Conversação com histórico funcionou');
      console.log(`📊 Modelo usado: ${conversationTest.data.model_used}`);
    } else {
      console.log('❌ Conversação com histórico falhou');
    }
    
    // Resumo final
    console.log('\n📋 RESUMO DOS TESTES');
    console.log('='.repeat(50));
    console.log(`✅ Testes aprovados: ${passedTests}/${totalTests}`);
    console.log(`📊 Taxa de sucesso: ${((passedTests / totalTests) * 100).toFixed(1)}%`);
    
    if (passedTests === totalTests) {
      console.log('🎉 Todos os testes passaram! AI Wizard está funcionando perfeitamente.');
    } else if (passedTests >= totalTests * 0.8) {
      console.log('✅ AI Wizard está funcionando bem com algumas limitações.');
    } else {
      console.log('⚠️ AI Wizard precisa de melhorias.');
    }
    
    // Salvar resultados em arquivo
    const results = {
      timestamp: new Date().toISOString(),
      totalTests,
      passedTests,
      successRate: (passedTests / totalTests) * 100,
      testResults: testCases.map(testCase => ({
        name: testCase.name,
        description: testCase.description,
        expected: testCase.expected,
        status: 'tested'
      }))
    };
    
    fs.writeFileSync('/tmp/ai-wizard-test-results.json', JSON.stringify(results, null, 2));
    console.log('\n📁 Resultados salvos em /tmp/ai-wizard-test-results.json');
    
  } catch (error) {
    console.error('❌ Erro durante os testes:', error.message);
    
    // Tentar verificar se o servidor está rodando
    try {
      await makeRequest({
        hostname: 'localhost',
        port: 8768,
        path: '/health',
        method: 'GET'
      });
    } catch (e) {
      console.log('❌ Servidor não está acessível em http://localhost:8768');
      console.log('💡 Certifique-se de que o backend está rodando:');
      console.log('   cd /home/ubuntu/dumont-cloud && python -m uvicorn src.main:app --host 0.0.0.0 --port 8768');
    }
  }
}

// Verificar se servidor está rodando
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

// Executar testes
async function main() {
  console.log('🔍 Verificando se o servidor backend está rodando...');
  
  const serverRunning = await checkServer();
  if (!serverRunning) {
    console.log('❌ Servidor backend não está rodando em http://localhost:8768');
    console.log('💡 Por favor, inicie o servidor backend:');
    console.log('   cd /home/ubuntu/dumont-cloud && python -m uvicorn src.main:app --host 0.0.0.0 --port 8768');
    process.exit(1);
  }
  
  console.log('✅ Servidor backend está rodando');
  
  await testAIWizardAPI();
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { testAIWizardAPI };
