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

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}/h`
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
          label: (context) => `$${context.parsed.y?.toFixed(2)}/h`
        }
      }
    },
    scales: {
      y: {
        ticks: {
          color: '#9ca3af',
          callback: (value) => `$${value.toFixed(2)}`
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
    return (
      <div className="ta-card">
        <div className="ta-card-body flex items-center justify-center min-h-[200px]">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  const chartData = getChartData()

  return (
    <div className="ta-card hover-glow">
      <div className="ta-card-header flex justify-between items-center">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-success pulse-dot">
            <Target size={18} />
          </div>
          Previsão de Preços Spot
        </h3>
        <span className="gpu-badge">{data?.gpu_name}</span>
      </div>

      <div className="ta-card-body">
        {data?.prediction_summary && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '0ms' }}>
              <div className="stat-card-icon stat-card-icon-success">
                <TrendingDown size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Preço Mínimo</span>
                <span className="text-lg font-bold text-brand-400">{formatPrice(data.prediction_summary.predicted_min)}</span>
              </div>
            </div>
            <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '50ms' }}>
              <div className="stat-card-icon stat-card-icon-danger">
                <TrendingUp size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Preço Máximo</span>
                <span className="text-lg font-bold text-red-400">{formatPrice(data.prediction_summary.predicted_max)}</span>
              </div>
            </div>
            <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '100ms' }}>
              <div className="stat-card-icon stat-card-icon-primary">
                <Clock size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Melhor Horário</span>
                <span className="text-lg font-bold text-blue-400">{data.prediction_summary.best_hour}:00 UTC</span>
              </div>
            </div>
          </div>
        )}

        {chartData && (
          <div className="h-[200px] my-4 p-3 bg-white/[0.02] rounded-xl border border-white/5">
            <Line data={chartData} options={chartOptions} />
          </div>
        )}

        <div className="flex justify-between pt-3 border-t border-white/10 text-xs">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-500"></span>
            <span className="text-gray-400">Confiança:</span>
            <span className="text-brand-400 font-semibold">{formatPercent(data?.model_confidence)}</span>
          </span>
          <span className="text-gray-500">Modelo: {data?.model_version}</span>
        </div>
      </div>
    </div>
  )
}
