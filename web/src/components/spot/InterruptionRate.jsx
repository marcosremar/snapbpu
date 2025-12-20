import { useState, useEffect } from 'react'
import { AlertTriangle, Shield, Server } from 'lucide-react'

const API_BASE = ''

export default function InterruptionRate({ getAuthHeaders }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/interruption-rates`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        setData({
          global_stats: {
            avg_interruption_rate: result.avg_interruption_rate,
            total_providers: result.items?.length || 0,
            safe_providers: result.safest_providers || 0
          },
          providers: result.items || []
        })
      }
    } catch (err) {
      console.error('Erro ao carregar interruption rate:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [])

  const formatPercent = (value) => `${(value * 100)?.toFixed(1) || '0'}%`

  const getRateColor = (rate) => {
    if (rate < 0.05) return 'text-emerald-400'
    if (rate < 0.15) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getRateBgColor = (rate) => {
    if (rate < 0.05) return 'bg-emerald-500'
    if (rate < 0.15) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  if (loading) {
    return (
      <div className="ta-card">
        <div className="ta-card-body flex items-center justify-center min-h-[200px]">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="ta-card hover-glow">
      <div className="ta-card-header">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-warning pulse-dot">
            <AlertTriangle size={18} />
          </div>
          Taxa de Interrupção por Provedor
        </h3>
      </div>

      <div className="ta-card-body">
        {data?.global_stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
            <div className="stat-card text-center animate-fade-in" style={{ animationDelay: '0ms' }}>
              <div className="flex justify-center mb-2">
                <div className={`stat-card-icon ${data.global_stats.avg_interruption_rate < 0.05 ? 'stat-card-icon-success' : data.global_stats.avg_interruption_rate < 0.15 ? 'stat-card-icon-warning' : 'stat-card-icon-danger'}`}>
                  <AlertTriangle size={16} />
                </div>
              </div>
              <span className="block text-[11px] text-gray-400 uppercase tracking-wide mb-1">Taxa Média Global</span>
              <span className={`text-2xl font-extrabold ${getRateColor(data.global_stats.avg_interruption_rate)}`}>
                {formatPercent(data.global_stats.avg_interruption_rate)}
              </span>
            </div>
            <div className="stat-card text-center animate-fade-in" style={{ animationDelay: '50ms' }}>
              <div className="flex justify-center mb-2">
                <div className="stat-card-icon stat-card-icon-primary">
                  <Server size={16} />
                </div>
              </div>
              <span className="block text-[11px] text-gray-400 uppercase tracking-wide mb-1">Provedores Analisados</span>
              <span className="text-2xl font-extrabold text-white">{data.global_stats.total_providers}</span>
            </div>
            <div className="stat-card text-center animate-fade-in" style={{ animationDelay: '100ms' }}>
              <div className="flex justify-center mb-2">
                <div className="stat-card-icon stat-card-icon-success">
                  <Shield size={16} />
                </div>
              </div>
              <span className="block text-[11px] text-gray-400 uppercase tracking-wide mb-1">Provedores Seguros (&lt;5%)</span>
              <span className="text-2xl font-extrabold text-emerald-400">{data.global_stats.safe_providers}</span>
            </div>
          </div>
        )}

        <div className="p-4 bg-white/[0.02] rounded-xl border border-white/5">
          <h4 className="text-sm text-gray-400 mb-3">Provedores com Menor Taxa de Interrupção</h4>
          <div className="flex flex-col gap-2">
            {data?.providers?.slice(0, 8).map((provider, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 p-3 bg-white/[0.03] hover:bg-white/[0.06] rounded-lg transition-colors animate-fade-in" style={{ animationDelay: `${idx * 40}ms` }}>
                <div className="text-emerald-400 font-bold text-lg hidden sm:block">#{idx + 1}</div>
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center flex-shrink-0">
                    <Server size={16} className="text-emerald-400" />
                  </div>
                  <div>
                    <span className="text-white font-medium">{provider.hostname || `Host ${provider.machine_id}`}</span>
                    <span className="block text-xs text-gray-500">{provider.geolocation}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${getRateBgColor(provider.interruption_rate)}`}
                      style={{ width: `${Math.max(provider.interruption_rate * 100, 3)}%` }}
                    />
                  </div>
                  <span className={`font-bold text-sm min-w-[45px] text-right ${getRateColor(provider.interruption_rate)}`}>
                    {formatPercent(provider.interruption_rate)}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{provider.total_rentals} aluguéis</span>
                  {provider.verified && <Shield size={14} className="text-emerald-400" />}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
