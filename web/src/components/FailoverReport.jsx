import React, { useState, useEffect } from 'react'
import {
  Zap, Clock, CheckCircle, XCircle, TrendingUp, TrendingDown,
  Activity, Server, Cpu, RefreshCw, Calendar, BarChart3,
  AlertTriangle, Shield, ArrowRight, Timer
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from './ui/card'

/**
 * FailoverReport - Relatório completo de failovers
 *
 * Mostra:
 * - Total de failovers
 * - Taxa de sucesso
 * - Tempo médio de recuperação (MTTR)
 * - Latência de detecção
 * - Histórico detalhado de cada failover
 * - Gráfico de tendência
 */

// Dados demo de histórico de failover
const DEMO_FAILOVER_HISTORY = [
  {
    id: 'fo-001',
    timestamp: new Date(Date.now() - 86400000 * 2).toISOString(), // 2 dias atrás
    machine_id: 12345678,
    gpu_name: 'RTX 4090',
    new_gpu_name: 'RTX 4080',
    reason: 'spot_preemption',
    phases: {
      detection_time_ms: 850,
      failover_time_ms: 1200,
      search_time_ms: 3500,
      provisioning_time_ms: 45000,
      restore_time_ms: 28000,
      total_time_ms: 78550
    },
    data_restored_mb: 1250,
    files_synced: 1847,
    status: 'success',
    cpu_standby_ip: '35.192.45.123',
    new_gpu_ip: '203.0.113.78'
  },
  {
    id: 'fo-002',
    timestamp: new Date(Date.now() - 86400000 * 5).toISOString(), // 5 dias atrás
    machine_id: 23456789,
    gpu_name: 'A100 80GB',
    new_gpu_name: 'A100 80GB',
    reason: 'network_timeout',
    phases: {
      detection_time_ms: 1200,
      failover_time_ms: 980,
      search_time_ms: 2800,
      provisioning_time_ms: 52000,
      restore_time_ms: 35000,
      total_time_ms: 91980
    },
    data_restored_mb: 2340,
    files_synced: 3421,
    status: 'success',
    cpu_standby_ip: '35.204.123.45',
    new_gpu_ip: '198.51.100.92'
  },
  {
    id: 'fo-003',
    timestamp: new Date(Date.now() - 86400000 * 8).toISOString(), // 8 dias atrás
    machine_id: 12345678,
    gpu_name: 'RTX 4090',
    new_gpu_name: 'RTX 3090',
    reason: 'cuda_error',
    phases: {
      detection_time_ms: 650,
      failover_time_ms: 1100,
      search_time_ms: 4200,
      provisioning_time_ms: 38000,
      restore_time_ms: 22000,
      total_time_ms: 65950
    },
    data_restored_mb: 890,
    files_synced: 1234,
    status: 'success',
    cpu_standby_ip: '35.192.45.123',
    new_gpu_ip: '192.0.2.55'
  },
  {
    id: 'fo-004',
    timestamp: new Date(Date.now() - 86400000 * 12).toISOString(), // 12 dias atrás
    machine_id: 56789012,
    gpu_name: 'H100 80GB',
    new_gpu_name: null,
    reason: 'spot_preemption',
    phases: {
      detection_time_ms: 920,
      failover_time_ms: 1050,
      search_time_ms: 180000, // Demorou muito procurando
      provisioning_time_ms: 0,
      restore_time_ms: 0,
      total_time_ms: 182000
    },
    data_restored_mb: 0,
    files_synced: 0,
    status: 'failed',
    failure_reason: 'no_gpu_available',
    cpu_standby_ip: '35.231.89.123',
    new_gpu_ip: null
  },
  {
    id: 'fo-005',
    timestamp: new Date(Date.now() - 86400000 * 15).toISOString(), // 15 dias atrás
    machine_id: 23456789,
    gpu_name: 'A100 80GB',
    new_gpu_name: 'A100 40GB',
    reason: 'host_maintenance',
    phases: {
      detection_time_ms: 500,
      failover_time_ms: 850,
      search_time_ms: 2100,
      provisioning_time_ms: 48000,
      restore_time_ms: 41000,
      total_time_ms: 92450
    },
    data_restored_mb: 3100,
    files_synced: 4521,
    status: 'success',
    cpu_standby_ip: '35.204.123.45',
    new_gpu_ip: '198.51.100.123'
  }
]

// Helper para formatar duração
const formatDuration = (ms) => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`
}

// Helper para formatar data
const formatDate = (isoString) => {
  const date = new Date(isoString)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Helper para razão do failover
const getReasonLabel = (reason) => {
  const reasons = {
    'spot_preemption': 'Spot Instance Preempted',
    'network_timeout': 'Network Timeout',
    'cuda_error': 'CUDA Error',
    'host_maintenance': 'Host Maintenance',
    'out_of_memory': 'Out of Memory',
    'unknown': 'Unknown'
  }
  return reasons[reason] || reason
}

// Componente de métrica individual
const MetricCard = ({ icon: Icon, label, value, subValue, color = 'green', trend = null }) => (
  <div className="p-4 rounded-lg bg-gray-800/50 border border-gray-700/50">
    <div className="flex items-center gap-2 mb-2">
      <Icon className={`w-4 h-4 text-${color}-400`} />
      <span className="text-xs text-gray-400 uppercase">{label}</span>
    </div>
    <div className="flex items-end gap-2">
      <span className={`text-2xl font-bold text-${color}-400`}>{value}</span>
      {trend !== null && (
        <span className={`text-xs flex items-center gap-0.5 ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {Math.abs(trend)}%
        </span>
      )}
    </div>
    {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}
  </div>
)

// Componente de timeline de um failover
const FailoverTimeline = ({ failover }) => {
  const phases = [
    { key: 'detection', label: 'Detecção', time: failover.phases.detection_time_ms, icon: AlertTriangle, color: 'red' },
    { key: 'failover', label: 'Failover', time: failover.phases.failover_time_ms, icon: Shield, color: 'yellow' },
    { key: 'search', label: 'Busca GPU', time: failover.phases.search_time_ms, icon: Activity, color: 'blue' },
    { key: 'provisioning', label: 'Provisioning', time: failover.phases.provisioning_time_ms, icon: Server, color: 'purple' },
    { key: 'restore', label: 'Restauração', time: failover.phases.restore_time_ms, icon: RefreshCw, color: 'cyan' }
  ]

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {phases.map((phase, idx) => (
        <React.Fragment key={phase.key}>
          <div
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
              phase.time > 0 ? `bg-${phase.color}-500/20 text-${phase.color}-400` : 'bg-gray-700/30 text-gray-500'
            }`}
            title={`${phase.label}: ${formatDuration(phase.time)}`}
          >
            <phase.icon className="w-3 h-3" />
            <span>{formatDuration(phase.time)}</span>
          </div>
          {idx < phases.length - 1 && <ArrowRight className="w-3 h-3 text-gray-600" />}
        </React.Fragment>
      ))}
    </div>
  )
}

// Componente principal
export default function FailoverReport({ isDemo = true }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('30d') // 7d, 30d, 90d

  useEffect(() => {
    // Load data based on mode
    const loadHistory = () => {
      // Try to get real data from localStorage first (from simulations)
      let localHistory = []
      try {
        const stored = localStorage.getItem('failover_history')
        if (stored) {
          localHistory = JSON.parse(stored).map(item => ({
            ...item,
            // Normalize the data structure
            id: item.id,
            timestamp: item.started_at || item.timestamp,
            machine_id: item.machine_id,
            gpu_name: item.gpu_name,
            new_gpu_name: item.new_gpu_name,
            reason: item.reason || 'spot_preemption',
            phases: {
              detection_time_ms: item.detection_time_ms || 0,
              failover_time_ms: item.failover_time_ms || 0,
              search_time_ms: item.search_time_ms || 0,
              provisioning_time_ms: item.provisioning_time_ms || 0,
              restore_time_ms: item.restore_time_ms || 0,
              total_time_ms: item.total_time_ms || 0
            },
            data_restored_mb: item.data_restored_mb || 0,
            files_synced: item.files_synced || 0,
            status: item.status || 'success',
            cpu_standby_ip: item.cpu_standby_ip,
            new_gpu_ip: item.new_gpu_ip
          }))
        }
      } catch (e) {
        console.error('Error loading local failover history:', e)
      }

      // If we have local data, combine with demo data
      if (localHistory.length > 0) {
        // Sort by timestamp, newest first
        const combined = [...localHistory, ...DEMO_FAILOVER_HISTORY].sort(
          (a, b) => new Date(b.timestamp || b.started_at) - new Date(a.timestamp || a.started_at)
        )
        setHistory(combined)
        setLoading(false)
        return
      }

      // Otherwise use demo data in demo mode
      if (isDemo) {
        setHistory(DEMO_FAILOVER_HISTORY)
        setLoading(false)
        return
      }

      // In production, fetch from API
      const fetchHistory = async () => {
        try {
          const res = await fetch('/api/v1/standby/failover-history')
          if (res.ok) {
            const data = await res.json()
            setHistory(data.history || [])
          }
        } catch (err) {
          console.error('Error fetching failover history:', err)
        } finally {
          setLoading(false)
        }
      }
      fetchHistory()
    }

    loadHistory()

    // Also listen for storage changes (in case failover happens in another tab)
    const handleStorageChange = (e) => {
      if (e.key === 'failover_history') {
        loadHistory()
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [isDemo, timeRange])

  // Calcular métricas
  const totalFailovers = history.length
  const successfulFailovers = history.filter(f => f.status === 'success').length
  const failedFailovers = history.filter(f => f.status === 'failed').length
  const successRate = totalFailovers > 0 ? ((successfulFailovers / totalFailovers) * 100).toFixed(1) : 0

  // MTTR (Mean Time To Recovery) - apenas dos bem-sucedidos
  const successfulRecoveryTimes = history
    .filter(f => f.status === 'success')
    .map(f => f.phases.total_time_ms)
  const avgRecoveryTime = successfulRecoveryTimes.length > 0
    ? successfulRecoveryTimes.reduce((a, b) => a + b, 0) / successfulRecoveryTimes.length
    : 0

  // Latência média de detecção
  const detectionTimes = history.map(f => f.phases.detection_time_ms)
  const avgDetectionTime = detectionTimes.length > 0
    ? detectionTimes.reduce((a, b) => a + b, 0) / detectionTimes.length
    : 0

  // Total de dados restaurados
  const totalDataRestored = history.reduce((sum, f) => sum + (f.data_restored_mb || 0), 0)

  // Razões mais comuns
  const reasonCounts = history.reduce((acc, f) => {
    acc[f.reason] = (acc[f.reason] || 0) + 1
    return acc
  }, {})

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-700/50 rounded w-1/3"></div>
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-700/50 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6" data-testid="failover-report">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-red-500/20">
            <Zap className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Relatório de Failover</h2>
            <p className="text-sm text-gray-400">Histórico e métricas de recuperação automática</p>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex gap-1 bg-gray-800/50 rounded-lg p-1">
          {['7d', '30d', '90d'].map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                timeRange === range
                  ? 'bg-green-500/20 text-green-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {range === '7d' ? '7 dias' : range === '30d' ? '30 dias' : '90 dias'}
            </button>
          ))}
        </div>
      </div>

      {/* Métricas Principais */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="failover-metrics">
        <MetricCard
          icon={Zap}
          label="Total de Failovers"
          value={totalFailovers}
          subValue={`${successfulFailovers} sucesso, ${failedFailovers} falha`}
          color="yellow"
        />
        <MetricCard
          icon={CheckCircle}
          label="Taxa de Sucesso"
          value={`${successRate}%`}
          subValue={successRate >= 95 ? 'Excelente' : successRate >= 80 ? 'Bom' : 'Precisa atenção'}
          color={successRate >= 95 ? 'green' : successRate >= 80 ? 'yellow' : 'red'}
        />
        <MetricCard
          icon={Timer}
          label="MTTR (Tempo Médio)"
          value={formatDuration(avgRecoveryTime)}
          subValue="Tempo médio de recuperação"
          color="blue"
        />
        <MetricCard
          icon={Activity}
          label="Latência Detecção"
          value={formatDuration(avgDetectionTime)}
          subValue="Tempo para detectar falha"
          color="purple"
        />
      </div>

      {/* Métricas Secundárias */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={RefreshCw}
          label="Dados Restaurados"
          value={`${(totalDataRestored / 1024).toFixed(1)} GB`}
          subValue={`${history.reduce((s, f) => s + f.files_synced, 0).toLocaleString()} arquivos`}
          color="cyan"
        />
        <MetricCard
          icon={Server}
          label="GPUs Provisionadas"
          value={successfulFailovers}
          subValue="Novas instâncias criadas"
          color="green"
        />
        <MetricCard
          icon={Cpu}
          label="CPU Standby Ativo"
          value={`${history.filter(f => f.phases.failover_time_ms > 0).length}`}
          subValue="Vezes utilizado como backup"
          color="blue"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Causa Principal"
          value={Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?
            getReasonLabel(Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0][0]).split(' ')[0] : 'N/A'}
          subValue={Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0]?.[1] + ' ocorrências' || ''}
          color="orange"
        />
      </div>

      {/* Gráfico de Latências por Fase */}
      <Card className="border-gray-700/50 bg-gray-800/30">
        <CardHeader>
          <CardTitle className="text-white text-sm flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            Latência por Fase (Média)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3" data-testid="latency-breakdown">
            {[
              { label: 'Detecção', key: 'detection_time_ms', color: 'red' },
              { label: 'Failover para CPU', key: 'failover_time_ms', color: 'yellow' },
              { label: 'Busca de GPU', key: 'search_time_ms', color: 'blue' },
              { label: 'Provisionamento', key: 'provisioning_time_ms', color: 'purple' },
              { label: 'Restauração', key: 'restore_time_ms', color: 'cyan' }
            ].map(phase => {
              const avgTime = history.length > 0
                ? history.reduce((s, f) => s + f.phases[phase.key], 0) / history.length
                : 0
              const maxTime = Math.max(...history.map(f => f.phases.total_time_ms), 1)
              const percentage = (avgTime / maxTime) * 100

              return (
                <div key={phase.key} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">{phase.label}</span>
                    <span className={`text-${phase.color}-400 font-medium`}>{formatDuration(avgTime)}</span>
                  </div>
                  <div className="h-2 bg-gray-700/50 rounded-full overflow-hidden">
                    <div
                      className={`h-full bg-${phase.color}-500/50 rounded-full transition-all`}
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Histórico Detalhado */}
      <Card className="border-gray-700/50 bg-gray-800/30">
        <CardHeader>
          <CardTitle className="text-white text-sm flex items-center gap-2">
            <Calendar className="w-4 h-4 text-green-400" />
            Histórico de Failovers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4" data-testid="failover-history">
            {history.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Nenhum failover registrado</p>
            ) : (
              history.map(failover => (
                <div
                  key={failover.id}
                  className={`p-4 rounded-lg border ${
                    failover.status === 'success'
                      ? 'border-green-500/30 bg-green-500/5'
                      : 'border-red-500/30 bg-red-500/5'
                  }`}
                  data-testid={`failover-item-${failover.id}`}
                >
                  {/* Header do Failover */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {failover.status === 'success' ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-400" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-white font-medium">{failover.gpu_name}</span>
                          {failover.new_gpu_name && (
                            <>
                              <ArrowRight className="w-3 h-3 text-gray-500" />
                              <span className="text-green-400 font-medium">{failover.new_gpu_name}</span>
                            </>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatDate(failover.timestamp)} • {getReasonLabel(failover.reason)}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-lg font-bold ${
                        failover.status === 'success' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {formatDuration(failover.phases.total_time_ms)}
                      </div>
                      <div className="text-xs text-gray-500">tempo total</div>
                    </div>
                  </div>

                  {/* Timeline das Fases */}
                  <FailoverTimeline failover={failover} />

                  {/* Detalhes */}
                  {failover.status === 'success' && (
                    <div className="mt-3 pt-3 border-t border-gray-700/50 flex gap-4 text-xs text-gray-400">
                      <span>
                        <RefreshCw className="w-3 h-3 inline mr-1" />
                        {failover.data_restored_mb} MB restaurados
                      </span>
                      <span>
                        <Activity className="w-3 h-3 inline mr-1" />
                        {failover.files_synced.toLocaleString()} arquivos
                      </span>
                      <span>
                        <Server className="w-3 h-3 inline mr-1" />
                        CPU: {failover.cpu_standby_ip}
                      </span>
                    </div>
                  )}

                  {/* Razão da Falha */}
                  {failover.status === 'failed' && failover.failure_reason && (
                    <div className="mt-3 pt-3 border-t border-gray-700/50">
                      <span className="text-xs text-red-400">
                        <AlertTriangle className="w-3 h-3 inline mr-1" />
                        Falha: {failover.failure_reason === 'no_gpu_available'
                          ? 'Nenhuma GPU disponível encontrada'
                          : failover.failure_reason}
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
