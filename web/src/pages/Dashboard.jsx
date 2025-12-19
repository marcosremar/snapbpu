import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VectorMap } from '@react-jvectormap/core';
import { worldMill } from '@react-jvectormap/world';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import OnboardingWizard from '../components/onboarding/OnboardingWizard';
import {
  Cpu, Server, Wifi, DollarSign, Shield, HardDrive,
  Activity, Search, RotateCcw, Sliders, Wand2,
  Gauge, Globe, Zap, Monitor, ChevronDown, ChevronLeft, ChevronRight, Sparkles,
  Send, Bot, User, Loader2
} from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Input } from '../components/ui/input';
import { Checkbox } from '../components/ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Tabs as TabsUI, TabsList as TabsListUI, TabsTrigger as TabsTriggerUI } from '../components/ui/tabs';
import { Label } from '../components/ui/label';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { MetricCard, MetricsGrid, Avatar, AvatarImage, AvatarFallback, Popover, PopoverTrigger, PopoverContent } from '../components/ui/dumont-ui';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { SkeletonList } from '../components/Skeleton';
import { useTheme } from '../context/ThemeContext';
const API_BASE = import.meta.env.VITE_API_URL || '';

const regionToApiRegion = { 'EUA': 'US', 'Europa': 'EU', 'Asia': 'ASIA', 'AmericaDoSul': 'SA', 'Global': '' };

// Todas as GPUs disponíveis no Vast.ai
const GPU_OPTIONS = [
  { value: 'any', label: 'Qualquer GPU' },
  // Consumer
  { value: 'RTX_3060', label: 'RTX 3060' },
  { value: 'RTX_3060_Ti', label: 'RTX 3060 Ti' },
  { value: 'RTX_3070', label: 'RTX 3070' },
  { value: 'RTX_3070_Ti', label: 'RTX 3070 Ti' },
  { value: 'RTX_3080', label: 'RTX 3080' },
  { value: 'RTX_3080_Ti', label: 'RTX 3080 Ti' },
  { value: 'RTX_3090', label: 'RTX 3090' },
  { value: 'RTX_3090_Ti', label: 'RTX 3090 Ti' },
  { value: 'RTX_4060', label: 'RTX 4060' },
  { value: 'RTX_4060_Ti', label: 'RTX 4060 Ti' },
  { value: 'RTX_4070', label: 'RTX 4070' },
  { value: 'RTX_4070_Ti', label: 'RTX 4070 Ti' },
  { value: 'RTX_4070_Ti_Super', label: 'RTX 4070 Ti Super' },
  { value: 'RTX_4080', label: 'RTX 4080' },
  { value: 'RTX_4080_Super', label: 'RTX 4080 Super' },
  { value: 'RTX_4090', label: 'RTX 4090' },
  { value: 'RTX_5090', label: 'RTX 5090' },
  // Datacenter
  { value: 'A100', label: 'A100' },
  { value: 'A100_PCIE', label: 'A100 PCIe' },
  { value: 'A100_SXM4', label: 'A100 SXM4' },
  { value: 'A100_80GB', label: 'A100 80GB' },
  { value: 'H100', label: 'H100' },
  { value: 'H100_PCIe', label: 'H100 PCIe' },
  { value: 'H100_SXM5', label: 'H100 SXM5' },
  { value: 'A6000', label: 'RTX A6000' },
  { value: 'A5000', label: 'RTX A5000' },
  { value: 'A4000', label: 'RTX A4000' },
  { value: 'A4500', label: 'RTX A4500' },
  { value: 'L40', label: 'L40' },
  { value: 'L40S', label: 'L40S' },
  { value: 'V100', label: 'V100' },
  { value: 'V100_SXM2', label: 'V100 SXM2' },
  { value: 'Tesla_T4', label: 'Tesla T4' },
  { value: 'P100', label: 'P100' },
];

// GPU Categories para o seletor visual - por tipo de workload
const GPU_CATEGORIES = [
  {
    id: 'any',
    name: 'Automático',
    icon: 'auto',
    description: 'Melhor custo-benefício',
    color: 'gray',
    gpus: []
  },
  {
    id: 'inference',
    name: 'Inferência',
    icon: 'inference',
    description: 'Deploy de modelos / APIs',
    color: 'green',
    gpus: ['RTX_4060', 'RTX_4060_Ti', 'RTX_4070', 'RTX_3060', 'RTX_3060_Ti', 'RTX_3070', 'RTX_3070_Ti', 'Tesla_T4', 'A4000', 'L40']
  },
  {
    id: 'training',
    name: 'Treinamento',
    icon: 'training',
    description: 'Fine-tuning / ML Training',
    color: 'blue',
    gpus: ['RTX_4080', 'RTX_4080_Super', 'RTX_4090', 'RTX_3080', 'RTX_3080_Ti', 'RTX_3090', 'RTX_3090_Ti', 'RTX_5090', 'A5000', 'A6000', 'L40S']
  },
  {
    id: 'hpc',
    name: 'HPC / LLMs',
    icon: 'hpc',
    description: 'Modelos grandes / Multi-GPU',
    color: 'blue',
    gpus: ['A100', 'A100_PCIE', 'A100_SXM4', 'A100_80GB', 'H100', 'H100_PCIe', 'H100_SXM5', 'V100', 'V100_SXM2']
  },
];

const REGION_OPTIONS = [
  { value: 'any', label: 'Todas as Regiões' },
  { value: 'US', label: 'Estados Unidos' },
  { value: 'EU', label: 'Europa' },
  { value: 'ASIA', label: 'Ásia' },
  { value: 'SA', label: 'América do Sul' },
  { value: 'OC', label: 'Oceania' },
  { value: 'AF', label: 'África' },
];

const CUDA_OPTIONS = [
  { value: 'any', label: 'Qualquer versão' },
  { value: '11.0', label: 'CUDA 11.0+' },
  { value: '11.7', label: 'CUDA 11.7+' },
  { value: '11.8', label: 'CUDA 11.8+' },
  { value: '12.0', label: 'CUDA 12.0+' },
  { value: '12.1', label: 'CUDA 12.1+' },
  { value: '12.2', label: 'CUDA 12.2+' },
  { value: '12.4', label: 'CUDA 12.4+' },
];

const ORDER_OPTIONS = [
  { value: 'dph_total', label: 'Preço (menor primeiro)' },
  { value: 'dlperf', label: 'DL Performance (maior)' },
  { value: 'gpu_ram', label: 'GPU RAM (maior)' },
  { value: 'inet_down', label: 'Download (maior)' },
  { value: 'reliability', label: 'Confiabilidade' },
  { value: 'pcie_bw', label: 'PCIe Bandwidth' },
];

const RENTAL_TYPE_OPTIONS = [
  { value: 'on-demand', label: 'On-Demand' },
  { value: 'bid', label: 'Bid/Interruptible' },
];

const WorldMap = ({ activeRegion }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Datacenter markers for each region
  const datacenterMarkers = [
    { latLng: [37.77, -122.42], name: 'San Francisco, EUA', region: 'EUA' },
    { latLng: [40.71, -74.01], name: 'New York, EUA', region: 'EUA' },
    { latLng: [51.51, -0.13], name: 'London, UK', region: 'Europa' },
    { latLng: [48.86, 2.35], name: 'Paris, França', region: 'Europa' },
    { latLng: [52.52, 13.40], name: 'Berlin, Alemanha', region: 'Europa' },
    { latLng: [35.68, 139.69], name: 'Tokyo, Japão', region: 'Asia' },
    { latLng: [1.35, 103.82], name: 'Singapore', region: 'Asia' },
    { latLng: [-23.55, -46.63], name: 'São Paulo, Brasil', region: 'AmericaDoSul' },
  ];

  // Filter markers based on active region
  const visibleMarkers = activeRegion === 'Global'
    ? datacenterMarkers
    : datacenterMarkers.filter(m => m.region === activeRegion);

  return (
    <div className="relative w-full h-full">
      <VectorMap
        map={worldMill}
        backgroundColor="transparent"
        markerStyle={{
          initial: {
            fill: '#3b82f6',
            r: 5,
          },
          hover: {
            fill: '#60a5fa',
            r: 7,
          },
        }}
        markers={visibleMarkers.map(m => ({
          latLng: m.latLng,
          name: m.name,
          style: { fill: '#3b82f6', borderWidth: 1, borderColor: 'white' },
        }))}
        zoomOnScroll={false}
        zoomMax={12}
        zoomMin={1}
        regionStyle={{
          initial: {
            fill: isDark ? '#374151' : '#e2e8f0',
            fillOpacity: 1,
            stroke: isDark ? '#4b5563' : '#cbd5e1',
            strokeWidth: 0.5,
            strokeOpacity: 1,
          },
          hover: {
            fillOpacity: 0.8,
            cursor: 'pointer',
            fill: '#3b82f6',
          },
          selected: {
            fill: '#3b82f6',
          },
        }}
      />
    </div>
  );
};

const SpeedBars = ({ level, color }) => {
  const colors = { gray: '#6b7280', yellow: '#eab308', orange: '#ea580c', green: '#4ade80' };
  return (
    <div className="flex items-end gap-px">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} style={{ width: '3px', height: `${4 + i * 3}px`, backgroundColor: i <= level ? colors[color] : '#374151', borderRadius: '1px' }} />
      ))}
    </div>
  );
};

const TierCard = ({ tier, isSelected, onClick }) => (
  <Popover>
    <PopoverTrigger asChild>
      <button onClick={onClick}
        className={`flex flex-col p-3 md:p-4 rounded-lg border text-left transition-all shadow-theme-sm ${isSelected ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10' : 'border-gray-200 dark:border-dark-surface-border bg-white dark:bg-dark-surface-card hover:border-brand-300 dark:hover:border-brand-500/50'}`}
        style={{ minHeight: '160px' }}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-gray-900 dark:text-white font-semibold text-xs md:text-sm tracking-tight">{tier.name}</span>
          <SpeedBars level={tier.level} color={tier.color} />
        </div>
        <div className="text-green-400 text-[10px] md:text-xs font-mono font-medium tracking-tight">{tier.speed}</div>
        <div className="text-gray-500 dark:text-gray-400 text-[9px] md:text-[10px] mb-1.5">{tier.time}</div>
        <div className="text-gray-600 dark:text-gray-500 text-[9px] md:text-[10px] leading-relaxed">{tier.gpu}</div>
        <div className="text-gray-600 dark:text-gray-500 text-[9px] md:text-[10px] leading-relaxed">{tier.vram}</div>
        <div className="text-yellow-400/80 text-[9px] md:text-[10px] font-mono font-medium mt-1.5">{tier.priceRange}</div>
        <div className="mt-auto pt-2 border-t border-gray-200 dark:border-gray-700/30">
          <p className="text-gray-500 dark:text-gray-400 text-[8px] md:text-[9px] leading-relaxed">{tier.description}</p>
        </div>
      </button>
    </PopoverTrigger>
    <PopoverContent align="start" className="w-64">
      <div className="space-y-3">
        <div className="flex items-center gap-2 mb-3">
          <Cpu className="w-5 h-5 text-brand-500" />
          <span className="text-sm font-semibold text-gray-900 dark:text-white">{tier.name}</span>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 dark:text-gray-400">GPU:</span>
            <span className="text-gray-900 dark:text-white font-medium">{tier.gpu}</span>
          </div>

          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 dark:text-gray-400">VRAM:</span>
            <span className="text-gray-900 dark:text-white font-medium">{tier.vram}</span>
          </div>

          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 dark:text-gray-400">Velocidade:</span>
            <span className="text-brand-500 font-medium">{tier.speed}</span>
          </div>

          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 dark:text-gray-400">Tempo Treino:</span>
            <span className="text-gray-900 dark:text-white font-medium">{tier.time}</span>
          </div>

          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-400">Preço:</span>
            <span className="text-yellow-400 font-medium">{tier.priceRange}</span>
          </div>
        </div>

        <div className="pt-2 border-t border-gray-200 dark:border-gray-200 dark:border-gray-700/30">
          <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{tier.description}</p>
        </div>
      </div>
    </PopoverContent>
  </Popover>
);

// Componente do Seletor de GPU Visual
const GPUSelector = ({ selectedGPU, onSelectGPU, selectedCategory, onSelectCategory }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getCategoryIcon = (iconType, isActive) => {
    const colorClass = isActive ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400';
    switch (iconType) {
      case 'auto':
        return <Zap className={`w-4 h-4 ${colorClass}`} />;
      case 'inference':
        return <Activity className={`w-4 h-4 ${colorClass}`} />;
      case 'training':
        return <Gauge className={`w-4 h-4 ${colorClass}`} />;
      case 'hpc':
        return <Server className={`w-4 h-4 ${colorClass}`} />;
      default:
        return <Cpu className={`w-4 h-4 ${colorClass}`} />;
    }
  };

  const getCategoryBgColor = (color, isActive) => {
    if (!isActive) return 'bg-gray-100 dark:bg-dark-surface-secondary';
    switch (color) {
      case 'green': return 'bg-success-50 dark:bg-success-600/30 border-success-500';
      case 'blue': return 'bg-brand-50 dark:bg-brand-600/30 border-brand-500';
      default: return 'bg-gray-100 dark:bg-gray-600/30 border-gray-400';
    }
  };

  const getIconBgColor = (color) => {
    switch (color) {
      case 'green': return 'bg-green-500/20';
      case 'blue': return 'bg-brand-500/20';
      default: return 'bg-gray-500/20';
    }
  };

  const currentCategory = GPU_CATEGORIES.find(c => c.id === selectedCategory) || GPU_CATEGORIES[0];
  const availableGPUs = currentCategory.gpus.length > 0
    ? GPU_OPTIONS.filter(g => currentCategory.gpus.includes(g.value))
    : [];

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-500/20 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <CardTitle className="text-sm">GPU</CardTitle>
            <CardDescription className="text-[10px]">Selecione o tipo</CardDescription>
          </div>
        </div>
        {selectedGPU !== 'any' && (
          <span className="px-2 py-1 rounded-full bg-green-100 dark:bg-green-500/20 text-green-600 dark:text-green-400 text-[10px] font-medium">
            {GPU_OPTIONS.find(g => g.value === selectedGPU)?.label}
          </span>
        )}
      </CardHeader>

      {/* Category Grid */}
      <CardContent className="p-3">
        <div className="grid grid-cols-2 gap-2">
          {GPU_CATEGORIES.map((cat) => {
            const isActive = selectedCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => {
                  onSelectCategory(cat.id);
                  if (cat.id === 'any') {
                    onSelectGPU('any');
                    setIsExpanded(false);
                  } else {
                    setIsExpanded(true);
                  }
                }}
                className={`p-3 rounded-lg border transition-all text-left ${
                  isActive
                    ? getCategoryBgColor(cat.color, true)
                    : 'border-gray-200 hover:border-gray-300 dark:border-dark-surface-border bg-gray-100 dark:bg-dark-surface-secondary'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-6 h-6 rounded-md ${getIconBgColor(cat.color)} flex items-center justify-center`}>
                    {getCategoryIcon(cat.icon, isActive)}
                  </div>
                  <span className={`text-xs font-semibold ${isActive ? 'text-white' : 'text-gray-300'}`}>
                    {cat.name}
                  </span>
                </div>
                <p className={`text-[9px] ${isActive ? 'text-gray-300' : 'text-gray-500'}`}>
                  {cat.description}
                </p>
              </button>
            );
          })}
        </div>

        {/* GPU Dropdown - aparece quando categoria específica selecionada */}
        {isExpanded && selectedCategory !== 'any' && availableGPUs.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50">
            <Label className="text-[10px] text-gray-500 dark:text-gray-400 mb-2 block">Modelo Específico (opcional)</Label>
            <Select value={selectedGPU} onValueChange={onSelectGPU}>
              <SelectTrigger className="bg-gray-100 dark:bg-dark-surface-secondary border-gray-200 dark:border-dark-surface-border h-9 text-xs">
                <SelectValue placeholder="Qualquer modelo da categoria" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Qualquer {currentCategory.name}</SelectItem>
                {availableGPUs.map(gpu => (
                  <SelectItem key={gpu.value} value={gpu.value}>{gpu.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Componente do AI Wizard Chat
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
        // AI needs more info, show questions
        const questionsText = data.questions.join('\n\n');
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Preciso de mais algumas informações para fazer uma recomendação precisa:\n\n${questionsText}`
        }]);
      } else {
        // Handle all stages (research, options, selection, reservation, or legacy recommendation)
        const stage = data.stage || (data.recommendation ? 'recommendation' : 'unknown');
        let messageContent = data.explanation || (data.recommendation?.explanation) || 'Processamento concluído.';
        
        // Prepare payload based on stage
        const msgPayload = {
          role: 'assistant',
          content: messageContent,
          stage: stage,
          data: data, // Store full data for rendering
          recommendation: data.recommendation, // Keep for legacy compatibility
          showCards: true
        };

        setMessages(prev => [...prev, msgPayload]);
        
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
      // If specific GPU option selected, use it
      if (gpuOption) {
        onSearchWithFilters({
          gpu_name: gpuOption.gpu,
          min_gpu_ram: parseInt(gpuOption.vram) || 8
        });
      } else if (recommendation.gpu_options && recommendation.gpu_options.length > 0) {
        // Use recommended option (middle one)
        const recOption = recommendation.gpu_options.find(o => o.tier === 'recomendada') || recommendation.gpu_options[1];
        onSearchWithFilters({
          gpu_name: recOption.gpu,
          min_gpu_ram: parseInt(recOption.vram) || 8
        });
      } else if (recommendation.recommended_gpus) {
        // Fallback to old format
        onSearchWithFilters({
          gpu_name: recommendation.recommended_gpus[0] || 'any',
          min_gpu_ram: recommendation.min_vram_gb,
          tier: recommendation.tier_suggestion
        });
      }
    }
  };

  if (compact) {
    // COMPACT MODE: Minimal layout for sidebar
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
        <div className="flex-1 overflow-y-auto space-y-2 min-h-[200px]" style={{ paddingLeft: '0.5rem', paddingRight: '0.5rem', paddingTop: '0.5rem', paddingBottom: '0.5rem' }}>
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
                    className="px-1.5 py-0.5 text-[9px] text-gray-400 bg-gray-100 dark:bg-gray-800/40 rounded hover:bg-gray-200 dark:bg-gray-700/50 transition-colors text-left"
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
              msg.role === 'user'
                ? 'ai-wizard-message-user'
                : 'ai-wizard-message-assistant'
            }`}>
              {/* Text content - Compact */}
              <div className="prose prose-invert prose-sm max-w-none prose-p:my-0.5 prose-headings:my-1 prose-strong:text-green-400 prose-ul:my-0.5 prose-li:my-0 prose-hr:border-gray-200 dark:border-gray-700 prose-h2:text-xs prose-h3:text-[9px] prose-h4:text-[8px]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              </div>

              {/* Interactive Stage Displays - Minimal in compact mode */}
              {msg.showCards && (
                <div className="mt-1 pt-1 border-t border-gray-200 dark:border-gray-700/30">
                  {/* Legacy Recommendation */}
                  {(msg.stage === 'recommendation' || (!msg.stage && msg.recommendation?.gpu_options)) && (
                    <GPUWizardDisplay
                      recommendation={msg.recommendation}
                      onSearch={(opt) => applyRecommendation(opt)}
                    />
                  )}

                  {/* Research Stage */}
                  {msg.stage === 'research' && msg.data?.research_results && (
                    <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-3 text-xs space-y-2">
                      <div className="font-semibold text-brand-400">Resultados da Pesquisa:</div>
                      {msg.data.research_results.findings && (
                        <div><span className="text-gray-400">Descobertas:</span> {msg.data.research_results.findings}</div>
                      )}
                      {msg.data.research_results.benchmarks && (
                        <div><span className="text-gray-400">Benchmarks:</span> {msg.data.research_results.benchmarks}</div>
                      )}
                      {msg.data.research_results.prices && (
                        <div><span className="text-gray-400">Preços:</span> {msg.data.research_results.prices}</div>
                      )}
                    </div>
                  )}

                  {/* Options Stage */}
                  {msg.stage === 'options' && msg.data?.price_options && (
                    <div className="space-y-2">
                      <div className="font-semibold text-brand-400 text-xs mb-2">Opções de Preço Encontradas:</div>
                      <div className="grid grid-cols-1 gap-2">
                        {msg.data.price_options.map((opt, idx) => (
                          <div key={idx} className="bg-gray-100 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-brand-500/50 transition-colors">
                            <div className="flex justify-between items-start mb-1">
                              <span className="font-bold text-gray-900 dark:text-white text-sm">{opt.tier}</span>
                              <span className="text-green-400 font-mono text-xs">{opt.price_per_hour}</span>
                            </div>
                            <div className="text-gray-400 text-xs mb-1">{opt.gpus.join(', ')}</div>
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
                  )}

                  {/* Selection Stage */}
                  {msg.stage === 'selection' && msg.data?.machines && (
                    <div className="space-y-2">
                      <div className="font-semibold text-green-400 text-xs mb-2">Máquinas Disponíveis:</div>
                      <div className="grid grid-cols-1 gap-2">
                        {msg.data.machines.map((machine, idx) => (
                          <div key={idx} className="bg-gray-100 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-green-500/50 transition-colors">
                            <div className="flex justify-between items-center mb-1">
                              <span className="font-bold text-gray-900 dark:text-white text-xs">{machine.gpu}</span>
                              <span className="text-green-400 font-mono text-xs">{machine.price_per_hour}</span>
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
                              className="w-full py-1.5 text-[10px] font-medium bg-green-600/20 text-green-400 rounded hover:bg-green-600/30 transition-colors"
                            >
                              Reservar Agora
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reservation Stage */}
                  {msg.stage === 'reservation' && msg.data?.reservation && (
                    <div className="bg-green-900/20 border border-green-500/30 p-4 rounded-lg text-center">
                      <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
                        <Zap className="w-5 h-5 text-green-400" />
                      </div>
                      <h4 className="text-green-400 font-bold text-sm mb-1">Pronto para Reservar!</h4>
                      <p className="text-gray-300 text-xs mb-3">{msg.data.reservation.details}</p>
                      <button className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded-lg transition-colors shadow-lg shadow-green-900/20">
                        Confirmar e Pagar
                      </button>
                    </div>
                  )}

                  {/* Optimization Tips (keep existing) */}
                  {msg.recommendation?.optimization_tips && msg.recommendation.optimization_tips.length > 0 && (
                    <div className="mt-3 p-2 rounded bg-sky-900/15 border border-sky-700/20">
                      <div className="text-[10px] text-sky-400/80 font-semibold mb-1">Dicas de Otimização:</div>
                      <ul className="text-[10px] text-gray-400 space-y-0.5">
                        {msg.recommendation.optimization_tips.map((tip, idx) => (
                          <li key={idx}>• {tip}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Fallback: Simple search button if no visual cards */}
              {msg.recommendation && !msg.showCards && (
                <button
                  onClick={() => applyRecommendation()}
                  className="mt-3 w-full py-2 px-3 text-xs font-medium text-white bg-blue-600/50 hover:bg-brand-600/70 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <Search className="w-3 h-3" />
                  Buscar GPUs Recomendadas
                </button>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-green-400" />
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

  // FULL MODE: Regular layout
  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800/50">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500/20 to-blue-600/20 flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h3 className="text-gray-900 dark:text-white font-semibold text-sm">AI GPU Advisor</h3>
          <p className="text-gray-500 text-[10px]">Descreva seu projeto e receba recomendações</p>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[300px] max-h-[500px]">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Bot className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 text-sm mb-2">Olá! Sou seu assistente de GPU.</p>
            <p className="text-gray-500 text-xs">Descreva seu projeto e eu vou recomendar a GPU ideal.</p>
            <div className="mt-4 space-y-2">
              <p className="text-gray-600 text-[10px]">Exemplos:</p>
              <div className="flex flex-wrap gap-2 justify-center">
                {['Fine-tuning LLaMA 7B', 'API de Stable Diffusion', 'Treinar modelo de visão'].map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setInputValue(ex)}
                    className="px-2 py-1 text-[10px] text-gray-400 bg-gray-100 dark:bg-gray-800/50 rounded hover:bg-gray-200 dark:bg-gray-700/50 transition-colors"
                  >
                    {ex}
                  </button>
                ))}
              </div>
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
              msg.role === 'user'
                ? 'ai-wizard-message-user'
                : 'ai-wizard-message-assistant'
            }`}>
              {/* Text content */}
              <div className="text-xs prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-strong:text-green-400 prose-ul:my-1 prose-li:my-0 prose-hr:border-gray-200 dark:border-gray-700 prose-h2:text-base prose-h3:text-sm prose-h4:text-xs mb-3">
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

                  {/* Research Stage */}
                  {msg.stage === 'research' && msg.data?.research_results && (
                    <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-3 text-xs space-y-2">
                      <div className="font-semibold text-brand-400">Resultados da Pesquisa:</div>
                      {msg.data.research_results.findings && (
                        <div><span className="text-gray-400">Descobertas:</span> {msg.data.research_results.findings}</div>
                      )}
                      {msg.data.research_results.benchmarks && (
                        <div><span className="text-gray-400">Benchmarks:</span> {msg.data.research_results.benchmarks}</div>
                      )}
                      {msg.data.research_results.prices && (
                        <div><span className="text-gray-400">Preços:</span> {msg.data.research_results.prices}</div>
                      )}
                    </div>
                  )}

                  {/* Options Stage */}
                  {msg.stage === 'options' && msg.data?.price_options && (
                    <div className="space-y-2">
                      <div className="font-semibold text-brand-400 text-xs mb-2">Opções de Preço Encontradas:</div>
                      <div className="grid grid-cols-1 gap-2">
                        {msg.data.price_options.map((opt, idx) => (
                          <div key={idx} className="bg-gray-100 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-brand-500/50 transition-colors">
                            <div className="flex justify-between items-start mb-1">
                              <span className="font-bold text-gray-900 dark:text-white text-sm">{opt.tier}</span>
                              <span className="text-green-400 font-mono text-xs">{opt.price_per_hour}</span>
                            </div>
                            <div className="text-gray-400 text-xs mb-1">{opt.gpus.join(', ')}</div>
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
                  )}

                  {/* Selection Stage */}
                  {msg.stage === 'selection' && msg.data?.machines && (
                    <div className="space-y-2">
                      <div className="font-semibold text-green-400 text-xs mb-2">Máquinas Disponíveis:</div>
                      <div className="grid grid-cols-1 gap-2">
                        {msg.data.machines.map((machine, idx) => (
                          <div key={idx} className="bg-gray-100 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-green-500/50 transition-colors">
                            <div className="flex justify-between items-center mb-1">
                              <span className="font-bold text-gray-900 dark:text-white text-xs">{machine.gpu}</span>
                              <span className="text-green-400 font-mono text-xs">{machine.price_per_hour}</span>
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
                              className="w-full py-1.5 text-[10px] font-medium bg-green-600/20 text-green-400 rounded hover:bg-green-600/30 transition-colors"
                            >
                              Reservar Agora
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reservation Stage */}
                  {msg.stage === 'reservation' && msg.data?.reservation && (
                    <div className="bg-green-900/20 border border-green-500/30 p-4 rounded-lg text-center">
                      <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
                        <Zap className="w-5 h-5 text-green-400" />
                      </div>
                      <h4 className="text-green-400 font-bold text-sm mb-1">Pronto para Reservar!</h4>
                      <p className="text-gray-300 text-xs mb-3">{msg.data.reservation.details}</p>
                      <button className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded-lg transition-colors shadow-lg shadow-green-900/20">
                        Confirmar e Pagar
                      </button>
                    </div>
                  )}

                  {/* Optimization Tips (keep existing) */}
                  {msg.recommendation?.optimization_tips && msg.recommendation.optimization_tips.length > 0 && (
                    <div className="mt-3 p-2 rounded bg-sky-900/15 border border-sky-700/20">
                      <div className="text-[10px] text-sky-400/80 font-semibold mb-1">Dicas de Otimização:</div>
                      <ul className="text-[10px] text-gray-400 space-y-0.5">
                        {msg.recommendation.optimization_tips.map((tip, idx) => (
                          <li key={idx}>• {tip}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Fallback: Simple search button if no visual cards */}
              {msg.recommendation && !msg.showCards && (
                <button
                  onClick={() => applyRecommendation()}
                  className="mt-3 w-full py-2 px-3 text-xs font-medium text-white bg-blue-600/50 hover:bg-brand-600/70 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <Search className="w-3 h-3" />
                  Buscar GPUs Recomendadas
                </button>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-green-400" />
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
        {/* Botões de ação rápida */}
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
            placeholder="Descreva seu projeto... (ex: Quero rodar LLaMA 13B para fine-tuning)"
            className="flex-1 ai-wizard-improved-input"
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

// Visual GPU Recommendation Card Component - Cores suavizadas
const GPURecommendationCard = ({ option, onSearch }) => {
  // Cores mais suaves e elegantes
  const tierColors = {
    'mínima': {
      bg: 'bg-gray-100 dark:bg-gray-800/40',
      border: 'border-gray-600/20',
      badge: 'bg-gray-200 dark:bg-gray-700/50 text-gray-400',
      button: 'bg-gray-600/40 hover:bg-gray-600/60'
    },
    'recomendada': {
      bg: 'bg-emerald-900/20',
      border: 'border-emerald-700/25',
      badge: 'bg-emerald-800/40 text-emerald-400',
      button: 'bg-emerald-700/40 hover:bg-emerald-700/60'
    },
    'máxima': {
      bg: 'bg-violet-900/20',
      border: 'border-violet-700/25',
      badge: 'bg-violet-800/40 text-violet-400',
      button: 'bg-violet-700/40 hover:bg-violet-700/60'
    }
  };
  const colors = tierColors[option.tier] || tierColors['recomendada'];

  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} p-3 flex flex-col`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${colors.badge}`}>
          {option.tier}
        </span>
        <span className="text-amber-400/80 text-xs font-mono font-bold">{option.price_per_hour}</span>
      </div>

      {/* GPU Info */}
      <div className="mb-2">
        <div className="text-gray-900 dark:text-white font-semibold text-sm">{option.gpu}</div>
        <div className="text-gray-400 text-[11px]">VRAM: {option.vram}</div>
        {option.quantization && (
          <div className="text-gray-500 text-[10px]">Quantização: {option.quantization}</div>
        )}
      </div>

      {/* Framework Performance Table */}
      {option.frameworks && Object.keys(option.frameworks).length > 0 && (
        <div className="mb-2">
          <div className="text-gray-500 text-[10px] mb-1 font-semibold">Performance por Framework:</div>
          <table className="w-full text-[10px]">
            <tbody>
              {Object.entries(option.frameworks).map(([framework, perf]) => (
                <tr key={framework} className="border-b border-gray-200 dark:border-gray-700/20">
                  <td className="py-0.5 text-gray-400">{framework}</td>
                  <td className="py-0.5 text-emerald-400/80 font-mono text-right">{perf}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tokens per second (legacy support) */}
      {option.tokens_per_second && !option.frameworks && (
        <div className="text-emerald-400/80 text-[11px] font-mono mb-2">
          ~{option.tokens_per_second} tokens/s
        </div>
      )}

      {/* RAM Offload */}
      {option.ram_offload && (
        <div className="text-amber-500/70 text-[10px] mb-2">
          RAM Offload: {option.ram_offload}
        </div>
      )}

      {/* Observation */}
      {option.observation && (
        <div className="text-gray-500 text-[10px] italic mb-2">{option.observation}</div>
      )}

      {/* Search Button */}
      <button
        onClick={() => onSearch(option)}
        className={`mt-auto py-1.5 px-2 text-[10px] font-medium text-white ${colors.button} rounded transition-colors flex items-center justify-center gap-1`}
      >
        <Search className="w-3 h-3" />
        Buscar {option.gpu}
      </button>
    </div>
  );
};

// Interactive GPU Wizard Component - Main display with model info and slider
const GPUWizardDisplay = ({ recommendation, onSearch }) => {
  const [currentIndex, setCurrentIndex] = useState(1); // Start at recommended (middle)
  const options = recommendation?.gpu_options || [];
  const currentOption = options[currentIndex];

  if (!currentOption) return null;

  const goLeft = () => setCurrentIndex(prev => Math.max(0, prev - 1));
  const goRight = () => setCurrentIndex(prev => Math.min(options.length - 1, prev + 1));

  // Extract model info from recommendation
  const modelName = recommendation?.model_name || 'Modelo';
  const modelSize = recommendation?.model_size || '';

  // Get tier colors
  const tierStyles = {
    'mínima': { accent: 'text-gray-400', bg: 'bg-gray-700/30', border: 'border-gray-600/30' },
    'recomendada': { accent: 'text-emerald-400', bg: 'bg-emerald-900/20', border: 'border-emerald-600/30' },
    'máxima': { accent: 'text-violet-400', bg: 'bg-violet-900/20', border: 'border-violet-600/30' }
  };
  const style = tierStyles[currentOption.tier] || tierStyles['recomendada'];

  // Parse tokens per second for display
  const getMainToksPerSec = () => {
    if (currentOption.frameworks?.vllm) return currentOption.frameworks.vllm;
    if (currentOption.frameworks?.pytorch) return currentOption.frameworks.pytorch;
    if (currentOption.tokens_per_second) return `${currentOption.tokens_per_second} tok/s`;
    return null;
  };

  return (
    <div className={`rounded-xl border ${style.border} ${style.bg} p-4 transition-all duration-300`}>
      {/* Model Header */}
      <div className="text-center mb-4 pb-3 border-b border-gray-200 dark:border-gray-700/30">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Modelo</div>
        <div className="text-gray-900 dark:text-white font-bold text-lg">{modelName}</div>
        {modelSize && <div className="text-gray-400 text-xs">{modelSize}</div>}
      </div>

      {/* Main Content with Navigation */}
      <div className="flex items-center gap-2">
        {/* Left Arrow - Cheaper */}
        <button
          onClick={goLeft}
          disabled={currentIndex === 0}
          className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all ${
            currentIndex === 0
              ? 'bg-gray-800/30 text-gray-600 cursor-not-allowed'
              : 'bg-gray-200 dark:bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 hover:text-white'
          }`}
          title="Mais barato"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        {/* Center Card - Current Selection */}
        <div className="flex-1 text-center">
          {/* Tier Badge */}
          <div className={`inline-block px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider mb-3 ${style.bg} ${style.accent}`}>
            {currentOption.tier}
          </div>

          {/* GPU Name */}
          <div className="text-gray-900 dark:text-white font-bold text-xl mb-1">{currentOption.gpu}</div>

          {/* VRAM & Quantization */}
          <div className="flex items-center justify-center gap-2 text-xs text-gray-400 mb-3">
            <span>{currentOption.vram}</span>
            {currentOption.quantization && (
              <>
                <span className="text-gray-600">•</span>
                <span className={`px-2 py-0.5 rounded ${style.bg} ${style.accent}`}>
                  {currentOption.quantization}
                </span>
              </>
            )}
          </div>

          {/* Main Performance Display */}
          {getMainToksPerSec() && (
            <div className="mb-3">
              <div className={`text-3xl font-bold ${style.accent}`}>
                {getMainToksPerSec()}
              </div>
              <div className="text-[10px] text-gray-500">tokens/segundo</div>
            </div>
          )}

          {/* Price */}
          <div className="text-amber-400 font-mono text-lg font-bold mb-3">
            {currentOption.price_per_hour}
          </div>

          {/* Framework Performance Grid */}
          {currentOption.frameworks && Object.keys(currentOption.frameworks).length > 1 && (
            <div className="grid grid-cols-3 gap-2 mb-3 text-[10px]">
              {Object.entries(currentOption.frameworks).slice(0, 3).map(([fw, perf]) => (
                <div key={fw} className="bg-gray-800/30 rounded p-2">
                  <div className="text-gray-500 uppercase">{fw}</div>
                  <div className={`font-mono ${style.accent}`}>{perf}</div>
                </div>
              ))}
            </div>
          )}

          {/* RAM Offload Warning */}
          {currentOption.ram_offload && currentOption.ram_offload !== 'Não necessário' && (
            <div className="text-amber-500/80 text-[10px] mb-2 flex items-center justify-center gap-1">
              <span>⚠️</span>
              <span>RAM Offload: {currentOption.ram_offload}</span>
            </div>
          )}

          {/* Observation */}
          {currentOption.observation && (
            <div className="text-gray-500 text-[10px] italic mb-3">{currentOption.observation}</div>
          )}
        </div>

        {/* Right Arrow - Faster */}
        <button
          onClick={goRight}
          disabled={currentIndex === options.length - 1}
          className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all ${
            currentIndex === options.length - 1
              ? 'bg-gray-800/30 text-gray-600 cursor-not-allowed'
              : 'bg-gray-200 dark:bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 hover:text-white'
          }`}
          title="Mais rápido"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Slider Visual */}
      <div className="mt-4 px-4">
        <div className="flex items-center justify-between text-[9px] text-gray-500 mb-1">
          <span>💰 Economia</span>
          <span>Performance 🚀</span>
        </div>
        <div className="relative h-2 bg-gray-200 dark:bg-gray-700/50 rounded-full">
          {/* Track gradient */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-gray-600 via-emerald-600 to-violet-600 opacity-30" />
          {/* Dots */}
          <div className="absolute inset-0 flex items-center justify-between px-1">
            {options.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`w-3 h-3 rounded-full transition-all ${
                  idx === currentIndex
                    ? `${style.accent.replace('text-', 'bg-')} scale-125 ring-2 ring-white/20`
                    : 'bg-gray-600 hover:bg-gray-500'
                }`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Search Button */}
      <button
        onClick={() => onSearch(currentOption)}
        className={`mt-4 w-full py-3 px-4 rounded-lg font-medium text-white transition-all flex items-center justify-center gap-2 ${
          currentOption.tier === 'recomendada'
            ? 'bg-emerald-600/50 hover:bg-emerald-600/70'
            : currentOption.tier === 'máxima'
            ? 'bg-violet-600/50 hover:bg-violet-600/70'
            : 'bg-gray-600/50 hover:bg-gray-600/70'
        }`}
      >
        <Search className="w-4 h-4" />
        Buscar {currentOption.gpu}
      </button>
    </div>
  );
};

// Legacy GPU Carousel Component (for compact view)
const GPUCarousel = ({ options, onSearch }) => {
  const [currentIndex, setCurrentIndex] = useState(1);

  const goLeft = () => setCurrentIndex(prev => Math.max(0, prev - 1));
  const goRight = () => setCurrentIndex(prev => Math.min(options.length - 1, prev + 1));

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={goLeft}
          disabled={currentIndex === 0}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-all ${
            currentIndex === 0 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Economia</span>
        </button>

        <div className="flex items-center gap-2">
          {options.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              className={`w-2 h-2 rounded-full transition-all ${
                idx === currentIndex ? 'bg-emerald-500 w-4' : 'bg-gray-600 hover:bg-gray-500'
              }`}
            />
          ))}
        </div>

        <button
          onClick={goRight}
          disabled={currentIndex === options.length - 1}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-all ${
            currentIndex === options.length - 1 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
          }`}
        >
          <span>Performance</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <GPURecommendationCard option={options[currentIndex]} onSearch={onSearch} />
    </div>
  );
};

const OfferCard = ({ offer, onSelect }) => (
  <Card className="hover:border-green-300 dark:hover:border-green-500/30 transition-all">
    <CardContent className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-green-600 dark:text-green-400" />
          <span className="text-gray-900 dark:text-white font-semibold text-sm">{offer.gpu_name}</span>
          {offer.num_gpus > 1 && <span className="text-xs text-gray-500 dark:text-gray-400">x{offer.num_gpus}</span>}
        </div>
        <div className="text-green-600 dark:text-green-400 font-mono font-semibold text-sm">
          ${offer.dph_total?.toFixed(3)}/hr
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3 text-[11px]">
        <div className="text-gray-600 dark:text-gray-400"><span className="text-gray-500">VRAM:</span> {offer.gpu_ram?.toFixed(0) || '-'} GB</div>
        <div className="text-gray-600 dark:text-gray-400"><span className="text-gray-500">CPU:</span> {offer.cpu_cores_effective || '-'} cores</div>
        <div className="text-gray-600 dark:text-gray-400"><span className="text-gray-500">Disco:</span> {offer.disk_space?.toFixed(0) || '-'} GB</div>
        <div className="text-gray-600 dark:text-gray-400"><span className="text-gray-500">Rede:</span> {offer.inet_down?.toFixed(0) || '-'} Mbps</div>
        <div className="text-gray-600 dark:text-gray-400"><span className="text-gray-500">DLPerf:</span> {offer.dlperf?.toFixed(1) || '-'}</div>
        <div className="text-gray-600 dark:text-gray-400"><span className="text-gray-500">PCIe:</span> {offer.pcie_bw?.toFixed(1) || '-'} GB/s</div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${(offer.reliability || 0) >= 0.9 ? 'bg-green-500' : (offer.reliability || 0) >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'}`} />
          <span className="text-[10px] text-gray-500 dark:text-gray-400">{((offer.reliability || 0) * 100).toFixed(0)}%</span>
          {offer.verified && <span className="text-[9px] text-green-600 dark:text-green-400 px-1.5 py-0.5 bg-green-100 dark:bg-green-500/10 rounded">Verificado</span>}
        </div>
        <Button onClick={() => onSelect(offer)} size="sm">
          Selecionar
        </Button>
      </div>
    </CardContent>
  </Card>
);

// Collapsible Filter Section
const FilterSection = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <Card className="overflow-hidden hover:border-gray-300 dark:hover:border-dark-surface-hover transition-all">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3.5 text-left hover:bg-gray-50 dark:hover:bg-dark-surface-hover transition-colors group"
      >
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-md bg-gray-100 dark:bg-dark-surface-secondary group-hover:bg-gray-200 dark:group-hover:bg-dark-surface-hover transition-colors">
            <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </div>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-200">{title}</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-all ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <CardContent className="pt-2 border-t border-gray-100 dark:border-gray-700/30">
          {children}
        </CardContent>
      )}
    </Card>
  );
};

// Stats Card Component with tooltip and animation support

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [mode, setMode] = useState('wizard');
  const [dashboardStats, setDashboardStats] = useState({
    activeMachines: 0,
    totalMachines: 0,
    dailyCost: 0,
    savings: 0,
    uptime: 0
  });

  useEffect(() => {
    checkOnboarding();
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (res.ok) {
        const data = await res.json();
        const instances = data.instances || [];
        const running = instances.filter(i => i.status === 'running');
        const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0);

        setDashboardStats({
          activeMachines: running.length,
          totalMachines: instances.length,
          dailyCost: (totalCost * 24).toFixed(2),
          savings: ((totalCost * 24 * 0.89) * 30).toFixed(0), // 89% economia estimada
          uptime: running.length > 0 ? 99.9 : 0
        });
      }
    } catch (e) {
      console.error('Error fetching dashboard stats:', e);
      // Demo mode fallback
      setDashboardStats({
        activeMachines: 2,
        totalMachines: 3,
        dailyCost: '4.80',
        savings: '127',
        uptime: 99.9
      });
    }
  };

  const checkOnboarding = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      const data = await res.json();
      if (data.authenticated) {
        setUser(data.user);
        // Verificar se o onboarding já foi completado
        const hasCompleted = data.user?.settings?.has_completed_onboarding;
        if (!hasCompleted) {
          setShowOnboarding(true);
        } else {
          setShowOnboarding(false);
        }
      }
    } catch (e) {
      console.error('Error checking onboarding:', e);
      // Em caso de erro, não mostrar o onboarding
      setShowOnboarding(false);
    }
  };

  const handleCompleteOnboarding = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings/complete-onboarding`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (res.ok) {
        // Atualizar o estado do usuário localmente
        setUser(prev => ({
          ...prev,
          settings: {
            ...prev?.settings,
            has_completed_onboarding: true
          }
        }));
        setShowOnboarding(false);
      } else {
        console.error('Failed to complete onboarding:', res.statusText);
        setShowOnboarding(false);
      }
    } catch (e) {
      console.error('Error completing onboarding:', e);
      setShowOnboarding(false);
    }
  };
  const [activeTab, setActiveTab] = useState('EUA');
  const [selectedTier, setSelectedTier] = useState('Rapido');
  const [selectedGPU, setSelectedGPU] = useState('any');
  const [selectedGPUCategory, setSelectedGPUCategory] = useState('any');
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showResults, setShowResults] = useState(false);

  // Filtros avançados completos do Vast.ai - Organizados por categoria
  const [advancedFilters, setAdvancedFilters] = useState({
    // GPU
    gpu_name: 'any',
    num_gpus: 1,
    min_gpu_ram: 0,
    gpu_frac: 1,
    gpu_mem_bw: 0,
    gpu_max_power: 0,
    bw_nvlink: 0,
    // CPU & Memória & Armazenamento
    min_cpu_cores: 1,
    min_cpu_ram: 1,
    min_disk: 50,
    cpu_ghz: 0,
    // Performance
    min_dlperf: 0,
    min_pcie_bw: 0,
    total_flops: 0,
    cuda_vers: 'any',
    compute_cap: 0,
    // Rede
    min_inet_down: 100,
    min_inet_up: 50,
    direct_port_count: 0,
    // Preço
    max_price: 5.0,
    rental_type: 'on-demand',
    // Qualidade & Localização
    min_reliability: 0,
    region: 'any',
    verified_only: false,
    datacenter: false,
    // Opções avançadas
    static_ip: false,
    // Ordenação
    order_by: 'dph_total',
    limit: 100
  });

  const tabs = ['EUA', 'Europa', 'Ásia', 'América do Sul', 'Global'];
  const tabIds = ['EUA', 'Europa', 'Asia', 'AmericaDoSul', 'Global'];

  const tiers = [
    { name: 'Lento', level: 1, color: 'slate', speed: '100-250 Mbps', time: '~5 min', gpu: 'RTX 3070/3080', vram: '8-12GB VRAM', priceRange: '$0.05 - $0.25/hr', description: 'Econômico. Ideal para tarefas básicas e testes.', filter: { max_price: 0.25, min_gpu_ram: 8 } },
    { name: 'Medio', level: 2, color: 'amber', speed: '500-1000 Mbps', time: '~2 min', gpu: 'RTX 4070/4080', vram: '12-16GB VRAM', priceRange: '$0.25 - $0.50/hr', description: 'Balanceado. Bom para desenvolvimento diário.', filter: { max_price: 0.50, min_gpu_ram: 12 } },
    { name: 'Rapido', level: 3, color: 'lime', speed: '1000-2000 Mbps', time: '~30s', gpu: 'RTX 4090', vram: '24GB VRAM', priceRange: '$0.50 - $1.00/hr', description: 'Alta performance. Treinamentos e workloads pesados.', filter: { max_price: 1.00, min_gpu_ram: 24 } },
    { name: 'Ultra', level: 4, color: 'emerald', speed: '2000+ Mbps', time: '~10s', gpu: 'A100/H100', vram: '40-80GB VRAM', priceRange: '$1.00 - $10.00/hr', description: 'Máxima potência. Para as tarefas mais exigentes.', filter: { max_price: 10.0, min_gpu_ram: 40 } }
  ];

  const getToken = () => localStorage.getItem('auth_token');

  // Demo offers for testing when API is unavailable or returns empty
  const DEMO_OFFERS = [
    { id: 1001, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24000, cpu_cores: 16, cpu_ram: 64000, disk_space: 200, dph_total: 0.45, inet_down: 2000, verified: true, geolocation: 'US' },
    { id: 1002, gpu_name: 'RTX 5090', num_gpus: 1, gpu_ram: 32000, cpu_cores: 24, cpu_ram: 128000, disk_space: 500, dph_total: 0.89, inet_down: 5000, verified: true, geolocation: 'EU' },
    { id: 1003, gpu_name: 'A100 80GB', num_gpus: 1, gpu_ram: 80000, cpu_cores: 32, cpu_ram: 256000, disk_space: 1000, dph_total: 2.10, inet_down: 10000, verified: true, geolocation: 'US' },
    { id: 1004, gpu_name: 'H100 80GB', num_gpus: 1, gpu_ram: 80000, cpu_cores: 64, cpu_ram: 512000, disk_space: 2000, dph_total: 3.50, inet_down: 25000, verified: true, geolocation: 'EU' },
  ];

  const searchOffers = async (filters) => {
    setLoading(true);
    setError(null);
    setShowResults(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });
      const response = await fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (!response.ok) throw new Error('Falha ao buscar ofertas');
      const data = await response.json();
      const realOffers = data.offers || [];

      // Use demo offers as fallback when API returns empty (e.g., no VAST_API_KEY)
      if (realOffers.length === 0) {
        console.log('[Dashboard] No offers from API, using demo offers');
        setOffers(DEMO_OFFERS);
      } else {
        setOffers(realOffers);
      }
    } catch (err) {
      console.log('[Dashboard] API error, using demo offers:', err.message);
      // Use demo offers on API error for testing
      setOffers(DEMO_OFFERS);
    } finally {
      setLoading(false);
    }
  };

  const handleWizardSearch = () => {
    const tier = tiers.find(t => t.name === selectedTier);
    if (tier) {
      searchOffers({
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      });
    }
  };

  const handleAdvancedSearch = () => {
    const filters = { ...advancedFilters };
    if (filters.gpu_name === 'any') filters.gpu_name = '';
    if (filters.region === 'any') filters.region = '';
    if (filters.cuda_vers === 'any') filters.cuda_vers = '';
    searchOffers(filters);
  };

  const handleAdvancedFilterChange = (key, value) => {
    setAdvancedFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleSelectOffer = (offer) => {
    console.log('[Dashboard] Navigating to /app/machines with offer:', offer);
    navigate('/app/machines', { state: { selectedOffer: offer } });
  };

  const resetAdvancedFilters = () => {
    setAdvancedFilters({
      gpu_name: 'any', num_gpus: 1, min_gpu_ram: 0, gpu_frac: 1, gpu_mem_bw: 0, gpu_max_power: 0, bw_nvlink: 0,
      min_cpu_cores: 1, min_cpu_ram: 1, min_disk: 50, cpu_ghz: 0,
      min_dlperf: 0, min_pcie_bw: 0, total_flops: 0, cuda_vers: 'any', compute_cap: 0,
      min_inet_down: 100, min_inet_up: 50, direct_port_count: 0,
      max_price: 5.0, rental_type: 'on-demand',
      min_reliability: 0, region: 'any', verified_only: false, datacenter: false,
      static_ip: false, order_by: 'dph_total', limit: 100
    });
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 bg-gray-50 dark:bg-dark-surface-bg" style={{ fontFamily: "'Inter', sans-serif" }}>
      {showOnboarding && (
        <OnboardingWizard
          user={user}
          onClose={() => setShowOnboarding(false)}
          onComplete={handleCompleteOnboarding}
        />
      )}

      {/* Page Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Visão geral das suas máquinas GPU</p>
      </div>

      {/* Dashboard Stats Cards */}
      <div className="max-w-7xl mx-auto mb-6">
        <MetricsGrid columns={3}>
          <MetricCard
            icon={Server}
            title="Máquinas Ativas"
            value={`${dashboardStats.activeMachines}/${dashboardStats.totalMachines}`}
            subtext="Instâncias em execução"
            color="green"
            tooltip="Total de GPUs rodando vs contratadas"
          />
          <MetricCard
            icon={DollarSign}
            title="Custo Diário"
            value={`$${dashboardStats.dailyCost}`}
            subtext="Estimativa baseada no uso"
            color="yellow"
            tooltip="Custo estimado baseado nas horas de uso hoje"
          />
          <MetricCard
            icon={Shield}
            title="Economia Mensal"
            value={`$${dashboardStats.savings}`}
            subtext="vs. preços on-demand"
            color="blue"
            trend={89}
            animate={true}
            tooltip="Economia comparada a provedores tradicionais"
            comparison="vs AWS: $6,547 → você paga $724"
          />
        </MetricsGrid>
      </div>

      {/* Deploy Wizard */}
      <div className="max-w-7xl mx-auto">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                <CardTitle>Deploy GPU</CardTitle>
                <CardDescription>Crie uma nova instância</CardDescription>
              </div>
            </div>

            <TabsUI value={mode} onValueChange={(v) => { setMode(v); setShowResults(false); }}>
              <TabsListUI>
                <TabsTriggerUI value="wizard" className="gap-1.5">
                  <Wand2 className="w-3.5 h-3.5" />
                  Wizard
                </TabsTriggerUI>
                <TabsTriggerUI value="advanced" className="gap-1.5">
                  <Sliders className="w-3.5 h-3.5" />
                  Avançado
                </TabsTriggerUI>
              </TabsListUI>
            </TabsUI>
          </CardHeader>

          {/* WIZARD MODE */}
          {mode === 'wizard' && !showResults && (
            <>
              <div className="flex flex-wrap gap-2 px-5 py-3 border-y border-gray-100 dark:border-dark-surface-border bg-gray-50 dark:bg-dark-surface-secondary">
                {tabs.map((tab, i) => (
                  <Button
                    key={tab}
                    variant={activeTab === tabIds[i] ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setActiveTab(tabIds[i])}
                  >
                    {tab}
                  </Button>
                ))}
              </div>

              <CardContent className="pt-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                {/* Main Wizard - 2 cols */}
                <div className="lg:col-span-2">
                  <div className="flex flex-col gap-4">
                    <div>
                      <Label className="text-gray-600 dark:text-gray-400 text-xs mb-2 block">Região</Label>
                      <div className="h-44 md:h-52 rounded-xl overflow-hidden shadow-sm">
                        <WorldMap activeRegion={activeTab} onRegionClick={setActiveTab} />
                      </div>
                    </div>
                    <div>
                      <Label className="text-gray-600 dark:text-gray-400 text-xs mb-2 block">GPU (opcional)</Label>
                      <GPUSelector
                        selectedGPU={selectedGPU}
                        onSelectGPU={setSelectedGPU}
                        selectedCategory={selectedGPUCategory}
                        onSelectCategory={setSelectedGPUCategory}
                      />
                    </div>
                  </div>
                </div>

                {/* AI Advisor - 1 col */}
                <div className="lg:col-span-1">
                  <Card className="border-brand-200 dark:border-brand-600/30 bg-gradient-to-br from-brand-50 dark:from-brand-600/10 to-transparent overflow-hidden h-full flex flex-col min-h-[280px]">
                    <CardHeader className="py-3 border-b border-brand-100 dark:border-brand-600/20 bg-brand-50/50 dark:bg-blue-600/5">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-brand-500 dark:text-brand-400" />
                        <CardTitle className="text-sm">AI Advisor</CardTitle>
                      </div>
                      <CardDescription>Pergunte sobre GPUs para seu projeto</CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-hidden p-0">
                      <AIWizardChat
                        compact={false}
                        onRecommendation={(rec) => {
                          console.log('AI Recommendation:', rec);
                        }}
                        onSearchWithFilters={(filters) => {
                          const tierMap = {
                            'Lento': tiers[0],
                            'Medio': tiers[1],
                            'Rapido': tiers[2],
                            'Ultra': tiers[3]
                          };
                          const tier = tierMap[filters.tier] || tiers[2];
                          searchOffers({
                            ...tier.filter,
                            gpu_name: filters.gpu_name !== 'any' ? filters.gpu_name : '',
                            min_gpu_ram: filters.min_gpu_ram || tier.filter.min_gpu_ram,
                            region: regionToApiRegion[activeTab] || ''
                          });
                        }}
                      />
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="mb-6">
                <Label className="text-gray-600 dark:text-gray-500 text-xs mb-3 block">Velocidade & Custo</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-6">
                  {tiers.map((tier) => (
                    <TierCard key={tier.name} tier={tier} isSelected={selectedTier === tier.name} onClick={() => setSelectedTier(tier.name)} />
                  ))}
                </div>

                <div className="relative h-2.5 rounded-full mb-6 mx-1 bg-gray-200 dark:bg-dark-surface-secondary">
                  <div className="absolute inset-y-0 left-0 rounded-full"
                    style={{ width: `${tiers.findIndex(t => t.name === selectedTier) * 25 + 25}%`, background: 'linear-gradient(to right, #4b5563, #ca8a04, #ea580c, #22c55e)' }} />
                  <div className="absolute top-1/2 -translate-y-1/2 w-5 h-5 bg-white rounded-full border-2 border-green-500 shadow-lg"
                    style={{ left: `calc(${tiers.findIndex(t => t.name === selectedTier) * 25 + 25}% - 10px)` }} />
                </div>
              </div>

              <Button
                onClick={handleWizardSearch}
                className="w-full"
                size="lg"
              >
                <Search className="w-4 h-4" />
                Buscar Máquinas Disponíveis
              </Button>
              </CardContent>
            </>
          )}

        {/* ADVANCED MODE */}
        {mode === 'advanced' && !showResults && (
          <CardContent className="pt-6">
            {/* Header */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-green-100 dark:bg-gradient-to-br dark:from-emerald-500/20 dark:to-emerald-600/20">
                    <Sliders className="w-6 h-6 text-green-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Busca Avançada</h2>
                    <p className="text-gray-500 dark:text-gray-400 text-sm mt-0.5">Ajuste os filtros para encontrar as melhores máquinas disponíveis</p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  onClick={resetAdvancedFilters}
                  className="gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  Resetar Filtros
                </Button>
              </div>
              <div className="h-0.5 bg-gradient-to-r from-green-500/30 dark:from-emerald-500/30 to-transparent rounded-full"></div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
              {/* GPU */}
              <FilterSection title="GPU" icon={Cpu}>
                <div className="space-y-4 mt-3">
                  <div>
                    <Label className="text-xs text-gray-400 mb-2 block">Modelo da GPU</Label>
                    <Select value={advancedFilters.gpu_name} onValueChange={(v) => handleAdvancedFilterChange('gpu_name', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {GPU_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Quantidade de GPUs</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.num_gpus}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.num_gpus]}
                      onValueChange={([v]) => handleAdvancedFilterChange('num_gpus', Math.round(v))}
                      max={8}
                      min={1}
                      step={1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>1</span>
                      <span>4</span>
                      <span>8</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">VRAM Mínima (GB)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_gpu_ram.toFixed(0)} GB</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_gpu_ram]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_gpu_ram', Math.round(v))}
                      max={80}
                      min={0}
                      step={4}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0 GB</span>
                      <span>40 GB</span>
                      <span>80 GB</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Fração de GPU</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.gpu_frac.toFixed(1)}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.gpu_frac]}
                      onValueChange={([v]) => handleAdvancedFilterChange('gpu_frac', v)}
                      max={1}
                      min={0.1}
                      step={0.1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0.1</span>
                      <span>0.5</span>
                      <span>1.0</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Largura de Banda Memória (GB/s)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.gpu_mem_bw.toFixed(0)}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.gpu_mem_bw]}
                      onValueChange={([v]) => handleAdvancedFilterChange('gpu_mem_bw', v)}
                      max={1000}
                      min={0}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0 GB/s</span>
                      <span>500 GB/s</span>
                      <span>1000 GB/s</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Potência Máxima (W)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.gpu_max_power.toFixed(0)} W</span>
                    </div>
                    <Slider
                      value={[advancedFilters.gpu_max_power]}
                      onValueChange={([v]) => handleAdvancedFilterChange('gpu_max_power', v)}
                      max={500}
                      min={0}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0 W</span>
                      <span>250 W</span>
                      <span>500 W</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Largura de Banda NVLink (GB/s)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.bw_nvlink.toFixed(0)}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.bw_nvlink]}
                      onValueChange={([v]) => handleAdvancedFilterChange('bw_nvlink', v)}
                      max={600}
                      min={0}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0 GB/s</span>
                      <span>300 GB/s</span>
                      <span>600 GB/s</span>
                    </div>
                  </div>
                </div>
              </FilterSection>

              {/* CPU & Memória */}
              <FilterSection title="CPU & Memória" icon={Server}>
                <div className="space-y-4 mt-3">
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">CPU Cores Mínimos</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_cpu_cores}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_cpu_cores]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_cpu_cores', Math.round(v))}
                      max={64}
                      min={1}
                      step={1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>1</span>
                      <span>32</span>
                      <span>64</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">RAM CPU Mínima (GB)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_cpu_ram.toFixed(0)} GB</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_cpu_ram]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_cpu_ram', Math.round(v))}
                      max={256}
                      min={1}
                      step={2}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>1 GB</span>
                      <span>128 GB</span>
                      <span>256 GB</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Disco Mínimo (GB)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_disk.toFixed(0)} GB</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_disk]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_disk', Math.round(v))}
                      max={2000}
                      min={10}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>10 GB</span>
                      <span>1000 GB</span>
                      <span>2000 GB</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Velocidade CPU Mínima (GHz)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.cpu_ghz.toFixed(1)} GHz</span>
                    </div>
                    <Slider
                      value={[advancedFilters.cpu_ghz]}
                      onValueChange={([v]) => handleAdvancedFilterChange('cpu_ghz', v)}
                      max={5}
                      min={0}
                      step={0.1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0 GHz</span>
                      <span>2.5 GHz</span>
                      <span>5.0 GHz</span>
                    </div>
                  </div>
                </div>
              </FilterSection>

              {/* Performance */}
              <FilterSection title="Performance" icon={Gauge}>
                <div className="space-y-4 mt-3">
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">DLPerf Mínimo</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_dlperf.toFixed(1)}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_dlperf]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_dlperf', v)}
                      max={100}
                      min={0}
                      step={1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0</span>
                      <span>50</span>
                      <span>100</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">PCIe BW Mínima (GB/s)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_pcie_bw.toFixed(1)} GB/s</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_pcie_bw]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_pcie_bw', v)}
                      max={100}
                      min={0}
                      step={1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0 GB/s</span>
                      <span>50 GB/s</span>
                      <span>100 GB/s</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">TFLOPs Totais Mínimos</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.total_flops.toFixed(0)} TFLOP</span>
                    </div>
                    <Slider
                      value={[advancedFilters.total_flops]}
                      onValueChange={([v]) => handleAdvancedFilterChange('total_flops', v)}
                      max={10000}
                      min={0}
                      step={100}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0 TFLOP</span>
                      <span>5000 TFLOP</span>
                      <span>10000 TFLOP</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Compute Capability Mínimo</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{(advancedFilters.compute_cap / 10).toFixed(1)}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.compute_cap]}
                      onValueChange={([v]) => handleAdvancedFilterChange('compute_cap', v)}
                      max={900}
                      min={300}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>3.0</span>
                      <span>6.0</span>
                      <span>9.0</span>
                    </div>
                  </div>

                  <div>
                    <Label className="text-xs text-gray-400 mb-2 block">Versão CUDA Mínima</Label>
                    <Select value={advancedFilters.cuda_vers} onValueChange={(v) => handleAdvancedFilterChange('cuda_vers', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {CUDA_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </FilterSection>

              {/* Rede */}
              <FilterSection title="Rede" icon={Wifi}>
                <div className="space-y-4 mt-3">
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Download Mínimo (Mbps)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_inet_down.toFixed(0)} Mbps</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_inet_down]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_inet_down', Math.round(v))}
                      max={1000}
                      min={10}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>10 Mbps</span>
                      <span>500 Mbps</span>
                      <span>1000 Mbps</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Upload Mínimo (Mbps)</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.min_inet_up.toFixed(0)} Mbps</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_inet_up]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_inet_up', Math.round(v))}
                      max={1000}
                      min={10}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>10 Mbps</span>
                      <span>500 Mbps</span>
                      <span>1000 Mbps</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Portas Diretas Mínimas</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{advancedFilters.direct_port_count}</span>
                    </div>
                    <Slider
                      value={[advancedFilters.direct_port_count]}
                      onValueChange={([v]) => handleAdvancedFilterChange('direct_port_count', Math.round(v))}
                      max={32}
                      min={0}
                      step={1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0</span>
                      <span>16</span>
                      <span>32</span>
                    </div>
                  </div>
                </div>
              </FilterSection>

              {/* Preço */}
              <FilterSection title="Preço" icon={DollarSign}>
                <div className="space-y-4 mt-3">
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Preço Máximo</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">${advancedFilters.max_price.toFixed(2)}/hr</span>
                    </div>
                    <Slider
                      value={[advancedFilters.max_price]}
                      onValueChange={([v]) => handleAdvancedFilterChange('max_price', v)}
                      max={15}
                      min={0.05}
                      step={0.05}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>$0.05</span>
                      <span>$7.50</span>
                      <span>$15.00</span>
                    </div>
                  </div>

                  <div>
                    <Label className="text-xs text-gray-400 mb-2 block">Tipo de Aluguel</Label>
                    <Select value={advancedFilters.rental_type} onValueChange={(v) => handleAdvancedFilterChange('rental_type', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {RENTAL_TYPE_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </FilterSection>

              {/* Localização & Qualidade */}
              <FilterSection title="Localização & Qualidade" icon={Globe}>
                <div className="space-y-4 mt-3">
                  <div>
                    <Label className="text-xs text-gray-400 mb-2 block">Região Preferida</Label>
                    <Select value={advancedFilters.region} onValueChange={(v) => handleAdvancedFilterChange('region', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {REGION_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <Label className="text-xs text-gray-500 dark:text-gray-400">Confiabilidade Mínima</Label>
                      <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{(advancedFilters.min_reliability * 100).toFixed(0)}%</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_reliability]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_reliability', v)}
                      max={1}
                      min={0}
                      step={0.05}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                      <span>0%</span>
                      <span>50%</span>
                      <span>100%</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border border-gray-200 dark:border-gray-700/30 rounded-lg p-3 bg-gray-900/20">
                    <Label className="text-sm text-gray-300">Apenas Datacenters Certificados</Label>
                    <Switch
                      checked={advancedFilters.datacenter}
                      onCheckedChange={(checked) => handleAdvancedFilterChange('datacenter', checked)}
                    />
                  </div>
                </div>
              </FilterSection>
            </div>

            {/* Opções & Ordenação */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
              <FilterSection title="Opções Adicionais" icon={Shield} defaultOpen={false}>
                <div className="space-y-3 mt-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm text-gray-300">Apenas Hosts Verificados</Label>
                    <Switch
                      checked={advancedFilters.verified_only}
                      onCheckedChange={(checked) => handleAdvancedFilterChange('verified_only', checked)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label className="text-sm text-gray-300">IP Estático</Label>
                    <Switch
                      checked={advancedFilters.static_ip}
                      onCheckedChange={(checked) => handleAdvancedFilterChange('static_ip', checked)}
                    />
                  </div>
                </div>
              </FilterSection>

              <FilterSection title="Ordenação" icon={Activity} defaultOpen={false}>
                <div className="space-y-3 mt-3">
                  <div>
                    <Label className="text-xs text-gray-400 mb-2 block">Ordenar Por</Label>
                    <Select value={advancedFilters.order_by} onValueChange={(v) => handleAdvancedFilterChange('order_by', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {ORDER_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-400 mb-2 block">Limite de Resultados</Label>
                    <Input type="number" min="10" max="500" value={advancedFilters.limit}
                      onChange={(e) => handleAdvancedFilterChange('limit', parseInt(e.target.value) || 100)} />
                  </div>
                </div>
              </FilterSection>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                onClick={handleAdvancedSearch}
                className="flex-1"
                size="lg"
              >
                <Search className="w-4 h-4" />
                Buscar Máquinas
              </Button>
              <Button
                variant="outline"
                onClick={() => setMode('wizard')}
                size="lg"
              >
                <ChevronLeft className="w-4 h-4" />
                Voltar ao Wizard
              </Button>
            </div>
          </CardContent>
        )}

        {/* RESULTS VIEW */}
        {showResults && (
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-gray-900 dark:text-white text-lg font-semibold">Máquinas Disponíveis</h2>
                <p className="text-gray-500 text-xs">{offers.length} resultados encontrados</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowResults(false)}
              >
                <ChevronLeft className="w-4 h-4" />
                Voltar
              </Button>
            </div>

            {loading && (
              <SkeletonList count={6} type="offer" />
            )}

            {error && !loading && (
              <ErrorState
                message={error}
                onRetry={() => {
                  setError(null);
                  setShowResults(false);
                }}
                retryText="Tentar novamente"
              />
            )}

            {!loading && !error && offers.length === 0 && (
              <EmptyState
                icon="search"
                title="Nenhuma máquina encontrada"
                description="Não encontramos ofertas com os filtros selecionados. Tente ajustar os critérios de busca."
                action={() => setShowResults(false)}
                actionText="Ajustar filtros"
              />
            )}

            {!loading && offers.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {offers.map((offer, index) => (
                  <OfferCard key={offer.id || index} offer={offer} onSelect={handleSelectOffer} />
                ))}
              </div>
            )}
          </CardContent>
        )}
        </Card>
      </div>
    </div>
  );
}
