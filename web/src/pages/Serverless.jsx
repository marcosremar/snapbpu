import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Zap,
  Plus,
  Activity,
  Clock,
  DollarSign,
  TrendingUp,
  AlertCircle,
  Server,
  Play,
  Pause,
  Trash2,
  Settings as SettingsIcon,
  BarChart3,
  Gauge
} from 'lucide-react'
import { Badge, Button, Alert } from '../components/tailadmin-ui'
import ServerlessCard from '../components/serverless/ServerlessCard'
import CreateServerlessModal from '../components/serverless/CreateServerlessModal'

const API_BASE = ''

export default function Serverless() {
  const navigate = useNavigate()
  const location = useLocation()
  const isDemo = location.pathname.startsWith('/demo-app')

  const [endpoints, setEndpoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    loadEndpoints()
    loadStats()

    // Poll a cada 5 segundos
    const interval = setInterval(() => {
      loadEndpoints()
      loadStats()
    }, 5000)

    return () => clearInterval(interval)
  }, [isDemo])

  const loadEndpoints = async () => {
    try {
      if (isDemo) {
        // Dados demo
        setEndpoints([
          {
            id: 'endpoint-1',
            name: 'llama2-inference',
            status: 'running',
            machine_type: 'spot',
            gpu_name: 'RTX 4090',
            region: 'US',
            created_at: '2024-12-20T10:00:00Z',
            metrics: {
              requests_per_sec: 45.2,
              avg_latency_ms: 120,
              p99_latency_ms: 350,
              cold_starts_24h: 3,
              total_requests_24h: 125000,
              uptime_percent: 99.8,
            },
            pricing: {
              price_per_hour: 0.31,
              price_per_request: 0.00001,
              cost_24h: 7.44,
            },
            auto_scaling: {
              enabled: true,
              min_instances: 0,
              max_instances: 5,
              current_instances: 2,
            },
          },
          {
            id: 'endpoint-2',
            name: 'stable-diffusion-xl',
            status: 'running',
            machine_type: 'on-demand',
            gpu_name: 'RTX 3090',
            region: 'EU',
            created_at: '2024-12-19T15:30:00Z',
            metrics: {
              requests_per_sec: 12.8,
              avg_latency_ms: 2500,
              p99_latency_ms: 4200,
              cold_starts_24h: 0,
              total_requests_24h: 32000,
              uptime_percent: 100,
            },
            pricing: {
              price_per_hour: 0.20,
              price_per_request: 0.00005,
              cost_24h: 4.80,
            },
            auto_scaling: {
              enabled: true,
              min_instances: 1,
              max_instances: 3,
              current_instances: 1,
            },
          },
          {
            id: 'endpoint-3',
            name: 'whisper-transcription',
            status: 'scaled_to_zero',
            machine_type: 'spot',
            gpu_name: 'RTX 3080',
            region: 'ASIA',
            created_at: '2024-12-18T08:00:00Z',
            metrics: {
              requests_per_sec: 0,
              avg_latency_ms: 0,
              p99_latency_ms: 0,
              cold_starts_24h: 15,
              total_requests_24h: 3500,
              uptime_percent: 92.5,
            },
            pricing: {
              price_per_hour: 0.15,
              price_per_request: 0.00002,
              cost_24h: 0.70,
            },
            auto_scaling: {
              enabled: true,
              min_instances: 0,
              max_instances: 10,
              current_instances: 0,
            },
          },
        ])
        setLoading(false)
        return
      }

      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/serverless/endpoints`, {
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      const data = await res.json()
      setEndpoints(data.endpoints || [])
    } catch (e) {
      console.error('Failed to load serverless endpoints:', e)
    }
    setLoading(false)
  }

  const loadStats = async () => {
    try {
      if (isDemo) {
        setStats({
          total_endpoints: 3,
          total_requests_24h: 160500,
          avg_latency_ms: 856,
          total_cost_24h: 12.94,
          active_instances: 3,
          cold_starts_24h: 18,
        })
        return
      }

      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/serverless/stats`, {
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      const data = await res.json()
      setStats(data)
    } catch (e) {
      console.error('Failed to load serverless stats:', e)
    }
  }

  const handleCreateEndpoint = async (config) => {
    try {
      if (isDemo) {
        alert('Demo mode: Endpoint would be created with config: ' + JSON.stringify(config))
        setShowCreateModal(false)
        return
      }

      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/serverless/endpoints`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(config)
      })

      if (res.ok) {
        setShowCreateModal(false)
        loadEndpoints()
      }
    } catch (e) {
      console.error('Failed to create endpoint:', e)
    }
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="flex items-center justify-center py-20">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <div className="stat-card-icon stat-card-icon-primary">
                <Zap className="w-5 h-5" />
              </div>
              Serverless Endpoints
            </h1>
            <p className="page-subtitle">Auto-scaling GPU endpoints com Spot pricing</p>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
            icon={Plus}
          >
            Criar Endpoint
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Total Requests (24h)</span>
              <Activity className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {stats.total_requests_24h.toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {endpoints.filter(e => e.status === 'running').length} endpoints ativos
            </div>
          </div>

          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Latência Média</span>
              <Clock className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {stats.avg_latency_ms}ms
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {stats.cold_starts_24h} cold starts
            </div>
          </div>

          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Custo (24h)</span>
              <DollarSign className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              ${stats.total_cost_24h.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              ~${(stats.total_cost_24h * 30).toFixed(2)}/mês
            </div>
          </div>

          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Instâncias Ativas</span>
              <Server className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {stats.active_instances}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {stats.total_endpoints} endpoints configurados
            </div>
          </div>
        </div>
      )}

      {/* Endpoints List */}
      {endpoints.length === 0 ? (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-brand-500/10 mb-4">
            <Zap className="w-8 h-8 text-brand-400" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Nenhum endpoint serverless</h3>
          <p className="text-sm text-gray-500 mb-6">
            Crie seu primeiro endpoint auto-scaling com spot pricing
          </p>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
            icon={Plus}
          >
            Criar Primeiro Endpoint
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {endpoints.map((endpoint) => (
            <ServerlessCard
              key={endpoint.id}
              endpoint={endpoint}
              onReload={loadEndpoints}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateServerlessModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateEndpoint}
        />
      )}
    </div>
  )
}
