import { useState, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Sparkles,
  Zap,
  Server,
  ArrowRight,
  Check,
  TrendingDown,
  Filter,
  Search,
  SortAsc,
  SortDesc,
  Cpu,
  HardDrive,
  Gauge,
  DollarSign
} from 'lucide-react'
import { Badge } from '../components/tailadmin-ui'

// Dados de GPUs com preços reais baseados em Vast.ai (Dezembro 2024)
const GPU_OFFERS = [
  {
    id: 'rtx-4090',
    name: 'RTX 4090',
    brand: 'NVIDIA',
    architecture: 'Ada Lovelace',
    vram: 24,
    vramType: 'GDDR6X',
    cudaCores: 16384,
    tensorCores: 512,
    fp32: 82.6, // TFLOPS
    fp16: 165, // TFLOPS
    price: 0.31,
    priceAws: 3.50,
    availability: 'high',
    useCases: ['Inferência', 'Fine-tuning', 'Gaming', 'Rendering'],
    popular: true,
  },
  {
    id: 'rtx-4080',
    name: 'RTX 4080',
    brand: 'NVIDIA',
    architecture: 'Ada Lovelace',
    vram: 16,
    vramType: 'GDDR6X',
    cudaCores: 9728,
    tensorCores: 304,
    fp32: 48.7,
    fp16: 97,
    price: 0.25,
    priceAws: 2.80,
    availability: 'high',
    useCases: ['Inferência', 'Dev', 'Gaming'],
    popular: false,
  },
  {
    id: 'rtx-3090',
    name: 'RTX 3090',
    brand: 'NVIDIA',
    architecture: 'Ampere',
    vram: 24,
    vramType: 'GDDR6X',
    cudaCores: 10496,
    tensorCores: 328,
    fp32: 35.6,
    fp16: 71,
    price: 0.20,
    priceAws: 2.50,
    availability: 'medium',
    useCases: ['Inferência', 'Fine-tuning', 'Rendering'],
    popular: false,
  },
  {
    id: 'rtx-3080',
    name: 'RTX 3080',
    brand: 'NVIDIA',
    architecture: 'Ampere',
    vram: 10,
    vramType: 'GDDR6X',
    cudaCores: 8704,
    tensorCores: 272,
    fp32: 29.8,
    fp16: 59,
    price: 0.15,
    priceAws: 2.00,
    availability: 'high',
    useCases: ['Dev', 'Inferência leve', 'Gaming'],
    popular: false,
  },
  {
    id: 'a100-40gb',
    name: 'A100 40GB',
    brand: 'NVIDIA',
    architecture: 'Ampere',
    vram: 40,
    vramType: 'HBM2e',
    cudaCores: 6912,
    tensorCores: 432,
    fp32: 19.5,
    fp16: 312, // Tensor cores
    price: 0.64,
    priceAws: 4.10,
    availability: 'medium',
    useCases: ['Training', 'Fine-tuning', 'Produção'],
    popular: true,
    enterprise: true,
  },
  {
    id: 'a100-80gb',
    name: 'A100 80GB',
    brand: 'NVIDIA',
    architecture: 'Ampere',
    vram: 80,
    vramType: 'HBM2e',
    cudaCores: 6912,
    tensorCores: 432,
    fp32: 19.5,
    fp16: 312,
    price: 0.90,
    priceAws: 5.12,
    availability: 'low',
    useCases: ['LLMs grandes', 'Training distribuído'],
    popular: false,
    enterprise: true,
  },
  {
    id: 'h100-pcie',
    name: 'H100 PCIe',
    brand: 'NVIDIA',
    architecture: 'Hopper',
    vram: 80,
    vramType: 'HBM3',
    cudaCores: 14592,
    tensorCores: 456,
    fp32: 51,
    fp16: 1513, // Tensor cores FP8
    price: 1.20,
    priceAws: 8.00,
    availability: 'low',
    useCases: ['LLMs', 'Training em escala', 'Pesquisa'],
    popular: true,
    enterprise: true,
    flagship: true,
  },
  {
    id: 'h100-sxm',
    name: 'H100 SXM',
    brand: 'NVIDIA',
    architecture: 'Hopper',
    vram: 80,
    vramType: 'HBM3',
    cudaCores: 14592,
    tensorCores: 528,
    fp32: 67,
    fp16: 1979,
    price: 2.50,
    priceAws: 12.00,
    availability: 'low',
    useCases: ['Training massivo', 'Multi-GPU'],
    popular: false,
    enterprise: true,
    flagship: true,
  },
  {
    id: 'l40s',
    name: 'L40S',
    brand: 'NVIDIA',
    architecture: 'Ada Lovelace',
    vram: 48,
    vramType: 'GDDR6',
    cudaCores: 18176,
    tensorCores: 568,
    fp32: 91.6,
    fp16: 183,
    price: 0.85,
    priceAws: 4.50,
    availability: 'medium',
    useCases: ['Inferência', 'Video AI', 'Generative AI'],
    popular: false,
    enterprise: true,
  },
  {
    id: 'a6000',
    name: 'RTX A6000',
    brand: 'NVIDIA',
    architecture: 'Ampere',
    vram: 48,
    vramType: 'GDDR6',
    cudaCores: 10752,
    tensorCores: 336,
    fp32: 38.7,
    fp16: 77,
    price: 0.45,
    priceAws: 3.20,
    availability: 'medium',
    useCases: ['Workstation', 'Rendering', 'AI'],
    popular: false,
    enterprise: true,
  },
]

const SORT_OPTIONS = [
  { value: 'price-asc', label: 'Menor preço' },
  { value: 'price-desc', label: 'Maior preço' },
  { value: 'vram-desc', label: 'Mais VRAM' },
  { value: 'savings-desc', label: 'Maior economia' },
  { value: 'performance-desc', label: 'Melhor performance' },
]

const VRAM_FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: '16', label: '16GB+' },
  { value: '24', label: '24GB+' },
  { value: '40', label: '40GB+' },
  { value: '80', label: '80GB+' },
]

export default function GpuOffers() {
  const navigate = useNavigate()
  const location = useLocation()
  const isDemo = location.pathname.startsWith('/demo-app')
  const basePath = isDemo ? '/demo-app' : '/app'

  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('price-asc')
  const [vramFilter, setVramFilter] = useState('all')
  const [showEnterprise, setShowEnterprise] = useState(true)

  const filteredOffers = useMemo(() => {
    let result = [...GPU_OFFERS]

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(gpu =>
        gpu.name.toLowerCase().includes(query) ||
        gpu.architecture.toLowerCase().includes(query) ||
        gpu.useCases.some(uc => uc.toLowerCase().includes(query))
      )
    }

    // VRAM filter
    if (vramFilter !== 'all') {
      const minVram = parseInt(vramFilter)
      result = result.filter(gpu => gpu.vram >= minVram)
    }

    // Enterprise filter
    if (!showEnterprise) {
      result = result.filter(gpu => !gpu.enterprise)
    }

    // Sort
    const [field, direction] = sortBy.split('-')
    result.sort((a, b) => {
      let aVal, bVal
      switch (field) {
        case 'price':
          aVal = a.price
          bVal = b.price
          break
        case 'vram':
          aVal = a.vram
          bVal = b.vram
          break
        case 'savings':
          aVal = ((a.priceAws - a.price) / a.priceAws) * 100
          bVal = ((b.priceAws - b.price) / b.priceAws) * 100
          break
        case 'performance':
          aVal = a.fp16
          bVal = b.fp16
          break
        default:
          aVal = a.price
          bVal = b.price
      }
      return direction === 'asc' ? aVal - bVal : bVal - aVal
    })

    return result
  }, [searchQuery, sortBy, vramFilter, showEnterprise])

  const handleProvision = (gpu) => {
    // Redireciona para página de machines com GPU selecionada
    navigate(`${basePath}/machines`, { state: { selectedGpu: gpu.name } })
  }

  const getAvailabilityBadge = (availability) => {
    switch (availability) {
      case 'high':
        return <Badge variant="success" dot>Alta disponibilidade</Badge>
      case 'medium':
        return <Badge variant="warning" dot>Disponível</Badge>
      case 'low':
        return <Badge variant="gray" dot>Limitado</Badge>
      default:
        return null
    }
  }

  const getSavingsPercent = (gpu) => {
    return Math.round(((gpu.priceAws - gpu.price) / gpu.priceAws) * 100)
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <div className="stat-card-icon stat-card-icon-primary">
                <Sparkles className="w-5 h-5" />
              </div>
              Ofertas GPU Cloud
            </h1>
            <p className="page-subtitle">GPUs de alto desempenho com até 85% de economia vs AWS/GCP</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 p-4 rounded-xl bg-dark-surface-card border border-white/10">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Buscar por GPU, arquitetura ou caso de uso..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-sm text-white bg-dark-surface-secondary border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500 focus:border-brand-500 placeholder:text-gray-500"
            />
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <SortAsc className="w-4 h-4 text-gray-500" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2.5 text-sm text-white bg-dark-surface-secondary border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
            >
              {SORT_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* VRAM Filter */}
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-gray-500" />
            <select
              value={vramFilter}
              onChange={(e) => setVramFilter(e.target.value)}
              className="px-3 py-2.5 text-sm text-white bg-dark-surface-secondary border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
            >
              {VRAM_FILTERS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Enterprise Toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showEnterprise}
              onChange={(e) => setShowEnterprise(e.target.checked)}
              className="w-4 h-4 rounded border-white/20 bg-dark-surface-secondary text-brand-500 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-400">Incluir Enterprise</span>
          </label>
        </div>
      </div>

      {/* GPU Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filteredOffers.map((gpu) => (
          <div
            key={gpu.id}
            className={`relative p-5 rounded-xl bg-dark-surface-card border transition-all hover:border-brand-500/50 ${
              gpu.flagship ? 'border-brand-500/30' : 'border-white/10'
            }`}
          >
            {/* Popular Badge */}
            {gpu.popular && (
              <div className="absolute -top-2 -right-2">
                <Badge variant="primary" className="text-[10px] font-bold">
                  <Zap className="w-3 h-3 mr-1" />
                  Popular
                </Badge>
              </div>
            )}

            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold text-white">{gpu.name}</h3>
                <p className="text-xs text-gray-500">{gpu.architecture}</p>
              </div>
              {getAvailabilityBadge(gpu.availability)}
            </div>

            {/* Specs */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-2 rounded-lg bg-white/5">
                <div className="flex items-center gap-1.5 mb-1">
                  <HardDrive className="w-3 h-3 text-gray-500" />
                  <span className="text-[10px] text-gray-500 uppercase">VRAM</span>
                </div>
                <div className="text-sm font-bold text-white">{gpu.vram}GB</div>
                <div className="text-[10px] text-gray-500">{gpu.vramType}</div>
              </div>

              <div className="p-2 rounded-lg bg-white/5">
                <div className="flex items-center gap-1.5 mb-1">
                  <Gauge className="w-3 h-3 text-gray-500" />
                  <span className="text-[10px] text-gray-500 uppercase">FP16</span>
                </div>
                <div className="text-sm font-bold text-white">{gpu.fp16} TFLOPS</div>
                <div className="text-[10px] text-gray-500">{gpu.tensorCores} Tensor Cores</div>
              </div>
            </div>

            {/* Use Cases */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              {gpu.useCases.slice(0, 3).map((useCase, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 text-[10px] text-gray-400 bg-white/5 rounded-full"
                >
                  {useCase}
                </span>
              ))}
            </div>

            {/* Pricing */}
            <div className="p-3 rounded-lg bg-brand-500/10 border border-brand-500/20 mb-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="text-2xl font-bold text-white">
                    ${gpu.price.toFixed(2)}
                    <span className="text-sm text-gray-400 font-normal">/hora</span>
                  </div>
                  <div className="text-xs text-gray-500 line-through">
                    AWS: ${gpu.priceAws.toFixed(2)}/h
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-1 text-brand-400">
                    <TrendingDown className="w-4 h-4" />
                    <span className="text-lg font-bold">{getSavingsPercent(gpu)}%</span>
                  </div>
                  <div className="text-[10px] text-gray-500">economia</div>
                </div>
              </div>

              <div className="flex items-center gap-2 text-[10px] text-gray-400">
                <Check className="w-3 h-3 text-brand-400" />
                <span>Sem compromisso • Pague por hora</span>
              </div>
            </div>

            {/* CTA */}
            <button
              onClick={() => handleProvision(gpu)}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-brand-800/20 hover:bg-brand-800/30 border border-brand-700/40 text-brand-400 text-sm font-medium transition-all"
            >
              <Server className="w-4 h-4" />
              Provisionar
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {filteredOffers.length === 0 && (
        <div className="text-center py-12">
          <Search className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">Nenhuma GPU encontrada</h3>
          <p className="text-sm text-gray-500">Tente ajustar os filtros ou termos de busca</p>
        </div>
      )}

      {/* Info Footer */}
      <div className="mt-8 p-4 rounded-xl bg-dark-surface-card border border-white/10">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-brand-500/10">
            <DollarSign className="w-5 h-5 text-brand-400" />
          </div>
          <div>
            <h4 className="text-sm font-medium text-white mb-1">Preços atualizados em tempo real</h4>
            <p className="text-xs text-gray-500">
              Os preços são baseados em Vast.ai e outras clouds de GPU. Podem variar de acordo com a disponibilidade
              e demanda. A economia é calculada comparando com preços equivalentes na AWS/GCP.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
