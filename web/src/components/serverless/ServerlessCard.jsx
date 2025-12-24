import { useState } from 'react'
import {
  Zap,
  Activity,
  Clock,
  Server,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Pause,
  Play,
  Trash2,
  Settings,
  MoreHorizontal,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ExternalLink,
  Gauge,
  BarChart3
} from 'lucide-react'
import { Badge } from '../tailadmin-ui'

export default function ServerlessCard({ endpoint, onReload }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const getStatusBadge = (status) => {
    switch (status) {
      case 'running':
        return (
          <Badge variant="success" dot>
            Running
          </Badge>
        )
      case 'scaled_to_zero':
        return (
          <Badge variant="gray" dot>
            Scaled to Zero
          </Badge>
        )
      case 'paused':
        return (
          <Badge variant="warning" dot>
            Paused
          </Badge>
        )
      case 'error':
        return (
          <Badge variant="error" dot>
            Error
          </Badge>
        )
      default:
        return (
          <Badge variant="gray" dot>
            {status}
          </Badge>
        )
    }
  }

  const getMachineTypeBadge = (type) => {
    if (type === 'spot') {
      return (
        <Badge className="bg-brand-500/10 text-brand-400 border-brand-500/20">
          <Zap className="w-3 h-3 mr-1" />
          Spot
        </Badge>
      )
    }
    return (
      <Badge className="bg-white/5 text-gray-400 border-white/10">
        On-Demand
      </Badge>
    )
  }

  const handleCopyEndpoint = () => {
    const url = `https://${endpoint.id}.dumont.cloud`
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-xl bg-dark-surface-card border border-white/10 overflow-hidden hover:border-brand-500/30 transition-colors">
      {/* Header */}
      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-bold text-white">{endpoint.name}</h3>
              {getStatusBadge(endpoint.status)}
              {getMachineTypeBadge(endpoint.machine_type)}
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <Server className="w-3.5 h-3.5" />
                {endpoint.gpu_name}
              </span>
              <span>•</span>
              <span>{endpoint.region}</span>
              <span>•</span>
              <span>
                {endpoint.auto_scaling.current_instances}/{endpoint.auto_scaling.max_instances} instâncias
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors">
              <Settings className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors">
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Endpoint URL */}
        <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10 mb-4">
          <code className="flex-1 text-sm text-brand-400 font-mono">
            https://{endpoint.id}.dumont.cloud
          </code>
          <button
            onClick={handleCopyEndpoint}
            className="p-1.5 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
          >
            {copied ? (
              <CheckCircle2 className="w-4 h-4 text-brand-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button className="p-1.5 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors">
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Requests */}
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs text-gray-500 uppercase">Requests/s</span>
            </div>
            <div className="text-lg font-bold text-white">
              {endpoint.metrics.requests_per_sec.toFixed(1)}
            </div>
            <div className="text-xs text-gray-500">
              {endpoint.metrics.total_requests_24h.toLocaleString()} (24h)
            </div>
          </div>

          {/* Latency */}
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs text-gray-500 uppercase">Latência</span>
            </div>
            <div className="text-lg font-bold text-white">
              {endpoint.metrics.avg_latency_ms}ms
            </div>
            <div className="text-xs text-gray-500">
              p99: {endpoint.metrics.p99_latency_ms}ms
            </div>
          </div>

          {/* Cold Starts */}
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center gap-2 mb-1">
              <Gauge className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs text-gray-500 uppercase">Cold Starts</span>
            </div>
            <div className="text-lg font-bold text-white">
              {endpoint.metrics.cold_starts_24h}
            </div>
            <div className="text-xs text-gray-500">
              {endpoint.metrics.uptime_percent.toFixed(1)}% uptime
            </div>
          </div>

          {/* Cost */}
          <div className="p-3 rounded-lg bg-brand-500/10 border border-brand-500/20">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-xs text-brand-400 uppercase">Custo (24h)</span>
            </div>
            <div className="text-lg font-bold text-white">
              ${endpoint.pricing.cost_24h.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500">
              ${endpoint.pricing.price_per_hour.toFixed(2)}/h
            </div>
          </div>
        </div>

        {/* Auto-scaling info */}
        {endpoint.auto_scaling.enabled && (
          <div className="mt-4 p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp className="w-4 h-4 text-brand-400" />
                <span className="text-gray-400">
                  Auto-scaling: {endpoint.auto_scaling.min_instances}-{endpoint.auto_scaling.max_instances} instâncias
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  {Array.from({ length: endpoint.auto_scaling.max_instances }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-2 h-4 rounded-sm ${
                        i < endpoint.auto_scaling.current_instances
                          ? 'bg-brand-400'
                          : 'bg-white/10'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-sm font-medium text-white">
                  {endpoint.auto_scaling.current_instances}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Spot interruption warning */}
        {endpoint.machine_type === 'spot' && endpoint.status === 'running' && (
          <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-amber-300">
                  Endpoint usando Spot pricing - pode ser interrompido a qualquer momento
                </p>
                <p className="text-xs text-amber-400/60 mt-1">
                  Auto-restart habilitado com Regional Volume
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-5 py-3 bg-white/5 border-t border-white/10 flex items-center justify-between">
        <div className="text-xs text-gray-500">
          Criado {new Date(endpoint.created_at).toLocaleDateString('pt-BR')}
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 transition-colors">
            <BarChart3 className="w-3.5 h-3.5 inline mr-1" />
            Métricas
          </button>
          <button className="px-3 py-1.5 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 transition-colors">
            <Settings className="w-3.5 h-3.5 inline mr-1" />
            Configurar
          </button>
        </div>
      </div>
    </div>
  )
}
