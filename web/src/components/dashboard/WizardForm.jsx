import React, { useState, useEffect, useRef } from 'react';
import {
  Search, Globe, MapPin, X, Cpu, MessageSquare, Lightbulb, Code, Zap,
  Sparkles, Gauge, Activity, Clock, Loader2, AlertCircle, Check, ChevronRight, ChevronLeft,
  Shield, Server, HardDrive, Cloud, Timer, DollarSign, Database, Filter, Star, TrendingUp,
  ChevronDown, ChevronUp, Info, HelpCircle, Rocket, Hourglass
} from 'lucide-react';
import { Button, Label, CardContent } from '../tailadmin-ui';
import { WorldMap, GPUSelector } from './';
import { COUNTRY_DATA, PERFORMANCE_TIERS } from './constants';

// Componente Tooltip simples
const Tooltip = ({ children, text }) => (
  <span className="relative group inline-flex items-center">
    {children}
    <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-[10px] text-gray-200 bg-gray-800 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
      {text}
      <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
    </span>
  </span>
);

// Tooltips para termos técnicos
const TERM_TOOLTIPS = {
  'warm_pool': 'GPU reservada e pronta para uso imediato',
  'cpu_standby': 'CPU pequena que mantém dados sincronizados',
  'snapshot': 'Backup compactado dos seus dados',
  'serverless': 'Paga apenas quando a GPU está em uso',
  'failover': 'Recuperação automática em caso de falha',
  'rsync': 'Sincronização contínua de arquivos',
  'lz4': 'Compressão rápida de dados',
};

const WizardForm = ({
  // Step 1: Location
  searchCountry,
  selectedLocation,
  onSearchChange,
  onRegionSelect,
  onCountryClick,
  onClearSelection,
  // Step 2: Hardware
  selectedGPU,
  onSelectGPU,
  selectedGPUCategory,
  onSelectGPUCategory,
  selectedTier,
  onSelectTier,
  // Actions
  loading,
  onSubmit,
  // Provisioning (Step 4)
  provisioningCandidates = [],
  provisioningWinner = null,
  isProvisioning = false,
  onCancelProvisioning,
  onCompleteProvisioning,
  currentRound = 1,
  maxRounds = 3,
}) => {
  const tiers = PERFORMANCE_TIERS;
  const countryData = COUNTRY_DATA;
  const [validationErrors, setValidationErrors] = useState([]);
  const [currentStep, setCurrentStep] = useState(1);
  const [failoverStrategy, setFailoverStrategy] = useState('vast_warmpool');

  // Machine selection state
  const [selectionMode, setSelectionMode] = useState('recommended'); // 'recommended' or 'manual'
  const [provisioningStartTime, setProvisioningStartTime] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Track elapsed time during provisioning
  useEffect(() => {
    if (currentStep === 4 && !provisioningWinner) {
      setProvisioningStartTime(Date.now());
      const interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    } else if (provisioningWinner) {
      // Stop timer when winner found
    } else {
      setElapsedTime(0);
      setProvisioningStartTime(null);
    }
  }, [currentStep, provisioningWinner]);

  // Format time as mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Estimate remaining time
  const getETA = () => {
    if (provisioningWinner) return 'Concluído!';
    const activeCandidates = provisioningCandidates.filter(c => c.status !== 'failed');
    if (activeCandidates.length === 0) return 'Sem máquinas ativas';
    const maxProgress = Math.max(...activeCandidates.map(c => c.progress || 0));
    if (maxProgress <= 10 || elapsedTime < 3) return 'Estimando...';
    const estimatedTotal = (elapsedTime / maxProgress) * 100;
    const remaining = Math.max(0, Math.ceil(estimatedTotal - elapsedTime));
    if (remaining < 60) return `~${remaining}s restantes`;
    return `~${Math.ceil(remaining / 60)}min restantes`;
  };
  const [recommendedMachines, setRecommendedMachines] = useState([]);
  const [loadingMachines, setLoadingMachines] = useState(false);
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [gpuSearchQuery, setGpuSearchQuery] = useState('');

  // Lista completa de GPUs disponíveis
  const allGPUs = [
    { name: 'RTX 3060', vram: '12GB', priceRange: '$0.10-0.20/h' },
    { name: 'RTX 3070', vram: '8GB', priceRange: '$0.15-0.25/h' },
    { name: 'RTX 3080', vram: '10GB', priceRange: '$0.20-0.35/h' },
    { name: 'RTX 3090', vram: '24GB', priceRange: '$0.30-0.50/h' },
    { name: 'RTX 4070', vram: '12GB', priceRange: '$0.25-0.40/h' },
    { name: 'RTX 4080', vram: '16GB', priceRange: '$0.40-0.60/h' },
    { name: 'RTX 4090', vram: '24GB', priceRange: '$0.55-0.85/h' },
    { name: 'GTX 1080 Ti', vram: '11GB', priceRange: '$0.08-0.15/h' },
    { name: 'A100 40GB', vram: '40GB', priceRange: '$0.80-1.20/h' },
    { name: 'A100 80GB', vram: '80GB', priceRange: '$1.20-2.00/h' },
    { name: 'H100 80GB', vram: '80GB', priceRange: '$2.00-3.50/h' },
    { name: 'A10', vram: '24GB', priceRange: '$0.35-0.55/h' },
    { name: 'A40', vram: '48GB', priceRange: '$0.50-0.80/h' },
    { name: 'L40', vram: '48GB', priceRange: '$0.70-1.00/h' },
    { name: 'V100', vram: '16GB', priceRange: '$0.40-0.70/h' },
    { name: 'T4', vram: '16GB', priceRange: '$0.20-0.35/h' },
  ];

  // Filtrar GPUs pela busca
  const filteredGPUs = gpuSearchQuery
    ? allGPUs.filter(gpu =>
        gpu.name.toLowerCase().includes(gpuSearchQuery.toLowerCase()) ||
        gpu.vram.toLowerCase().includes(gpuSearchQuery.toLowerCase())
      )
    : allGPUs;

  const COUNTRY_NAMES = {
    'US': 'Estados Unidos',
    'CA': 'Canadá',
    'MX': 'México',
    'GB': 'Reino Unido',
    'FR': 'França',
    'DE': 'Alemanha',
    'ES': 'Espanha',
    'IT': 'Itália',
    'PT': 'Portugal',
    'JP': 'Japão',
    'CN': 'China',
    'KR': 'Coreia do Sul',
    'SG': 'Singapura',
    'IN': 'Índia',
    'BR': 'Brasil',
    'AR': 'Argentina',
    'CL': 'Chile',
    'CO': 'Colômbia',
  };

  const steps = [
    { id: 1, name: 'Região', icon: Globe, description: 'Localização' },
    { id: 2, name: 'Hardware', icon: Cpu, description: 'GPU e performance' },
    { id: 3, name: 'Estratégia', icon: Shield, description: 'Failover' },
    { id: 4, name: 'Provisionar', icon: Rocket, description: 'Conectando' },
  ];

  // Estratégias REAIS de failover - custos são ADICIONAIS ao custo da GPU
  const failoverOptions = [
    {
      id: 'vast_warmpool',
      name: 'VAST.ai Warm Pool',
      provider: 'VAST.ai + GCP + B2',
      icon: Zap,
      description: 'Failover completo com GPU warm, CPU standby e snapshots automáticos.',
      recoveryTime: '30-90 seg',
      dataLoss: 'Zero',
      costHour: '+$0.03/h',
      costMonth: '~$22/mês',
      costDetail: 'CPU GCP $0.01/h + Volume VAST $0.02/h + B2 ~$0.50/mês',
      howItWorks: 'GPU #2 fica parada no mesmo host (volume compartilhado). CPU no GCP (e2-medium spot $0.01/h) faz rsync contínuo. Snapshots LZ4 vão para Backblaze B2 a cada 60min.',
      features: [
        'GPU warm pool no mesmo host',
        'CPU standby GCP (+$0.01/h)',
        'Volume persistente VAST (+$0.02/h)',
        'Snapshots B2 (~$0.50/mês)',
      ],
      requirements: 'Host VAST.ai com 2+ GPUs',
      recommended: true,
      available: true,
    },
    {
      id: 'snapshot_only',
      name: 'Snapshot Only',
      provider: 'GCP + B2',
      icon: Database,
      description: 'Apenas snapshots automáticos. CPU GCP para restore quando necessário.',
      recoveryTime: '2-5 min',
      dataLoss: 'Até 60 min',
      costHour: '+$0.01/h',
      costMonth: '~$8/mês',
      costDetail: 'CPU GCP $0.01/h + B2 ~$0.50/mês',
      howItWorks: 'Snapshots LZ4 automáticos a cada 60min para Backblaze B2. CPU GCP (e2-medium spot $0.01/h) sempre ligada. Quando falhar, nova GPU é provisionada e dados restaurados.',
      features: [
        'Snapshots automáticos (60min)',
        'CPU standby GCP (+$0.01/h)',
        'Storage B2 (~$0.50/mês)',
        'Sem GPU idle',
      ],
      requirements: 'Nenhum extra',
      recommended: false,
      available: true,
    },
    {
      id: 'tensordock',
      name: 'Tensor Dock Serverless',
      provider: 'Tensor Dock + B2',
      icon: Cloud,
      description: 'Abordagem serverless-like. Paga só quando usa.',
      recoveryTime: '~2 min',
      dataLoss: 'Último snapshot',
      costHour: '+$0.001/h',
      costMonth: '~$1/mês',
      costDetail: 'Só storage B2 (~$0.50/mês) + custo GPU sob demanda',
      howItWorks: 'Snapshots automáticos para B2. Sem máquina idle. Quando precisar, GPU é provisionada sob demanda no Tensor Dock e dados restaurados.',
      features: [
        'Sem máquina idle ($0/h parado)',
        'Snapshots B2 (~$0.50/mês)',
        'GPU sob demanda',
        'Boot otimizado',
      ],
      requirements: 'Conta Tensor Dock',
      recommended: false,
      available: true,
    },
  ];

  // Fetch recommended machines when tier or location changes
  useEffect(() => {
    const fetchRecommendedMachines = async () => {
      if (!selectedTier) {
        setRecommendedMachines([]);
        return;
      }

      setLoadingMachines(true);
      try {
        // Get tier config for price range
        const tier = tiers.find(t => t.name === selectedTier);
        const regionCode = selectedLocation?.codes?.[0] || '';

        // Try to fetch from API
        const response = await fetch(`/api/v1/instances/offers?limit=3&order_by=dph_total&region=${regionCode}`);

        if (response.ok) {
          const data = await response.json();
          if (data.offers && data.offers.length > 0) {
            setRecommendedMachines(data.offers.slice(0, 3));
            return;
          }
        }

        // Fallback to mock data based on tier
        const mockMachines = getMockMachinesForTier(selectedTier);
        setRecommendedMachines(mockMachines);
      } catch {
        // Use mock data on error
        const mockMachines = getMockMachinesForTier(selectedTier);
        setRecommendedMachines(mockMachines);
      } finally {
        setLoadingMachines(false);
      }
    };

    fetchRecommendedMachines();
  }, [selectedTier, selectedLocation]);

  // Mock machines based on tier
  const getMockMachinesForTier = (tierName) => {
    const mockData = {
      'Lento': [
        { id: 'eco1', gpu_name: 'RTX 3060', gpu_ram: 12, num_gpus: 1, dph_total: 0.15, reliability: 98.5, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
        { id: 'eco2', gpu_name: 'RTX 3070', gpu_ram: 8, num_gpus: 1, dph_total: 0.18, reliability: 99.1, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
        { id: 'eco3', gpu_name: 'GTX 1080 Ti', gpu_ram: 11, num_gpus: 1, dph_total: 0.12, reliability: 97.8, location: 'US-East', provider: 'vast.ai', label: 'Mais rápido' },
      ],
      'Medio': [
        { id: 'med1', gpu_name: 'RTX 3080', gpu_ram: 10, num_gpus: 1, dph_total: 0.25, reliability: 99.2, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
        { id: 'med2', gpu_name: 'RTX 3090', gpu_ram: 24, num_gpus: 1, dph_total: 0.35, reliability: 99.5, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
        { id: 'med3', gpu_name: 'RTX 4070', gpu_ram: 12, num_gpus: 1, dph_total: 0.30, reliability: 99.8, location: 'US-East', provider: 'tensordock', label: 'Mais rápido' },
      ],
      'Rapido': [
        { id: 'rap1', gpu_name: 'RTX 4080', gpu_ram: 16, num_gpus: 1, dph_total: 0.45, reliability: 99.5, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
        { id: 'rap2', gpu_name: 'RTX 4090', gpu_ram: 24, num_gpus: 1, dph_total: 0.65, reliability: 99.7, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
        { id: 'rap3', gpu_name: 'A100 40GB', gpu_ram: 40, num_gpus: 1, dph_total: 0.85, reliability: 99.9, location: 'US-East', provider: 'vast.ai', label: 'Mais rápido' },
      ],
      'Ultra': [
        { id: 'ult1', gpu_name: 'A100 80GB', gpu_ram: 80, num_gpus: 1, dph_total: 1.20, reliability: 99.8, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
        { id: 'ult2', gpu_name: 'H100 80GB', gpu_ram: 80, num_gpus: 1, dph_total: 2.50, reliability: 99.9, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
        { id: 'ult3', gpu_name: 'A100 80GB', gpu_ram: 80, num_gpus: 2, dph_total: 2.40, reliability: 99.9, location: 'US-East', provider: 'vast.ai', label: 'Mais rápido' },
      ],
    };
    return mockData[tierName] || mockData['Medio'];
  };

  // Verifica se os dados do step estão preenchidos
  const isStepDataComplete = (stepId) => {
    if (stepId === 1) return !!selectedLocation;
    if (stepId === 2) return !!selectedTier;
    if (stepId === 3) return !!failoverStrategy;
    if (stepId === 4) return !!provisioningWinner;
    return false;
  };

  // Verifica se o step já foi passado (usuário avançou além dele)
  const isStepPassed = (stepId) => {
    return currentStep > stepId && isStepDataComplete(stepId);
  };

  // Mantém compatibilidade com código existente
  const isStepComplete = isStepDataComplete;

  const canProceedToStep = (stepId) => {
    if (stepId < currentStep) return true;
    if (stepId === currentStep + 1) return isStepDataComplete(currentStep);
    if (stepId === currentStep) return true;
    return false;
  };

  const goToStep = (stepId) => {
    if (canProceedToStep(stepId)) {
      setCurrentStep(stepId);
    }
  };

  const handleNext = () => {
    if (currentStep < steps.length && isStepComplete(currentStep)) {
      // Se está no step 3 e vai para o step 4, iniciar provisioning
      if (currentStep === 3) {
        handleStartProvisioning();
      } else {
        setCurrentStep(currentStep + 1);
      }
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      // Se está no step 4 (provisioning) e quer voltar, cancelar o provisioning
      if (currentStep === 4 && onCancelProvisioning) {
        onCancelProvisioning();
      }
      setCurrentStep(currentStep - 1);
    }
  };

  // State for payment confirmation and balance
  const [showPaymentConfirm, setShowPaymentConfirm] = useState(false);
  const [userBalance, setUserBalance] = useState(null);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [balanceError, setBalanceError] = useState(null);

  // Fetch user balance when entering step 3
  useEffect(() => {
    if (currentStep === 3) {
      fetchUserBalance();
    }
  }, [currentStep]);

  const fetchUserBalance = async () => {
    setLoadingBalance(true);
    setBalanceError(null);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        // Try to get balance from user data or default to 10.00 for demo
        const balance = data.user?.balance ?? data.balance ?? 10.00;
        setUserBalance(parseFloat(balance) || 10.00);
      } else {
        // Demo mode - assume $10 balance
        setUserBalance(10.00);
      }
    } catch (e) {
      // Demo mode fallback
      setUserBalance(10.00);
    } finally {
      setLoadingBalance(false);
    }
  };

  const handleStartProvisioning = () => {
    const errors = [];

    if (!selectedLocation) {
      errors.push('Por favor, selecione uma localização para sua máquina');
    }

    if (!selectedTier) {
      errors.push('Por favor, selecione um tier de performance');
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      if (!selectedLocation) setCurrentStep(1);
      else if (!selectedTier) setCurrentStep(2);
      return;
    }

    setValidationErrors([]);
    // Show payment confirmation before proceeding
    setShowPaymentConfirm(true);
  };

  const handleConfirmPayment = () => {
    setShowPaymentConfirm(false);
    setCurrentStep(4);
    onSubmit(); // Inicia o provisioning
  };

  const handleCancelPayment = () => {
    setShowPaymentConfirm(false);
  };

  const selectedFailover = failoverOptions.find(o => o.id === failoverStrategy);

  // Get estimated cost based on selected tier
  const getEstimatedCost = () => {
    const tierData = tiers.find(t => t.name === selectedTier);
    if (!tierData) return { hourly: '0.00', daily: '0.00' };
    // Extract min price from priceRange like "$0.10-0.30/h"
    const match = tierData.priceRange?.match(/\$(\d+\.?\d*)/);
    const minPrice = match ? parseFloat(match[1]) : 0.20;
    return {
      hourly: minPrice.toFixed(2),
      daily: (minPrice * 24).toFixed(2)
    };
  };

  return (
    <CardContent className="p-6 space-y-6">
      {/* Payment Confirmation Modal */}
      {showPaymentConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl animate-scaleIn">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-500/10 border border-brand-500/30 mb-4">
                <DollarSign className="w-7 h-7 text-brand-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Confirmar Provisionamento</h3>
              <p className="text-sm text-gray-400">
                Você está prestes a provisionar uma máquina GPU. Verifique os custos estimados abaixo.
              </p>
            </div>

            {/* Balance Display */}
            <div className={`rounded-lg p-3 mb-4 flex items-center justify-between ${
              userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                ? 'bg-red-500/10 border border-red-500/30'
                : 'bg-green-500/10 border border-green-500/30'
            }`}>
              <div className="flex items-center gap-2">
                <DollarSign className={`w-4 h-4 ${
                  userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                    ? 'text-red-400'
                    : 'text-green-400'
                }`} />
                <span className="text-sm text-gray-300">Seu saldo:</span>
              </div>
              <span className={`text-lg font-bold ${
                userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                  ? 'text-red-400'
                  : 'text-green-400'
              }`}>
                ${userBalance?.toFixed(2) || '-.--'}
              </span>
            </div>

            {/* Insufficient balance warning */}
            {userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly) && (
              <div className="flex items-start gap-2 mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs text-red-400 font-medium">Saldo insuficiente</p>
                  <p className="text-[10px] text-red-400/80">
                    Você precisa de pelo menos ${getEstimatedCost().hourly}/h. Adicione créditos antes de continuar.
                  </p>
                </div>
              </div>
            )}

            {/* Cost Summary */}
            <div className="bg-gray-800/50 rounded-lg p-4 mb-6 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">GPU Tier</span>
                <span className="text-sm font-medium text-white">{selectedTier}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Região</span>
                <span className="text-sm font-medium text-white">{selectedLocation?.name || 'Global'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Estratégia</span>
                <span className="text-sm font-medium text-white">{selectedFailover?.name || '-'}</span>
              </div>
              <div className="border-t border-gray-700 my-2" />
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Custo estimado/hora</span>
                <span className="text-lg font-bold text-brand-400">${getEstimatedCost().hourly}/h</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Custo estimado/dia</span>
                <span className="text-sm text-gray-300">${getEstimatedCost().daily}/dia</span>
              </div>
              {selectedFailover?.costHour && (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-500">+ Failover</span>
                  <span className="text-gray-400">{selectedFailover.costHour}</span>
                </div>
              )}
            </div>

            {/* Warning */}
            <div className="flex items-start gap-2 mb-6 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-yellow-400/90">
                A cobrança começa assim que a máquina ficar online. Você pode pausar ou destruir a instância a qualquer momento.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <Button
                onClick={handleCancelPayment}
                variant="ghost"
                className="flex-1 text-gray-400 hover:text-white hover:bg-gray-800"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleConfirmPayment}
                disabled={userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)}
                className={`flex-1 ${
                  userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                    ? 'bg-gray-600 cursor-not-allowed opacity-50'
                    : 'bg-brand-500 hover:bg-brand-600'
                } text-white`}
                data-testid="confirm-payment-button"
              >
                <Check className="w-4 h-4 mr-2" />
                {userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                  ? 'Saldo Insuficiente'
                  : 'Confirmar e Iniciar'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Stepper Progress Bar */}
      <div className="relative">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const StepIcon = step.icon;
            const isPassed = isStepPassed(step.id);
            const isCurrent = currentStep === step.id;
            const isClickable = canProceedToStep(step.id);

            return (
              <React.Fragment key={step.id}>
                <button
                  onClick={() => goToStep(step.id)}
                  disabled={!isClickable}
                  className={`relative z-10 flex flex-col items-center gap-2 transition-all ${
                    isClickable ? 'cursor-pointer' : 'cursor-not-allowed'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${
                    isPassed
                      ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                      : isCurrent
                        ? 'bg-brand-500/10 border-brand-400 text-brand-400'
                        : 'bg-white/5 border-white/10 text-gray-500'
                  }`}>
                    {isPassed ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <StepIcon className="w-4 h-4" />
                    )}
                  </div>
                  <div className="text-center">
                    <div className={`text-[10px] font-bold mb-0.5 ${
                      isPassed ? 'text-brand-400' : isCurrent ? 'text-brand-400' : 'text-gray-600'
                    }`}>
                      {step.id}/{steps.length}
                    </div>
                    <div className={`text-xs font-medium ${
                      isPassed ? 'text-brand-400' : isCurrent ? 'text-gray-200' : 'text-gray-500'
                    }`}>
                      {step.name}
                    </div>
                    <div className={`text-[10px] ${
                      isCurrent || isPassed ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {step.description}
                    </div>
                  </div>
                </button>

                {index < steps.length - 1 && (
                  <div className="flex-1 h-0.5 mx-3 relative top-[-16px]">
                    <div className="absolute inset-0 bg-white/10 rounded-full" />
                    <div
                      className="absolute inset-y-0 left-0 bg-brand-500 rounded-full transition-all duration-500"
                      style={{ width: isStepPassed(step.id) ? '100%' : '0%' }}
                    />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-400 mb-2">
                Por favor, corrija os seguintes campos:
              </h4>
              <ul className="space-y-1">
                {validationErrors.map((error, idx) => (
                  <li key={idx} className="text-sm text-red-300/80 flex items-start gap-2">
                    <span className="text-red-400/60 mt-1">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Step 1: Localização */}
      {currentStep === 1 && (
        <div className="space-y-5 animate-fadeIn">
          <div className="space-y-4">
            <div className="flex flex-col gap-3">
              <div className="relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
                  <Search className="w-4 h-4 text-gray-500" />
                </div>
                <input
                  type="text"
                  placeholder="Buscar país ou região (ex: Brasil, Europa, Japão...)"
                  className="w-full pl-11 pr-4 py-3 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-white/20 focus:border-white/20 placeholder:text-gray-500 transition-all"
                  value={searchCountry}
                  onChange={(e) => onSearchChange(e.target.value)}
                />
              </div>

              {selectedLocation && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">
                    {selectedLocation.isRegion ? 'Região:' : 'País:'}
                  </span>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 text-gray-200 rounded-full text-sm font-medium">
                    {selectedLocation.isRegion ? <Globe className="w-3.5 h-3.5" /> : <MapPin className="w-3.5 h-3.5" />}
                    <span>{selectedLocation.name}</span>
                    <button
                      onClick={onClearSelection}
                      className="ml-1 p-0.5 rounded-full hover:bg-white/10 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}

              {!selectedLocation && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs text-gray-500 mr-1 self-center">Regiões:</span>
                  {['eua', 'europa', 'asia', 'america do sul'].map((regionKey) => (
                    <button
                      key={regionKey}
                      data-testid={`region-${regionKey.replace(' ', '-')}`}
                      onClick={() => onRegionSelect(regionKey)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10 hover:border-white/20 hover:text-gray-200 transition-all cursor-pointer"
                    >
                      <Globe className="w-3 h-3" />
                      {countryData[regionKey].name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="h-64 rounded-lg overflow-hidden border border-white/10 bg-dark-surface-card relative">
              <WorldMap
                selectedCodes={selectedLocation?.codes || []}
                onCountryClick={(code) => {
                  if (COUNTRY_NAMES[code]) {
                    onCountryClick({ codes: [code], name: COUNTRY_NAMES[code], isRegion: false });
                  }
                }}
              />
              <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-[#0a0d0a] via-transparent to-transparent opacity-60" />
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Hardware & Performance */}
      {currentStep === 2 && (
        <div className="space-y-5 animate-fadeIn">
          {/* Seção 1: O que você vai fazer? */}
          <div className="space-y-3">
            <div>
              <Label className="text-gray-300 text-sm font-medium">O que você vai fazer?</Label>
              <p className="text-xs text-gray-500 mt-1">Selecione seu objetivo para recomendarmos o hardware ideal</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[
                { id: 'test', label: 'Experimentar', icon: Lightbulb, tier: 'Lento', desc: 'Testes rápidos' },
                { id: 'develop', label: 'Desenvolver', icon: Code, tier: 'Medio', desc: 'Dev diário' },
                { id: 'train', label: 'Treinar modelo', icon: Zap, tier: 'Rapido', desc: 'Fine-tuning' },
                { id: 'production', label: 'Produção', icon: Sparkles, tier: 'Ultra', desc: 'LLMs grandes' }
              ].map((useCase) => {
                const isSelected = selectedTier === useCase.tier;
                const UseCaseIcon = useCase.icon;
                return (
                  <button
                    key={useCase.id}
                    data-testid={`use-case-${useCase.id}`}
                    onClick={() => onSelectTier(useCase.tier)}
                    className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                      isSelected
                        ? "bg-brand-500/10 border-brand-500"
                        : "bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20"
                    }`}
                  >
                    <div className="flex flex-col items-center gap-2 text-center">
                      <div className={`w-8 h-8 rounded-md flex items-center justify-center ${
                        isSelected ? "bg-brand-500/20 text-brand-400" : "bg-white/5 text-gray-500"
                      }`}>
                        <UseCaseIcon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className={`text-xs font-medium ${isSelected ? "text-brand-400" : "text-gray-300"}`}>
                          {useCase.label}
                        </div>
                        <div className={`text-[10px] ${isSelected ? "text-gray-400" : "text-gray-500"}`}>
                          {useCase.desc}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Seção 2: Seleção de GPU */}
          {selectedTier && (
            <div className="space-y-3">
              <div>
                <Label className="text-gray-300 text-sm font-medium">Seleção de GPU</Label>
                <p className="text-xs text-gray-500 mt-1">Escolha uma das máquinas recomendadas</p>
              </div>

              {/* 3 máquinas recomendadas */}
              <div className="space-y-2">
                {loadingMachines ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-400 mr-2" />
                    <span className="text-sm text-gray-400">Buscando máquinas disponíveis...</span>
                  </div>
                ) : recommendedMachines.length > 0 ? (
                  <>
                    {recommendedMachines.map((machine, index) => {
                      const isSelected = selectedMachine?.id === machine.id;
                      const labelIcons = {
                        'Mais econômico': DollarSign,
                        'Melhor custo-benefício': TrendingUp,
                        'Mais rápido': Zap,
                      };
                      const LabelIcon = labelIcons[machine.label] || Star;

                      return (
                        <button
                          key={machine.id}
                          data-testid={`machine-${machine.id}`}
                          onClick={() => {
                            setSelectedMachine(machine);
                            onSelectGPU(machine.gpu_name);
                            onSelectGPUCategory('any');
                          }}
                          className={`w-full p-3 rounded-lg border text-left transition-all cursor-pointer ${
                            isSelected
                              ? "bg-brand-500/10 border-brand-500"
                              : "bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            {/* Radio indicator */}
                            <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                              isSelected ? "border-brand-500 bg-brand-500/20" : "border-white/20"
                            }`}>
                              {isSelected && <div className="w-2 h-2 rounded-full bg-brand-400" />}
                            </div>

                            {/* GPU Icon */}
                            <div className={`w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 ${
                              isSelected ? "bg-brand-500/20 text-brand-400" : "bg-white/5 text-gray-500"
                            }`}>
                              <Cpu className="w-4 h-4" />
                            </div>

                            {/* Machine Info */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={`text-sm font-medium ${isSelected ? "text-brand-400" : "text-gray-200"}`}>
                                  {machine.gpu_name}
                                </span>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                                  {machine.gpu_ram}GB
                                </span>
                                {machine.num_gpus > 1 && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                                    x{machine.num_gpus}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500">
                                <span>{machine.location}</span>
                                <span>•</span>
                                <span>{machine.provider}</span>
                                <span>•</span>
                                <span>{machine.reliability}% uptime</span>
                              </div>
                            </div>

                            {/* Label & Price */}
                            <div className="flex flex-col items-end gap-1 flex-shrink-0">
                              <div className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded ${
                                index === 1 ? "bg-brand-500/20 text-brand-400" : "bg-white/10 text-gray-400"
                              }`}>
                                <LabelIcon className="w-3 h-3" />
                                {machine.label}
                              </div>
                              <span className="text-sm font-mono font-medium text-gray-200">
                                ${machine.dph_total.toFixed(2)}/h
                              </span>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </>
                ) : (
                  <div className="text-center py-6 text-gray-500 text-sm">
                    <AlertCircle className="w-5 h-5 mx-auto mb-2 opacity-50" />
                    Nenhuma máquina encontrada para esta configuração
                  </div>
                )}

                {/* Botão expandir busca manual */}
                <button
                  onClick={() => setSelectionMode(selectionMode === 'manual' ? 'recommended' : 'manual')}
                  className="w-full p-2 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded-lg transition-all flex items-center justify-center gap-1.5"
                  data-testid="toggle-manual-selection"
                >
                  {selectionMode === 'manual' ? (
                    <>
                      <ChevronUp className="w-3.5 h-3.5" />
                      Ocultar opções avançadas
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-3.5 h-3.5" />
                      Ver mais opções
                    </>
                  )}
                </button>

                {/* Busca manual expandida (aparece abaixo) */}
                {selectionMode === 'manual' && (
                  <div className="pt-3 border-t border-white/10 space-y-3">
                    {/* Campo de busca */}
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                      <input
                        type="text"
                        placeholder="Buscar GPU (ex: RTX 4090, A100, H100...)"
                        className="w-full pl-10 pr-4 py-2.5 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all"
                        value={gpuSearchQuery}
                        onChange={(e) => setGpuSearchQuery(e.target.value)}
                        data-testid="gpu-search-input"
                      />
                    </div>

                    {/* Lista de GPUs filtradas */}
                    <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                      {filteredGPUs.length > 0 ? (
                        filteredGPUs.map((gpu) => {
                          const isSelected = selectedGPU === gpu.name;
                          return (
                            <button
                              key={gpu.name}
                              data-testid={`gpu-option-${gpu.name.toLowerCase().replace(/\s+/g, '-')}`}
                              onClick={() => {
                                onSelectGPU(gpu.name);
                                setSelectedMachine(null);
                              }}
                              className={`w-full p-2.5 rounded-lg border text-left transition-all cursor-pointer flex items-center justify-between ${
                                isSelected
                                  ? "bg-brand-500/10 border-brand-500"
                                  : "bg-white/[0.02] border-white/10 hover:bg-white/5 hover:border-white/20"
                              }`}
                            >
                              <div className="flex items-center gap-2.5">
                                <div className={`w-7 h-7 rounded flex items-center justify-center ${
                                  isSelected ? "bg-brand-500/20 text-brand-400" : "bg-white/5 text-gray-500"
                                }`}>
                                  <Cpu className="w-3.5 h-3.5" />
                                </div>
                                <div>
                                  <span className={`text-sm font-medium ${isSelected ? "text-brand-400" : "text-gray-200"}`}>
                                    {gpu.name}
                                  </span>
                                  <span className="text-[10px] text-gray-500 ml-2">{gpu.vram}</span>
                                </div>
                              </div>
                              <span className="text-xs text-gray-500">{gpu.priceRange}</span>
                            </button>
                          );
                        })
                      ) : (
                        <div className="text-center py-4 text-gray-500 text-xs">
                          Nenhuma GPU encontrada para "{gpuSearchQuery}"
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Resumo da seleção */}
          {selectedTier && (
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-md bg-brand-500/20 flex items-center justify-center flex-shrink-0">
                  {selectedTier === 'Lento' && <Gauge className="w-4 h-4 text-brand-400" />}
                  {selectedTier === 'Medio' && <Activity className="w-4 h-4 text-brand-400" />}
                  {selectedTier === 'Rapido' && <Zap className="w-4 h-4 text-brand-400" />}
                  {selectedTier === 'Ultra' && <Sparkles className="w-4 h-4 text-brand-400" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-200">
                      Tier: {tiers.find(t => t.name === selectedTier)?.name}
                    </span>
                    <span className="text-xs font-mono text-brand-400">
                      {tiers.find(t => t.name === selectedTier)?.priceRange}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
                    <span>{tiers.find(t => t.name === selectedTier)?.gpu}</span>
                    <span className="mx-1">•</span>
                    <span>{tiers.find(t => t.name === selectedTier)?.vram}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 3: Estratégia de Failover */}
      {currentStep === 3 && (
        <div className="space-y-5 animate-fadeIn">
          <div>
            <div className="flex items-center gap-2">
              <Label className="text-gray-300 text-sm font-medium">Estratégia de Failover</Label>
              <Tooltip text="Recuperação automática em caso de falha da GPU">
                <HelpCircle className="w-3.5 h-3.5 text-gray-500 hover:text-gray-400 cursor-help" />
              </Tooltip>
            </div>
            <p className="text-xs text-gray-500 mt-1">Como recuperar automaticamente se a máquina falhar?</p>
          </div>

          <div className="space-y-3">
            {failoverOptions.map((option) => {
              const isSelected = failoverStrategy === option.id;
              const OptionIcon = option.icon;
              const isDisabled = option.comingSoon;
              return (
                <button
                  key={option.id}
                  data-testid={`failover-option-${option.id}`}
                  onClick={() => !isDisabled && setFailoverStrategy(option.id)}
                  disabled={isDisabled}
                  className={`w-full p-4 rounded-lg border text-left transition-all ${
                    isDisabled
                      ? "bg-white/[0.02] border-white/5 cursor-not-allowed opacity-60"
                      : isSelected
                        ? "bg-brand-500/10 border-brand-500"
                        : "bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isDisabled ? "bg-white/5 text-gray-600" : isSelected ? "bg-white/20 text-white" : "bg-white/5 text-gray-500"
                    }`}>
                      <OptionIcon className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className={`text-sm font-medium ${isDisabled ? "text-gray-500" : isSelected ? "text-gray-100" : "text-gray-300"}`}>
                          {option.name}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                          {option.provider}
                        </span>
                        {option.recommended && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                            Recomendado
                          </span>
                        )}
                        {option.comingSoon && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">
                            Em breve
                          </span>
                        )}
                      </div>
                      <p className={`text-xs mb-3 ${isDisabled ? "text-gray-600" : "text-gray-400"}`}>{option.description}</p>

                      {/* Features list */}
                      {option.features && (
                        <div className="grid grid-cols-2 gap-1 mb-3">
                          {option.features.map((feature, idx) => (
                            <div key={idx} className="flex items-center gap-1.5 text-[10px]">
                              <Check className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                              <span className={isDisabled ? "text-gray-600" : "text-gray-400"}>{feature}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Métricas em grid */}
                      <div className="grid grid-cols-3 gap-2 text-[10px]">
                        <div className="flex items-center gap-1">
                          <Timer className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                          <span className={isDisabled ? "text-gray-600" : "text-gray-500"}>Recovery:</span>
                          <span className={`font-medium ${isDisabled ? "text-gray-600" : isSelected ? 'text-gray-200' : 'text-gray-400'}`}>
                            {option.recoveryTime}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <HardDrive className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                          <span className={isDisabled ? "text-gray-600" : "text-gray-500"}>Perda:</span>
                          <span className={`font-medium ${isDisabled ? "text-gray-600" : option.dataLoss === 'Zero' ? 'text-emerald-400' : 'text-gray-400'}`}>
                            {option.dataLoss}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <DollarSign className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                          <span className={isDisabled ? "text-gray-600" : "text-gray-500"}>Custo:</span>
                          <span className={`font-medium ${isDisabled ? "text-gray-600" : isSelected ? 'text-gray-200' : 'text-gray-400'}`}>
                            {option.costHour}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                      isDisabled ? "border-white/10" : isSelected ? "border-white/40 bg-white/20" : "border-white/20"
                    }`}>
                      {isSelected && !isDisabled && <div className="w-2 h-2 rounded-full bg-white" />}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Detalhes da estratégia selecionada */}
          {selectedFailover && (
            <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-3">
              <h4 className="text-xs font-medium text-gray-300">Como funciona</h4>
              <p className="text-xs text-gray-400">{selectedFailover.howItWorks}</p>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500">Requisitos:</span>
                <span className="text-gray-400">{selectedFailover.requirements}</span>
              </div>

              <div className="pt-3 border-t border-white/10">
                <h4 className="text-xs font-medium text-gray-400 mb-2">Resumo da configuração</h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Região</span>
                    <span className="text-gray-300">{selectedLocation?.name || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Performance</span>
                    <span className="text-gray-300">{selectedTier || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Failover</span>
                    <span className="text-gray-300">{selectedFailover.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Custo extra</span>
                    <span className="text-gray-300">{selectedFailover.costHour}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 4: Provisioning */}
      {currentStep === 4 && (
        <div className="space-y-5 animate-fadeIn">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-500/10 border border-brand-500/30 mb-4">
              {provisioningWinner ? (
                <Check className="w-7 h-7 text-brand-400" />
              ) : (
                <Loader2 className="w-7 h-7 text-brand-400 animate-spin" />
              )}
            </div>
            <h3 className="text-lg font-semibold text-gray-100 mb-1">
              {provisioningWinner ? 'Máquina Conectada!' : 'Provisionando Máquinas...'}
            </h3>
            <p className="text-xs text-gray-400">
              {provisioningWinner
                ? 'Sua máquina está pronta para uso'
                : `Testando ${provisioningCandidates.length} máquinas simultaneamente. A primeira a responder será selecionada.`}
            </p>

            {/* Round indicator and Timer */}
            {!provisioningWinner && provisioningCandidates.length > 0 && (
              <div className="flex items-center justify-center gap-3 mt-3 text-xs flex-wrap">
                {/* Round indicator */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/30">
                  <Rocket className="w-3.5 h-3.5 text-purple-400" />
                  <span className="text-purple-400 font-medium">Round {currentRound}/{maxRounds}</span>
                </div>
                {/* Timer */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-gray-300 font-mono">{formatTime(elapsedTime)}</span>
                </div>
                {/* ETA */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/30">
                  <Timer className="w-3.5 h-3.5 text-brand-400" />
                  <span className="text-brand-400">{getETA()}</span>
                </div>
              </div>
            )}
          </div>

          {/* Race Track - Grid layout for compact display */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
            {provisioningCandidates.map((candidate, index) => {
              const isWinner = provisioningWinner?.id === candidate.id;
              const isCancelled = provisioningWinner && !isWinner;
              const status = candidate.status;

              return (
                <div
                  key={candidate.id}
                  data-testid={`provisioning-candidate-${index}`}
                  className={`relative overflow-hidden rounded-lg border transition-all ${
                    isWinner
                      ? 'border-brand-500 bg-brand-500/10'
                      : isCancelled
                      ? 'border-white/5 bg-white/[0.02] opacity-50'
                      : status === 'failed'
                      ? 'border-red-500/30 bg-red-500/5'
                      : 'border-white/10 bg-white/5'
                  }`}
                >
                  {/* Progress bar for connecting state */}
                  {status === 'connecting' && !provisioningWinner && (
                    <div
                      className="absolute bottom-0 left-0 h-0.5 bg-brand-500 transition-all duration-300 ease-out"
                      style={{ width: `${candidate.progress || 0}%` }}
                    />
                  )}

                  <div className="p-3 flex items-center gap-3">
                    {/* Position/Status Icon */}
                    <div className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center font-bold text-sm ${
                      isWinner
                        ? 'bg-brand-500/20 text-brand-400'
                        : isCancelled
                        ? 'bg-white/5 text-gray-600'
                        : status === 'failed'
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-white/5 text-gray-400'
                    }`}>
                      {isWinner ? (
                        <Check className="w-4 h-4" />
                      ) : isCancelled ? (
                        <X className="w-4 h-4" />
                      ) : status === 'failed' ? (
                        <X className="w-4 h-4" />
                      ) : (
                        <span>{index + 1}</span>
                      )}
                    </div>

                    {/* Machine Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Cpu className={`w-3.5 h-3.5 ${isWinner ? 'text-brand-400' : 'text-gray-500'}`} />
                        <span className={`text-sm font-medium truncate ${isWinner ? 'text-gray-100' : 'text-gray-300'}`}>
                          {candidate.gpu_name}
                        </span>
                        {candidate.num_gpus > 1 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                            x{candidate.num_gpus}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500">
                        <span>{candidate.gpu_ram?.toFixed(0)}GB</span>
                        <span>•</span>
                        <span>{candidate.geolocation || candidate.location || 'Unknown'}</span>
                        <span>•</span>
                        <span className="text-brand-400 font-medium">${candidate.dph_total?.toFixed(2)}/h</span>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div className="flex-shrink-0">
                      {isWinner ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-brand-500/20 text-brand-400 text-[10px] font-medium">
                          <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                          Conectado
                        </span>
                      ) : isCancelled ? (
                        <span className="text-[10px] text-gray-600">Cancelado</span>
                      ) : status === 'failed' ? (
                        <div className="flex flex-col items-end">
                          <span className="text-[10px] text-red-400">Falhou</span>
                          {candidate.errorMessage && (
                            <span className="text-[9px] text-red-400/70">{candidate.errorMessage}</span>
                          )}
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-400">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Conectando...
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary when winner is selected */}
          {provisioningWinner && (
            <div className="p-4 rounded-lg bg-brand-500/5 border border-brand-500/20">
              <h4 className="text-xs font-medium text-brand-400 mb-3">Resumo da Instância</h4>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">GPU</span>
                  <span className="text-gray-200">{provisioningWinner.gpu_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">VRAM</span>
                  <span className="text-gray-200">{provisioningWinner.gpu_ram?.toFixed(0)}GB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Localização</span>
                  <span className="text-gray-200">{provisioningWinner.geolocation || provisioningWinner.location}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Custo</span>
                  <span className="text-brand-400 font-medium">${provisioningWinner.dph_total?.toFixed(2)}/h</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Failover</span>
                  <span className="text-gray-200">{selectedFailover?.name || '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Custo extra</span>
                  <span className="text-gray-200">{selectedFailover?.costHour || '-'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between pt-4 border-t border-white/10">
        {/* Left button: Voltar or Cancelar */}
        {currentStep === 4 ? (
          <Button
            onClick={() => {
              if (onCancelProvisioning) onCancelProvisioning();
              setCurrentStep(3);
            }}
            variant="ghost"
            className="px-4 py-2 text-gray-400 hover:text-gray-200"
          >
            <X className="w-4 h-4 mr-1" />
            {provisioningWinner ? 'Buscar Outras' : 'Cancelar'}
          </Button>
        ) : (
          <Button
            onClick={handlePrev}
            disabled={currentStep === 1}
            variant="ghost"
            className={`px-4 py-2 text-gray-400 hover:text-gray-200 ${currentStep === 1 ? 'opacity-0 pointer-events-none' : ''}`}
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Voltar
          </Button>
        )}

        {/* Right button: Próximo, Iniciar, or Usar Esta Máquina */}
        {currentStep === 4 ? (
          <Button
            onClick={() => provisioningWinner && onCompleteProvisioning && onCompleteProvisioning(provisioningWinner)}
            disabled={!provisioningWinner}
            className="px-5 py-2 bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 disabled:opacity-40"
          >
            {provisioningWinner ? (
              <>
                <Check className="w-4 h-4 mr-2" />
                Usar Esta Máquina
              </>
            ) : (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Conectando...
              </>
            )}
          </Button>
        ) : currentStep < 3 ? (
          <Button
            onClick={handleNext}
            disabled={!isStepComplete(currentStep)}
            className="px-5 py-2 bg-white/10 hover:bg-white/15 text-gray-200 border border-white/10 disabled:opacity-40"
          >
            Próximo
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        ) : (
          <Button
            onClick={handleNext}
            disabled={!isStepComplete(currentStep) || loading}
            className="px-5 py-2 bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 disabled:opacity-40"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Iniciando...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 mr-2" />
                Iniciar
              </>
            )}
          </Button>
        )}
      </div>
    </CardContent>
  );
};

export default WizardForm;
