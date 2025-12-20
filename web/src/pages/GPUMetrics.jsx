import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { BarChart3, TrendingUp, TrendingDown, ArrowRight, Package, Cpu, AlertTriangle, Shield, Zap, DollarSign, Clock, Server, Sparkles, PiggyBank } from 'lucide-react'
import {
  SpotMonitor,
  SavingsCalculator,
  InterruptionRate,
  SafeWindows,
  LLMGpuRanking,
  SpotPrediction,
  InstantAvailability,
  ReliabilityScore,
  TrainingCost,
  FleetStrategy
} from '../components/spot'
import RealSavingsDashboard from '../components/RealSavingsDashboard'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/dumont-ui'
import { Badge, Progress } from '../components/tailadmin-ui'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const API_BASE = ''

export default function GPUMetrics() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)

  // Read tab and report from URL params
  const urlTab = searchParams.get('tab') || 'market'
  const urlReport = searchParams.get('report') || null
  const [activeTab, setActiveTab] = useState(urlTab)
  const [activeReport, setActiveReport] = useState(urlReport)

  // Update state when URL changes
  useEffect(() => {
    setActiveTab(searchParams.get('tab') || 'market')
    setActiveReport(searchParams.get('report') || null)
  }, [searchParams])

  // Update URL when tab changes
  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setSearchParams({ tab })
  }

  // Market data
  const [marketData, setMarketData] = useState([])
  const [marketSummary, setMarketSummary] = useState({})
  const [availableGPUs, setAvailableGPUs] = useState([])
  const [machineTypes, setMachineTypes] = useState([])

  // Providers data
  const [providers, setProviders] = useState([])

  // Efficiency data
  const [efficiency, setEfficiency] = useState([])

  // Predictions
  const [predictions, setPredictions] = useState(null)

  // Filters
  const [selectedGPU, setSelectedGPU] = useState('all')
  const [selectedType, setSelectedType] = useState('all')
  const [timeRange, setTimeRange] = useState(24)

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    loadMarketData()
  }, [selectedGPU, selectedType, timeRange])

  const getAuthHeaders = () => {
    const token = localStorage.getItem('auth_token')
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }

  const loadInitialData = async () => {
    try {
      // Load available GPUs and types
      const [gpusRes, typesRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/metrics/gpus`, {
          credentials: 'include',
          headers: getAuthHeaders()
        }),
        fetch(`${API_BASE}/api/v1/metrics/types`, {
          credentials: 'include',
          headers: getAuthHeaders()
        })
      ])

      if (gpusRes.ok) {
        const data = await gpusRes.json()
        setAvailableGPUs(data.gpus || [])
      }

      if (typesRes.ok) {
        const data = await typesRes.json()
        setMachineTypes(data.types || ['on-demand', 'interruptible', 'bid'])
      }

      await loadMarketData()
      setLoading(false)
    } catch (error) {
      console.error('Erro ao carregar dados iniciais:', error)
      setLoading(false)
    }
  }

  const loadMarketData = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedGPU !== 'all') params.append('gpu_name', selectedGPU)
      if (selectedType !== 'all') params.append('machine_type', selectedType)
      params.append('hours', timeRange)
      params.append('limit', 100)

      const [marketRes, summaryRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/metrics/market?${params}`, {
          credentials: 'include',
          headers: getAuthHeaders()
        }),
        fetch(`${API_BASE}/api/v1/metrics/market/summary?${params}`, {
          credentials: 'include',
          headers: getAuthHeaders()
        })
      ])

      if (marketRes.ok) {
        const data = await marketRes.json()
        setMarketData(Array.isArray(data) ? data : (data.data || []))
      }

      if (summaryRes.ok) {
        const data = await summaryRes.json()
        setMarketSummary(data.data || {})
      }
    } catch (error) {
      console.error('Erro ao carregar dados de mercado:', error)
    }
  }

  const loadProviders = async () => {
    try {
      const params = new URLSearchParams()
      params.append('limit', 50)

      const res = await fetch(`${API_BASE}/api/v1/metrics/providers?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })

      if (res.ok) {
        const data = await res.json()
        setProviders(Array.isArray(data) ? data : (data.data || []))
      }
    } catch (error) {
      console.error('Erro ao carregar provedores:', error)
    }
  }

  const loadEfficiency = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedGPU !== 'all') params.append('gpu_name', selectedGPU)
      if (selectedType !== 'all') params.append('machine_type', selectedType)
      params.append('limit', 50)

      const res = await fetch(`${API_BASE}/api/v1/metrics/efficiency?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })

      if (res.ok) {
        const data = await res.json()
        setEfficiency(Array.isArray(data) ? data : (data.data || []))
      }
    } catch (error) {
      console.error('Erro ao carregar eficiência:', error)
    }
  }

  const loadPredictions = async (gpuName) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/predictions/${encodeURIComponent(gpuName)}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })

      if (res.ok) {
        const data = await res.json()
        setPredictions(data.predictions)
      }
    } catch (error) {
      console.error('Erro ao carregar previsões:', error)
    }
  }

  useEffect(() => {
    if (activeTab === 'providers') loadProviders()
    if (activeTab === 'efficiency') loadEfficiency()
  }, [activeTab, selectedGPU, selectedType])

  const formatPrice = (price) => price ? `$${price.toFixed(2)}/h` : '-'
  const formatPercent = (value) => value ? `${(value * 100).toFixed(1)}%` : '-'
  const formatTime = (timestamp) => new Date(timestamp).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })

  const getMachineTypeLabel = (type) => {
    const labels = {
      'on-demand': 'On-Demand',
      'interruptible': 'Spot/Interruptible',
      'bid': 'Bid'
    }
    return labels[type] || type
  }

  const getMachineTypeColor = (type) => {
    const colors = {
      'on-demand': '#3b82f6',
      'interruptible': '#22c55e',
      'bid': '#f59e0b'
    }
    return colors[type] || '#6b7280'
  }

  const getReportTitle = (report) => {
    const titles = {
      'monitor': 'Monitor de Preços Spot',
      'savings': 'Calculadora de Economia',
      'availability': 'Disponibilidade Instantânea',
      'prediction': 'Previsão de Preços',
      'safe-windows': 'Janelas Seguras',
      'reliability': 'Score de Confiabilidade',
      'interruption': 'Taxa de Interrupção',
      'llm': 'Melhor GPU para LLM',
      'training': 'Custo por Treinamento',
      'fleet': 'Estratégia de Fleet'
    }
    return titles[report] || 'Relatórios Spot'
  }

  // Chart data for market summary
  const getMarketChartData = () => {
    const gpuData = {}

    marketData.forEach(record => {
      const key = record.gpu_name
      if (!gpuData[key]) gpuData[key] = []
      gpuData[key].push(record)
    })

    const datasets = Object.entries(gpuData).map(([gpu, records], index) => {
      const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
      const color = colors[index % colors.length]

      return {
        label: gpu,
        data: records.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)).map(r => r.avg_price),
        borderColor: color,
        backgroundColor: `${color}20`,
        fill: false,
        tension: 0.4,
      }
    })

    const labels = marketData.length > 0
      ? [...new Set(marketData.map(r => formatTime(r.timestamp)))].slice(-20)
      : []

    return { labels, datasets }
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: { color: '#9ca3af', font: { size: 11 }, usePointStyle: true },
      },
      tooltip: {
        callbacks: {
          label: (context) => `${context.dataset.label}: $${context.parsed.y?.toFixed(2)}/h`,
        },
      },
    },
    scales: {
      y: {
        ticks: { color: '#9ca3af', callback: (value) => `$${value.toFixed(2)}` },
        grid: { color: '#30363d' },
      },
      x: {
        ticks: { color: '#9ca3af', maxRotation: 45 },
        grid: { display: false },
      },
    },
  }

  if (loading) {
    return (
      <div className="p-6 max-w-[1400px] mx-auto min-h-screen">
        <div className="flex flex-col items-center justify-center min-h-[400px] text-gray-400">
          <div className="ta-spinner mb-4"></div>
          <p>Carregando métricas...</p>
        </div>
      </div>
    )
  }

  const getTabTitle = () => {
    const titles = {
      'market': 'Mercado',
      'providers': 'Provedores',
      'efficiency': 'Eficiência',
      'savings': 'Economia',
      'spot': activeReport ? getReportTitle(activeReport) : 'Spot Reports'
    }
    return titles[activeTab] || 'Métricas'
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-[1400px] mx-auto min-h-screen">
      {/* Header with Breadcrumb */}
      <div className="mb-8">
        <nav className="flex items-center gap-2 text-sm text-gray-500 mb-3">
          <a href="/app" className="hover:text-emerald-400 transition-colors">Home</a>
          <span className="text-gray-600">/</span>
          <a href="/app/metrics" className="hover:text-emerald-400 transition-colors">Métricas</a>
          <span className="text-gray-600">/</span>
          <span className="text-white font-medium">{getTabTitle()}</span>
        </nav>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
              <div className="stat-card-icon stat-card-icon-success">
                <BarChart3 size={24} />
              </div>
              Métricas de GPU
            </h1>
            <p className="text-gray-400 mt-1">Análise completa de preços, provedores e eficiência</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="ta-tabs w-fit mb-6">
        <button
          className={`ta-tab ${activeTab === 'market' ? 'ta-tab-active' : ''}`}
          onClick={() => handleTabChange('market')}
        >
          <TrendingUp size={18} /> Mercado
        </button>
        <button
          className={`ta-tab ${activeTab === 'providers' ? 'ta-tab-active' : ''}`}
          onClick={() => handleTabChange('providers')}
        >
          <Shield size={18} /> Provedores
        </button>
        <button
          className={`ta-tab ${activeTab === 'efficiency' ? 'ta-tab-active' : ''}`}
          onClick={() => handleTabChange('efficiency')}
        >
          <Zap size={18} /> Eficiência
        </button>
        <button
          className={`ta-tab ${activeTab === 'savings' ? 'ta-tab-active' : ''}`}
          onClick={() => handleTabChange('savings')}
        >
          <PiggyBank size={18} /> Economia
        </button>
        <button
          className={`ta-tab ${activeTab === 'spot' ? 'ta-tab-active' : ''}`}
          onClick={() => handleTabChange('spot')}
        >
          <Sparkles size={18} /> Spot Reports
        </button>
      </div>

      {/* Filters */}
      {/* Filters Toolbar */}
      <div className="mb-8 p-1 bg-white/[0.03] border border-white/10 rounded-2xl w-fit backdrop-blur-sm shadow-xl">
        <div className="flex flex-wrap items-center gap-2 p-2">
          {/* GPU Select */}
          <div className="relative group">
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <Cpu size={16} className="text-emerald-400" />
            </div>
            <select
              className="pl-10 pr-8 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500/50 appearance-none min-w-[200px] cursor-pointer hover:bg-white/10 transition-colors"
              value={selectedGPU}
              onChange={(e) => setSelectedGPU(e.target.value)}
            >
              <option value="all">Todas as GPUs</option>
              {availableGPUs.map(gpu => (
                <option key={gpu} value={gpu}>{gpu}</option>
              ))}
            </select>
            <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
              <TrendingDown size={14} className="text-gray-500" />
            </div>
          </div>

          <div className="w-px h-8 bg-white/10 hidden md:block mx-2"></div>

          {/* Type Select */}
          <div className="relative group">
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <Package size={16} className="text-emerald-400" />
            </div>
            <select
              className="pl-10 pr-8 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500/50 appearance-none min-w-[200px] cursor-pointer hover:bg-white/10 transition-colors"
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
            >
              <option value="all">Todos os Tipos</option>
              {machineTypes.map(type => (
                <option key={type} value={type}>{getMachineTypeLabel(type)}</option>
              ))}
            </select>
            <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
              <TrendingDown size={14} className="text-gray-500" />
            </div>
          </div>

          <div className="w-px h-8 bg-white/10 hidden md:block mx-2"></div>

          {/* Time Range */}
          <div className="flex items-center gap-1 p-1 bg-white/5 rounded-xl border border-white/10">
            {[1, 6, 24, 168].map(hours => (
              <button
                key={hours}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${timeRange === hours
                    ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                onClick={() => setTimeRange(hours)}
              >
                {hours === 1 ? '1h' : hours === 6 ? '6h' : hours === 24 ? '24h' : '7d'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Market Tab */}
      {activeTab === 'market' && (
        <>
          {/* Market Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
            {Object.entries(marketSummary).map(([gpuName, types]) => (
              <div key={gpuName} className="ta-card group hover:border-emerald-500/30 transition-all duration-300">
                <div className="ta-card-header flex items-center justify-between pb-4 border-b border-white/5">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 flex items-center justify-center border border-emerald-500/20 group-hover:scale-110 transition-transform duration-300">
                      <Cpu size={20} className="text-emerald-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white tracking-tight">{gpuName}</h3>
                      <p className="text-xs text-gray-500">Analytics Tempo Real</p>
                    </div>
                  </div>
                  <div className="px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-gray-400 font-mono">
                    {Object.values(types).reduce((acc, curr) => acc + (curr.total_offers || 0), 0)} offers
                  </div>
                </div>

                <div className="p-4 grid gap-3">
                  {Object.entries(types).map(([type, data]) => {
                    const isSpot = type === 'interruptible';
                    const isBestPrice = Object.values(types).every(t => t.avg_price >= data.avg_price);

                    return (
                      <div key={type} className={`relative p-3 rounded-xl border transition-all ${isSpot
                          ? 'bg-emerald-500/5 border-emerald-500/20 hover:bg-emerald-500/10'
                          : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05]'
                        }`}>
                        {isBestPrice && (
                          <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-emerald-500 text-white text-[9px] font-bold uppercase tracking-wider rounded-full shadow-lg shadow-emerald-500/20">
                            Melhor Preço
                          </div>
                        )}
                        <div className="flex items-center justify-between mb-2">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${type === 'on-demand' ? 'bg-blue-500/10 text-blue-400' :
                              type === 'interruptible' ? 'bg-emerald-500/10 text-emerald-400' :
                                'bg-yellow-500/10 text-yellow-400'
                            }`}>
                            {getMachineTypeLabel(type)}
                          </span>
                          <span className="text-xs text-gray-500 font-mono">
                            {data.total_offers} un.
                          </span>
                        </div>

                        <div className="flex items-baseline justify-between">
                          <div className="flex flex-col">
                            <div className="text-lg font-bold text-white font-mono flex items-baseline gap-1">
                              {formatPrice(data.avg_price)}
                            </div>
                            <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
                              <span>Min: <span className="text-gray-300">{formatPrice(data.min_price)}</span></span>
                              <span className="w-1 h-1 rounded-full bg-gray-600"></span>
                              <span>Max: <span className="text-gray-300">{formatPrice(data.max_price)}</span></span>
                            </div>
                          </div>

                          {/* Price Bar Visualization */}
                          <div className="w-16 h-8 flex items-end justify-between gap-0.5">
                            <div className="w-full bg-emerald-500/20 rounded-t-sm" style={{ height: '40%' }}></div>
                            <div className="w-full bg-emerald-500/40 rounded-t-sm" style={{ height: '70%' }}></div>
                            <div className="w-full bg-emerald-500/20 rounded-t-sm" style={{ height: '50%' }}></div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {Object.keys(marketSummary).length === 0 && (
            <div className="ta-card">
              <div className="ta-empty-state">
                <BarChart3 className="ta-empty-state-icon" />
                <h3 className="ta-empty-state-title">Coletando dados de mercado...</h3>
                <p className="ta-empty-state-description">O monitor de métricas coleta dados das GPUs periodicamente. Aguarde alguns minutos.</p>
              </div>
            </div>
          )}

          {/* Price Chart */}
          {marketData.length > 0 && (
            <div className="ta-card mb-6">
              <div className="ta-card-header">
                <h2 className="ta-card-title flex items-center gap-2">
                  <TrendingUp size={22} className="text-emerald-400" />
                  Histórico de Preços
                </h2>
              </div>
              <div className="ta-card-body">
                <div style={{ height: '300px' }}>
                  <Line data={getMarketChartData()} options={chartOptions} />
                </div>
              </div>
            </div>
          )}

          {/* Market Data Table */}
          {marketData.length > 0 && (
            <div className="ta-card">
              <div className="ta-card-header">
                <h2 className="ta-card-title">Dados Detalhados</h2>
              </div>
              <div className="ta-card-body overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow hoverable={false}>
                      <TableHead>GPU</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Data/Hora</TableHead>
                      <TableHead align="right">Preço Médio</TableHead>
                      <TableHead align="right">Mínimo</TableHead>
                      <TableHead align="right">Máximo</TableHead>
                      <TableHead align="right">Ofertas</TableHead>
                      <TableHead align="right">$/TFLOPS</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {marketData.slice(0, 50).map((record, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <Badge variant="success">{record.gpu_name}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="primary">{getMachineTypeLabel(record.machine_type)}</Badge>
                        </TableCell>
                        <TableCell>{formatTime(record.timestamp)}</TableCell>
                        <TableCell align="right">{formatPrice(record.avg_price)}</TableCell>
                        <TableCell align="right" className="text-green-400">{formatPrice(record.min_price)}</TableCell>
                        <TableCell align="right" className="text-red-400">{formatPrice(record.max_price)}</TableCell>
                        <TableCell align="right">{record.total_offers}</TableCell>
                        <TableCell align="right">{formatPrice(record.min_cost_per_tflops)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Providers Tab */}
      {activeTab === 'providers' && (
        <div className="ta-card">
          <div className="ta-card-header">
            <h2 className="ta-card-title flex items-center gap-2">
              <Shield size={22} className="text-emerald-400" />
              Ranking de Provedores por Confiabilidade
            </h2>
          </div>

          <div className="ta-card-body overflow-x-auto">
            {providers.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow hoverable={false}>
                    <TableHead>#</TableHead>
                    <TableHead>Host</TableHead>
                    <TableHead>Localização</TableHead>
                    <TableHead align="center">Confiabilidade</TableHead>
                    <TableHead align="center">Disponibilidade</TableHead>
                    <TableHead align="center">Estabilidade Preço</TableHead>
                    <TableHead align="right">Observações</TableHead>
                    <TableHead>Verificado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {providers.map((provider, idx) => (
                    <TableRow key={provider.machine_id}>
                      <TableCell>{idx + 1}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Server size={16} />
                          {provider.hostname || `Host ${provider.machine_id}`}
                        </div>
                      </TableCell>
                      <TableCell>{provider.geolocation || '-'}</TableCell>
                      <TableCell align="center">
                        <div className="flex items-center justify-center gap-2">
                          <Progress value={Math.min((provider.reliability_score || 0) * 100, 100)} className="w-24" />
                          <span className="text-sm font-semibold min-w-[50px]">{formatPercent(provider.reliability_score)}</span>
                        </div>
                      </TableCell>
                      <TableCell align="center">{formatPercent(provider.availability_score)}</TableCell>
                      <TableCell align="center">{formatPercent(provider.price_stability_score)}</TableCell>
                      <TableCell align="right">{provider.total_observations}</TableCell>
                      <TableCell>
                        {provider.verified ? (
                          <Badge variant="success">Verificado</Badge>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="ta-empty-state">
                <Shield className="ta-empty-state-icon" />
                <h3 className="ta-empty-state-title">Coletando dados de provedores...</h3>
                <p className="ta-empty-state-description">Os dados de confiabilidade são calculados com base em múltiplas observações ao longo do tempo.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Efficiency Tab */}
      {activeTab === 'efficiency' && (
        <div className="ta-card">
          <div className="ta-card-header">
            <h2 className="ta-card-title flex items-center gap-2">
              <Zap size={22} className="text-yellow-400" />
              Ranking de Custo-Benefício
            </h2>
          </div>

          <div className="ta-card-body">
            {efficiency.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {efficiency.slice(0, 20).map((item, idx) => {
                  const score = item.efficiency_score || 0
                  const scoreColor = score >= 85 ? '#22c55e' : score >= 70 ? '#eab308' : '#ef4444'
                  const scoreLabel = score >= 85 ? 'Excelente' : score >= 70 ? 'Bom' : 'Regular'

                  return (
                    <div key={item.offer_id} className="p-4 rounded-lg border border-gray-700/40 bg-[#161a16] hover:border-green-500/30 transition-all relative">
                      {/* Rank Badge */}
                      <div className="absolute -top-2 -left-2 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                        style={{
                          backgroundColor: idx === 0 ? '#22c55e' : idx === 1 ? '#3b82f6' : idx === 2 ? '#f59e0b' : '#374151',
                          color: 'white'
                        }}>
                        #{idx + 1}
                      </div>

                      {/* Header: GPU + Type Badge */}
                      <div className="flex items-center justify-between mb-4 pt-1">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center border border-white/10">
                            <Cpu className="w-4 h-4 text-emerald-400" />
                          </div>
                          <div>
                            <span className="text-white font-bold text-sm block">{item.gpu_name}</span>
                            <span className="text-[10px] text-gray-500 block">GPU Cluster</span>
                          </div>
                        </div>
                        <span
                          className="text-[10px] px-2.5 py-1 rounded-full font-medium border border-white/5"
                          style={{
                            backgroundColor: getMachineTypeColor(item.machine_type) + '15',
                            color: getMachineTypeColor(item.machine_type),
                            borderColor: getMachineTypeColor(item.machine_type) + '30'
                          }}
                        >
                          {getMachineTypeLabel(item.machine_type)}
                        </span>
                      </div>

                      {/* Score Circle */}
                      <div className="flex items-center justify-center mb-4">
                        <div className="relative w-20 h-20">
                          <svg className="w-full h-full transform -rotate-90">
                            <circle
                              cx="40" cy="40" r="36"
                              fill="none"
                              stroke="#1f2937"
                              strokeWidth="6"
                            />
                            <circle
                              cx="40" cy="40" r="36"
                              fill="none"
                              stroke={scoreColor}
                              strokeWidth="6"
                              strokeLinecap="round"
                              strokeDasharray={`${score * 2.26} 226`}
                            />
                          </svg>
                          <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-xl font-bold text-white">{score.toFixed(0)}</span>
                            <span className="text-[9px] text-gray-400">{scoreLabel}</span>
                          </div>
                        </div>
                      </div>

                      {/* Stats Grid */}
                      <div className="grid grid-cols-2 gap-2 mb-3 text-[11px]">
                        <div className="text-gray-400 flex items-center gap-1">
                          <DollarSign size={12} className="text-gray-500" />
                          <span className="text-gray-500">Preço:</span>
                          <span className="text-green-400 font-mono font-medium">{formatPrice(item.dph_total)}</span>
                        </div>
                        <div className="text-gray-400 flex items-center gap-1">
                          <Cpu size={12} className="text-gray-500" />
                          <span className="text-gray-500">TFLOPS:</span>
                          <span className="text-white">{item.total_flops?.toFixed(1) || '-'}</span>
                        </div>
                        <div className="text-gray-400 flex items-center gap-1">
                          <Zap size={12} className="text-gray-500" />
                          <span className="text-gray-500">$/TFLOPS:</span>
                          <span className="text-white">{formatPrice(item.cost_per_tflops)}</span>
                        </div>
                        <div className="text-gray-400 flex items-center gap-1">
                          <Package size={12} className="text-gray-500" />
                          <span className="text-gray-500">VRAM:</span>
                          <span className="text-white">{item.gpu_ram?.toFixed(0) || '-'} GB</span>
                        </div>
                      </div>

                      {/* Footer with reliability indicator */}
                      <div className="flex items-center justify-between pt-2 border-t border-gray-700/30">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${score >= 80 ? 'bg-green-400' : score >= 65 ? 'bg-yellow-400' : 'bg-red-400'}`} />
                          <span className="text-[10px] text-gray-400">Eficiência {score >= 80 ? 'Alta' : score >= 65 ? 'Média' : 'Baixa'}</span>
                        </div>
                        {item.verified && (
                          <span className="text-[9px] text-green-400 px-1.5 py-0.5 bg-green-500/10 rounded">Verificado</span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="ta-empty-state">
                <Zap className="ta-empty-state-icon" />
                <h3 className="ta-empty-state-title">Calculando rankings de eficiência...</h3>
                <p className="ta-empty-state-description">Os rankings são calculados com base em preço, performance e confiabilidade.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Economia Tab - Dashboard de Economia Real */}
      {activeTab === 'savings' && (
        <div>
          <RealSavingsDashboard getAuthHeaders={getAuthHeaders} />
        </div>
      )}

      {/* Spot Reports Tab */}
      {activeTab === 'spot' && (
        <div>
          {/* If specific report requested, show only that one, otherwise show all */}
          {activeReport ? (
            <div className="max-w-[900px] mx-auto">
              {activeReport === 'monitor' && <SpotMonitor getAuthHeaders={getAuthHeaders} />}
              {activeReport === 'availability' && <InstantAvailability getAuthHeaders={getAuthHeaders} />}
              {activeReport === 'savings' && <SavingsCalculator getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU} />}
              {activeReport === 'training' && <TrainingCost getAuthHeaders={getAuthHeaders} />}
              {activeReport === 'prediction' && <SpotPrediction getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU !== 'all' ? selectedGPU : 'RTX 4090'} />}
              {activeReport === 'safe-windows' && <SafeWindows getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU !== 'all' ? selectedGPU : 'RTX 4090'} />}
              {activeReport === 'reliability' && <ReliabilityScore getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU} />}
              {activeReport === 'interruption' && <InterruptionRate getAuthHeaders={getAuthHeaders} />}
              {activeReport === 'llm' && <LLMGpuRanking getAuthHeaders={getAuthHeaders} />}
              {activeReport === 'fleet' && <FleetStrategy getAuthHeaders={getAuthHeaders} />}
            </div>
          ) : (
            <>
              {/* Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
                <div className="stat-card">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Relatórios Disponíveis</p>
                      <p className="text-2xl font-bold text-white">10</p>
                      <p className="text-xs text-gray-500 mt-1">Análises de Spot</p>
                    </div>
                    <div className="stat-card-icon stat-card-icon-success">
                      <Sparkles size={20} />
                    </div>
                  </div>
                </div>
                <div className="stat-card">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Preços</p>
                      <p className="text-2xl font-bold text-emerald-400">Monitor</p>
                      <p className="text-xs text-gray-500 mt-1">Acompanhe em tempo real</p>
                    </div>
                    <div className="stat-card-icon stat-card-icon-success">
                      <TrendingUp size={20} />
                    </div>
                  </div>
                </div>
                <div className="stat-card">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Economia</p>
                      <p className="text-2xl font-bold text-yellow-400">Calculadora</p>
                      <p className="text-xs text-gray-500 mt-1">Simule suas economias</p>
                    </div>
                    <div className="stat-card-icon stat-card-icon-warning">
                      <DollarSign size={20} />
                    </div>
                  </div>
                </div>
                <div className="stat-card">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Confiabilidade</p>
                      <p className="text-2xl font-bold text-emerald-400">Score</p>
                      <p className="text-xs text-gray-500 mt-1">Provedores verificados</p>
                    </div>
                    <div className="stat-card-icon stat-card-icon-success">
                      <Shield size={20} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Reports Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SpotMonitor getAuthHeaders={getAuthHeaders} />
                <InstantAvailability getAuthHeaders={getAuthHeaders} />
                <SavingsCalculator getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU} />
                <TrainingCost getAuthHeaders={getAuthHeaders} />
                <SpotPrediction getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU !== 'all' ? selectedGPU : 'RTX 4090'} />
                <SafeWindows getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU !== 'all' ? selectedGPU : 'RTX 4090'} />
                <ReliabilityScore getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU} />
                <InterruptionRate getAuthHeaders={getAuthHeaders} />
                <LLMGpuRanking getAuthHeaders={getAuthHeaders} />
                <FleetStrategy getAuthHeaders={getAuthHeaders} />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
