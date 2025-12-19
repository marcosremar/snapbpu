import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react'

const API_BASE = ''

export default function SpotMonitor({ getAuthHeaders }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/monitor`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        setData(result)
        setError(null)
      } else {
        setError('Erro ao carregar dados')
      }
    } catch (err) {
      setError('Erro de conexão')
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const getTrendIcon = (trend) => {
    if (trend === 'up') return <TrendingUp size={16} className="trend-up" />
    if (trend === 'down') return <TrendingDown size={16} className="trend-down" />
    return <Minus size={16} className="trend-stable" />
  }

  const formatPrice = (price) => `$${price?.toFixed(4) || '0.0000'}/h`
  const formatPercent = (value) => `${value?.toFixed(1) || '0'}%`

  if (loading && !data) {
    return <div className="spot-card loading">Carregando monitor spot...</div>
  }

  if (error) {
    return <div className="spot-card error">{error}</div>
  }

  return (
    <div className="spot-card spot-monitor">
      <div className="spot-card-header">
        <h3>Monitor de Preços Spot</h3>
        <button onClick={loadData} className="refresh-btn" disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      <div className="spot-monitor-grid">
        {data?.items?.slice(0, 8).map((item, idx) => (
          <div key={idx} className="spot-monitor-item">
            <div className="spot-gpu-name">{item.gpu_name}</div>
            <div className="spot-price-row">
              <span className="spot-price">{formatPrice(item.spot_price)}</span>
              {getTrendIcon(item.price_trend)}
            </div>
            <div className="spot-savings">
              <span className="savings-badge">-{formatPercent(item.savings_percent)}</span>
              vs On-Demand
            </div>
            <div className="spot-meta">
              <span>{item.available_gpus} disponíveis</span>
              <span>Min: {formatPrice(item.min_price)}</span>
            </div>
          </div>
        ))}
      </div>

      {data?.market_overview && (
        <div className="spot-overview">
          <div className="overview-item">
            <span className="label">Total GPUs Spot:</span>
            <span className="value">{data.market_overview.total_spot_gpus}</span>
          </div>
          <div className="overview-item">
            <span className="label">Economia Média:</span>
            <span className="value savings">{formatPercent(data.market_overview.avg_savings_percent)}</span>
          </div>
        </div>
      )}
    </div>
  )
}
