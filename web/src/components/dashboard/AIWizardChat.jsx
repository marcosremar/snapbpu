import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Search, Send, Bot, User, Loader2, Sparkles, Zap } from 'lucide-react';
import GPUWizardDisplay from './GPUWizardDisplay';

const API_BASE = import.meta.env.VITE_API_URL || '';

const AIWizardChat = ({ onRecommendation, onSearchWithFilters, compact = false }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState(null);

  const getToken = () => localStorage.getItem('auth_token');

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/v1/ai-wizard/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify({
          project_description: userMessage,
          conversation_history: messages
        })
      });

      const data = await response.json();

      if (data.needs_more_info) {
        const questionsText = data.questions.join('\n\n');
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Preciso de mais algumas informações para fazer uma recomendação precisa:\n\n${questionsText}`
        }]);
      } else {
        const stage = data.stage || (data.recommendation ? 'recommendation' : 'unknown');
        let messageContent = data.explanation || (data.recommendation?.explanation) || 'Processamento concluído.';

        const msgPayload = {
          role: 'assistant',
          content: messageContent,
          stage: stage,
          data: data,
          recommendation: data.recommendation,
          showCards: true
        };

        setMessages(prev => [...prev, msgPayload]);
        setRecommendation(data.recommendation);

        if (data.recommendation && onRecommendation) {
          onRecommendation(data.recommendation);
        }
      }
    } catch (error) {
      console.error('AI Wizard error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Desculpe, houve um erro ao processar sua solicitação. Por favor, tente novamente.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const applyRecommendation = (gpuOption = null) => {
    if (recommendation && onSearchWithFilters) {
      if (gpuOption) {
        onSearchWithFilters({
          gpu_name: gpuOption.gpu,
          min_gpu_ram: parseInt(gpuOption.vram) || 8
        });
      } else if (recommendation.gpu_options && recommendation.gpu_options.length > 0) {
        const recOption = recommendation.gpu_options.find(o => o.tier === 'recomendada') || recommendation.gpu_options[1];
        onSearchWithFilters({
          gpu_name: recOption.gpu,
          min_gpu_ram: parseInt(recOption.vram) || 8
        });
      } else if (recommendation.recommended_gpus) {
        onSearchWithFilters({
          gpu_name: recommendation.recommended_gpus[0] || 'any',
          min_gpu_ram: recommendation.min_vram_gb,
          tier: recommendation.tier_suggestion
        });
      }
    }
  };

  // Stage renderers
  const renderResearchStage = (data) => (
    <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-3 text-xs space-y-2">
      <div className="font-semibold text-brand-400">Resultados da Pesquisa:</div>
      {data.research_results?.findings && (
        <div><span className="text-gray-400">Descobertas:</span> {data.research_results.findings}</div>
      )}
      {data.research_results?.benchmarks && (
        <div><span className="text-gray-400">Benchmarks:</span> {data.research_results.benchmarks}</div>
      )}
      {data.research_results?.prices && (
        <div><span className="text-gray-400">Preços:</span> {data.research_results.prices}</div>
      )}
    </div>
  );

  const renderOptionsStage = (data) => (
    <div className="space-y-2">
      <div className="font-semibold text-brand-400 text-xs mb-2">Opções de Preço Encontradas:</div>
      <div className="grid grid-cols-1 gap-2">
        {data.price_options?.map((opt, idx) => (
          <div key={idx} className="bg-gray-100 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-brand-500/50 transition-colors">
            <div className="flex justify-between items-start mb-1">
              <span className="font-bold text-gray-900 dark:text-white text-sm">{opt.tier}</span>
              <span className="text-brand-400 font-mono text-xs">{opt.price_per_hour}</span>
            </div>
            <div className="text-gray-400 text-xs mb-1">{opt.gpus?.join(', ')}</div>
            <div className="text-gray-500 text-[10px]">{opt.performance}</div>
            <button
              onClick={() => {
                setInputValue(`Escolher opção ${opt.tier}`);
                sendMessage();
              }}
              className="mt-2 w-full py-1 text-[10px] bg-brand-600/20 text-brand-400 rounded hover:bg-brand-600/30 transition-colors"
            >
              Selecionar {opt.tier}
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  const renderSelectionStage = (data) => (
    <div className="space-y-2">
      <div className="font-semibold text-brand-400 text-xs mb-2">Máquinas Disponíveis:</div>
      <div className="grid grid-cols-1 gap-2">
        {data.machines?.map((machine, idx) => (
          <div key={idx} className="bg-gray-100 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-brand-500/50 transition-colors">
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-gray-900 dark:text-white text-xs">{machine.gpu}</span>
              <span className="text-brand-400 font-mono text-xs">{machine.price_per_hour}</span>
            </div>
            <div className="flex justify-between text-[10px] text-gray-500 mb-2">
              <span>{machine.vram}</span>
              <span>{machine.location}</span>
            </div>
            <button
              onClick={() => {
                setInputValue(`Reservar máquina ${machine.id}`);
                sendMessage();
              }}
              className="w-full py-1.5 text-[10px] font-medium bg-brand-600/20 text-brand-400 rounded hover:bg-brand-600/30 transition-colors"
            >
              Reservar Agora
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  const renderReservationStage = (data) => (
    <div className="bg-brand-900/20 border border-brand-500/30 p-4 rounded-lg text-center">
      <div className="w-10 h-10 bg-brand-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
        <Zap className="w-5 h-5 text-brand-400" />
      </div>
      <h4 className="text-brand-400 font-bold text-sm mb-1">Pronto para Reservar!</h4>
      <p className="text-gray-300 text-xs mb-3">{data.reservation?.details}</p>
      <button className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold rounded-lg transition-colors">
        Confirmar e Pagar
      </button>
    </div>
  );

  const renderOptimizationTips = (tips) => (
    <div className="mt-3 p-2 rounded bg-sky-900/15 border border-sky-700/20">
      <div className="text-[10px] text-sky-400/80 font-semibold mb-1">Dicas de Otimização:</div>
      <ul className="text-[10px] text-gray-400 space-y-0.5">
        {tips.map((tip, idx) => (
          <li key={idx}>• {tip}</li>
        ))}
      </ul>
    </div>
  );

  const renderMessageContent = (msg) => (
    <>
      {/* Text content */}
      <div className={`prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-strong:text-brand-400 prose-ul:my-1 prose-li:my-0 ${compact ? 'prose-h2:text-xs prose-h3:text-[9px]' : 'prose-h2:text-base prose-h3:text-sm'}`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
      </div>

      {/* Interactive Stage Displays */}
      {msg.showCards && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/30">
          {/* Legacy Recommendation */}
          {(msg.stage === 'recommendation' || (!msg.stage && msg.recommendation?.gpu_options)) && (
            <GPUWizardDisplay
              recommendation={msg.recommendation}
              onSearch={(opt) => applyRecommendation(opt)}
            />
          )}

          {msg.stage === 'research' && msg.data?.research_results && renderResearchStage(msg.data)}
          {msg.stage === 'options' && msg.data?.price_options && renderOptionsStage(msg.data)}
          {msg.stage === 'selection' && msg.data?.machines && renderSelectionStage(msg.data)}
          {msg.stage === 'reservation' && msg.data?.reservation && renderReservationStage(msg.data)}

          {msg.recommendation?.optimization_tips?.length > 0 && renderOptimizationTips(msg.recommendation.optimization_tips)}
        </div>
      )}

      {/* Fallback: Simple search button if no visual cards */}
      {msg.recommendation && !msg.showCards && (
        <button
          onClick={() => applyRecommendation()}
          className="mt-3 w-full py-2 px-3 text-xs font-medium text-white bg-brand-600/50 hover:bg-brand-600/70 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          <Search className="w-3 h-3" />
          Buscar GPUs Recomendadas
        </button>
      )}
    </>
  );

  if (compact) {
    return (
      <div className="flex flex-col h-full">
        {/* Minimal header */}
        <div className="px-2 py-2">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            <h3 className="text-gray-900 dark:text-white font-semibold text-xs">AI Advisor</h3>
          </div>
          <p className="text-gray-500 text-[9px]">Descreva seu projeto</p>
        </div>

        {/* Chat Messages - Compact */}
        <div className="flex-1 overflow-y-auto space-y-2 min-h-[200px] p-2">
          {messages.length === 0 && (
            <div className="text-center py-4">
              <Bot className="w-8 h-8 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-400 text-[10px] mb-2">Olá! Sou seu assistente.</p>
              <div className="space-y-1">
                <p className="text-gray-600 text-[9px] font-medium">Exemplos rápidos:</p>
                <div className="flex flex-col gap-1">
                  {['Fine-tuning LLaMA', 'Stable Diffusion', 'Treinar YOLO'].map((ex) => (
                    <button
                      key={ex}
                      onClick={() => setInputValue(ex)}
                      className="px-1.5 py-0.5 text-[9px] text-gray-400 bg-gray-100 dark:bg-gray-800/40 rounded hover:bg-gray-200 dark:hover:bg-gray-700/50 transition-colors text-left"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-1.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-5 h-5 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot className="w-3 h-3 text-brand-400" />
                </div>
              )}
              <div className={`max-w-[85%] p-1.5 rounded text-[9px] ${
                msg.role === 'user' ? 'ai-wizard-message-user' : 'ai-wizard-message-assistant'
              }`}>
                {renderMessageContent(msg)}
              </div>
              {msg.role === 'user' && (
                <div className="w-5 h-5 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0">
                  <User className="w-3 h-3 text-brand-400" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-2 justify-start">
              <div className="w-5 h-5 rounded-lg bg-brand-500/20 flex items-center justify-center">
                <Bot className="w-3 h-3 text-brand-400" />
              </div>
              <div className="ai-wizard-loading">
                <Loader2 className="w-3 h-3 text-brand-400 ai-wizard-loading-spinner" />
                <span className="text-[9px]">Processando...</span>
              </div>
            </div>
          )}
        </div>

        {/* Compact Input */}
        <div className="p-2 border-t border-gray-800/50">
          <div className="flex gap-1">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Descreva seu projeto..."
              className="flex-1 ai-wizard-improved-input text-[9px] px-2 py-1"
            />
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="ai-wizard-improved-send-button"
            >
              <Send className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // FULL MODE
  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800/50">
        <div className="w-10 h-10 rounded-lg bg-brand-900/30 flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h3 className="text-gray-900 dark:text-white font-semibold text-base">AI GPU Advisor</h3>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[300px] max-h-[500px]">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Bot className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400 text-base mb-6">Descreva seu projeto e receba a GPU ideal</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-md mx-auto">
              {['Fine-tuning LLaMA 7B', 'Stable Diffusion API', 'Treinar YOLO'].map((ex) => (
                <button
                  key={ex}
                  onClick={() => setInputValue(ex)}
                  className="px-4 py-2 text-xs font-semibold text-gray-700 dark:text-brand-300 bg-gray-100 dark:bg-brand-500/10 border border-gray-300 dark:border-brand-500/30 rounded-full hover:bg-brand-50 dark:hover:bg-brand-500/20 hover:border-brand-400 dark:hover:border-brand-500/50 hover:text-brand-600 dark:hover:text-brand-200 transition-all"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-brand-400" />
              </div>
            )}
            <div className={`max-w-[90%] p-3 rounded-lg ${
              msg.role === 'user' ? 'ai-wizard-message-user' : 'ai-wizard-message-assistant'
            }`}>
              {renderMessageContent(msg)}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-brand-400" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-brand-400" />
            </div>
            <div className="ai-wizard-loading">
              <Loader2 className="w-4 h-4 text-brand-400 ai-wizard-loading-spinner" />
              Processando...
            </div>
          </div>
        )}
      </div>

      {/* Chat Input */}
      <div className="p-4 border-t border-gray-800/50">
        {/* Quick Actions */}
        <div className="ai-wizard-quick-actions">
          {['Fine-tuning LLaMA 7B', 'Stable Diffusion XL', 'YOLO object detection', 'Orçamento $50/hora'].map((action) => (
            <button
              key={action}
              onClick={() => setInputValue(action)}
              className="ai-wizard-quick-action"
            >
              {action}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Descreva seu projeto aqui..."
            className="flex-1 ai-wizard-improved-input text-sm"
            rows={2}
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="ai-wizard-improved-send-button"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIWizardChat;
