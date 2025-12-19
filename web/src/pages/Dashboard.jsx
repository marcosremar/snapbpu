import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';
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
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { SkeletonList } from '../components/Skeleton';

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";
const API_BASE = import.meta.env.VITE_API_URL || '';

const regionCountries = {
  'EUA': ['USA'],
  'Europa': ['GBR', 'FRA', 'DEU', 'ITA', 'ESP', 'PRT', 'NLD', 'BEL', 'CHE', 'AUT', 'POL', 'CZE', 'SVK', 'HUN', 'ROU', 'BGR', 'GRC', 'SWE', 'NOR', 'DNK', 'FIN', 'IRL'],
  'Asia': ['CHN', 'JPN', 'KOR', 'IND', 'THA', 'VNM', 'SGP', 'MYS', 'IDN', 'PHL', 'PAK', 'BGD'],
  'AmericaDoSul': ['BRA', 'ARG', 'CHL', 'COL', 'PER', 'VEN', 'ECU', 'BOL', 'PRY', 'URY']
};

const markers = [
  { name: 'EUA', coordinates: [-95, 37], region: 'EUA' },
  { name: 'Europa', coordinates: [10, 50], region: 'Europa' },
  { name: 'Asia', coordinates: [105, 35], region: 'Asia' },
  { name: 'Brasil', coordinates: [-52, -15], region: 'AmericaDoSul' }
];

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
    color: 'purple',
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

const WorldMap = ({ activeRegion, onRegionClick }) => {
  const getRegionForCountry = (countryCode) => {
    for (const [region, countries] of Object.entries(regionCountries)) {
      if (countries.includes(countryCode)) return region;
    }
    return null;
  };

  return (
    <div className="relative w-full h-full overflow-hidden rounded-lg" style={{ backgroundColor: '#1c211c' }}>
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
        <defs>
          <pattern id="dotGrid" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
            <circle cx="4" cy="4" r="0.8" fill="#2a352a" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dotGrid)" />
      </svg>

      <div className="relative w-full h-full" style={{ zIndex: 1 }}>
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{ scale: 100, center: [0, 20] }}
          width={800}
          height={400}
          style={{ width: '100%', height: '100%' }}
        >
          <Geographies geography={geoUrl}>
            {({ geographies }) => {
              const regions = { EUA: [], Europa: [], Asia: [], AmericaDoSul: [] };
              geographies.forEach((geo) => {
                const region = getRegionForCountry(geo.id);
                if (region && regions[region]) regions[region].push(geo);
              });

              return (
                <>
                  {Object.entries(regions).map(([regionName, geos]) => {
                    const isActive = regionName === activeRegion || activeRegion === 'Global';
                    return (
                      <g key={regionName} onClick={() => onRegionClick(regionName)} style={{ cursor: 'pointer' }}>
                        {geos.map((geo) => (
                          <Geography
                            key={geo.rsmKey}
                            geography={geo}
                            fill={isActive ? '#4ade80' : '#1a1f1a'}
                            stroke="#0a0d0a"
                            strokeWidth={0.3}
                            style={{
                              default: { outline: 'none' },
                              hover: { fill: '#22c55e', outline: 'none' },
                              pressed: { fill: '#4ade80', outline: 'none' }
                            }}
                          />
                        ))}
                      </g>
                    );
                  })}
                  {geographies.filter((geo) => !getRegionForCountry(geo.id)).map((geo) => (
                    <Geography key={geo.rsmKey} geography={geo} fill="#0f120f" stroke="#1c211c" strokeWidth={0.5}
                      style={{ default: { outline: 'none', pointerEvents: 'none' } }} />
                  ))}
                </>
              );
            }}
          </Geographies>
          {markers.map(({ name, coordinates, region }) => {
            const isActive = activeRegion === region || activeRegion === 'Global';
            return isActive ? (
              <Marker key={name} coordinates={coordinates}>
                <circle r={8} fill="#22c55e" opacity={0.25}>
                  <animate attributeName="r" values="8;12;8" dur="1.5s" repeatCount="indefinite" />
                </circle>
                <circle r={3} fill="#4ade80" />
              </Marker>
            ) : null;
          })}
        </ComposableMap>
      </div>
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
  <button onClick={onClick}
    className={`flex flex-col p-3 md:p-4 rounded-lg border text-left transition-all ${isSelected ? 'border-green-500/50 bg-[#1a2418]' : 'border-gray-700/30 bg-[#161a16] hover:border-gray-600'}`}
    style={{ minHeight: '160px' }}
  >
    <div className="flex items-center justify-between mb-2">
      <span className="text-white font-semibold text-xs md:text-sm tracking-tight">{tier.name}</span>
      <SpeedBars level={tier.level} color={tier.color} />
    </div>
    <div className="text-green-400 text-[10px] md:text-xs font-mono font-medium tracking-tight">{tier.speed}</div>
    <div className="text-gray-400 text-[9px] md:text-[10px] mb-1.5">{tier.time}</div>
    <div className="text-gray-500 text-[9px] md:text-[10px] leading-relaxed">{tier.gpu}</div>
    <div className="text-gray-500 text-[9px] md:text-[10px] leading-relaxed">{tier.vram}</div>
    <div className="text-yellow-400/80 text-[9px] md:text-[10px] font-mono font-medium mt-1.5">{tier.priceRange}</div>
    <div className="mt-auto pt-2 border-t border-gray-700/30">
      <p className="text-gray-500 text-[8px] md:text-[9px] leading-relaxed">{tier.description}</p>
    </div>
  </button>
);

// Componente do Seletor de GPU Visual
const GPUSelector = ({ selectedGPU, onSelectGPU, selectedCategory, onSelectCategory }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getCategoryIcon = (iconType, isActive) => {
    const colorClass = isActive ? 'text-white' : 'text-gray-400';
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
    if (!isActive) return 'bg-[#1a1f1a]';
    switch (color) {
      case 'green': return 'bg-green-600/30 border-green-500/50';
      case 'blue': return 'bg-blue-600/30 border-blue-500/50';
      case 'purple': return 'bg-purple-600/30 border-purple-500/50';
      default: return 'bg-gray-600/30 border-gray-500/50';
    }
  };

  const getIconBgColor = (color) => {
    switch (color) {
      case 'green': return 'bg-green-500/20';
      case 'blue': return 'bg-blue-500/20';
      case 'purple': return 'bg-purple-500/20';
      default: return 'bg-gray-500/20';
    }
  };

  const currentCategory = GPU_CATEGORIES.find(c => c.id === selectedCategory) || GPU_CATEGORIES[0];
  const availableGPUs = currentCategory.gpus.length > 0
    ? GPU_OPTIONS.filter(g => currentCategory.gpus.includes(g.value))
    : [];

  return (
    <div className="rounded-xl border border-gray-800/50 bg-[#161a16] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-green-400" />
          </div>
          <div>
            <p className="text-white text-sm font-medium">GPU</p>
            <p className="text-gray-500 text-[10px]">Selecione o tipo</p>
          </div>
        </div>
        {selectedGPU !== 'any' && (
          <span className="px-2 py-1 rounded-full bg-green-500/20 text-green-400 text-[10px] font-medium">
            {GPU_OPTIONS.find(g => g.value === selectedGPU)?.label}
          </span>
        )}
      </div>

      {/* Category Grid */}
      <div className="p-3">
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
                    : 'border-gray-800/50 hover:border-gray-700 bg-[#1a1f1a]'
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
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <Label className="text-[10px] text-gray-400 mb-2 block">Modelo Específico (opcional)</Label>
            <Select value={selectedGPU} onValueChange={onSelectGPU}>
              <SelectTrigger className="bg-[#1a1f1a] border-gray-700/50 h-9 text-xs">
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
      </div>
    </div>
  );
};

// Componente do AI Wizard Chat
const AIWizardChat = ({ onRecommendation, onSearchWithFilters }) => {
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

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800/50">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h3 className="text-white font-semibold text-sm">AI GPU Advisor</h3>
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
                    className="px-2 py-1 text-[10px] text-gray-400 bg-gray-800/50 rounded hover:bg-gray-700/50 transition-colors"
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
              <div className="w-7 h-7 rounded-lg bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-purple-400" />
              </div>
            )}
            <div className={`max-w-[90%] p-3 rounded-lg ${
              msg.role === 'user'
                ? 'ai-wizard-message-user'
                : 'ai-wizard-message-assistant'
            }`}>
              {/* Text content */}
              <div className="text-xs prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-strong:text-green-400 prose-ul:my-1 prose-li:my-0 prose-hr:border-gray-700 prose-h2:text-base prose-h3:text-sm prose-h4:text-xs mb-3">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              </div>

              {/* Interactive Stage Displays */}
              {msg.showCards && (
                <div className="mt-3 pt-3 border-t border-gray-700/30">
                  {/* Legacy Recommendation */}
                  {(msg.stage === 'recommendation' || (!msg.stage && msg.recommendation?.gpu_options)) && (
                    <GPUWizardDisplay
                      recommendation={msg.recommendation}
                      onSearch={(opt) => applyRecommendation(opt)}
                    />
                  )}

                  {/* Research Stage */}
                  {msg.stage === 'research' && msg.data?.research_results && (
                    <div className="bg-gray-800/50 rounded-lg p-3 text-xs space-y-2">
                      <div className="font-semibold text-blue-400">Resultados da Pesquisa:</div>
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
                      <div className="font-semibold text-purple-400 text-xs mb-2">Opções de Preço Encontradas:</div>
                      <div className="grid grid-cols-1 gap-2">
                        {msg.data.price_options.map((opt, idx) => (
                          <div key={idx} className="bg-gray-800/50 p-3 rounded-lg border border-gray-700 hover:border-purple-500/50 transition-colors">
                            <div className="flex justify-between items-start mb-1">
                              <span className="font-bold text-white text-sm">{opt.tier}</span>
                              <span className="text-green-400 font-mono text-xs">{opt.price_per_hour}</span>
                            </div>
                            <div className="text-gray-400 text-xs mb-1">{opt.gpus.join(', ')}</div>
                            <div className="text-gray-500 text-[10px]">{opt.performance}</div>
                            <button 
                              onClick={() => {
                                setInputValue(`Escolher opção ${opt.tier}`);
                                sendMessage();
                              }}
                              className="mt-2 w-full py-1 text-[10px] bg-purple-600/20 text-purple-400 rounded hover:bg-purple-600/30 transition-colors"
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
                          <div key={idx} className="bg-gray-800/50 p-3 rounded-lg border border-gray-700 hover:border-green-500/50 transition-colors">
                            <div className="flex justify-between items-center mb-1">
                              <span className="font-bold text-white text-xs">{machine.gpu}</span>
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
                  className="mt-3 w-full py-2 px-3 text-xs font-medium text-white bg-purple-600/50 hover:bg-purple-600/70 rounded-lg transition-colors flex items-center justify-center gap-2"
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
            <div className="w-7 h-7 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-purple-400" />
            </div>
            <div className="ai-wizard-loading">
              <Loader2 className="w-4 h-4 text-purple-400 ai-wizard-loading-spinner" />
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
      bg: 'bg-gray-800/40',
      border: 'border-gray-600/20',
      badge: 'bg-gray-700/50 text-gray-400',
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
        <div className="text-white font-semibold text-sm">{option.gpu}</div>
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
                <tr key={framework} className="border-b border-gray-700/20">
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
      <div className="text-center mb-4 pb-3 border-b border-gray-700/30">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Modelo</div>
        <div className="text-white font-bold text-lg">{modelName}</div>
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
              : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 hover:text-white'
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
          <div className="text-white font-bold text-xl mb-1">{currentOption.gpu}</div>

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
              : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 hover:text-white'
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
        <div className="relative h-2 bg-gray-700/50 rounded-full">
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
  <div className="p-4 rounded-lg border border-gray-700/40 bg-[#161a16] hover:border-green-500/30 transition-all">
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <Cpu className="w-5 h-5 text-green-400" />
        <span className="text-white font-semibold text-sm">{offer.gpu_name}</span>
        {offer.num_gpus > 1 && <span className="text-xs text-gray-400">x{offer.num_gpus}</span>}
      </div>
      <div className="text-green-400 font-mono font-semibold text-sm">
        ${offer.dph_total?.toFixed(3)}/hr
      </div>
    </div>
    <div className="grid grid-cols-2 gap-2 mb-3 text-[11px]">
      <div className="text-gray-400"><span className="text-gray-500">VRAM:</span> {offer.gpu_ram?.toFixed(0) || '-'} GB</div>
      <div className="text-gray-400"><span className="text-gray-500">CPU:</span> {offer.cpu_cores_effective || '-'} cores</div>
      <div className="text-gray-400"><span className="text-gray-500">Disco:</span> {offer.disk_space?.toFixed(0) || '-'} GB</div>
      <div className="text-gray-400"><span className="text-gray-500">Rede:</span> {offer.inet_down?.toFixed(0) || '-'} Mbps</div>
      <div className="text-gray-400"><span className="text-gray-500">DLPerf:</span> {offer.dlperf?.toFixed(1) || '-'}</div>
      <div className="text-gray-400"><span className="text-gray-500">PCIe:</span> {offer.pcie_bw?.toFixed(1) || '-'} GB/s</div>
    </div>
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${(offer.reliability || 0) >= 0.9 ? 'bg-green-400' : (offer.reliability || 0) >= 0.7 ? 'bg-yellow-400' : 'bg-red-400'}`} />
        <span className="text-[10px] text-gray-400">{((offer.reliability || 0) * 100).toFixed(0)}%</span>
        {offer.verified && <span className="text-[9px] text-green-400 px-1.5 py-0.5 bg-green-500/10 rounded">Verificado</span>}
      </div>
      <button
        onClick={() => onSelect(offer)}
        className="px-3 py-1.5 text-xs font-medium text-white bg-[#4a5d4a] hover:bg-[#5a6d5a] rounded transition-colors"
      >
        Selecionar
      </button>
    </div>
  </div>
);

// Collapsible Filter Section
const FilterSection = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-800/50 rounded-lg bg-[#161a16] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-[#1a1f1a] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-green-400" />
          <span className="text-sm font-medium text-white">{title}</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && <div className="p-3 pt-0 border-t border-gray-800/50">{children}</div>}
    </div>
  );
};

// Stats Card Component with tooltip and animation support
const StatCard = ({ icon: Icon, title, value, subtext, color = 'green', trend = null, tooltip = null, animate = false, comparison = null }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [displayValue, setDisplayValue] = useState(animate ? '$0' : value);

  // Count-up animation for numeric values
  useEffect(() => {
    if (!animate || typeof value !== 'string') return;

    const match = value.match(/^\$?([\d,]+)/);
    if (!match) {
      setDisplayValue(value);
      return;
    }

    const targetNum = parseInt(match[1].replace(/,/g, ''), 10);
    const prefix = value.startsWith('$') ? '$' : '';
    const duration = 1500; // 1.5s animation
    const steps = 30;
    const stepDuration = duration / steps;
    let currentStep = 0;

    const timer = setInterval(() => {
      currentStep++;
      const progress = currentStep / steps;
      const easeOut = 1 - Math.pow(1 - progress, 3); // Ease-out cubic
      const currentValue = Math.floor(targetNum * easeOut);
      setDisplayValue(`${prefix}${currentValue.toLocaleString()}`);

      if (currentStep >= steps) {
        clearInterval(timer);
        setDisplayValue(value);
      }
    }, stepDuration);

    return () => clearInterval(timer);
  }, [animate, value]);

  const colorClasses = {
    green: 'from-green-500/20 to-green-600/20 border-green-500/30 text-green-400',
    blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/30 text-blue-400',
    purple: 'from-purple-500/20 to-purple-600/20 border-purple-500/30 text-purple-400',
    yellow: 'from-yellow-500/20 to-yellow-600/20 border-yellow-500/30 text-yellow-400',
    red: 'from-red-500/20 to-red-600/20 border-red-500/30 text-red-400'
  };

  return (
    <div
      className={`p-4 rounded-xl border bg-gradient-to-br ${colorClasses[color]} backdrop-blur-sm relative`}
      onMouseEnter={() => tooltip && setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Tooltip */}
      {tooltip && showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-300 whitespace-nowrap z-50 shadow-lg">
          {tooltip}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
        </div>
      )}

      <div className="flex items-center justify-between mb-2">
        <Icon className="w-5 h-5 opacity-80" />
        {trend && (
          <span className={`text-xs font-medium ${trend > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div className={`text-2xl font-bold text-white mb-1 ${animate ? 'transition-all' : ''}`}>
        {animate ? displayValue : value}
      </div>
      <div className="text-xs text-gray-400">{title}</div>
      {subtext && <div className="text-[10px] text-gray-500 mt-1">{subtext}</div>}
      {comparison && (
        <div className="text-[10px] text-green-400/80 mt-1 font-medium">
          {comparison}
        </div>
      )}
    </div>
  );
};

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

  // Filtros avançados completos do Vast.ai
  const [advancedFilters, setAdvancedFilters] = useState({
    // GPU
    gpu_name: 'any',
    num_gpus: 1,
    min_gpu_ram: 0,
    gpu_frac: 1,
    // CPU & Memória
    min_cpu_cores: 1,
    min_cpu_ram: 1,
    min_disk: 50,
    // Performance
    min_dlperf: 0,
    min_pcie_bw: 0,
    cuda_vers: 'any',
    // Rede
    min_inet_down: 100,
    min_inet_up: 50,
    direct_port_count: 1,
    // Preço
    max_price: 5.0,
    rental_type: 'on-demand',
    // Qualidade & Localização
    min_reliability: 0,
    region: 'any',
    verified_only: false,
    // Opções avançadas
    static_ip: false,
    // Ordenação
    order_by: 'dph_total',
    limit: 100
  });

  const tabs = ['EUA', 'Europa', 'Ásia', 'América do Sul', 'Global'];
  const tabIds = ['EUA', 'Europa', 'Asia', 'AmericaDoSul', 'Global'];

  const tiers = [
    { name: 'Lento', level: 1, color: 'gray', speed: '100-250 Mbps', time: '~5 min', gpu: 'RTX 3070/3080', vram: '8-12GB VRAM', priceRange: '$0.05 - $0.25/hr', description: 'Econômico. Ideal para tarefas básicas e testes.', filter: { max_price: 0.25, min_gpu_ram: 8 } },
    { name: 'Medio', level: 2, color: 'yellow', speed: '500-1000 Mbps', time: '~2 min', gpu: 'RTX 4070/4080', vram: '12-16GB VRAM', priceRange: '$0.25 - $0.50/hr', description: 'Balanceado. Bom para desenvolvimento diário.', filter: { max_price: 0.50, min_gpu_ram: 12 } },
    { name: 'Rapido', level: 3, color: 'orange', speed: '1000-2000 Mbps', time: '~30s', gpu: 'RTX 4090', vram: '24GB VRAM', priceRange: '$0.50 - $1.00/hr', description: 'Alta performance. Treinamentos e workloads pesados.', filter: { max_price: 1.00, min_gpu_ram: 24 } },
    { name: 'Ultra', level: 4, color: 'green', speed: '2000+ Mbps', time: '~10s', gpu: 'A100/H100', vram: '40-80GB VRAM', priceRange: '$1.00 - $10.00/hr', description: 'Máxima potência. Para as tarefas mais exigentes.', filter: { max_price: 10.0, min_gpu_ram: 40 } }
  ];

  const getToken = () => localStorage.getItem('auth_token');

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
      setOffers(data.offers || []);
    } catch (err) {
      setError(err.message);
      setOffers([]);
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
    navigate('/machines', { state: { selectedOffer: offer } });
  };

  const resetAdvancedFilters = () => {
    setAdvancedFilters({
      gpu_name: 'any', num_gpus: 1, min_gpu_ram: 0, gpu_frac: 1,
      min_cpu_cores: 1, min_cpu_ram: 1, min_disk: 50,
      min_dlperf: 0, min_pcie_bw: 0, cuda_vers: 'any',
      min_inet_down: 100, min_inet_up: 50, direct_port_count: 1,
      max_price: 5.0, rental_type: 'on-demand',
      min_reliability: 0, region: 'any', verified_only: false,
      static_ip: false, order_by: 'dph_total', limit: 100
    });
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8" style={{ backgroundColor: '#0e110e', fontFamily: "'Inter', sans-serif" }}>
      {showOnboarding && (
        <OnboardingWizard
          user={user}
          onClose={() => setShowOnboarding(false)}
          onComplete={handleCompleteOnboarding}
        />
      )}

      {/* Dashboard Stats Cards */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <StatCard
            icon={Server}
            title="Máquinas Ativas"
            value={`${dashboardStats.activeMachines}/${dashboardStats.totalMachines}`}
            subtext="Instâncias em execução"
            color="green"
            tooltip="Total de GPUs rodando vs contratadas"
          />
          <StatCard
            icon={DollarSign}
            title="Custo Diário"
            value={`$${dashboardStats.dailyCost}`}
            subtext="Estimativa baseada no uso"
            color="yellow"
            tooltip="Custo estimado baseado nas horas de uso hoje"
          />
          <StatCard
            icon={Shield}
            title="Economia Mensal"
            value={`$${dashboardStats.savings}`}
            subtext="vs. preços on-demand"
            color="purple"
            trend={89}
            animate={true}
            tooltip="Economia comparada a provedores tradicionais"
            comparison="vs AWS: $6,547 → você paga $724"
          />
          <StatCard
            icon={Activity}
            title="Uptime"
            value={`${dashboardStats.uptime}%`}
            subtext="Disponibilidade média"
            color="blue"
            tooltip="Disponibilidade média das suas máquinas"
          />
        </div>
      </div>

      {/* Deploy Wizard */}
      <div className="flex items-center justify-center">
      <div className="w-full max-w-md md:max-w-2xl lg:max-w-4xl xl:max-w-6xl rounded-xl overflow-hidden border border-gray-800/50 shadow-2xl" style={{ backgroundColor: '#131713' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-gray-800/50">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-green-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <span className="text-white text-lg font-semibold tracking-tight">Deploy</span>
          </div>

          <div className="flex gap-1 p-1 rounded-lg bg-[#1a1f1a]">
            <button
              onClick={() => { setMode('wizard'); setShowResults(false); }}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-all flex items-center gap-1.5 ${
                mode === 'wizard' ? 'bg-[#4a5d4a] text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Wand2 className="w-3.5 h-3.5" />
              Wizard
            </button>
            <button
              onClick={() => { setMode('ai'); setShowResults(false); }}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-all flex items-center gap-1.5 ${
                mode === 'ai' ? 'bg-purple-600/50 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              AI
            </button>
            <button
              onClick={() => { setMode('advanced'); setShowResults(false); }}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-all flex items-center gap-1.5 ${
                mode === 'advanced' ? 'bg-[#4a5d4a] text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              Avançado
            </button>
          </div>
        </div>

        {/* WIZARD MODE */}
        {mode === 'wizard' && !showResults && (
          <>
            <div className="flex flex-wrap gap-1 px-4 md:px-6 py-3 border-b border-gray-800/50">
              {tabs.map((tab, i) => (
                <button key={tab} onClick={() => setActiveTab(tabIds[i])}
                  className={`px-3 py-1.5 text-xs font-medium transition-all rounded border ${activeTab === tabIds[i] ? 'text-gray-200 bg-gray-600/30 border-gray-500/40' : 'text-gray-500 hover:text-gray-300 border-transparent'}`}>
                  {tab}
                </button>
              ))}
            </div>

            <div className="p-4 md:p-6 lg:p-8">
              <div className="flex flex-col md:flex-row gap-4 md:gap-6 mb-6">
                <div className="flex-1">
                  <Label className="text-gray-400 text-xs mb-2 block">Região</Label>
                  <div className="h-40 md:h-48 lg:h-56 rounded-lg overflow-hidden border border-gray-800/40">
                    <WorldMap activeRegion={activeTab} onRegionClick={setActiveTab} />
                  </div>
                </div>
                <div className="w-full md:w-72 lg:w-80">
                  <Label className="text-gray-400 text-xs mb-2 block">GPU (opcional)</Label>
                  <GPUSelector
                    selectedGPU={selectedGPU}
                    onSelectGPU={setSelectedGPU}
                    selectedCategory={selectedGPUCategory}
                    onSelectCategory={setSelectedGPUCategory}
                  />
                </div>
              </div>

              <Label className="text-gray-500 text-xs mb-3 block">Velocidade & Custo</Label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-6">
                {tiers.map((tier) => (
                  <TierCard key={tier.name} tier={tier} isSelected={selectedTier === tier.name} onClick={() => setSelectedTier(tier.name)} />
                ))}
              </div>

              <div className="relative h-2.5 rounded-full mb-6 mx-1" style={{ backgroundColor: '#252a25' }}>
                <div className="absolute inset-y-0 left-0 rounded-full"
                  style={{ width: `${tiers.findIndex(t => t.name === selectedTier) * 25 + 25}%`, background: 'linear-gradient(to right, #4b5563, #ca8a04, #ea580c, #22c55e)' }} />
                <div className="absolute top-1/2 -translate-y-1/2 w-5 h-5 bg-white rounded-full border-2 border-green-500 shadow-lg"
                  style={{ left: `calc(${tiers.findIndex(t => t.name === selectedTier) * 25 + 25}% - 10px)` }} />
              </div>

              <button
                onClick={handleWizardSearch}
                className="w-full py-3 md:py-4 rounded-lg text-white text-sm font-semibold transition-all bg-[#4a5d4a] hover:bg-[#5a6d5a] flex items-center justify-center gap-2"
              >
                <Search className="w-4 h-4" />
                Buscar Máquinas Disponíveis
              </button>
            </div>
          </>
        )}

        {/* AI MODE */}
        {mode === 'ai' && !showResults && (
          <div className="p-4 md:p-6 lg:p-8">
            <div className="max-w-2xl mx-auto">
              <div className="rounded-xl border border-gray-800/50 bg-[#161a16] overflow-hidden">
                <AIWizardChat
                  onRecommendation={(rec) => {
                    console.log('AI Recommendation:', rec);
                  }}
                  onSearchWithFilters={(filters) => {
                    // Apply AI recommendation to search
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
                      region: ''
                    });
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* ADVANCED MODE */}
        {mode === 'advanced' && !showResults && (
          <div className="p-4 md:p-6 lg:p-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-white text-lg font-semibold">Busca Avançada</h2>
                <p className="text-gray-500 text-xs">Todos os filtros disponíveis do Vast.ai</p>
              </div>
              <button
                onClick={resetAdvancedFilters}
                className="px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 rounded transition-colors flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Limpar
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-4">
              {/* GPU */}
              <FilterSection title="GPU" icon={Cpu}>
                <div className="space-y-3 mt-3">
                  <div>
                    <Label className="text-xs text-gray-400 mb-1 block">Modelo da GPU</Label>
                    <Select value={advancedFilters.gpu_name} onValueChange={(v) => handleAdvancedFilterChange('gpu_name', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {GPU_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">Qtd GPUs</Label>
                      <Input type="number" min="1" max="8" value={advancedFilters.num_gpus}
                        onChange={(e) => handleAdvancedFilterChange('num_gpus', parseInt(e.target.value) || 1)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">VRAM Min</Label>
                      <Input type="number" min="0" step="4" value={advancedFilters.min_gpu_ram}
                        onChange={(e) => handleAdvancedFilterChange('min_gpu_ram', parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">GPU Frac</Label>
                      <Input type="number" min="0.1" max="1" step="0.1" value={advancedFilters.gpu_frac}
                        onChange={(e) => handleAdvancedFilterChange('gpu_frac', parseFloat(e.target.value) || 1)} />
                    </div>
                  </div>
                </div>
              </FilterSection>

              {/* CPU & Memória */}
              <FilterSection title="CPU & Memória" icon={Server}>
                <div className="space-y-3 mt-3">
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">CPU Cores</Label>
                      <Input type="number" min="1" value={advancedFilters.min_cpu_cores}
                        onChange={(e) => handleAdvancedFilterChange('min_cpu_cores', parseInt(e.target.value) || 1)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">RAM (GB)</Label>
                      <Input type="number" min="1" value={advancedFilters.min_cpu_ram}
                        onChange={(e) => handleAdvancedFilterChange('min_cpu_ram', parseFloat(e.target.value) || 1)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">Disco (GB)</Label>
                      <Input type="number" min="10" value={advancedFilters.min_disk}
                        onChange={(e) => handleAdvancedFilterChange('min_disk', parseFloat(e.target.value) || 50)} />
                    </div>
                  </div>
                </div>
              </FilterSection>

              {/* Performance */}
              <FilterSection title="Performance" icon={Gauge}>
                <div className="space-y-3 mt-3">
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">DLPerf Min</Label>
                      <Input type="number" min="0" step="0.1" value={advancedFilters.min_dlperf}
                        onChange={(e) => handleAdvancedFilterChange('min_dlperf', parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">PCIe BW</Label>
                      <Input type="number" min="0" step="0.1" value={advancedFilters.min_pcie_bw}
                        onChange={(e) => handleAdvancedFilterChange('min_pcie_bw', parseFloat(e.target.value) || 0)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">CUDA</Label>
                      <Select value={advancedFilters.cuda_vers} onValueChange={(v) => handleAdvancedFilterChange('cuda_vers', v)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {CUDA_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              </FilterSection>

              {/* Rede */}
              <FilterSection title="Rede" icon={Wifi}>
                <div className="space-y-3 mt-3">
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">Download</Label>
                      <Input type="number" min="10" value={advancedFilters.min_inet_down}
                        onChange={(e) => handleAdvancedFilterChange('min_inet_down', parseFloat(e.target.value) || 100)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">Upload</Label>
                      <Input type="number" min="10" value={advancedFilters.min_inet_up}
                        onChange={(e) => handleAdvancedFilterChange('min_inet_up', parseFloat(e.target.value) || 50)} />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-400 mb-1 block">Direct Ports</Label>
                      <Input type="number" min="0" value={advancedFilters.direct_port_count}
                        onChange={(e) => handleAdvancedFilterChange('direct_port_count', parseInt(e.target.value) || 1)} />
                    </div>
                  </div>
                </div>
              </FilterSection>

              {/* Preço */}
              <FilterSection title="Preço" icon={DollarSign}>
                <div className="space-y-3 mt-3">
                  <div>
                    <div className="flex justify-between mb-1">
                      <Label className="text-xs text-gray-400">Preço Máximo</Label>
                      <span className="text-xs text-green-400 font-mono">${advancedFilters.max_price.toFixed(2)}/hr</span>
                    </div>
                    <Slider
                      value={[advancedFilters.max_price]}
                      onValueChange={([v]) => handleAdvancedFilterChange('max_price', v)}
                      max={15}
                      min={0.05}
                      step={0.05}
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-gray-400 mb-1 block">Tipo de Aluguel</Label>
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
                <div className="space-y-3 mt-3">
                  <div>
                    <Label className="text-xs text-gray-400 mb-1 block">Região</Label>
                    <Select value={advancedFilters.region} onValueChange={(v) => handleAdvancedFilterChange('region', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {REGION_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <Label className="text-xs text-gray-400">Confiabilidade Mínima</Label>
                      <span className="text-xs text-green-400 font-mono">{(advancedFilters.min_reliability * 100).toFixed(0)}%</span>
                    </div>
                    <Slider
                      value={[advancedFilters.min_reliability]}
                      onValueChange={([v]) => handleAdvancedFilterChange('min_reliability', v)}
                      max={1}
                      min={0}
                      step={0.05}
                    />
                  </div>
                </div>
              </FilterSection>
            </div>

            {/* Opções & Ordenação */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-4">
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
                    <Label className="text-xs text-gray-400 mb-1 block">Ordenar Por</Label>
                    <Select value={advancedFilters.order_by} onValueChange={(v) => handleAdvancedFilterChange('order_by', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {ORDER_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-400 mb-1 block">Limite de Resultados</Label>
                    <Input type="number" min="10" max="500" value={advancedFilters.limit}
                      onChange={(e) => handleAdvancedFilterChange('limit', parseInt(e.target.value) || 100)} />
                  </div>
                </div>
              </FilterSection>
            </div>

            <button
              onClick={handleAdvancedSearch}
              className="w-full py-3 md:py-4 rounded-lg text-white text-sm font-semibold transition-all bg-[#4a5d4a] hover:bg-[#5a6d5a] flex items-center justify-center gap-2"
            >
              <Search className="w-4 h-4" />
              Buscar Máquinas
            </button>
          </div>
        )}

        {/* RESULTS VIEW */}
        {showResults && (
          <div className="p-4 md:p-6 lg:p-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-white text-lg font-semibold">Máquinas Disponíveis</h2>
                <p className="text-gray-500 text-xs">{offers.length} resultados encontrados</p>
              </div>
              <button
                onClick={() => setShowResults(false)}
                className="px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 rounded transition-colors"
              >
                ← Voltar
              </button>
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
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
