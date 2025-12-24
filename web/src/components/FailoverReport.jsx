import React, { useState, useEffect } from 'react'
import {
  Zap, Clock, CheckCircle, XCircle, TrendingUp, TrendingDown,
  Activity, Server, Cpu, RefreshCw, Calendar, BarChart3,
  AlertTriangle, Shield, ArrowRight, Timer, HardDrive, Database,
  Download, Bot
} from 'lucide-react'

/**
 * FailoverReport - Relatório completo de failovers
 * Estilo TailAdmin com cores estáticas
 */

// Benchmarks Reais (Dezembro 2024)
// Estes valores são baseados em testes reais de integração
const REAL_BENCHMARKS = {
  cpu_standby_gcp: {
    start: 9780,  // 9.78s - GCP instance start
    stop: 135210, // 135.21s - GCP instance stop
  },
  pause_resume_vast: {
    // Varia por GPU
    rtx_a2000: { pause: 7400, resume: 7500 },
    rtx_4060_ti: { pause: 31000, resume: 44100 },
    rtx_5070: { pause: 11550, resume: 153570 }, // GPU lenta
    average: { pause: 15000, resume: 50000 },
  },
  spot_failover: {
    search: 1570,      // 1.57s - buscar ofertas spot
    detection: 10000,  // 10s - polling interval
    deploy: 30000,     // ~30s - estimado
    restore: 30000,    // ~30s - estimado
    total: 71570,      // ~72s total
  },
  cloud_storage: {
    upload: 20000,     // ~20s snapshot creation
    download: 25000,   // ~25s download
    total: 45000,      // ~45s total
  },
};

// Dados demo de histórico de failover
const DEMO_FAILOVER_HISTORY = [
  {
    id: 'fo-001',
    timestamp: new Date(Date.now() - 86400000 * 2).toISOString(),
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
    timestamp: new Date(Date.now() - 86400000 * 5).toISOString(),
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
    timestamp: new Date(Date.now() - 86400000 * 8).toISOString(),
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
    timestamp: new Date(Date.now() - 86400000 * 12).toISOString(),
    machine_id: 56789012,
    gpu_name: 'H100 80GB',
    new_gpu_name: null,
    reason: 'spot_preemption',
    phases: {
      detection_time_ms: 920,
      failover_time_ms: 1050,
      search_time_ms: 180000,
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
    'spot_preemption': 'Spot Preemption',
    'network_timeout': 'Network Timeout',
    'cuda_error': 'CUDA Error',
    'host_maintenance': 'Host Maintenance',
    'out_of_memory': 'Out of Memory',
    'unknown': 'Unknown'
  }
  return reasons[reason] || reason
}

// Componente de métrica individual - TailAdmin Style
const MetricCard = ({ icon: Icon, label, value, subValue, variant = 'primary' }) => {
  const variantClasses = {
    primary: 'stat-card-icon-primary',
    success: 'stat-card-icon-success',
    warning: 'stat-card-icon-warning',
    error: 'stat-card-icon-error',
  }

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <div>
          <p className="stat-card-label">{label}</p>
          <p className="stat-card-value">{value}</p>
          {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}
        </div>
        <div className={`stat-card-icon ${variantClasses[variant] || variantClasses.primary}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}

// Componente de timeline de um failover - cores estáticas
const FailoverTimeline = ({ failover }) => {
  const phases = [
    { key: 'detection', label: 'Detecção', time: failover.phases.detection_time_ms, icon: AlertTriangle, bgClass: 'bg-red-500/20', textClass: 'text-red-400' },
    { key: 'failover', label: 'Failover', time: failover.phases.failover_time_ms, icon: Shield, bgClass: 'bg-yellow-500/20', textClass: 'text-yellow-400' },
    { key: 'search', label: 'Busca GPU', time: failover.phases.search_time_ms, icon: Activity, bgClass: 'bg-blue-500/20', textClass: 'text-blue-400' },
    { key: 'provisioning', label: 'Provisioning', time: failover.phases.provisioning_time_ms, icon: Server, bgClass: 'bg-purple-500/20', textClass: 'text-purple-400' },
    { key: 'restore', label: 'Restauração', time: failover.phases.restore_time_ms, icon: RefreshCw, bgClass: 'bg-cyan-500/20', textClass: 'text-cyan-400' }
  ]

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {phases.map((phase, idx) => (
        <React.Fragment key={phase.key}>
          <div
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
              phase.time > 0 ? `${phase.bgClass} ${phase.textClass}` : 'bg-gray-700/30 text-gray-500'
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

// Visual Timeline Breakdown Component
const VisualTimelineBreakdown = ({ phases, totalTime }) => {
  const phaseList = [
    { key: 'snapshot_creation', label: 'Snapshot', colorClass: 'bg-blue-500', time: phases?.snapshot_creation_ms || 0 },
    { key: 'gpu_search', label: 'Busca GPU', colorClass: 'bg-purple-500', time: phases?.gpu_search_ms || 0 },
    { key: 'gpu_provision', label: 'Provisioning', colorClass: 'bg-yellow-500', time: phases?.gpu_provision_ms || 0 },
    { key: 'gpu_ready_wait', label: 'Aguardando', colorClass: 'bg-orange-500', time: phases?.gpu_ready_wait_ms || 0 },
    { key: 'restore', label: 'Restore', colorClass: 'bg-cyan-500', time: phases?.restore_ms || 0 },
    { key: 'inference', label: 'Inference', colorClass: 'bg-brand-500', time: phases?.inference_after_ms || 0 },
  ]

  const validPhases = phaseList.filter(p => p.time > 0)
  const total = totalTime || validPhases.reduce((s, p) => s + p.time, 0)

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1 text-xs text-gray-400">
        <Clock className="w-3 h-3" />
        <span>Tempo Total: {formatDuration(total)}</span>
      </div>
      <div className="flex h-6 rounded-lg overflow-hidden bg-gray-700/30">
        {validPhases.map((phase) => {
          const pct = (phase.time / total) * 100
          return (
            <div
              key={phase.key}
              className={`${phase.colorClass} flex items-center justify-center text-[10px] text-white font-medium transition-all hover:brightness-125`}
              style={{ width: `${Math.max(pct, 5)}%` }}
              title={`${phase.label}: ${formatDuration(phase.time)} (${pct.toFixed(1)}%)`}
            >
              {pct > 10 ? phase.label : ''}
            </div>
          )
        })}
      </div>
      <div className="flex flex-wrap gap-2 text-[10px]">
        {validPhases.map(phase => (
          <div key={phase.key} className="flex items-center gap-1">
            <div className={`w-2 h-2 rounded-sm ${phase.colorClass}`} />
            <span className="text-gray-400">{phase.label}: {formatDuration(phase.time)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Real Failover Test Card Component
const RealFailoverCard = ({ test }) => {
  const phases = test.phase_timings || {}

  return (
    <div
      className={`p-4 rounded-lg border ${
        test.totals?.success
          ? 'border-brand-500/30 bg-brand-500/5'
          : 'border-red-500/30 bg-red-500/5'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {test.totals?.success ? (
            <CheckCircle className="w-5 h-5 text-brand-400" />
          ) : (
            <XCircle className="w-5 h-5 text-red-400" />
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-medium">{test.gpu?.original_type || 'GPU'}</span>
              {test.gpu?.new_type && (
                <>
                  <ArrowRight className="w-3 h-3 text-gray-500" />
                  <span className="text-brand-400 font-medium">{test.gpu.new_type}</span>
                </>
              )}
            </div>
            <div className="text-xs text-gray-500">
              {test.started_at ? formatDate(test.started_at) : 'N/A'} • ID: {test.failover_id}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${test.totals?.success ? 'text-brand-400' : 'text-red-400'}`}>
            {formatDuration(test.totals?.total_time_ms || 0)}
          </div>
          <div className="text-xs text-gray-500">tempo total</div>
        </div>
      </div>

      {/* Visual Timeline */}
      <VisualTimelineBreakdown phases={phases} totalTime={test.totals?.total_time_ms} />

      {/* Snapshot Info */}
      {test.snapshot && (
        <div className="mt-4 pt-4 border-t border-gray-700/50">
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <HardDrive className="w-3 h-3 text-blue-400" />
            <span className="text-blue-400 font-medium">Snapshot Details</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Tamanho</div>
              <div className="text-white font-medium">{test.snapshot.size_mb || 0} MB</div>
            </div>
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Criação</div>
              <div className="text-white font-medium">{formatDuration(test.snapshot.creation_time_ms || 0)}</div>
            </div>
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Storage</div>
              <div className="text-white font-medium">{test.snapshot.storage || 'B2'}</div>
            </div>
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Compressão</div>
              <div className="text-white font-medium">{test.snapshot.compression || 'LZ4'}</div>
            </div>
          </div>
        </div>
      )}

      {/* Restore Info */}
      {test.restore && test.restore.time_ms > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <Download className="w-3 h-3 text-cyan-400" />
            <span className="text-cyan-400 font-medium">Restore Details</span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Download</div>
              <div className="text-white font-medium">{formatDuration(test.restore.download_time_ms || 0)}</div>
            </div>
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Decompress</div>
              <div className="text-white font-medium">{formatDuration(test.restore.decompress_time_ms || 0)}</div>
            </div>
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Total</div>
              <div className="text-white font-medium">{formatDuration(test.restore.time_ms || 0)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Inference Test */}
      {test.inference && (
        <div className="mt-3">
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <Bot className="w-3 h-3 text-brand-400" />
            <span className="text-brand-400 font-medium">Inference Test</span>
            {test.inference.success ? (
              <span className="px-1.5 py-0.5 bg-brand-500/20 text-brand-400 rounded text-[10px]">PASSED</span>
            ) : (
              <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded text-[10px]">FAILED</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Modelo</div>
              <div className="text-white font-medium">{test.inference.model || 'N/A'}</div>
            </div>
            <div className="p-2 bg-white/5 rounded">
              <div className="text-gray-500">Time to Inference</div>
              <div className="text-white font-medium">{formatDuration(test.inference.ready_time_ms || 0)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {!test.totals?.success && test.totals?.failure_reason && (
        <div className="mt-3 pt-3 border-t border-red-500/30">
          <span className="text-xs text-red-400">
            <AlertTriangle className="w-3 h-3 inline mr-1" />
            Falha: {test.totals.failure_reason}
          </span>
        </div>
      )}
    </div>
  )
}

// Componente principal
export default function FailoverReport({ isDemo = true }) {
  const [history, setHistory] = useState([])
  const [realTests, setRealTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('30d')

  useEffect(() => {
    const loadHistory = async () => {
      let localHistory = []
      try {
        const stored = localStorage.getItem('failover_history')
        if (stored) {
          localHistory = JSON.parse(stored).map(item => ({
            ...item,
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

      try {
        const token = localStorage.getItem('auth_token')
        const res = await fetch('/api/standby/failover/test-real/history', {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
        if (res.ok) {
          const data = await res.json()
          setRealTests(data.tests || [])
        }
      } catch (err) {
        console.error('Error fetching real failover tests:', err)
      }

      if (localHistory.length > 0) {
        const combined = [...localHistory, ...DEMO_FAILOVER_HISTORY].sort(
          (a, b) => new Date(b.timestamp || b.started_at) - new Date(a.timestamp || a.started_at)
        )
        setHistory(combined)
        setLoading(false)
        return
      }

      if (isDemo) {
        setHistory(DEMO_FAILOVER_HISTORY)
        setLoading(false)
        return
      }

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

    loadHistory()

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

  const successfulRecoveryTimes = history
    .filter(f => f.status === 'success')
    .map(f => f.phases.total_time_ms)
  const avgRecoveryTime = successfulRecoveryTimes.length > 0
    ? successfulRecoveryTimes.reduce((a, b) => a + b, 0) / successfulRecoveryTimes.length
    : 0

  const detectionTimes = history.map(f => f.phases.detection_time_ms)
  const avgDetectionTime = detectionTimes.length > 0
    ? detectionTimes.reduce((a, b) => a + b, 0) / detectionTimes.length
    : 0

  const totalDataRestored = history.reduce((sum, f) => sum + (f.data_restored_mb || 0), 0)

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
          <div className="stat-card-icon stat-card-icon-error">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Relatório de Failover</h2>
            <p className="text-sm text-gray-400">Histórico e métricas de recuperação automática</p>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="ta-tabs">
          {['7d', '30d', '90d'].map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`ta-tab ${timeRange === range ? 'ta-tab-active' : ''}`}
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
          variant="warning"
        />
        <MetricCard
          icon={CheckCircle}
          label="Taxa de Sucesso"
          value={`${successRate}%`}
          subValue={Number(successRate) >= 95 ? 'Excelente' : Number(successRate) >= 80 ? 'Bom' : 'Precisa atenção'}
          variant={Number(successRate) >= 95 ? 'success' : Number(successRate) >= 80 ? 'warning' : 'error'}
        />
        <MetricCard
          icon={Timer}
          label="MTTR (Tempo Médio)"
          value={formatDuration(avgRecoveryTime)}
          subValue="Tempo médio de recuperação"
          variant="primary"
        />
        <MetricCard
          icon={Activity}
          label="Latência Detecção"
          value={formatDuration(avgDetectionTime)}
          subValue="Tempo para detectar falha"
          variant="primary"
        />
      </div>

      {/* Métricas Secundárias */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={RefreshCw}
          label="Dados Restaurados"
          value={`${(totalDataRestored / 1024).toFixed(1)} GB`}
          subValue={`${history.reduce((s, f) => s + f.files_synced, 0).toLocaleString()} arquivos`}
          variant="primary"
        />
        <MetricCard
          icon={Server}
          label="GPUs Provisionadas"
          value={successfulFailovers}
          subValue="Novas instâncias criadas"
          variant="success"
        />
        <MetricCard
          icon={Cpu}
          label="CPU Standby Ativo"
          value={`${history.filter(f => f.phases.failover_time_ms > 0).length}`}
          subValue="Vezes utilizado como backup"
          variant="primary"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Causa Principal"
          value={Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?
            getReasonLabel(Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0][0]).split(' ')[0] : 'N/A'}
          subValue={Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0]?.[1] + ' ocorrências' || ''}
          variant="warning"
        />
      </div>

      {/* Gráfico de Latências por Fase */}
      <div className="ta-card">
        <div className="ta-card-header">
          <h3 className="ta-card-title flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            Latência por Fase (Média)
          </h3>
        </div>
        <div className="ta-card-body">
          <div className="space-y-3" data-testid="latency-breakdown">
            {[
              { label: 'Detecção', key: 'detection_time_ms', colorClass: 'bg-red-500' },
              { label: 'Failover para CPU', key: 'failover_time_ms', colorClass: 'bg-yellow-500' },
              { label: 'Busca de GPU', key: 'search_time_ms', colorClass: 'bg-blue-500' },
              { label: 'Provisionamento', key: 'provisioning_time_ms', colorClass: 'bg-purple-500' },
              { label: 'Restauração', key: 'restore_time_ms', colorClass: 'bg-cyan-500' }
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
                    <span className="text-white font-medium">{formatDuration(avgTime)}</span>
                  </div>
                  <div className="h-2 bg-gray-700/50 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${phase.colorClass} rounded-full transition-all`}
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Real Failover Tests */}
      {realTests.length > 0 && (
        <div className="ta-card border-blue-500/30">
          <div className="ta-card-header">
            <h3 className="ta-card-title flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-400" />
              Testes Reais de Failover (com Snapshots B2)
              <span className="ml-2 px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-[10px]">
                {realTests.length} teste{realTests.length !== 1 ? 's' : ''}
              </span>
            </h3>
          </div>
          <div className="ta-card-body">
            <div className="space-y-4" data-testid="real-failover-tests">
              {realTests.map(test => (
                <RealFailoverCard key={test.failover_id} test={test} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Histórico Detalhado */}
      <div className="ta-card">
        <div className="ta-card-header">
          <h3 className="ta-card-title flex items-center gap-2">
            <Calendar className="w-4 h-4 text-brand-400" />
            Histórico de Failovers
          </h3>
        </div>
        <div className="ta-card-body">
          <div className="space-y-4" data-testid="failover-history">
            {history.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Nenhum failover registrado</p>
            ) : (
              history.map(failover => (
                <div
                  key={failover.id}
                  className={`p-4 rounded-lg border ${
                    failover.status === 'success'
                      ? 'border-brand-500/30 bg-brand-500/5'
                      : 'border-red-500/30 bg-red-500/5'
                  }`}
                  data-testid={`failover-item-${failover.id}`}
                >
                  {/* Header do Failover */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {failover.status === 'success' ? (
                        <CheckCircle className="w-5 h-5 text-brand-400" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-400" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-white font-medium">{failover.gpu_name}</span>
                          {failover.new_gpu_name && (
                            <>
                              <ArrowRight className="w-3 h-3 text-gray-500" />
                              <span className="text-brand-400 font-medium">{failover.new_gpu_name}</span>
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
                        failover.status === 'success' ? 'text-brand-400' : 'text-red-400'
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
        </div>
      </div>
    </div>
  )
}
