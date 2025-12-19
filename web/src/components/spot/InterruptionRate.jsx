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
        // Map API response to expected format
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
    if (rate < 0.05) return '#22c55e'
    if (rate < 0.15) return '#f59e0b'
    return '#ef4444'
  }

  if (loading) {
    return <div className="spot-card loading">Carregando taxas de interrupção...</div>
  }

  return (
    <div className="spot-card interruption-rate">
      <div className="spot-card-header">
        <h3><AlertTriangle size={20} /> Taxa de Interrupção por Provedor</h3>
      </div>

      {data?.global_stats && (
        <div className="global-stats">
          <div className="stat-item">
            <span className="label">Taxa Média Global</span>
            <span
              className="value"
              style={{ color: getRateColor(data.global_stats.avg_interruption_rate) }}
            >
              {formatPercent(data.global_stats.avg_interruption_rate)}
            </span>
          </div>
          <div className="stat-item">
            <span className="label">Provedores Analisados</span>
            <span className="value">{data.global_stats.total_providers}</span>
          </div>
          <div className="stat-item">
            <span className="label">Provedores Seguros (&lt;5%)</span>
            <span className="value safe">{data.global_stats.safe_providers}</span>
          </div>
        </div>
      )}

      <div className="providers-list">
        <h4>Provedores com Menor Taxa de Interrupção</h4>
        <div className="provider-items">
          {data?.providers?.slice(0, 8).map((provider, idx) => (
            <div key={idx} className="provider-item">
              <div className="provider-rank">#{idx + 1}</div>
              <div className="provider-info">
                <Server size={16} />
                <span className="hostname">{provider.hostname || `Host ${provider.machine_id}`}</span>
                <span className="location">{provider.geolocation}</span>
              </div>
              <div className="provider-stats">
                <div
                  className="rate-bar"
                  style={{ '--rate-width': `${provider.interruption_rate * 100}%` }}
                >
                  <div
                    className="rate-fill"
                    style={{ backgroundColor: getRateColor(provider.interruption_rate) }}
                  />
                </div>
                <span
                  className="rate-value"
                  style={{ color: getRateColor(provider.interruption_rate) }}
                >
                  {formatPercent(provider.interruption_rate)}
                </span>
              </div>
              <div className="provider-meta">
                <span>{provider.total_rentals} aluguéis</span>
                {provider.verified && <Shield size={14} className="verified" />}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
