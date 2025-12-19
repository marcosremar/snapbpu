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
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge } from '../components/ui/dumont-ui'

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
        // API returns array directly for /market
        setMarketData(Array.isArray(data) ? data : (data.data || []))
      }

      if (summaryRes.ok) {
        const data = await summaryRes.json()
        // /market/summary returns { data: {...} }
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
        // API returns array directly, not { data: [...] }
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
        // API returns array directly, not { data: [...] }
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

  const formatPrice = (price) => price ? `$${price.toFixed(4)}/h` : '-'
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
          label: (context) => `${context.dataset.label}: $${context.parsed.y?.toFixed(4)}/h`,
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
      <div className="metrics-container">
        <div className="loading-state">
          <div className="spinner-large"></div>
          <p>Carregando métricas...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="metrics-container">
      {/* Header */}
      <div className="metrics-header">
        <div>
          <h1 className="metrics-title">
            <BarChart3 size={28} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '12px' }} />
            Métricas de GPU
          </h1>
          <p className="metrics-subtitle">Análise completa de preços, provedores e eficiência - Vast.ai</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="metrics-tabs">
        <button
          className={`metrics-tab ${activeTab === 'market' ? 'active' : ''}`}
          onClick={() => handleTabChange('market')}
        >
          <TrendingUp size={18} /> Mercado
        </button>
        <button
          className={`metrics-tab ${activeTab === 'providers' ? 'active' : ''}`}
          onClick={() => handleTabChange('providers')}
        >
          <Shield size={18} /> Provedores
        </button>
        <button
          className={`metrics-tab ${activeTab === 'efficiency' ? 'active' : ''}`}
          onClick={() => handleTabChange('efficiency')}
        >
          <Zap size={18} /> Eficiência
        </button>
        <button
          className={`metrics-tab ${activeTab === 'savings' ? 'active' : ''}`}
          onClick={() => handleTabChange('savings')}
        >
          <PiggyBank size={18} /> Economia
        </button>
        <button
          className={`metrics-tab ${activeTab === 'spot' ? 'active' : ''}`}
          onClick={() => handleTabChange('spot')}
        >
          <Sparkles size={18} /> Spot Reports
        </button>
      </div>

      {/* Filters */}
      <div className="filters-panel">
        <div className="filter-section">
          <label className="filter-label">GPU</label>
          <select
            className="filter-select"
            value={selectedGPU}
            onChange={(e) => setSelectedGPU(e.target.value)}
          >
            <option value="all">Todas as GPUs</option>
            {availableGPUs.map(gpu => (
              <option key={gpu} value={gpu}>{gpu}</option>
            ))}
          </select>
        </div>

        <div className="filter-section">
          <label className="filter-label">Tipo de Máquina</label>
          <select
            className="filter-select"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="all">Todos os Tipos</option>
            {machineTypes.map(type => (
              <option key={type} value={type}>{getMachineTypeLabel(type)}</option>
            ))}
          </select>
        </div>

        <div className="filter-section">
          <label className="filter-label">Período</label>
          <div className="filter-chips">
            {[1, 6, 24, 168].map(hours => (
              <button
                key={hours}
                className={`filter-chip ${timeRange === hours ? 'active' : ''}`}
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
          <div className="market-summary-grid">
            {Object.entries(marketSummary).map(([gpuName, types]) => (
              <div key={gpuName} className="summary-card">
                <h3 className="summary-card-title">{gpuName}</h3>
                <div className="summary-types">
                  {Object.entries(types).map(([type, data]) => (
                    <div key={type} className="summary-type-row">
                      <span
                        className="type-badge"
                        style={{ backgroundColor: getMachineTypeColor(type) }}
                      >
                        {getMachineTypeLabel(type)}
                      </span>
                      <div className="type-prices">
                        <span className="price-min">{formatPrice(data.min_price)}</span>
                        <span className="price-avg">{formatPrice(data.avg_price)}</span>
                        <span className="price-max">{formatPrice(data.max_price)}</span>
                      </div>
                      <span className="type-offers">{data.total_offers || 0} ofertas</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {Object.keys(marketSummary).length === 0 && (
            <div className="empty-state">
              <BarChart3 size={64} style={{ opacity: 0.5 }} />
              <h3>Coletando dados de mercado...</h3>
              <p>O monitor de métricas coleta dados das GPUs periodicamente. Aguarde alguns minutos.</p>
            </div>
          )}

          {/* Price Chart */}
          {marketData.length > 0 && (
            <div className="chart-section">
              <h2 className="section-title">
                <TrendingUp size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
                Histórico de Preços
              </h2>
              <div className="chart-container" style={{ height: '300px' }}>
                <Line data={getMarketChartData()} options={chartOptions} />
              </div>
            </div>
          )}

          {/* Market Data Table */}
          {marketData.length > 0 && (
            <div className="history-section">
              <h2 className="section-title">Dados Detalhados</h2>
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
                        <Badge color="success">{record.gpu_name}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge color="info">{getMachineTypeLabel(record.machine_type)}</Badge>
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
          )}
        </>
      )}

      {/* Providers Tab */}
      {activeTab === 'providers' && (
        <div className="providers-section">
          <h2 className="section-title">
            <Shield size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
            Ranking de Provedores por Confiabilidade
          </h2>

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
                        <div className="w-24 h-2 rounded bg-gray-700">
                          <div
                            className="h-full rounded"
                            style={{
                              width: `${(provider.reliability_score || 0) * 100}%`,
                              backgroundColor: provider.reliability_score > 0.8 ? '#22c55e' : provider.reliability_score > 0.5 ? '#f59e0b' : '#ef4444'
                            }}
                          />
                        </div>
                        <span className="text-sm">{formatPercent(provider.reliability_score)}</span>
                      </div>
                    </TableCell>
                    <TableCell align="center">{formatPercent(provider.availability_score)}</TableCell>
                    <TableCell align="center">{formatPercent(provider.price_stability_score)}</TableCell>
                    <TableCell align="right">{provider.total_observations}</TableCell>
                    <TableCell>
                      {provider.verified ? (
                        <Badge color="success">Verificado</Badge>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="empty-state">
              <Shield size={64} style={{ opacity: 0.5 }} />
              <h3>Coletando dados de provedores...</h3>
              <p>Os dados de confiabilidade são calculados com base em múltiplas observações ao longo do tempo.</p>
            </div>
          )}
        </div>
      )}

      {/* Efficiency Tab */}
      {activeTab === 'efficiency' && (
        <div className="efficiency-section">
          <h2 className="section-title">
            <Zap size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
            Ranking de Custo-Benefício
          </h2>

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
                    <div className="flex items-center justify-between mb-3 pt-1">
                      <div className="flex items-center gap-2">
                        <Cpu className="w-5 h-5 text-green-400" />
                        <span className="text-white font-semibold text-sm">{item.gpu_name}</span>
                      </div>
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                        style={{
                          backgroundColor: getMachineTypeColor(item.machine_type) + '20',
                          color: getMachineTypeColor(item.machine_type)
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
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-full bg-[#1a2418] flex items-center justify-center mb-4">
                <Zap size={32} className="text-green-400/50" />
              </div>
              <h3 className="text-white text-lg font-medium mb-2">Calculando rankings de eficiência...</h3>
              <p className="text-gray-400 text-sm max-w-md">Os rankings são calculados com base em preço, performance e confiabilidade.</p>
            </div>
          )}
        </div>
      )}

      {/* Economia Tab - Dashboard de Economia Real */}
      {activeTab === 'savings' && (
        <div className="savings-section">
          <RealSavingsDashboard getAuthHeaders={getAuthHeaders} />
        </div>
      )}

      {/* Spot Reports Tab */}
      {activeTab === 'spot' && (
        <div className="spot-section">
          <h2 className="section-title">
            <Sparkles size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
            {activeReport ? getReportTitle(activeReport) : 'Relatórios Spot - Maximize suas Economias'}
          </h2>

          {/* If specific report requested, show only that one, otherwise show all */}
          <div className={activeReport ? "spot-report-single" : "spot-reports-grid"}>
            {(!activeReport || activeReport === 'monitor') && (
              <SpotMonitor getAuthHeaders={getAuthHeaders} />
            )}
            {(!activeReport || activeReport === 'availability') && (
              <InstantAvailability getAuthHeaders={getAuthHeaders} />
            )}
            {(!activeReport || activeReport === 'savings') && (
              <SavingsCalculator getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU} />
            )}
            {(!activeReport || activeReport === 'training') && (
              <TrainingCost getAuthHeaders={getAuthHeaders} />
            )}
            {(!activeReport || activeReport === 'prediction') && (
              <SpotPrediction getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU !== 'all' ? selectedGPU : 'RTX 4090'} />
            )}
            {(!activeReport || activeReport === 'safe-windows') && (
              <SafeWindows getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU !== 'all' ? selectedGPU : 'RTX 4090'} />
            )}
            {(!activeReport || activeReport === 'reliability') && (
              <ReliabilityScore getAuthHeaders={getAuthHeaders} selectedGPU={selectedGPU} />
            )}
            {(!activeReport || activeReport === 'interruption') && (
              <InterruptionRate getAuthHeaders={getAuthHeaders} />
            )}
            {(!activeReport || activeReport === 'llm') && (
              <LLMGpuRanking getAuthHeaders={getAuthHeaders} />
            )}
            {(!activeReport || activeReport === 'fleet') && (
              <FleetStrategy getAuthHeaders={getAuthHeaders} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
