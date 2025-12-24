import React, { useState, useEffect, useCallback } from 'react';
import {
  Play, Square, RefreshCw, Clock, DollarSign, Cpu, Server,
  Plus, Loader2, CheckCircle, XCircle, AlertCircle, Terminal,
  Eye, ExternalLink, Copy, Key, Globe, Lock, Mic, Image, MessageSquare, Search,
  ChevronRight, ChevronLeft, Rocket, Zap
} from 'lucide-react';

// Model type icons
const MODEL_TYPE_CONFIG = {
  llm: { icon: MessageSquare, label: 'LLM', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  speech: { icon: Mic, label: 'Speech', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  image: { icon: Image, label: 'Image', color: 'text-pink-400', bg: 'bg-pink-500/10' },
  embeddings: { icon: Search, label: 'Embeddings', color: 'text-amber-400', bg: 'bg-amber-500/10' },
};

// Status colors and icons
const STATUS_CONFIG = {
  pending: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: Clock, label: 'Pendente' },
  deploying: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, label: 'Deployando' },
  downloading: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, label: 'Baixando' },
  starting: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, label: 'Iniciando' },
  running: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', icon: Play, label: 'Running' },
  stopped: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: Square, label: 'Parado' },
  error: { color: 'text-red-400', bg: 'bg-red-500/10', icon: XCircle, label: 'Erro' },
};

const Models = () => {
  const [models, setModels] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDeployWizard, setShowDeployWizard] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);

  // Wizard form state
  const [formData, setFormData] = useState({
    model_type: 'llm',
    model_id: '',
    custom_model: false,
    instance_id: null,
    create_new_instance: true,
    gpu_type: 'RTX 4090',
    num_gpus: 1,
    max_price: 2.0,
    access_type: 'private',
    port: 8000,
    name: '',
  });

  // Fetch models and templates
  const fetchModels = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/v1/models', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setModels(data.models || []);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const fetchTemplates = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/v1/models/templates', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
      }
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  }, []);

  useEffect(() => {
    fetchModels();
    fetchTemplates();
    // Auto-refresh every 10 seconds for deploying models
    const interval = setInterval(() => {
      if (models.some(m => ['pending', 'deploying', 'downloading', 'starting'].includes(m.status))) {
        fetchModels();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchModels, fetchTemplates, models]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchModels();
  };

  const openDeployWizard = () => {
    setWizardStep(1);
    setFormData({
      model_type: 'llm',
      model_id: '',
      custom_model: false,
      instance_id: null,
      create_new_instance: true,
      gpu_type: 'RTX 4090',
      num_gpus: 1,
      max_price: 2.0,
      access_type: 'private',
      port: 8000,
      name: '',
    });
    setShowDeployWizard(true);
  };

  const handleDeploy = async () => {
    setDeploying(true);
    try {
      const token = localStorage.getItem('auth_token');
      const payload = {
        model_type: formData.model_type,
        model_id: formData.model_id,
        instance_id: formData.create_new_instance ? null : formData.instance_id,
        gpu_type: formData.gpu_type,
        num_gpus: formData.num_gpus,
        max_price: formData.max_price,
        access_type: formData.access_type,
        port: formData.port,
        name: formData.name || undefined,
      };

      const response = await fetch('/api/v1/models/deploy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setShowDeployWizard(false);
        fetchModels();
      } else {
        const error = await response.json();
        alert(`Erro ao fazer deploy: ${error.detail || 'Erro desconhecido'}`);
      }
    } catch (error) {
      console.error('Error deploying model:', error);
      alert('Erro ao fazer deploy');
    } finally {
      setDeploying(false);
    }
  };

  const handleStopModel = async (modelId) => {
    if (!confirm('Tem certeza que deseja parar este modelo?')) return;

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/v1/models/${modelId}/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ force: false }),
      });
      if (response.ok) fetchModels();
    } catch (error) {
      console.error('Error stopping model:', error);
    }
  };

  const handleDeleteModel = async (modelId) => {
    if (!confirm('Tem certeza que deseja deletar este deploy? Esta ação não pode ser desfeita.')) return;

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/v1/models/${modelId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) fetchModels();
    } catch (error) {
      console.error('Error deleting model:', error);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const ModelStatusBadge = ({ status }) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    const isAnimated = ['deploying', 'downloading', 'starting'].includes(status);

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
        <Icon className={`w-3.5 h-3.5 ${isAnimated ? 'animate-spin' : ''}`} />
        {config.label}
      </span>
    );
  };

  const ModelTypeIcon = ({ type }) => {
    const config = MODEL_TYPE_CONFIG[type] || MODEL_TYPE_CONFIG.llm;
    const Icon = config.icon;
    return (
      <div className={`p-2 rounded-lg ${config.bg}`}>
        <Icon className={`w-5 h-5 ${config.color}`} />
      </div>
    );
  };

  // Get selected template
  const selectedTemplate = templates.find(t => t.type === formData.model_type);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Models</h1>
          <p className="text-sm text-gray-400 mt-1">
            Deploy modelos de ML/AI com endpoint de API
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-gray-200 transition-all border border-white/10"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={openDeployWizard}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 transition-all"
          >
            <Rocket className="w-4 h-4" />
            Deploy Model
          </button>
        </div>
      </div>

      {/* Deploy Wizard Modal */}
      {showDeployWizard && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-surface-card border border-white/10 rounded-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Wizard Header */}
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-100">Deploy Model</h2>
                  <p className="text-xs text-gray-500 mt-1">
                    Passo {wizardStep} de 4
                  </p>
                </div>
                <button
                  onClick={() => setShowDeployWizard(false)}
                  className="p-2 rounded-lg hover:bg-white/10 text-gray-400"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>

              {/* Progress bar */}
              <div className="flex gap-1">
                {[1, 2, 3, 4].map((step) => (
                  <div
                    key={step}
                    className={`h-1 flex-1 rounded-full transition-all ${
                      step <= wizardStep ? 'bg-brand-500' : 'bg-white/10'
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* Wizard Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Step 1: Choose Model Type */}
              {wizardStep === 1 && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-4">
                      Escolha o tipo de modelo
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      {templates.map((template) => {
                        const config = MODEL_TYPE_CONFIG[template.type];
                        const Icon = config?.icon || MessageSquare;
                        const isSelected = formData.model_type === template.type;

                        return (
                          <button
                            key={template.type}
                            type="button"
                            onClick={() => {
                              setFormData({ ...formData, model_type: template.type, model_id: '', port: template.default_port });
                            }}
                            className={`p-4 rounded-xl border text-left transition-all ${
                              isSelected
                                ? 'bg-brand-500/10 border-brand-500/50'
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className={`p-2 rounded-lg ${config?.bg || 'bg-blue-500/10'}`}>
                                <Icon className={`w-5 h-5 ${config?.color || 'text-blue-400'}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium text-gray-200">{template.name}</div>
                                <div className="text-xs text-gray-500 mt-1">{template.description}</div>
                                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                                  <span className="px-1.5 py-0.5 rounded bg-white/10">{template.runtime}</span>
                                  <span>GPU: {template.gpu_memory_required}GB+</span>
                                </div>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Step 2: Choose Model */}
              {wizardStep === 2 && selectedTemplate && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-4">
                      Escolha o modelo
                    </h3>

                    {/* Popular models */}
                    <div className="space-y-2 mb-6">
                      {selectedTemplate.popular_models.map((model) => (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => setFormData({ ...formData, model_id: model.id, custom_model: false })}
                          className={`w-full p-3 rounded-lg border text-left transition-all flex items-center justify-between ${
                            formData.model_id === model.id && !formData.custom_model
                              ? 'bg-brand-500/10 border-brand-500/50'
                              : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                          }`}
                        >
                          <div>
                            <div className="text-sm font-medium text-gray-200">{model.name}</div>
                            <div className="text-xs text-gray-500 font-mono">{model.id}</div>
                          </div>
                          <span className="text-xs px-2 py-1 rounded bg-white/10 text-gray-400">
                            {model.size}
                          </span>
                        </button>
                      ))}
                    </div>

                    {/* Custom model input */}
                    <div className="border-t border-white/10 pt-6">
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Ou use um modelo customizado (HuggingFace ID)
                      </label>
                      <input
                        type="text"
                        value={formData.custom_model ? formData.model_id : ''}
                        onChange={(e) => setFormData({ ...formData, model_id: e.target.value, custom_model: true })}
                        placeholder="Ex: meta-llama/Llama-3.2-3B-Instruct"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3: GPU Config */}
              {wizardStep === 3 && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-4">
                      Configuração de GPU
                    </h3>

                    <div className="space-y-4">
                      {/* GPU Type */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Tipo de GPU
                        </label>
                        <select
                          value={formData.gpu_type}
                          onChange={(e) => setFormData({ ...formData, gpu_type: e.target.value })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        >
                          <option value="RTX 3080">RTX 3080 (10GB)</option>
                          <option value="RTX 3090">RTX 3090 (24GB)</option>
                          <option value="RTX 4080">RTX 4080 (16GB)</option>
                          <option value="RTX 4090">RTX 4090 (24GB)</option>
                          <option value="A100">A100 (40/80GB)</option>
                          <option value="H100">H100 (80GB)</option>
                        </select>
                      </div>

                      {/* Num GPUs */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Quantidade de GPUs
                        </label>
                        <select
                          value={formData.num_gpus}
                          onChange={(e) => setFormData({ ...formData, num_gpus: parseInt(e.target.value) })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        >
                          {[1, 2, 4, 8].map((n) => (
                            <option key={n} value={n}>{n} GPU{n > 1 ? 's' : ''}</option>
                          ))}
                        </select>
                      </div>

                      {/* Max Price */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Preço máximo por hora ($/h)
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0.1"
                          max="10"
                          value={formData.max_price}
                          onChange={(e) => setFormData({ ...formData, max_price: parseFloat(e.target.value) })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        />
                      </div>

                      {/* Name */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Nome (opcional)
                        </label>
                        <input
                          type="text"
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          placeholder="Ex: Meu LLM de produção"
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 4: Access Config */}
              {wizardStep === 4 && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-4">
                      Configuração de Acesso
                    </h3>

                    <div className="space-y-4">
                      {/* Access Type */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Tipo de Acesso
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={() => setFormData({ ...formData, access_type: 'private' })}
                            className={`p-4 rounded-lg border text-left transition-all ${
                              formData.access_type === 'private'
                                ? 'bg-brand-500/10 border-brand-500/50'
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Lock className="w-4 h-4 text-amber-400" />
                              <span className="text-sm font-medium text-gray-200">Privado</span>
                            </div>
                            <p className="text-xs text-gray-500">
                              Acesso via API key gerada automaticamente
                            </p>
                          </button>
                          <button
                            type="button"
                            onClick={() => setFormData({ ...formData, access_type: 'public' })}
                            className={`p-4 rounded-lg border text-left transition-all ${
                              formData.access_type === 'public'
                                ? 'bg-brand-500/10 border-brand-500/50'
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Globe className="w-4 h-4 text-emerald-400" />
                              <span className="text-sm font-medium text-gray-200">Público</span>
                            </div>
                            <p className="text-xs text-gray-500">
                              Qualquer pessoa pode acessar o endpoint
                            </p>
                          </button>
                        </div>
                      </div>

                      {/* Port */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Porta
                        </label>
                        <input
                          type="number"
                          min="1024"
                          max="65535"
                          value={formData.port}
                          onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        />
                      </div>

                      {/* Summary */}
                      <div className="mt-6 p-4 rounded-lg bg-white/5 border border-white/10">
                        <h4 className="text-xs font-medium text-gray-400 mb-3">Resumo do Deploy</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-500">Tipo:</span>
                            <span className="text-gray-200">{MODEL_TYPE_CONFIG[formData.model_type]?.label}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Modelo:</span>
                            <span className="text-gray-200 font-mono text-xs">{formData.model_id || 'Não selecionado'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">GPU:</span>
                            <span className="text-gray-200">{formData.num_gpus}x {formData.gpu_type}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Acesso:</span>
                            <span className="text-gray-200">{formData.access_type === 'private' ? 'Privado (API Key)' : 'Público'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Porta:</span>
                            <span className="text-gray-200">{formData.port}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Wizard Footer */}
            <div className="p-6 border-t border-white/10 flex items-center justify-between">
              <button
                type="button"
                onClick={() => wizardStep > 1 ? setWizardStep(wizardStep - 1) : setShowDeployWizard(false)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-sm transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
                {wizardStep === 1 ? 'Cancelar' : 'Voltar'}
              </button>

              {wizardStep < 4 ? (
                <button
                  type="button"
                  onClick={() => setWizardStep(wizardStep + 1)}
                  disabled={wizardStep === 2 && !formData.model_id}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Próximo
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleDeploy}
                  disabled={deploying || !formData.model_id}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 text-sm transition-all disabled:opacity-50"
                >
                  {deploying ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Deployando...
                    </>
                  ) : (
                    <>
                      <Rocket className="w-4 h-4" />
                      Deploy
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Models List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400 mr-3" />
          <span className="text-gray-400">Carregando modelos...</span>
        </div>
      ) : models.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-white/10 rounded-xl">
          <Zap className="w-12 h-12 mx-auto text-gray-600 mb-4" />
          <h3 className="text-lg font-medium text-gray-300 mb-2">Nenhum modelo deployado</h3>
          <p className="text-sm text-gray-500 mb-6 max-w-md mx-auto">
            Deploy modelos de LLM, Speech-to-Text, Image Generation ou Embeddings com um clique
          </p>
          <button
            onClick={openDeployWizard}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 transition-all"
          >
            <Rocket className="w-4 h-4" />
            Deploy Primeiro Modelo
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {models.map((model) => {
            const isDeploying = ['pending', 'deploying', 'downloading', 'starting'].includes(model.status);
            const isRunning = model.status === 'running';

            return (
              <div
                key={model.id}
                className="border border-white/10 rounded-xl bg-white/[0.02] overflow-hidden"
              >
                {/* Card Header */}
                <div className="p-4 border-b border-white/5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <ModelTypeIcon type={model.model_type} />
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-200 truncate">
                          {model.name || model.model_id.split('/').pop()}
                        </div>
                        <div className="text-xs text-gray-500 font-mono truncate">
                          {model.model_id}
                        </div>
                      </div>
                    </div>
                    <ModelStatusBadge status={model.status} />
                  </div>
                </div>

                {/* Progress bar (when deploying) */}
                {isDeploying && (
                  <div className="px-4 py-3 border-b border-white/5 bg-white/[0.02]">
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-gray-400">{model.status_message || 'Preparando...'}</span>
                      <span className="text-gray-500">{Math.round(model.progress)}%</span>
                    </div>
                    <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full transition-all duration-500"
                        style={{ width: `${model.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Card Body */}
                <div className="p-4 space-y-3">
                  {/* GPU Info */}
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Cpu className="w-3.5 h-3.5" />
                    <span>{model.num_gpus}x {model.gpu_name || 'GPU'}</span>
                    <span className="text-gray-600">•</span>
                    <span>{model.runtime}</span>
                  </div>

                  {/* Endpoint (when running) */}
                  {isRunning && model.endpoint_url && (
                    <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                      <div className="flex items-center justify-between gap-2">
                        <code className="text-xs text-gray-300 truncate">{model.endpoint_url}</code>
                        <button
                          onClick={() => copyToClipboard(model.endpoint_url)}
                          className="p-1 rounded hover:bg-white/10 text-gray-400"
                          title="Copiar URL"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* API Key (when private) */}
                  {isRunning && model.access_type === 'private' && model.api_key && (
                    <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Key className="w-3.5 h-3.5 text-amber-400" />
                          <code className="text-xs text-amber-300 truncate">
                            {model.api_key.substring(0, 20)}...
                          </code>
                        </div>
                        <button
                          onClick={() => copyToClipboard(model.api_key)}
                          className="p-1 rounded hover:bg-amber-500/20 text-amber-400"
                          title="Copiar API Key"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Cost */}
                  {model.dph_total > 0 && (
                    <div className="flex items-center gap-2 text-xs">
                      <DollarSign className="w-3.5 h-3.5 text-gray-500" />
                      <span className="text-gray-400">
                        ${model.dph_total.toFixed(2)}/h
                      </span>
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                <div className="px-4 py-3 border-t border-white/5 flex items-center gap-2">
                  {isRunning && (
                    <>
                      <button
                        onClick={() => handleStopModel(model.id)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-xs transition-all"
                      >
                        <Square className="w-3.5 h-3.5" />
                        Stop
                      </button>
                      <a
                        href={`/api/v1/models/${model.id}/logs`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-xs transition-all"
                      >
                        <Terminal className="w-3.5 h-3.5" />
                        Logs
                      </a>
                    </>
                  )}
                  {!isDeploying && (
                    <button
                      onClick={() => handleDeleteModel(model.id)}
                      className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-red-500/10 text-red-400 text-xs transition-all"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Delete
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Info Box */}
      <div className="p-4 rounded-xl bg-brand-500/5 border border-brand-500/20">
        <h4 className="text-sm font-medium text-brand-400 mb-2">Tipos de Modelo Suportados</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-400">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
              <span className="font-medium text-gray-300">LLM</span>
            </div>
            <span>Chat & Completion (vLLM)</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Mic className="w-3.5 h-3.5 text-purple-400" />
              <span className="font-medium text-gray-300">Speech</span>
            </div>
            <span>Whisper (Transcription)</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Image className="w-3.5 h-3.5 text-pink-400" />
              <span className="font-medium text-gray-300">Image</span>
            </div>
            <span>SD, FLUX (Diffusers)</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Search className="w-3.5 h-3.5 text-amber-400" />
              <span className="font-medium text-gray-300">Embeddings</span>
            </div>
            <span>BGE, E5 (Sentence-Transformers)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Models;
