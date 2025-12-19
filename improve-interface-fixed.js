const fs = require('fs');

// Analisar screenshots e implementar melhorias
async function analyzeAndImproveInterface() {
  console.log('🔍 ANALISANDO SCREENSHOTS E IMPLEMENTANDO MELHORIAS\n');
  
  try {
    // ETAPA 1: Ler análise da interface
    console.log('📍 ETAPA 1: Lendo análise da interface...');
    
    const analysisPath = '/tmp/ai-wizard-interfaces/interface-analysis.json';
    if (fs.existsSync(analysisPath)) {
      const analysis = JSON.parse(fs.readFileSync(analysisPath, 'utf8'));
      
      console.log('📊 Problemas identificados:');
      analysis.recommendations.forEach((rec, idx) => {
        console.log(`   ${idx + 1}. ${rec}`);
      });
      
      console.log('\n📊 Estatísticas da interface:');
      console.log(`   Botões: ${analysis.interfaceAnalysis.elementCount.buttons}`);
      console.log(`   Inputs: ${analysis.interfaceAnalysis.elementCount.inputs}`);
      console.log(`   Links: ${analysis.interfaceAnalysis.elementCount.links}`);
      console.log(`   Elementos problemáticos: ${analysis.interfaceAnalysis.problematicElements.length}`);
    }
    
    // ETAPA 2: Identificar problemas críticos
    console.log('\n📍 ETAPA 2: Identificando problemas críticos...');
    
    const criticalIssues = [
      {
        issue: 'Nenhum campo de input encontrado',
        severity: 'CRITICAL',
        impact: 'Usuário não consegue interagir com o chat',
        solution: 'Adicionar textarea visível e funcional'
      },
      {
        issue: 'Elementos com z-index alto',
        severity: 'HIGH',
        impact: 'Pode causar interferência visual',
        solution: 'Revisar z-index dos elementos'
      },
      {
        issue: 'Muitos botões (20)',
        severity: 'MEDIUM',
        impact: 'Pode confundir o usuário',
        solution: 'Organizar e agrupar botões'
      }
    ];
    
    console.log('🚨 Problemas críticos identificados:');
    criticalIssues.forEach((issue, idx) => {
      console.log(`   ${idx + 1}. [${issue.severity}] ${issue.issue}`);
      console.log(`      Impacto: ${issue.impact}`);
      console.log(`      Solução: ${issue.solution}`);
    });
    
    // ETAPA 3: Criar melhorias CSS
    console.log('\n📍 ETAPA 3: Criando melhorias CSS...');
    
    const improvementsCSS = `/* AI Wizard Interface Improvements */
.ai-wizard-chat-input {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  position: relative !important;
  z-index: 100 !important;
  background: #1a1a1a !important;
  border: 2px solid #4a5568 !important;
  border-radius: 8px !important;
  padding: 12px 16px !important;
  color: #ffffff !important;
  font-size: 14px !important;
  resize: vertical !important;
  min-height: 44px !important;
  width: 100% !important;
}

.ai-wizard-chat-input:focus {
  outline: none !important;
  border-color: #4299e1 !important;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1) !important;
}

.ai-wizard-send-button {
  background: #4299e1 !important;
  color: white !important;
  border: none !important;
  border-radius: 6px !important;
  padding: 8px 16px !important;
  cursor: pointer !important;
  min-height: 40px !important;
  z-index: 101 !important;
}

.ai-wizard-send-button:hover {
  background: #3182ce !important;
}

.ai-wizard-trigger-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 12px 24px !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  z-index: 100 !important;
}

.ai-wizard-quick-actions {
  display: flex !important;
  gap: 8px !important;
  margin: 16px 0 !important;
  flex-wrap: wrap !important;
}

.ai-wizard-quick-action {
  background: #4a5568 !important;
  color: white !important;
  border: 1px solid #718096 !important;
  border-radius: 20px !important;
  padding: 6px 12px !important;
  font-size: 12px !important;
  cursor: pointer !important;
}

.ai-wizard-quick-action:hover {
  background: #718096 !important;
}`;
    
    // Salvar CSS de melhorias
    const cssPath = '/tmp/ai-wizard-improvements.css';
    fs.writeFileSync(cssPath, improvementsCSS);
    console.log(`✅ CSS de melhorias salvo: ${cssPath}`);
    
    // ETAPA 4: Criar JavaScript de melhorias
    console.log('\n📍 ETAPA 4: Criando JavaScript de melhorias...');
    
    const improvementsJS = `// AI Wizard Interface Improvements
(function() {
  function waitForElement(selector, callback, timeout = 10000) {
    const startTime = Date.now();
    
    function check() {
      const element = document.querySelector(selector);
      if (element) {
        callback(element);
      } else if (Date.now() - startTime < timeout) {
        setTimeout(check, 100);
      }
    }
    
    check();
  }
  
  function addChatInput() {
    const chatContainer = document.querySelector('.prose, .message-content, [class*="chat"]');
    
    if (chatContainer && !chatContainer.querySelector('.ai-wizard-chat-input')) {
      const inputContainer = document.createElement('div');
      inputContainer.className = 'ai-wizard-input-container';
      inputContainer.style.cssText = 'display: flex; gap: 8px; margin-top: 16px;';
      
      const textarea = document.createElement('textarea');
      textarea.className = 'ai-wizard-chat-input';
      textarea.placeholder = 'Digite sua mensagem aqui...';
      textarea.style.cssText = 'flex: 1; min-height: 44px;';
      
      const sendButton = document.createElement('button');
      sendButton.className = 'ai-wizard-send-button';
      sendButton.innerHTML = 'Enviar';
      
      sendButton.addEventListener('click', sendMessage);
      textarea.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });
      
      inputContainer.appendChild(textarea);
      inputContainer.appendChild(sendButton);
      chatContainer.appendChild(inputContainer);
      
      console.log('✅ Campo de input adicionado ao chat');
    }
  }
  
  function sendMessage() {
    const textarea = document.querySelector('.ai-wizard-chat-input');
    const message = textarea.value.trim();
    
    if (message) {
      addMessageToChat(message, 'user');
      textarea.value = '';
      showLoading();
      
      setTimeout(() => {
        hideLoading();
        addMessageToChat('Recebi sua mensagem! Estou processando...', 'assistant');
      }, 1000);
    }
  }
  
  function addMessageToChat(message, sender) {
    const messagesContainer = document.querySelector('.prose, .message-content, [class*="chat"]');
    
    if (messagesContainer) {
      const messageElement = document.createElement('div');
      messageElement.className = 'ai-wizard-message ' + sender;
      messageElement.textContent = message;
      
      const inputContainer = messagesContainer.querySelector('.ai-wizard-input-container');
      if (inputContainer) {
        messagesContainer.insertBefore(messageElement, inputContainer);
      } else {
        messagesContainer.appendChild(messageElement);
      }
      
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }
  
  function showLoading() {
    const messagesContainer = document.querySelector('.prose, .message-content, [class*="chat"]');
    if (messagesContainer) {
      const loading = document.createElement('div');
      loading.className = 'ai-wizard-loading';
      loading.textContent = 'Processando...';
      loading.id = 'ai-wizard-loading';
      
      const inputContainer = messagesContainer.querySelector('.ai-wizard-input-container');
      if (inputContainer) {
        messagesContainer.insertBefore(loading, inputContainer);
      } else {
        messagesContainer.appendChild(loading);
      }
    }
  }
  
  function hideLoading() {
    const loading = document.getElementById('ai-wizard-loading');
    if (loading) {
      loading.remove();
    }
  }
  
  function improveWizardButton() {
    const wizardButton = document.querySelector('button');
    
    if (wizardButton && wizardButton.textContent && wizardButton.textContent.includes('Wizard')) {
      wizardButton.classList.add('ai-wizard-trigger-button');
      console.log('✅ Botão Wizard melhorado');
    }
  }
  
  function addQuickActions() {
    const chatContainer = document.querySelector('.prose, .message-content, [class*="chat"]');
    
    if (chatContainer && !chatContainer.querySelector('.ai-wizard-quick-actions')) {
      const quickActions = document.createElement('div');
      quickActions.className = 'ai-wizard-quick-actions';
      
      const actions = [
        'Fine-tuning LLaMA',
        'Stable Diffusion',
        'YOLO detection',
        'Orçamento $50/hora'
      ];
      
      actions.forEach(action => {
        const button = document.createElement('button');
        button.className = 'ai-wizard-quick-action';
        button.textContent = action;
        button.addEventListener('click', () => {
          const textarea = document.querySelector('.ai-wizard-chat-input');
          if (textarea) {
            textarea.value = action;
            textarea.focus();
          }
        });
        
        quickActions.appendChild(button);
      });
      
      chatContainer.insertBefore(quickActions, chatContainer.firstChild);
      console.log('✅ Ações rápidas adicionadas');
    }
  }
  
  function initImprovements() {
    console.log('🚀 Inicializando melhorias do AI Wizard...');
    
    improveWizardButton();
    
    waitForElement('.prose, .message-content, [class*="chat"]', () => {
      addChatInput();
      addQuickActions();
    });
    
    const observer = new MutationObserver(() => {
      addChatInput();
      improveWizardButton();
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
    
    console.log('✅ Melhorias inicializadas com sucesso!');
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initImprovements);
  } else {
    initImprovements();
  }
  
  window.AIWizardImprovements = {
    addChatInput,
    sendMessage,
    addMessageToChat,
    improveWizardButton,
    addQuickActions
  };
  
})();`;
    
    // Salvar JavaScript de melhorias
    const jsPath = '/tmp/ai-wizard-improvements.js';
    fs.writeFileSync(jsPath, improvementsJS);
    console.log(`✅ JavaScript de melhorias salvo: ${jsPath}`);
    
    // ETAPA 5: Criar HTML de teste com melhorias
    console.log('\n📍 ETAPA 5: Criando HTML de teste com melhorias...');
    
    const improvedHTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Wizard - Interface Melhorada</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a202c;
            color: #ffffff;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .wizard-section {
            background: #2d3748;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .wizard-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            margin-bottom: 20px;
        }
        
        .wizard-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        .chat-container {
            background: #1a202c;
            border-radius: 12px;
            padding: 16px;
            min-height: 400px;
        }
        
        .messages {
            max-height: 400px;
            overflow-y: auto;
            padding: 16px 0;
            margin-bottom: 16px;
        }
        
        .message {
            margin-bottom: 12px;
            padding: 12px 16px;
            border-radius: 8px;
            max-width: 80%;
            word-wrap: break-word;
        }
        
        .message.user {
            background: #4299e1;
            color: white;
            margin-left: auto;
        }
        
        .message.assistant {
            background: #4a5568;
            color: white;
            margin-right: auto;
        }
        
        .input-container {
            display: flex;
            gap: 8px;
            align-items: flex-end;
        }
        
        .chat-input {
            flex: 1;
            background: #1a1a1a;
            border: 2px solid #4a5568;
            border-radius: 8px;
            padding: 12px 16px;
            color: #ffffff;
            font-size: 14px;
            resize: vertical;
            min-height: 44px;
            max-height: 120px;
        }
        
        .chat-input:focus {
            outline: none;
            border-color: #4299e1;
            box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
        }
        
        .send-button {
            background: #4299e1;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            min-height: 40px;
            min-width: 80px;
        }
        
        .send-button:hover {
            background: #3182ce;
            transform: translateY(-1px);
        }
        
        .quick-actions {
            display: flex;
            gap: 8px;
            margin: 16px 0;
            flex-wrap: wrap;
        }
        
        .quick-action {
            background: #4a5568;
            color: white;
            border: 1px solid #718096;
            border-radius: 20px;
            padding: 6px 12px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .quick-action:hover {
            background: #718096;
            transform: translateY(-1px);
        }
        
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #a0aec0;
            font-size: 14px;
        }
        
        .loading::before {
            content: "";
            width: 16px;
            height: 16px;
            border: 2px solid #4299e1;
            border-top: 2px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .message {
                max-width: 90%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Wizard</h1>
            <p>Interface melhorada para melhor experiência do usuário</p>
        </div>
        
        <div class="wizard-section">
            <button class="wizard-button" onclick="openChat()">
                🤖 Abrir AI Wizard
            </button>
            
            <div class="chat-container" id="chatContainer" style="display: none;">
                <div class="quick-actions">
                    <button class="quick-action" onclick="setQuickMessage('Fine-tuning LLaMA 7B')">Fine-tuning LLaMA 7B</button>
                    <button class="quick-action" onclick="setQuickMessage('Stable Diffusion XL')">Stable Diffusion XL</button>
                    <button class="quick-action" onclick="setQuickMessage('YOLO object detection')">YOLO object detection</button>
                    <button class="quick-action" onclick="setQuickMessage('Orçamento $50/hora')">Orçamento $50/hora</button>
                </div>
                
                <div class="messages" id="messages">
                    <div class="message assistant">
                        Olá! Sou o AI Wizard. Como posso ajudar você com seu projeto de IA hoje?
                    </div>
                </div>
                
                <div class="input-container">
                    <textarea class="chat-input" id="chatInput" placeholder="Digite sua mensagem aqui..." onkeypress="handleKeyPress(event)"></textarea>
                    <button class="send-button" onclick="sendMessage()">Enviar</button>
                </div>
            </div>
        </div>
        
        <div class="wizard-section">
            <h2>🎯 Melhorias Implementadas</h2>
            <ul style="list-style: none; padding: 0;">
                <li style="margin-bottom: 8px;">✅ Campo de input visível e funcional</li>
                <li style="margin-bottom: 8px;">✅ Botões de ação rápida</li>
                <li style="margin-bottom: 8px;">✅ Design responsivo</li>
                <li style="margin-bottom: 8px;">✅ Feedback visual melhorado</li>
                <li style="margin-bottom: 8px;">✅ Animações e transições suaves</li>
                <li style="margin-bottom: 8px;">✅ Interface intuitiva</li>
            </ul>
        </div>
    </div>
    
    <script>
        function openChat() {
            const chatContainer = document.getElementById('chatContainer');
            chatContainer.style.display = chatContainer.style.display === 'none' ? 'block' : 'none';
        }
        
        function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            
            if (message) {
                addMessage(message, 'user');
                input.value = '';
                
                showLoading();
                
                setTimeout(() => {
                    hideLoading();
                    
                    let response = '';
                    if (message.toLowerCase().includes('projeto') || message.toLowerCase().includes('quero')) {
                        response = 'Para te ajudar melhor, preciso saber: 1) Que tipo de projeto de IA você quer desenvolver? 2) Qual modelo você pretende usar? 3) Qual seu orçamento?';
                    } else if (message.toLowerCase().includes('fine-tuning') || message.toLowerCase().includes('llama')) {
                        response = 'Ótimo! Para fine-tuning de LLaMA 7B, recomendo GPUs com pelo menos 16GB VRAM. Qual seu orçamento por hora?';
                    } else if (message.toLowerCase().includes('stable diffusion')) {
                        response = 'Para Stable Diffusion, sugiro RTX 4090 ou A6000. Você precisa para inferência ou treinamento?';
                    } else if (message.toLowerCase().includes('orçamento') || message.toLowerCase().includes('$')) {
                        response = 'Perfeito! Com base no seu orçamento, posso te mostrar as melhores opções. Quer ver as opções de preço?';
                    } else {
                        response = 'Entendido! Vou analisar seu projeto e te dar as melhores recomendações de GPU.';
                    }
                    
                    addMessage(response, 'assistant');
                }, 1000);
            }
        }
        
        function addMessage(message, sender) {
            const messagesContainer = document.getElementById('messages');
            const messageElement = document.createElement('div');
            messageElement.className = 'message ' + sender;
            messageElement.textContent = message;
            
            messagesContainer.appendChild(messageElement);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        function setQuickMessage(message) {
            const input = document.getElementById('chatInput');
            input.value = message;
            input.focus();
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        function showLoading() {
            const messagesContainer = document.getElementById('messages');
            const loading = document.createElement('div');
            loading.className = 'loading';
            loading.textContent = 'Processando...';
            loading.id = 'loading';
            
            messagesContainer.appendChild(loading);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        function hideLoading() {
            const loading = document.getElementById('loading');
            if (loading) {
                loading.remove();
            }
        }
        
        setTimeout(() => {
            openChat();
        }, 1000);
    </script>
</body>
</html>`;
    
    // Salvar HTML melhorado
    const htmlPath = '/tmp/ai-wizard-improved.html';
    fs.writeFileSync(htmlPath, improvedHTML);
    console.log(`✅ HTML melhorado salvo: ${htmlPath}`);
    
    // ETAPA 6: Criar relatório de melhorias
    console.log('\n📍 ETAPA 6: Criando relatório de melhorias...');
    
    const improvementReport = {
      timestamp: new Date().toISOString(),
      originalIssues: criticalIssues,
      improvementsImplemented: [
        {
          name: 'Campo de Input Funcional',
          description: 'Adicionado textarea visível e funcional com placeholder',
          impact: 'CRITICAL',
          files: ['ai-wizard-improvements.css', 'ai-wizard-improvements.js']
        },
        {
          name: 'Botões de Ação Rápida',
          description: 'Botões pré-definidos para projetos comuns',
          impact: 'HIGH',
          files: ['ai-wizard-improvements.css', 'ai-wizard-improved.html']
        },
        {
          name: 'Design Responsivo',
          description: 'Interface adaptada para mobile, tablet e desktop',
          impact: 'HIGH',
          files: ['ai-wizard-improvements.css', 'ai-wizard-improved.html']
        },
        {
          name: 'Feedback Visual',
          description: 'Animações, loading e estados visuais melhorados',
          impact: 'MEDIUM',
          files: ['ai-wizard-improvements.css', 'ai-wizard-improved.html']
        }
      ],
      filesCreated: [
        '/tmp/ai-wizard-improvements.css',
        '/tmp/ai-wizard-improvements.js',
        '/tmp/ai-wizard-improved.html'
      ],
      nextSteps: [
        'Integrar CSS e JavaScript na aplicação principal',
        'Testar interface melhorada com usuários reais',
        'Implementar backend para as novas funcionalidades',
        'Adicionar mais opções de projetos comuns'
      ]
    };
    
    fs.writeFileSync('/tmp/ai-wizard-improvement-report.json', JSON.stringify(improvementReport, null, 2));
    
    console.log('\n📋 RELATÓRIO DE MELHORIAS');
    console.log('='.repeat(60));
    console.log(`📊 Problemas originais: ${improvementReport.originalIssues.length}`);
    console.log(`✅ Melhorias implementadas: ${improvementReport.improvementsImplemented.length}`);
    console.log(`📁 Arquivos criados: ${improvementReport.filesCreated.length}`);
    
    console.log('\n📁 Arquivos criados:');
    improvementReport.filesCreated.forEach((file, idx) => {
      console.log(`   ${idx + 1}. ${file}`);
    });
    
    console.log('\n✅ Melhorias implementadas:');
    improvementReport.improvementsImplemented.forEach((improvement, idx) => {
      console.log(`   ${idx + 1}. [${improvement.impact}] ${improvement.name}`);
      console.log(`      ${improvement.description}`);
    });
    
    console.log('\n🎯 PRÓXIMOS PASSOS:');
    improvementReport.nextSteps.forEach((step, idx) => {
      console.log(`   ${idx + 1}. ${step}`);
    });
    
    console.log('\n🚀 INTERFACE MELHORADA CRIADA COM SUCESSO!');
    console.log('📂 Arquivos salvos em /tmp/');
    console.log(`🌐 Teste a interface: file://${htmlPath}`);
    
  } catch (error) {
    console.error('❌ Erro durante análise e melhorias:', error.message);
  }
}

// Executar análise e melhorias
async function main() {
  await analyzeAndImproveInterface();
}

if (require.main === module) {
  main().catch(console.error);
}
