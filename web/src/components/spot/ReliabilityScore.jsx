import { useState, useEffect } from 'react'
import { Shield, Star, Server } from 'lucide-react'

const API_BASE = ''

export default function ReliabilityScore({ getAuthHeaders, selectedGPU = 'all' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (selectedGPU !== 'all') params.append('gpu_name', selectedGPU)

      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/reliability?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        const items = result.items || []
        const tiers = {
          'Excelente': items.filter(p => p.overall_score >= 90).length,
          'Bom': items.filter(p => p.overall_score >= 70 && p.overall_score < 90).length,
          'Regular': items.filter(p => p.overall_score >= 50 && p.overall_score < 70).length,
          'Ruim': items.filter(p => p.overall_score < 50).length
        }
        setData({
          market_average: (result.avg_score || 0) / 100,
          total_providers: items.length,
          tiers: tiers,
          top_providers: items.slice(0, 5).map(p => ({
            machine_id: p.machine_id,
            hostname: p.hostname,
            reliability_score: (p.overall_score || 0) / 100,
            total_observations: p.total_rentals || 1,
            verified: p.recommendation === 'recommended'
          }))
        })
      }
    } catch (err) {
      console.error('Erro ao carregar reliability:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [selectedGPU])

  const formatPercent = (value) => `${(value * 100)?.toFixed(0) || '0'}%`

  const getScoreColor = (score) => {
    if (score >= 0.9) return 'text-emerald-400'
    if (score >= 0.7) return 'text-lime-400'
    if (score >= 0.5) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getScoreBgColor = (score) => {
    if (score >= 0.9) return 'bg-emerald-500'
    if (score >= 0.7) return 'bg-lime-500'
    if (score >= 0.5) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getTierColor = (tier) => {
    if (tier === 'Excelente') return 'bg-emerald-500'
    if (tier === 'Bom') return 'bg-lime-500'
    if (tier === 'Regular') return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getStars = (score) => {
    const stars = Math.round(score * 5)
    return Array(5).fill(0).map((_, i) => (
      <Star
        key={i}
        size={14}
        className={i < stars ? 'text-yellow-400' : 'text-gray-600'}
        fill={i < stars ? '#facc15' : 'none'}
      />
    ))
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
          <div className="stat-card-icon stat-card-icon-success">
            <Shield size={18} />
          </div>
          Score de Confiabilidade de Provedores
        </h3>
      </div>

      <div className="ta-card-body">
        {data?.market_average !== undefined && (
          <div className="spot-highlight mb-5">
            <div className="flex items-center justify-center gap-4 relative z-10">
              <div>
                <span className="block text-xs text-emerald-300/70 uppercase font-semibold mb-1">Média do Mercado</span>
                <span className={`text-4xl font-extrabold ${getScoreColor(data.market_average)}`}>
                  {formatPercent(data.market_average)}
                </span>
              </div>
              <div className="flex gap-1">{getStars(data.market_average)}</div>
            </div>
          </div>
        )}

        <div className="mb-5 p-4 bg-white/[0.02] rounded-xl border border-white/5">
          <h4 className="text-sm text-gray-400 mb-3">Distribuição por Nível</h4>
          <div className="flex flex-col gap-2.5">
            {data?.tiers && Object.entries(data.tiers).map(([tier, count], idx) => (
              <div key={tier} className="grid grid-cols-[90px_1fr_50px] items-center gap-3 animate-fade-in" style={{ animationDelay: `${idx * 50}ms` }}>
                <span className="text-xs font-semibold text-white">{tier}</span>
                <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${getTierColor(tier)}`}
                    style={{ width: `${Math.max((count / (data.total_providers || 1)) * 100, 3)}%` }}
                  />
                </div>
                <span className="text-sm font-bold text-white text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 bg-white/[0.02] rounded-xl border border-white/5">
          <h4 className="text-sm text-gray-400 mb-3">Top 5 Provedores Mais Confiáveis</h4>
          <div className="flex flex-col gap-2">
            {data?.top_providers?.slice(0, 5).map((provider, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 p-3 bg-white/[0.03] hover:bg-white/[0.06] rounded-lg transition-colors animate-fade-in" style={{ animationDelay: `${idx * 50}ms` }}>
                <div className={`text-lg font-bold ${idx === 0 ? 'text-yellow-400' : idx === 1 ? 'text-gray-300' : idx === 2 ? 'text-orange-400' : 'text-blue-400'}`}>#{idx + 1}</div>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500/20 to-blue-500/20 flex items-center justify-center">
                    <Server size={14} className="text-emerald-400" />
                  </div>
                  <span className="text-white font-medium">{provider.hostname || `Host ${provider.machine_id}`}</span>
                </div>
                <span
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-lg ${getScoreBgColor(provider.reliability_score)}`}
                >
                  {formatPercent(provider.reliability_score)}
                </span>
                <div className="flex gap-0.5">{getStars(provider.reliability_score)}</div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{provider.total_observations} obs</span>
                  {provider.verified && <Shield size={12} className="text-emerald-400" />}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
