import { useState, useEffect } from 'react'
import { Zap, CheckCircle, XCircle, RefreshCw } from 'lucide-react'

const API_BASE = ''

export default function InstantAvailability({ getAuthHeaders }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/availability`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        // Map API response to expected format
        const gpus = result.items?.map(item => ({
          gpu_name: item.gpu_name,
          available: item.available_now,
          min_price: item.spot_price,
          max_price: item.spot_price * 1.2, // Estimate max as 20% higher
          regions: item.regions ? Object.keys(item.regions) : [],
          time_to_provision: item.time_to_provision,
          verified_count: item.verified_count
        })) || []

        setData({
          total_available: result.total_available || gpus.reduce((sum, g) => sum + g.available, 0),
          gpu_types: gpus.length,
          gpus: gpus,
          fastest_gpu: result.fastest_gpu,
          timestamp: result.generated_at
        })
      }
    } catch (err) {
      console.error('Erro ao carregar availability:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const formatPrice = (price) => `$${price?.toFixed(4) || '0.0000'}/h`

  const getAvailabilityColor = (available) => {
    if (available > 20) return '#22c55e'
    if (available > 5) return '#f59e0b'
    return '#ef4444'
  }

  if (loading && !data) {
    return <div className="spot-card loading">Verificando disponibilidade...</div>
  }

  return (
    <div className="spot-card instant-availability">
      <div className="spot-card-header">
        <h3><Zap size={20} /> Disponibilidade Instantânea Spot</h3>
        <button onClick={loadData} className="refresh-btn" disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      <div className="availability-summary">
        <div className="summary-item">
          <span className="big-number">{data?.total_available || 0}</span>
          <span className="label">GPUs Spot Disponíveis</span>
        </div>
        <div className="summary-item">
          <span className="big-number">{data?.gpu_types || 0}</span>
          <span className="label">Tipos de GPU</span>
        </div>
      </div>

      <div className="availability-grid">
        {data?.gpus?.slice(0, 8).map((gpu, idx) => (
          <div key={idx} className="availability-item">
            <div className="gpu-header">
              <span className="gpu-name">{gpu.gpu_name}</span>
              {gpu.available > 0 ? (
                <CheckCircle size={16} className="available" />
              ) : (
                <XCircle size={16} className="unavailable" />
              )}
            </div>
            <div className="gpu-stats">
              <div
                className="available-count"
                style={{ color: getAvailabilityColor(gpu.available) }}
              >
                {gpu.available} disponíveis
              </div>
              <div className="price-range">
                {formatPrice(gpu.min_price)} - {formatPrice(gpu.max_price)}
              </div>
            </div>
            <div className="availability-bar">
              <div
                className="bar-fill"
                style={{
                  width: `${Math.min(gpu.available / 50 * 100, 100)}%`,
                  backgroundColor: getAvailabilityColor(gpu.available)
                }}
              />
            </div>
            {gpu.regions && (
              <div className="regions">
                {gpu.regions.slice(0, 3).map((region, i) => (
                  <span key={i} className="region-tag">{region}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="last-update">
        Atualizado: {new Date(data?.timestamp).toLocaleTimeString('pt-BR')}
      </div>
    </div>
  )
}
