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
  Send, Bot, User, Loader2, Plus, Minus, X, Check, MapPin,
  MessageSquare, Lightbulb, Code, Clock
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Input,
  Checkbox,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Button,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Label,
  Slider,
  Switch,
  StatCard as MetricCard,
  StatsGrid as MetricsGrid,
  Avatar,
  AvatarImage,
  AvatarFallback,
  Popover,
  PopoverTrigger,
  PopoverContent,
} from '../components/tailadmin-ui';
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
    color: 'green',
    gpus: ['RTX_4080', 'RTX_4080_Super', 'RTX_4090', 'RTX_3080', 'RTX_3080_Ti', 'RTX_3090', 'RTX_3090_Ti', 'RTX_5090', 'A5000', 'A6000', 'L40S']
  },
  {
    id: 'hpc',
    name: 'HPC / LLMs',
    icon: 'hpc',
    description: 'Modelos grandes / Multi-GPU',
    color: 'green',
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

const WorldMap = ({ selectedCodes = [], onCountryClick }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Theme-aware colors
  const mapColors = {
    dark: {
      background: '#0a0d0a',           // Match page background
      landFill: '#1a2e1a',             // Dark green-tinted land
      landStroke: '#2d4a2d',           // Subtle green borders
      hoverFill: '#10b981',            // Emerald on hover
      hoverStroke: '#34d399',          // Light emerald stroke
      selectedFill: '#10b981',         // Emerald for selected
      markerFill: '#10b981',
      markerStroke: '#34d399',
    },
    light: {
      background: '#f0fdf4',           // Light green-tinted background
      landFill: '#d1fae5',             // Light emerald land
      landStroke: '#a7f3d0',           // Emerald borders
      hoverFill: '#34d399',            // Emerald on hover
      hoverStroke: '#10b981',          // Darker emerald stroke
      selectedFill: '#059669',         // Darker emerald for selected
      markerFill: '#059669',
      markerStroke: '#10b981',
    }
  };

  const colors = isDark ? mapColors.dark : mapColors.light;

  // Datacenter markers
  const datacenterMarkers = [
    { latLng: [37.77, -122.42], name: 'San Francisco', code: 'US' },
    { latLng: [40.71, -74.01], name: 'New York', code: 'US' },
    { latLng: [51.51, -0.13], name: 'London', code: 'GB' },
    { latLng: [48.86, 2.35], name: 'Paris', code: 'FR' },
    { latLng: [52.52, 13.40], name: 'Berlin', code: 'DE' },
    { latLng: [35.68, 139.69], name: 'Tokyo', code: 'JP' },
    { latLng: [1.35, 103.82], name: 'Singapore', code: 'SG' },
    { latLng: [-23.55, -46.63], name: 'São Paulo', code: 'BR' },
  ];

  // Filter markers based on selected codes
  const visibleMarkers = selectedCodes.length === 0
    ? datacenterMarkers
    : datacenterMarkers.filter(m => selectedCodes.includes(m.code));

  return (
    <div className="relative w-full h-full" style={{ backgroundColor: colors.background }}>
      <VectorMap
        key={`map-${theme}`}
        map={worldMill}
        backgroundColor="transparent"
        containerStyle={{
          width: '100%',
          height: '100%',
        }}
        markerStyle={{
          initial: {
            fill: colors.markerFill,
            r: 6,
            stroke: colors.markerStroke,
            strokeWidth: 2,
            fillOpacity: 0.9,
          },
          hover: {
            fill: '#34d399',
            r: 8,
            stroke: '#10b981',
            strokeWidth: 2,
            fillOpacity: 1,
          },
        }}
        markers={visibleMarkers.map(m => ({
          latLng: m.latLng,
          name: m.name,
          style: { fill: colors.markerFill, stroke: colors.markerStroke, strokeWidth: 2, fillOpacity: 0.9 },
        }))}
        zoomOnScroll={false}
        zoomMax={12}
        zoomMin={1}
        onRegionClick={(e, code) => {
          if (onCountryClick) {
            onCountryClick(code);
          }
        }}
        regionStyle={{
          initial: {
            fill: colors.landFill,
            fillOpacity: 1,
            stroke: colors.landStroke,
            strokeWidth: 0.5,
            strokeOpacity: 1,
          },
          hover: {
            fillOpacity: 0.9,
            cursor: 'pointer',
            fill: colors.hoverFill,
            stroke: colors.hoverStroke,
            strokeWidth: 1,
          },
        }}
        series={{
          regions: [{
            values: selectedCodes.reduce((acc, code) => {
              acc[code] = 1;
              return acc;
            }, {}),
            scale: {
              '1': colors.selectedFill
            },
            attribute: 'fill'
          }]
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
        className={`relative flex flex-col p-3 md:p-4 rounded-xl text-left transition-all overflow-hidden ${
          isSelected
            ? 'border-2 border-emerald-500/50 bg-emerald-500/10 shadow-lg shadow-emerald-500/10'
            : 'border border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
        }`}
        style={{ minHeight: '160px' }}
      >
        {/* Green accent bar on left when selected */}
        {isSelected && (
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald-400 via-emerald-500 to-teal-500" />
        )}

        <div className="flex items-center justify-between mb-2">
          <span className={`font-bold text-sm md:text-base tracking-tight ${isSelected ? 'text-white' : 'text-gray-100'}`}>{tier.name}</span>
          <SpeedBars level={tier.level} color={tier.color} />
        </div>
        <div className={`text-xs md:text-sm font-mono font-semibold tracking-tight ${isSelected ? 'text-emerald-400' : 'text-emerald-400'}`}>{tier.speed}</div>
        <div className="text-gray-400 text-[10px] md:text-xs mb-2">{tier.time}</div>
        <div className="text-gray-400 text-[10px] md:text-xs leading-relaxed">{tier.gpu}</div>
        <div className="text-gray-400 text-[10px] md:text-xs leading-relaxed">{tier.vram}</div>
        <div className={`text-xs md:text-sm font-mono font-semibold mt-2 ${isSelected ? 'text-yellow-400' : 'text-yellow-400/80'}`}>{tier.priceRange}</div>
        <div className="mt-auto pt-3 border-t border-white/10">
          <p className="text-gray-400 text-[9px] md:text-[10px] leading-relaxed">{tier.description}</p>
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
    const colorClass = isActive ? 'text-white' : 'text-gray-700 dark:text-gray-300';
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
      case 'green': return 'bg-emerald-50 dark:bg-emerald-600/30 border-emerald-500';
      default: return 'bg-gray-100 dark:bg-gray-600/30 border-gray-400';
    }
  };

  const getIconBgColor = (color) => {
    switch (color) {
      case 'green': return 'bg-emerald-500/20';
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
                className={`relative p-3 rounded-xl border transition-all text-left overflow-hidden ${isActive
                  ? 'border-emerald-500/50 bg-emerald-500/10'
                  : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                  }`}
              >
                {/* Left accent when active */}
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-emerald-500" />
                )}
                <div className="flex items-center gap-2.5 mb-1.5">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${isActive ? 'bg-emerald-500/20' : 'bg-white/10'}`}>
                    {getCategoryIcon(cat.icon, isActive)}
                  </div>
                  <span className={`text-sm font-bold ${isActive ? 'text-white' : 'text-gray-100'}`}>
                    {cat.name}
                  </span>
                </div>
                <p className={`text-[10px] pl-9 ${isActive ? 'text-emerald-300' : 'text-gray-400'}`}>
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
              <SelectTrigger className="bg-gray-100 dark:bg-dark-surface-secondary border-gray-200 dark:border-gray-800 h-9 text-xs">
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
              <div className={`max-w-[85%] p-1.5 rounded text-[9px] ${msg.role === 'user'
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
                    className="mt-3 w-full py-2 px-3 text-xs font-medium text-white bg-brand-600/50 hover:bg-brand-600/70 rounded-lg transition-colors flex items-center justify-center gap-2"
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
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500/20 to-brand-600/20 flex items-center justify-center">
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
                  className="px-4 py-2 text-xs font-semibold text-gray-700 dark:text-emerald-300 bg-gray-100 dark:bg-emerald-500/10 border border-gray-300 dark:border-emerald-500/30 rounded-full hover:bg-emerald-50 dark:hover:bg-emerald-500/20 hover:border-emerald-400 dark:hover:border-emerald-500/50 hover:text-emerald-600 dark:hover:text-emerald-200 transition-all"
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
            <div className={`max-w-[90%] p-3 rounded-lg ${msg.role === 'user'
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
                  className="mt-3 w-full py-2 px-3 text-xs font-medium text-white bg-brand-600/50 hover:bg-brand-600/70 rounded-lg transition-colors flex items-center justify-center gap-2"
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
      bg: 'bg-emerald-900/20',
      border: 'border-emerald-700/25',
      badge: 'bg-emerald-800/40 text-emerald-400',
      button: 'bg-emerald-700/40 hover:bg-emerald-700/60'
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
    'máxima': { accent: 'text-emerald-400', bg: 'bg-emerald-900/20', border: 'border-emerald-600/30' }
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
          className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all ${currentIndex === 0
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
          className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all ${currentIndex === options.length - 1
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
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-gray-600 via-emerald-600 to-emerald-400 opacity-30" />
          {/* Dots */}
          <div className="absolute inset-0 flex items-center justify-between px-1">
            {options.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`w-3 h-3 rounded-full transition-all ${idx === currentIndex
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
        className={`mt-4 w-full py-3 px-4 rounded-lg font-medium text-white transition-all flex items-center justify-center gap-2 ${currentOption.tier === 'recomendada'
          ? 'bg-emerald-600/50 hover:bg-emerald-600/70'
          : currentOption.tier === 'máxima'
            ? 'bg-emerald-600/50 hover:bg-emerald-600/70'
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
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-all ${currentIndex === 0 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
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
              className={`w-2 h-2 rounded-full transition-all ${idx === currentIndex ? 'bg-emerald-500 w-4' : 'bg-gray-600 hover:bg-gray-500'
                }`}
            />
          ))}
        </div>

        <button
          onClick={goRight}
          disabled={currentIndex === options.length - 1}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-all ${currentIndex === options.length - 1 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
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

const OfferCard = ({ offer, onSelect }) => {
  const reliability = offer.reliability || 0;
  const reliabilityColor = reliability >= 0.9 ? 'text-green-500' : reliability >= 0.7 ? 'text-yellow-500' : 'text-red-500';
  const reliabilityBg = reliability >= 0.9 ? 'bg-green-500/10' : reliability >= 0.7 ? 'bg-yellow-500/10' : 'bg-red-500/10';

  return (
    <Card className="group relative overflow-hidden hover:shadow-lg dark:hover:shadow-green-500/5 hover:border-green-400 dark:hover:border-green-500/50 transition-all duration-300">
      {/* Gradient accent bar */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-green-500 via-emerald-500 to-teal-500" />

      <CardContent className="p-5 pt-6">
        {/* Header with GPU info and price */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className="p-2 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/10 dark:from-green-500/30 dark:to-emerald-500/20">
                <Cpu className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h3 className="text-gray-900 dark:text-white font-bold text-base leading-tight">{offer.gpu_name}</h3>
                {offer.num_gpus > 1 && (
                  <span className="text-xs font-medium text-green-600 dark:text-green-400">x{offer.num_gpus} GPUs</span>
                )}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              ${offer.dph_total?.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">por hora</div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="text-center p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
            <div className="text-lg font-bold text-gray-900 dark:text-white">{offer.gpu_ram?.toFixed(0) || '-'}</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-medium">VRAM GB</div>
          </div>
          <div className="text-center p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
            <div className="text-lg font-bold text-gray-900 dark:text-white">{offer.cpu_cores_effective || '-'}</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-medium">CPU Cores</div>
          </div>
          <div className="text-center p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
            <div className="text-lg font-bold text-gray-900 dark:text-white">{offer.disk_space?.toFixed(0) || '-'}</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-medium">Disco GB</div>
          </div>
        </div>

        {/* Secondary Stats */}
        <div className="flex flex-wrap gap-2 mb-4 text-xs">
          <span className="px-2.5 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium">
            <Wifi className="w-3 h-3 inline mr-1" />{offer.inet_down?.toFixed(0) || '-'} Mbps
          </span>
          <span className="px-2.5 py-1 rounded-full bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 font-medium">
            <Zap className="w-3 h-3 inline mr-1" />DL {offer.dlperf?.toFixed(1) || '-'}
          </span>
          <span className="px-2.5 py-1 rounded-full bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 font-medium">
            PCIe {offer.pcie_bw?.toFixed(1) || '-'} GB/s
          </span>
        </div>

        {/* Footer with reliability and action */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${reliabilityBg}`}>
              <div className={`w-2 h-2 rounded-full ${reliability >= 0.9 ? 'bg-green-500' : reliability >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'}`} />
              <span className={`text-xs font-semibold ${reliabilityColor}`}>{(reliability * 100).toFixed(0)}%</span>
            </div>
            {offer.verified && (
              <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400 px-2 py-1 bg-green-100 dark:bg-green-500/10 rounded-full font-medium">
                <Check className="w-3 h-3" />
                Verificado
              </span>
            )}
          </div>
          <Button
            onClick={() => onSelect(offer)}
            size="sm"
            className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-md hover:shadow-lg transition-all"
          >
            Selecionar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

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

// Provisioning Race Screen Component
const ProvisioningRaceScreen = ({ candidates, winner, onCancel, onComplete }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-4xl mx-4">
        <Card className="border-2 border-emerald-500/30 bg-gradient-to-br from-gray-900 to-gray-950 shadow-2xl shadow-emerald-500/10">
          <CardContent className="p-8">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border-2 border-emerald-500/30 mb-4">
                {winner ? (
                  <Check className="w-8 h-8 text-emerald-400" />
                ) : (
                  <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">
                {winner ? 'Máquina Conectada!' : 'Provisionando Máquinas...'}
              </h2>
              <p className="text-gray-400">
                {winner
                  ? 'Sua máquina está pronta para uso'
                  : 'Testando conexão com 5 máquinas simultaneamente. A primeira que responder será selecionada.'}
              </p>
            </div>

            {/* Race Track */}
            <div className="space-y-3 mb-8">
              {candidates.map((candidate, index) => {
                const isWinner = winner?.id === candidate.id;
                const isCancelled = winner && !isWinner;
                const status = candidate.status; // 'connecting', 'connected', 'failed', 'cancelled'

                return (
                  <div
                    key={candidate.id}
                    className={`relative overflow-hidden rounded-xl border-2 transition-all duration-500 ${
                      isWinner
                        ? 'border-emerald-500 bg-emerald-500/10 scale-[1.02] shadow-lg shadow-emerald-500/20'
                        : isCancelled
                        ? 'border-gray-700 bg-gray-800/30 opacity-50 scale-[0.98]'
                        : status === 'failed'
                        ? 'border-red-500/50 bg-red-500/5'
                        : 'border-gray-700 bg-gray-800/50'
                    }`}
                  >
                    {/* Progress bar animation for connecting */}
                    {status === 'connecting' && !winner && (
                      <div className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-500 animate-pulse"
                        style={{ width: `${candidate.progress || 0}%`, transition: 'width 0.3s ease-out' }}
                      />
                    )}

                    <div className="p-4 flex items-center gap-4">
                      {/* Position/Status Icon */}
                      <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg ${
                        isWinner
                          ? 'bg-emerald-500 text-white'
                          : isCancelled
                          ? 'bg-gray-700 text-gray-500'
                          : status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-gray-700 text-gray-300'
                      }`}>
                        {isWinner ? (
                          <Check className="w-5 h-5" />
                        ) : isCancelled ? (
                          <X className="w-5 h-5" />
                        ) : status === 'failed' ? (
                          <X className="w-5 h-5" />
                        ) : (
                          <span>{index + 1}</span>
                        )}
                      </div>

                      {/* Machine Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Cpu className={`w-4 h-4 ${isWinner ? 'text-emerald-400' : 'text-gray-400'}`} />
                          <span className={`font-semibold truncate ${isWinner ? 'text-white' : 'text-gray-300'}`}>
                            {candidate.gpu_name}
                          </span>
                          {candidate.num_gpus > 1 && (
                            <span className="text-xs text-gray-500">x{candidate.num_gpus}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                          <span>{candidate.gpu_ram?.toFixed(0)} GB VRAM</span>
                          <span>•</span>
                          <span>{candidate.geolocation || 'Unknown'}</span>
                          <span>•</span>
                          <span className="text-emerald-400 font-medium">${candidate.dph_total?.toFixed(2)}/hr</span>
                        </div>
                      </div>

                      {/* Status */}
                      <div className="flex-shrink-0">
                        {isWinner ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/20 text-emerald-400 text-sm font-semibold">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            Conectado
                          </span>
                        ) : isCancelled ? (
                          <span className="text-sm text-gray-600">Cancelado</span>
                        ) : status === 'failed' ? (
                          <span className="text-sm text-red-400">Falhou</span>
                        ) : (
                          <span className="inline-flex items-center gap-2 text-sm text-gray-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Conectando...
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-center gap-4">
              {winner ? (
                <>
                  <Button
                    variant="outline"
                    onClick={onCancel}
                    className="border-gray-700 text-gray-400 hover:bg-gray-800"
                  >
                    Buscar Outras
                  </Button>
                  <Button
                    onClick={() => onComplete(winner)}
                    className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white px-8"
                  >
                    <Check className="w-4 h-4 mr-2" />
                    Usar Esta Máquina
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  onClick={onCancel}
                  className="border-gray-700 text-gray-400 hover:bg-gray-800"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancelar
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [mode, setMode] = useState('wizard');
  const [provisioningMode, setProvisioningMode] = useState(false);
  const [raceCandidates, setRaceCandidates] = useState([]);
  const [raceWinner, setRaceWinner] = useState(null);
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
  const [activeTab, setActiveTab] = useState('Global');
  const [selectedTier, setSelectedTier] = useState('Rapido');
  const [selectedGPU, setSelectedGPU] = useState('any');
  const [selectedGPUCategory, setSelectedGPUCategory] = useState('any');
  const [searchCountry, setSearchCountry] = useState('');
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showResults, setShowResults] = useState(false);
  const [deployMethod, setDeployMethod] = useState('manual'); // 'ai' | 'manual'

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

  // Country to ISO code and region mapping
  const countryData = {
    // Regiões (selecionam múltiplos países)
    'eua': { codes: ['US', 'CA', 'MX'], name: 'EUA', isRegion: true },
    'europa': { codes: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'], name: 'Europa', isRegion: true },
    'asia': { codes: ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'], name: 'Ásia', isRegion: true },
    'america do sul': { codes: ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'], name: 'América do Sul', isRegion: true },

    // Países individuais - EUA/América do Norte
    'estados unidos': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'usa': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'united states': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'canada': { codes: ['CA'], name: 'Canadá', isRegion: false },
    'canadá': { codes: ['CA'], name: 'Canadá', isRegion: false },
    'mexico': { codes: ['MX'], name: 'México', isRegion: false },
    'méxico': { codes: ['MX'], name: 'México', isRegion: false },

    // Países individuais - Europa
    'reino unido': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'uk': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'inglaterra': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'franca': { codes: ['FR'], name: 'França', isRegion: false },
    'frança': { codes: ['FR'], name: 'França', isRegion: false },
    'france': { codes: ['FR'], name: 'França', isRegion: false },
    'alemanha': { codes: ['DE'], name: 'Alemanha', isRegion: false },
    'germany': { codes: ['DE'], name: 'Alemanha', isRegion: false },
    'espanha': { codes: ['ES'], name: 'Espanha', isRegion: false },
    'spain': { codes: ['ES'], name: 'Espanha', isRegion: false },
    'italia': { codes: ['IT'], name: 'Itália', isRegion: false },
    'itália': { codes: ['IT'], name: 'Itália', isRegion: false },
    'italy': { codes: ['IT'], name: 'Itália', isRegion: false },
    'portugal': { codes: ['PT'], name: 'Portugal', isRegion: false },
    'holanda': { codes: ['NL'], name: 'Holanda', isRegion: false },
    'netherlands': { codes: ['NL'], name: 'Holanda', isRegion: false },
    'belgica': { codes: ['BE'], name: 'Bélgica', isRegion: false },
    'bélgica': { codes: ['BE'], name: 'Bélgica', isRegion: false },
    'suica': { codes: ['CH'], name: 'Suíça', isRegion: false },
    'suíça': { codes: ['CH'], name: 'Suíça', isRegion: false },
    'austria': { codes: ['AT'], name: 'Áustria', isRegion: false },
    'áustria': { codes: ['AT'], name: 'Áustria', isRegion: false },
    'irlanda': { codes: ['IE'], name: 'Irlanda', isRegion: false },
    'suecia': { codes: ['SE'], name: 'Suécia', isRegion: false },
    'suécia': { codes: ['SE'], name: 'Suécia', isRegion: false },
    'noruega': { codes: ['NO'], name: 'Noruega', isRegion: false },
    'dinamarca': { codes: ['DK'], name: 'Dinamarca', isRegion: false },
    'finlandia': { codes: ['FI'], name: 'Finlândia', isRegion: false },
    'finlândia': { codes: ['FI'], name: 'Finlândia', isRegion: false },
    'polonia': { codes: ['PL'], name: 'Polônia', isRegion: false },
    'polônia': { codes: ['PL'], name: 'Polônia', isRegion: false },

    // Países individuais - Ásia
    'japao': { codes: ['JP'], name: 'Japão', isRegion: false },
    'japão': { codes: ['JP'], name: 'Japão', isRegion: false },
    'japan': { codes: ['JP'], name: 'Japão', isRegion: false },
    'china': { codes: ['CN'], name: 'China', isRegion: false },
    'coreia': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'coréia': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'korea': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'singapore': { codes: ['SG'], name: 'Singapura', isRegion: false },
    'singapura': { codes: ['SG'], name: 'Singapura', isRegion: false },
    'india': { codes: ['IN'], name: 'Índia', isRegion: false },
    'índia': { codes: ['IN'], name: 'Índia', isRegion: false },
    'tailandia': { codes: ['TH'], name: 'Tailândia', isRegion: false },
    'tailândia': { codes: ['TH'], name: 'Tailândia', isRegion: false },
    'vietnam': { codes: ['VN'], name: 'Vietnã', isRegion: false },
    'vietnã': { codes: ['VN'], name: 'Vietnã', isRegion: false },
    'indonesia': { codes: ['ID'], name: 'Indonésia', isRegion: false },
    'indonésia': { codes: ['ID'], name: 'Indonésia', isRegion: false },
    'malasia': { codes: ['MY'], name: 'Malásia', isRegion: false },
    'malásia': { codes: ['MY'], name: 'Malásia', isRegion: false },
    'filipinas': { codes: ['PH'], name: 'Filipinas', isRegion: false },
    'taiwan': { codes: ['TW'], name: 'Taiwan', isRegion: false },

    // Países individuais - América do Sul
    'brasil': { codes: ['BR'], name: 'Brasil', isRegion: false },
    'brazil': { codes: ['BR'], name: 'Brasil', isRegion: false },
    'argentina': { codes: ['AR'], name: 'Argentina', isRegion: false },
    'chile': { codes: ['CL'], name: 'Chile', isRegion: false },
    'colombia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
    'colômbia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
    'peru': { codes: ['PE'], name: 'Peru', isRegion: false },
    'venezuela': { codes: ['VE'], name: 'Venezuela', isRegion: false },
    'equador': { codes: ['EC'], name: 'Equador', isRegion: false },
    'uruguai': { codes: ['UY'], name: 'Uruguai', isRegion: false },
    'paraguai': { codes: ['PY'], name: 'Paraguai', isRegion: false },
    'bolivia': { codes: ['BO'], name: 'Bolívia', isRegion: false },
    'bolívia': { codes: ['BO'], name: 'Bolívia', isRegion: false },
  };

  // State for selected location (can be country or region)
  const [selectedLocation, setSelectedLocation] = useState(null); // { codes: [], name: '', isRegion: bool }

  // Function to find location data from search query
  const findLocationFromSearch = (query) => {
    if (!query || query.length < 2) return null;
    const normalizedQuery = query.toLowerCase().trim();

    // Check exact match first
    if (countryData[normalizedQuery]) {
      return countryData[normalizedQuery];
    }

    // Check partial match
    for (const [key, data] of Object.entries(countryData)) {
      if (key.includes(normalizedQuery) || normalizedQuery.includes(key)) {
        return data;
      }
    }
    return null;
  };

  // Handle search input change with auto-selection
  const handleSearchChange = (value) => {
    setSearchCountry(value);
    const foundLocation = findLocationFromSearch(value);
    if (foundLocation) {
      setSelectedLocation(foundLocation);
    }
  };

  // Handle region button click
  const handleRegionSelect = (regionKey) => {
    const regionData = countryData[regionKey];
    if (regionData) {
      setSelectedLocation(regionData);
      setSearchCountry('');
    }
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedLocation(null);
    setSearchCountry('');
  };

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

  // Start provisioning race with top 5 offers
  const startProvisioningRace = (selectedOffers) => {
    // Take top 5 offers (or less if not available)
    const top5 = selectedOffers.slice(0, 5).map((offer, index) => ({
      ...offer,
      status: 'connecting',
      progress: 0,
      connectionTime: Math.random() * 5000 + 2000 // Random time between 2-7 seconds
    }));

    setRaceCandidates(top5);
    setRaceWinner(null);
    setProvisioningMode(true);

    // Simulate the race
    simulateRace(top5);
  };

  // Simulate connection race
  const simulateRace = (candidates) => {
    // Find which one will "win" (fastest connection time)
    const sortedBySpeed = [...candidates].sort((a, b) => a.connectionTime - b.connectionTime);
    const winnerIndex = candidates.findIndex(c => c.id === sortedBySpeed[0].id);

    // Update progress for each candidate
    const intervals = candidates.map((candidate, index) => {
      const progressIncrement = 100 / (candidate.connectionTime / 100);

      return setInterval(() => {
        setRaceCandidates(prev => {
          const updated = [...prev];
          if (updated[index] && updated[index].status === 'connecting') {
            updated[index] = {
              ...updated[index],
              progress: Math.min((updated[index].progress || 0) + progressIncrement, 100)
            };
          }
          return updated;
        });
      }, 100);
    });

    // Determine winner after their connection time
    setTimeout(() => {
      // Clear all intervals
      intervals.forEach(clearInterval);

      // Set the winner
      setRaceCandidates(prev => {
        return prev.map((c, i) => ({
          ...c,
          status: i === winnerIndex ? 'connected' : 'cancelled',
          progress: i === winnerIndex ? 100 : c.progress
        }));
      });

      setRaceWinner(candidates[winnerIndex]);
    }, sortedBySpeed[0].connectionTime);

    // Simulate some failures for realism (optional - 20% chance per non-winner)
    candidates.forEach((candidate, index) => {
      if (index !== winnerIndex && Math.random() < 0.2) {
        const failTime = Math.random() * sortedBySpeed[0].connectionTime;
        setTimeout(() => {
          setRaceCandidates(prev => {
            const updated = [...prev];
            if (updated[index] && updated[index].status === 'connecting') {
              updated[index] = { ...updated[index], status: 'failed' };
            }
            return updated;
          });
        }, failTime);
      }
    });
  };

  const cancelProvisioningRace = () => {
    setProvisioningMode(false);
    setRaceCandidates([]);
    setRaceWinner(null);
  };

  const completeProvisioningRace = (winner) => {
    setProvisioningMode(false);
    navigate('/app/machines', { state: { selectedOffer: winner } });
  };

  // Modified wizard search to start the race
  const handleWizardSearchWithRace = () => {
    const tier = tiers.find(t => t.name === selectedTier);
    if (tier) {
      // First fetch offers, then start race
      setLoading(true);
      const params = new URLSearchParams();
      const filters = {
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      };
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });

      fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
        .then(res => res.json())
        .then(data => {
          const realOffers = data.offers || [];
          const offersToUse = realOffers.length > 0 ? realOffers : DEMO_OFFERS;
          setOffers(offersToUse);
          setLoading(false);
          // Start the race with top offers
          if (offersToUse.length > 0) {
            startProvisioningRace(offersToUse);
          }
        })
        .catch(() => {
          setOffers(DEMO_OFFERS);
          setLoading(false);
          startProvisioningRace(DEMO_OFFERS);
        });
    }
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
    <div className="min-h-screen p-4 md:p-6 lg:p-8 bg-[#0a0d0a]" style={{ fontFamily: "'Inter', sans-serif" }}>
      {showOnboarding && (
        <OnboardingWizard
          user={user}
          onClose={() => setShowOnboarding(false)}
          onComplete={handleCompleteOnboarding}
        />
      )}

      {/* Provisioning Race Screen */}
      {provisioningMode && (
        <ProvisioningRaceScreen
          candidates={raceCandidates}
          winner={raceWinner}
          onCancel={cancelProvisioningRace}
          onComplete={completeProvisioningRace}
        />
      )}

      {/* Page Header + Stats - Compact Layout */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <h1 className="text-2xl font-bold text-white tracking-tight">Dashboard</h1>

          {/* Compact Stats - Inline */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <Server className="w-4 h-4 text-emerald-500" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Máquinas</p>
                <p className="text-sm font-bold text-white">{dashboardStats.activeMachines}/{dashboardStats.totalMachines}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
              <div className="w-8 h-8 rounded-lg bg-yellow-500/10 flex items-center justify-center">
                <DollarSign className="w-4 h-4 text-yellow-500" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Custo/Dia</p>
                <p className="text-sm font-bold text-white">${dashboardStats.dailyCost}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <Shield className="w-4 h-4 text-emerald-500" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Economia</p>
                <p className="text-sm font-bold text-emerald-500">${dashboardStats.savings} <span className="text-[10px] text-emerald-400">+89%</span></p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Deploy Wizard */}
      <div className="max-w-7xl mx-auto">
        <Card>
          <CardHeader className="flex flex-col space-y-4 pb-6 border-b border-white/5">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <Cpu className="w-6 h-6 text-emerald-500" />
                </div>
                <div>
                  <CardTitle className="text-xl">Deploy GPU</CardTitle>
                  <CardDescription>Crie uma nova instância em segundos</CardDescription>
                </div>
              </div>

              {/* Level 1: Method Selection */}
              <div className="flex bg-white/5 p-1.5 rounded-xl border border-white/10">
                <button
                  onClick={() => setDeployMethod('manual')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${deployMethod === 'manual'
                    ? 'bg-emerald-600 text-white shadow-md'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                    }`}
                >
                  <Server className="w-4 h-4" />
                  Seleção Manual
                </button>
                <button
                  onClick={() => setDeployMethod('ai')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${deployMethod === 'ai'
                    ? 'bg-emerald-600 text-white shadow-md'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                    }`}
                >
                  <Bot className="w-4 h-4" />
                  AI Assistant
                </button>
              </div>
            </div>

            {/* Level 2: Manual Mode Sub-tabs */}
            {deployMethod === 'manual' && (
              <div className="flex w-full pt-3">
                <Tabs value={mode} onValueChange={(v) => { setMode(v); setShowResults(false); }} className="w-full md:w-auto">
                  <TabsList className="bg-white/5 border border-white/10 h-11 p-1 gap-1 rounded-xl">
                    <TabsTrigger value="wizard" className="gap-2 rounded-lg data-[state=active]:bg-emerald-600 data-[state=active]:text-white data-[state=active]:shadow-md text-gray-300 font-semibold">
                      <Wand2 className="w-4 h-4" />
                      <span>Wizard</span>
                    </TabsTrigger>
                    <TabsTrigger value="advanced" className="gap-2 rounded-lg data-[state=active]:bg-emerald-600 data-[state=active]:text-white data-[state=active]:shadow-md text-gray-300 font-semibold">
                      <Sliders className="w-4 h-4" />
                      <span>Avançado</span>
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            )}
          </CardHeader>

          {/* AI MODE */}
          {deployMethod === 'ai' && (
            <CardContent className="h-[600px] p-0 relative">
              <AIWizardChat
                compact={false}
                onRecommendation={(rec) => console.log('AI Rec:', rec)}
                onSearchWithFilters={(filters) => {
                  // Logic to jump to search results
                  setDeployMethod('manual');
                  setMode('advanced');
                  // Apply filters...
                }}
              />
            </CardContent>
          )}

          {/* WIZARD MODE (MANUAL) */}
          {deployMethod === 'manual' && mode === 'wizard' && !showResults && (
            <CardContent className="p-6 space-y-8">

              {/* Step 1: Localização */}
              <div className="relative p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-sm">
                {/* Connector Line */}
                <div className="absolute left-10 top-[72px] bottom-6 w-0.5 bg-gradient-to-b from-emerald-500/30 via-emerald-500/10 to-transparent z-0" />

                <div className="space-y-6 relative z-10">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border-2 border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-base shadow-lg shadow-emerald-500/20">1</div>
                    <div>
                      <h3 className="text-xl font-bold text-white mb-1">Escolha a Região</h3>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium text-gray-400">Onde você quer que sua máquina esteja localizada?</p>
                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2.5 py-1 rounded-full border border-emerald-500/30 font-bold whitespace-nowrap">Closer = Faster</span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-6 pl-0 md:pl-14">
                    {/* Map & Tabs */}
                    <div className="space-y-4">
                      <div className="flex flex-col gap-4">
                        {/* Search Input + Selected Location Chip */}
                        <div className="flex flex-col gap-3">
                          {/* Search Input - Dark Theme Style */}
                          <div className="relative">
                            <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
                              <Search className="w-5 h-5 text-gray-400" />
                            </div>
                            <input
                              type="text"
                              placeholder="Buscar país ou região (ex: Brasil, Europa, Japão...)"
                              className="w-full pl-12 pr-4 py-3.5 text-sm text-white bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 placeholder:text-gray-500 transition-all"
                              value={searchCountry}
                              onChange={(e) => handleSearchChange(e.target.value)}
                            />
                          </div>

                          {/* Selected Location Chip (deletable) */}
                          {selectedLocation && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                                {selectedLocation.isRegion ? 'Região:' : 'País:'}
                              </span>
                              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-600 dark:bg-emerald-500 text-white rounded-full text-sm font-bold shadow-md">
                                {selectedLocation.isRegion ? <Globe className="w-4 h-4" /> : <MapPin className="w-4 h-4" />}
                                <span>{selectedLocation.name}</span>
                                <button
                                  onClick={clearSelection}
                                  className="ml-1 p-0.5 rounded-full hover:bg-white/20 transition-colors"
                                  title="Remover seleção"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                          )}

                          {/* Quick Select Buttons (only show when no location is selected) */}
                          {!selectedLocation && (
                            <div className="flex flex-wrap gap-2">
                              <span className="text-xs text-gray-400 font-medium mr-1 self-center">Regiões:</span>
                              {['eua', 'europa', 'asia', 'america do sul'].map((regionKey) => (
                                <button
                                  key={regionKey}
                                  onClick={() => handleRegionSelect(regionKey)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 text-gray-300 border border-white/10 hover:bg-emerald-500/10 hover:border-emerald-500/50 hover:text-emerald-400 transition-all"
                                >
                                  <Globe className="w-3 h-3" />
                                  {countryData[regionKey].name}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="h-64 rounded-xl overflow-hidden border border-white/10 bg-[#0a0d0a] relative group shadow-lg">
                        <WorldMap
                          selectedCodes={selectedLocation?.codes || []}
                          onCountryClick={(code) => {
                            // Find country name from code
                            const countryNames = {
                              'US': 'Estados Unidos', 'CA': 'Canadá', 'MX': 'México',
                              'GB': 'Reino Unido', 'FR': 'França', 'DE': 'Alemanha', 'ES': 'Espanha', 'IT': 'Itália', 'PT': 'Portugal',
                              'JP': 'Japão', 'CN': 'China', 'KR': 'Coreia do Sul', 'SG': 'Singapura', 'IN': 'Índia',
                              'BR': 'Brasil', 'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colômbia',
                            };
                            if (countryNames[code]) {
                              setSelectedLocation({ codes: [code], name: countryNames[code], isRegion: false });
                              setSearchCountry('');
                            }
                          }}
                        />
                        <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-gray-50 dark:from-[#0a0d0a] via-transparent to-transparent opacity-50" />
                      </div>
                    </div>


                  </div>
                </div>
              </div>

              {/* Step 2: Hardware & Performance */}
              <div className="relative p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-sm">
                {/* Connector Line */}
                <div className="absolute left-10 top-[72px] bottom-6 w-0.5 bg-gradient-to-b from-emerald-500/30 via-emerald-500/10 to-transparent z-0" />

                <div className="space-y-6 relative z-10">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border-2 border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-base shadow-lg shadow-emerald-500/20">2</div>
                    <div>
                      <h3 className="text-xl font-bold text-white mb-1">Defina o Hardware</h3>
                      <p className="text-sm font-medium text-gray-400">Qual potência de GPU e velocidade você precisa?</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pl-0 md:pl-14">
                  {/* GPU Selector */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 pb-1">
                      <Cpu className="w-4 h-4 text-emerald-400" />
                      <Label className="text-gray-200 text-sm font-bold tracking-wide">Modelo da GPU</Label>
                    </div>
                    <GPUSelector
                      selectedGPU={selectedGPU}
                      onSelectGPU={setSelectedGPU}
                      selectedCategory={selectedGPUCategory}
                      onSelectCategory={setSelectedGPUCategory}
                    />
                  </div>

                  {/* Use Case & Performance Selection - Redesigned */}
                  <div className="space-y-4">
                    {/* Question Header */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-emerald-700 dark:text-emerald-400" />
                        <Label className="text-gray-800 dark:text-gray-200 text-base font-bold">O que você vai fazer?</Label>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 pl-6">Escolha seu objetivo para ver as melhores recomendações</p>
                    </div>

                    {/* Use Case Quick Picks */}
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { id: 'test', label: 'Testar ideias', icon: Lightbulb, tier: 'Lento', desc: 'Protótipos e testes básicos' },
                        { id: 'develop', label: 'Desenvolver IA', icon: Code, tier: 'Medio', desc: 'Desenvolvimento diário' },
                        { id: 'train', label: 'Treinar modelos', icon: Zap, tier: 'Rapido', desc: 'Fine-tuning e training' },
                        { id: 'production', label: 'Projetos grandes', icon: Sparkles, tier: 'Ultra', desc: 'LLMs e workloads pesados' }
                      ].map((useCase) => {
                        const isSelected = selectedTier === useCase.tier;
                        const UseCaseIcon = useCase.icon;
                        return (
                          <div
                            key={useCase.id}
                            onClick={() => setSelectedTier(useCase.tier)}
                            className={`
                              p-3 rounded-lg border cursor-pointer transition-all duration-200
                              ${isSelected
                                ? "bg-emerald-500/10 border-emerald-500/50 shadow-sm"
                                : "bg-white/5 border-white/10 hover:border-emerald-500/30 hover:bg-white/10"}
                            `}
                          >
                            <div className="flex items-start gap-2">
                              <div className={`
                                w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                                ${isSelected
                                  ? "bg-emerald-500 text-white"
                                  : "bg-white/10 text-gray-400"}
                              `}>
                                <UseCaseIcon className="w-4 h-4" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className={`text-sm font-semibold ${isSelected ? "text-emerald-400" : "text-gray-100"}`}>
                                  {useCase.label}
                                </div>
                                <div className={`text-[10px] ${isSelected ? "text-emerald-500" : "text-gray-400"}`}>
                                  {useCase.desc}
                                </div>
                              </div>
                              {isSelected && (
                                <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                                  <div className="w-1.5 h-1.5 rounded-full bg-white" />
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Recommended Tier Info */}
                    {selectedTier && (
                      <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-lg bg-emerald-500 flex items-center justify-center flex-shrink-0">
                            {selectedTier === 'Lento' && <Gauge className="w-5 h-5 text-white" />}
                            {selectedTier === 'Medio' && <Activity className="w-5 h-5 text-white" />}
                            {selectedTier === 'Rapido' && <Zap className="w-5 h-5 text-white" />}
                            {selectedTier === 'Ultra' && <Sparkles className="w-5 h-5 text-white" />}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-sm font-bold text-gray-100">
                                Recomendação: {tiers.find(t => t.name === selectedTier)?.name}
                              </h4>
                              <span className="text-xs font-mono font-bold text-emerald-400">
                                {tiers.find(t => t.name === selectedTier)?.priceRange}
                              </span>
                            </div>
                            <div className="space-y-1.5">
                              <div className="flex items-center gap-2 text-xs text-gray-300">
                                <Cpu className="w-3.5 h-3.5" />
                                <span className="font-semibold">{tiers.find(t => t.name === selectedTier)?.gpu}</span>
                                <span className="text-gray-400">•</span>
                                <span>{tiers.find(t => t.name === selectedTier)?.vram}</span>
                              </div>
                              <div className="flex items-center gap-2 text-xs text-gray-400">
                                <Clock className="w-3.5 h-3.5" />
                                <span>Tempo médio de deploy: {tiers.find(t => t.name === selectedTier)?.time}</span>
                              </div>
                              <p className="text-xs text-gray-400 mt-2">
                                {tiers.find(t => t.name === selectedTier)?.description}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                </div>
              </div>

              {/* Action */}
              <div className="pt-2">
                <Button
                  onClick={handleWizardSearchWithRace}
                  disabled={loading}
                  className="w-full h-12 text-base font-bold bg-emerald-700 hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white shadow-md hover:shadow-lg rounded-xl transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Buscando...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 mr-2" />
                      Iniciar Provisionamento
                    </>
                  )}
                </Button>
              </div>

            </CardContent>
          )}

          {/* ADVANCED MODE (MANUAL) */}
          {deployMethod === 'manual' && mode === 'advanced' && !showResults && (
            <CardContent className="pt-6">
              {/* Header */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-emerald-100 border-2 border-emerald-600 dark:bg-gradient-to-br dark:from-emerald-500/20 dark:to-emerald-600/20 dark:border-emerald-500/30">
                      <Sliders className="w-6 h-6 text-emerald-700 dark:text-emerald-400" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Busca Avançada</h2>
                      <p className="text-gray-600 dark:text-gray-400 text-sm mt-0.5 font-medium">Ajuste os filtros para encontrar as melhores máquinas disponíveis</p>
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
                <div className="h-1 bg-gradient-to-r from-emerald-600/40 via-emerald-500/20 dark:from-emerald-500/30 dark:via-emerald-500/10 to-transparent rounded-full"></div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                {/* GPU */}
                <FilterSection title="GPU" icon={Cpu}>
                  <div className="space-y-4 mt-3">
                    <div>
                      <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Modelo da GPU</Label>
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
                      <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Versão CUDA Mínima</Label>
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
                      <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Tipo de Aluguel</Label>
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
                      <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Região Preferida</Label>
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

              {/* Opções Adicionais */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
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
              <div className="flex flex-col gap-4 mb-6">
                <div className="flex items-center justify-between">
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

                {/* Sorting Controls */}
                {offers.length > 0 && (
                  <div className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Ordenar por:</span>
                    </div>
                    <Select value={advancedFilters.order_by} onValueChange={(v) => handleAdvancedFilterChange('order_by', v)}>
                      <SelectTrigger className="w-[200px] h-9 bg-white dark:bg-gray-900">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ORDER_OPTIONS.map(opt => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="flex items-center gap-2 ml-4">
                      <span className="text-sm text-gray-500 dark:text-gray-400">Limite:</span>
                      <Input
                        type="number"
                        min="10"
                        max="500"
                        value={advancedFilters.limit}
                        onChange={(e) => handleAdvancedFilterChange('limit', parseInt(e.target.value) || 100)}
                        className="w-20 h-9 bg-white dark:bg-gray-900"
                      />
                    </div>
                  </div>
                )}
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
    </div >
  );
}
