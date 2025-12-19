import { useState, useEffect } from 'react'
import { Clock, CheckCircle, AlertCircle } from 'lucide-react'

const API_BASE = ''

export default function SafeWindows({ getAuthHeaders, selectedGPU = 'RTX 4090' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/safe-windows/${encodeURIComponent(selectedGPU)}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        // Map API response to expected format
        const hourlyAnalysis = []
        for (let h = 0; h < 24; h++) {
          const window = result.windows?.find(w => w.hour_utc === h)
          hourlyAnalysis.push({
            hour_utc: h,
            stability_score: window ? 1 - window.avg_interruption_rate : 0.5,
            is_safe: window?.recommendation === 'recommended'
          })
        }
        setData({
          gpu_name: result.gpu_name,
          recommendation: result.best_window ? {
            best_hours_utc: [result.best_window.hour_utc],
            confidence: 1 - (result.best_window.avg_interruption_rate || 0.1)
          } : null,
          hourly_analysis: hourlyAnalysis,
          daily_patterns: null  // API doesn't return daily patterns yet
        })
      }
    } catch (err) {
      console.error('Erro ao carregar safe windows:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [selectedGPU])

  const formatHour = (hour) => `${hour.toString().padStart(2, '0')}:00`
  const formatPercent = (value) => `${(value * 100)?.toFixed(0) || '0'}%`

  const getHourColor = (confidence) => {
    if (confidence > 0.8) return '#22c55e'
    if (confidence > 0.5) return '#f59e0b'
    return '#ef4444'
  }

  if (loading) {
    return <div className="spot-card loading">Analisando janelas seguras...</div>
  }

  return (
    <div className="spot-card safe-windows">
      <div className="spot-card-header">
        <h3><Clock size={20} /> Janelas Seguras para Spot</h3>
        <span className="gpu-tag">{data?.gpu_name}</span>
      </div>

      {data?.recommendation && (
        <div className="recommendation-box">
          <CheckCircle size={20} className="icon" />
          <div className="recommendation-text">
            <strong>Melhor Horário:</strong> {data.recommendation.best_hours_utc?.map(formatHour).join(', ')}
            <br />
            <span className="confidence">
              Confiança: {formatPercent(data.recommendation.confidence)}
            </span>
          </div>
        </div>
      )}

      <div className="hours-grid">
        <h4>Estabilidade por Hora (UTC)</h4>
        <div className="hour-blocks">
          {data?.hourly_analysis?.map((hour, idx) => (
            <div
              key={idx}
              className={`hour-block ${hour.is_safe ? 'safe' : 'risky'}`}
              style={{ backgroundColor: getHourColor(hour.stability_score) }}
              title={`${formatHour(hour.hour_utc)}: ${formatPercent(hour.stability_score)} estabilidade`}
            >
              <span className="hour-label">{hour.hour_utc}</span>
            </div>
          ))}
        </div>
        <div className="legend">
          <span className="legend-item safe">Alta estabilidade</span>
          <span className="legend-item medium">Média</span>
          <span className="legend-item risky">Baixa</span>
        </div>
      </div>

      {data?.daily_patterns && (
        <div className="daily-patterns">
          <h4>Padrões por Dia da Semana</h4>
          <div className="day-bars">
            {Object.entries(data.daily_patterns).map(([day, stats]) => (
              <div key={day} className="day-bar">
                <span className="day-name">{day.slice(0, 3)}</span>
                <div className="bar-container">
                  <div
                    className="bar-fill"
                    style={{
                      height: `${stats.avg_stability * 100}%`,
                      backgroundColor: getHourColor(stats.avg_stability)
                    }}
                  />
                </div>
                <span className="day-value">{formatPercent(stats.avg_stability)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
