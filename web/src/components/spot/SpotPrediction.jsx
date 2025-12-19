import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Clock, Target } from 'lucide-react'
import { Line } from 'react-chartjs-2'

const API_BASE = ''

export default function SpotPrediction({ getAuthHeaders, selectedGPU = 'RTX 4090' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/prediction/${encodeURIComponent(selectedGPU)}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        // Map API response to expected format
        const hourlyPredictions = {}
        result.predictions_24h?.forEach(p => {
          hourlyPredictions[p.hour_utc] = p.predicted_price
        })
        setData({
          gpu_name: result.gpu_name,
          hourly_predictions: hourlyPredictions,
          prediction_summary: {
            predicted_min: result.predicted_lowest_price,
            predicted_max: Math.max(...(result.predictions_24h?.map(p => p.predicted_price) || [0])),
            best_hour: result.best_time_to_rent
          },
          model_confidence: result.model_confidence,
          model_version: 'v1.0'
        })
      }
    } catch (err) {
      console.error('Erro ao carregar prediction:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [selectedGPU])

  const formatPrice = (price) => `$${price?.toFixed(4) || '0.0000'}/h`
  const formatPercent = (value) => `${(value * 100)?.toFixed(0) || '0'}%`

  const getChartData = () => {
    if (!data?.hourly_predictions) return null

    const hours = Object.keys(data.hourly_predictions).map(h => `${h}:00`)
    const prices = Object.values(data.hourly_predictions)

    return {
      labels: hours,
      datasets: [{
        label: 'Preço Previsto',
        data: prices,
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
      }]
    }
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => `$${context.parsed.y?.toFixed(4)}/h`
        }
      }
    },
    scales: {
      y: {
        ticks: {
          color: '#9ca3af',
          callback: (value) => `$${value.toFixed(3)}`
        },
        grid: { color: '#30363d' }
      },
      x: {
        ticks: { color: '#9ca3af' },
        grid: { display: false }
      }
    }
  }

  if (loading) {
    return <div className="spot-card loading">Gerando previsão...</div>
  }

  const chartData = getChartData()

  return (
    <div className="spot-card spot-prediction">
      <div className="spot-card-header">
        <h3><Target size={20} /> Previsão de Preços Spot</h3>
        <span className="gpu-tag">{data?.gpu_name}</span>
      </div>

      {data?.prediction_summary && (
        <div className="prediction-summary">
          <div className="prediction-item">
            <TrendingDown size={18} className="icon low" />
            <div>
              <span className="label">Preço Mínimo Previsto</span>
              <span className="value">{formatPrice(data.prediction_summary.predicted_min)}</span>
            </div>
          </div>
          <div className="prediction-item">
            <TrendingUp size={18} className="icon high" />
            <div>
              <span className="label">Preço Máximo Previsto</span>
              <span className="value">{formatPrice(data.prediction_summary.predicted_max)}</span>
            </div>
          </div>
          <div className="prediction-item">
            <Clock size={18} className="icon best" />
            <div>
              <span className="label">Melhor Horário (UTC)</span>
              <span className="value">{data.prediction_summary.best_hour}:00</span>
            </div>
          </div>
        </div>
      )}

      {chartData && (
        <div className="prediction-chart" style={{ height: '200px' }}>
          <Line data={chartData} options={chartOptions} />
        </div>
      )}

      <div className="model-info">
        <span className="confidence">
          Confiança: {formatPercent(data?.model_confidence)}
        </span>
        <span className="model-version">
          Modelo: {data?.model_version}
        </span>
      </div>
    </div>
  )
}
