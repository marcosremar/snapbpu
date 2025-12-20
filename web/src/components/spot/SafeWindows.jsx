import { useState, useEffect } from 'react'
import { Clock, CheckCircle } from 'lucide-react'

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
          daily_patterns: null
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
    if (confidence > 0.8) return 'bg-emerald-500'
    if (confidence > 0.5) return 'bg-yellow-500'
    return 'bg-red-500'
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
      <div className="ta-card-header flex justify-between items-center">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-primary">
            <Clock size={18} />
          </div>
          Janelas Seguras para Spot
        </h3>
        <span className="gpu-badge">{data?.gpu_name}</span>
      </div>

      <div className="ta-card-body">
        {data?.recommendation && (
          <div className="spot-highlight mb-5">
            <div className="flex items-center justify-center gap-3 relative z-10">
              <CheckCircle size={28} className="text-emerald-400" />
              <div className="text-left">
                <span className="block text-xs text-emerald-300/70 uppercase font-semibold">Melhor Horário para Alugar</span>
                <span className="block text-2xl font-bold text-white">{data.recommendation.best_hours_utc?.map(formatHour).join(', ')}</span>
                <span className="block text-sm text-emerald-200/60">
                  Confiança: <strong className="text-emerald-300">{formatPercent(data.recommendation.confidence)}</strong>
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="p-4 bg-white/[0.02] rounded-xl border border-white/5">
          <h4 className="text-sm text-gray-400 mb-3">Estabilidade por Hora (UTC)</h4>
          <div className="grid grid-cols-8 sm:grid-cols-12 gap-1.5 mb-3">
            {data?.hourly_analysis?.map((hour, idx) => (
              <div
                key={idx}
                className={`aspect-square flex items-center justify-center rounded-lg text-[10px] font-bold text-white cursor-pointer transition-all duration-200 hover:scale-125 hover:z-10 hover:shadow-lg animate-fade-in ${getHourColor(hour.stability_score)}`}
                style={{ animationDelay: `${idx * 20}ms` }}
                title={`${formatHour(hour.hour_utc)}: ${formatPercent(hour.stability_score)} estabilidade`}
              >
                {hour.hour_utc}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-3 sm:gap-4 text-xs text-gray-400 pt-3 border-t border-white/5">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/30"></span>
              Alta estabilidade
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-yellow-500 shadow-lg shadow-yellow-500/30"></span>
              Média
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-red-500 shadow-lg shadow-red-500/30"></span>
              Baixa
            </span>
          </div>
        </div>

        {data?.daily_patterns && (
          <div className="mt-5 pt-4 border-t border-white/10">
            <h4 className="text-sm text-gray-400 mb-3">Padrões por Dia da Semana</h4>
            <div className="flex justify-between items-end h-[100px]">
              {Object.entries(data.daily_patterns).map(([day, stats]) => (
                <div key={day} className="flex flex-col items-center flex-1">
                  <span className="text-[11px] text-gray-400 uppercase mb-1">{day.slice(0, 3)}</span>
                  <div className="w-full max-w-[30px] h-[60px] bg-white/10 rounded flex items-end overflow-hidden">
                    <div
                      className={`w-full rounded ${getHourColor(stats.avg_stability)}`}
                      style={{ height: `${stats.avg_stability * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-400 mt-1">{formatPercent(stats.avg_stability)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
