import { useState, useEffect } from 'react'
import { Server, Shield, Zap, CheckCircle, AlertTriangle } from 'lucide-react'

const API_BASE = ''

export default function FleetStrategy({ getAuthHeaders }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [targetGpus, setTargetGpus] = useState(4)
  const [budget, setBudget] = useState(2.0)

  const loadData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('target_gpus', targetGpus)
      params.append('max_budget_per_hour', budget)

      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/fleet-strategy?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        setData(result)
      }
    } catch (err) {
      console.error('Erro ao carregar fleet strategy:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [targetGpus, budget])

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}/h`
  const formatPercent = (value) => `${(value * 100)?.toFixed(0) || '0'}%`

  const getRiskColor = (risk) => {
    if (risk === 'low') return 'text-brand-400'
    if (risk === 'medium') return 'text-yellow-400'
    return 'text-red-400'
  }

  const getRiskBgColor = (risk) => {
    if (risk === 'low') return 'bg-brand-500'
    if (risk === 'medium') return 'bg-yellow-500'
    return 'bg-red-500'
  }

  if (loading && !data) {
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
          <div className="stat-card-icon stat-card-icon-primary">
            <Server size={18} />
          </div>
          Estratégia de Fleet Spot
        </h3>
      </div>

      <div className="ta-card-body">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5 p-4 bg-white/[0.03] rounded-xl border border-white/5">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-gray-500 uppercase tracking-wide">GPUs Necessárias</label>
            <input
              type="number"
              min="1"
              max="32"
              value={targetGpus}
              onChange={(e) => setTargetGpus(parseInt(e.target.value) || 1)}
              className="ta-input"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-gray-500 uppercase tracking-wide">Budget Máximo/h</label>
            <input
              type="number"
              min="0.5"
              max="50"
              step="0.5"
              value={budget}
              onChange={(e) => setBudget(parseFloat(e.target.value) || 0.5)}
              className="ta-input"
            />
          </div>
        </div>

        {data?.recommended_strategy && (
          <div className="spot-highlight mb-5">
            <div className="flex items-center justify-center gap-3 relative z-10">
              <CheckCircle size={28} className="text-brand-400" />
              <div className="text-left">
                <span className="block text-xs text-brand-300/70 uppercase font-semibold">Estratégia Recomendada</span>
                <span className="block text-xl font-bold text-white">{data.recommended_strategy.name}</span>
                <span className="block text-sm text-brand-200/60">
                  Custo estimado: <strong className="text-brand-300">{formatPrice(data.recommended_strategy.estimated_cost)}</strong>
                </span>
              </div>
            </div>
          </div>
        )}

        {data?.fleet_composition && (
          <div className="mb-4">
            <h4 className="text-sm text-gray-400 mb-3">Composição do Fleet</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {data.fleet_composition.map((item, idx) => (
                <div key={idx} className="stat-card flex flex-col gap-1.5">
                  <div className="flex items-center gap-1.5 text-white font-medium">
                    <Zap size={16} className="text-brand-400" />
                    {item.gpu_name}
                  </div>
                  <div className="text-xl font-extrabold text-brand-400">x{item.count}</div>
                  <div className="text-xs text-gray-400">{formatPrice(item.price_per_gpu)}</div>
                  <div className={`flex items-center gap-1 text-xs ${getRiskColor(item.risk_level)}`}>
                    <Shield size={14} />
                    {formatPercent(item.reliability)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data?.risk_analysis && (
          <div className="pt-4 border-t border-white/10 mb-4">
            <h4 className="text-sm text-gray-400 mb-3">Análise de Risco</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="stat-card text-center">
                <span className="block text-[11px] text-gray-400 mb-1">Risco Geral</span>
                <span className={`text-lg font-bold ${getRiskColor(data.risk_analysis.overall_risk)}`}>
                  {data.risk_analysis.overall_risk?.toUpperCase()}
                </span>
              </div>
              <div className="stat-card text-center">
                <span className="block text-[11px] text-gray-400 mb-1">Prob. Interrupção/h</span>
                <span className="text-lg font-bold text-white">
                  {formatPercent(data.risk_analysis.interruption_probability)}
                </span>
              </div>
              <div className="stat-card text-center">
                <span className="block text-[11px] text-gray-400 mb-1">Diversificação</span>
                <span className="text-lg font-bold text-white">
                  {data.risk_analysis.diversification_score?.toFixed(1)}/10
                </span>
              </div>
            </div>
          </div>
        )}

        {data?.recommendations && (
          <div className="ta-alert ta-alert-warning">
            <AlertTriangle size={16} className="flex-shrink-0" />
            <div>
              <h4 className="text-sm font-medium mb-1">Recomendações</h4>
              <ul className="text-xs space-y-0.5 list-disc pl-4">
                {data.recommendations.map((tip, idx) => (
                  <li key={idx}>{tip}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
