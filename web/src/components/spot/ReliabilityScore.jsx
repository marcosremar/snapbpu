import { useState, useEffect } from 'react'
import { Shield, Star, TrendingUp, Server } from 'lucide-react'

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
        // Map API response to expected format
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
    if (score >= 0.9) return '#22c55e'
    if (score >= 0.7) return '#84cc16'
    if (score >= 0.5) return '#f59e0b'
    return '#ef4444'
  }

  const getStars = (score) => {
    const stars = Math.round(score * 5)
    return Array(5).fill(0).map((_, i) => (
      <Star
        key={i}
        size={14}
        className={i < stars ? 'star-filled' : 'star-empty'}
        fill={i < stars ? '#f59e0b' : 'none'}
      />
    ))
  }

  if (loading) {
    return <div className="spot-card loading">Calculando scores de confiabilidade...</div>
  }

  return (
    <div className="spot-card reliability-score">
      <div className="spot-card-header">
        <h3><Shield size={20} /> Score de Confiabilidade de Provedores</h3>
      </div>

      {data?.market_average && (
        <div className="market-average">
          <span className="label">Média do Mercado:</span>
          <span
            className="score"
            style={{ color: getScoreColor(data.market_average) }}
          >
            {formatPercent(data.market_average)}
          </span>
          <div className="stars">{getStars(data.market_average)}</div>
        </div>
      )}

      <div className="reliability-tiers">
        <h4>Distribuição por Nível</h4>
        <div className="tier-bars">
          {data?.tiers && Object.entries(data.tiers).map(([tier, count]) => (
            <div key={tier} className="tier-bar">
              <span className="tier-name">{tier}</span>
              <div className="bar-container">
                <div
                  className="bar-fill"
                  style={{
                    width: `${(count / (data.total_providers || 1)) * 100}%`,
                    backgroundColor:
                      tier === 'Excelente' ? '#22c55e' :
                      tier === 'Bom' ? '#84cc16' :
                      tier === 'Regular' ? '#f59e0b' : '#ef4444'
                  }}
                />
              </div>
              <span className="tier-count">{count}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="top-providers">
        <h4>Top 5 Provedores Mais Confiáveis</h4>
        <div className="provider-list">
          {data?.top_providers?.slice(0, 5).map((provider, idx) => (
            <div key={idx} className="provider-row">
              <div className="rank-badge">#{idx + 1}</div>
              <div className="provider-info">
                <Server size={14} />
                <span className="hostname">{provider.hostname || `Host ${provider.machine_id}`}</span>
              </div>
              <div className="provider-score">
                <div
                  className="score-circle"
                  style={{ backgroundColor: getScoreColor(provider.reliability_score) }}
                >
                  {formatPercent(provider.reliability_score)}
                </div>
              </div>
              <div className="provider-stars">{getStars(provider.reliability_score)}</div>
              <div className="provider-meta">
                <span>{provider.total_observations} obs</span>
                {provider.verified && <Shield size={12} className="verified" />}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
