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
    const colors = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' }
    return colors[risk] || '#6b7280'
  }

  if (loading && !data) {
    return <div className="spot-card loading">Calculando estratégia de fleet...</div>
  }

  return (
    <div className="spot-card fleet-strategy">
      <div className="spot-card-header">
        <h3><Server size={20} /> Estratégia de Fleet Spot</h3>
      </div>

      <div className="fleet-config">
        <div className="config-item">
          <label>GPUs Necessárias:</label>
          <input
            type="number"
            min="1"
            max="32"
            value={targetGpus}
            onChange={(e) => setTargetGpus(parseInt(e.target.value) || 1)}
          />
        </div>
        <div className="config-item">
          <label>Budget Máximo/h:</label>
          <input
            type="number"
            min="0.5"
            max="50"
            step="0.5"
            value={budget}
            onChange={(e) => setBudget(parseFloat(e.target.value) || 0.5)}
          />
        </div>
      </div>

      {data?.recommended_strategy && (
        <div className="strategy-recommendation">
          <CheckCircle size={24} className="success-icon" />
          <div className="strategy-info">
            <span className="strategy-label">Estratégia Recomendada</span>
            <span className="strategy-name">{data.recommended_strategy.name}</span>
            <span className="strategy-cost">
              Custo estimado: {formatPrice(data.recommended_strategy.estimated_cost)}
            </span>
          </div>
        </div>
      )}

      {data?.fleet_composition && (
        <div className="fleet-composition">
          <h4>Composição do Fleet</h4>
          <div className="composition-grid">
            {data.fleet_composition.map((item, idx) => (
              <div key={idx} className="composition-item">
                <div className="gpu-info">
                  <Zap size={16} />
                  <span className="gpu-name">{item.gpu_name}</span>
                </div>
                <div className="gpu-count">x{item.count}</div>
                <div className="gpu-price">{formatPrice(item.price_per_gpu)}</div>
                <div
                  className="reliability-indicator"
                  style={{ color: getRiskColor(item.risk_level) }}
                >
                  <Shield size={14} />
                  {formatPercent(item.reliability)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data?.risk_analysis && (
        <div className="risk-analysis">
          <h4>Análise de Risco</h4>
          <div className="risk-metrics">
            <div className="risk-item">
              <span className="label">Risco Geral</span>
              <span
                className="value"
                style={{ color: getRiskColor(data.risk_analysis.overall_risk) }}
              >
                {data.risk_analysis.overall_risk?.toUpperCase()}
              </span>
            </div>
            <div className="risk-item">
              <span className="label">Prob. Interrupção/h</span>
              <span className="value">
                {formatPercent(data.risk_analysis.interruption_probability)}
              </span>
            </div>
            <div className="risk-item">
              <span className="label">Diversificação</span>
              <span className="value">
                {data.risk_analysis.diversification_score?.toFixed(1)}/10
              </span>
            </div>
          </div>
        </div>
      )}

      {data?.recommendations && (
        <div className="strategy-tips">
          <h4><AlertTriangle size={16} /> Recomendações</h4>
          <ul>
            {data.recommendations.map((tip, idx) => (
              <li key={idx}>{tip}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
