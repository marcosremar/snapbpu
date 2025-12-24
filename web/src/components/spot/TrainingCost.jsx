import { useState, useEffect } from 'react'
import { Clock, Cpu, Award } from 'lucide-react'

const API_BASE = ''

export default function TrainingCost({ getAuthHeaders }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [trainingHours, setTrainingHours] = useState(10)

  const loadData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('training_hours', trainingHours)

      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/training-cost?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        const comparisons = result.items?.map(item => ({
          gpu_name: item.gpu_name,
          spot_price_per_hour: item.spot_price,
          ondemand_price_per_hour: item.ondemand_price,
          total_spot_cost: item.spot_price * trainingHours,
          total_ondemand_cost: item.ondemand_price * trainingHours,
          savings_vs_ondemand: (item.ondemand_price - item.spot_price) * trainingHours,
          savings_percent: item.ondemand_price > 0
            ? ((item.ondemand_price - item.spot_price) / item.ondemand_price) * 100
            : 0,
          tflops: item.tflops,
          vram_gb: item.vram_gb,
          efficiency_rating: item.efficiency_rating
        })) || []

        const bestOption = result.most_cost_effective ? {
          gpu_name: result.most_cost_effective.gpu_name,
          total_cost: result.most_cost_effective.spot_price * trainingHours
        } : comparisons[0] ? {
          gpu_name: comparisons[0].gpu_name,
          total_cost: comparisons[0].total_spot_cost
        } : null

        setData({
          best_option: bestOption,
          comparisons: comparisons,
          fastest: result.fastest_training
        })
      }
    } catch (err) {
      console.error('Erro ao carregar training cost:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [trainingHours])

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}`

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
            <Clock size={18} />
          </div>
          Custo por Hora de Treinamento
        </h3>
      </div>

      <div className="ta-card-body">
        <div className="flex items-center gap-3 mb-4 p-4 bg-white/[0.03] rounded-xl border border-white/5">
          <label className="text-sm text-gray-400">Horas de Treinamento:</label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="1"
              max="1000"
              value={trainingHours}
              onChange={(e) => setTrainingHours(parseInt(e.target.value) || 1)}
              className="ta-input w-24"
            />
            <span className="text-gray-400 font-medium">horas</span>
          </div>
        </div>

        {data?.best_option && (
          <div className="spot-highlight mb-5">
            <div className="flex items-center justify-center gap-3 relative z-10">
              <Award size={28} className="text-brand-400" />
              <div className="text-left">
                <span className="block text-xs text-brand-300/70 uppercase font-semibold">Melhor Opção</span>
                <span className="block text-xl font-bold text-white">{data.best_option.gpu_name}</span>
                <span className="block text-sm text-brand-200/60">
                  Total: <strong className="text-brand-300">{formatPrice(data.best_option.total_cost)}</strong> para {trainingHours}h
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="ta-table">
            <thead>
              <tr>
                <th>GPU</th>
                <th>Spot/h</th>
                <th>Total ({trainingHours}h)</th>
                <th>vs On-Demand</th>
                <th>TFLOPS</th>
              </tr>
            </thead>
            <tbody>
              {data?.comparisons?.slice(0, 8).map((item, idx) => (
                <tr key={idx} className={`animate-fade-in ${idx === 0 ? 'bg-brand-500/10' : ''}`} style={{ animationDelay: `${idx * 50}ms` }}>
                  <td>
                    <span className="gpu-badge">{item.gpu_name}</span>
                  </td>
                  <td className="text-gray-300">${item.spot_price_per_hour?.toFixed(2)}</td>
                  <td className="font-bold text-white">{formatPrice(item.total_spot_cost)}</td>
                  <td className="text-brand-400">
                    <span className="font-semibold">-{formatPrice(item.savings_vs_ondemand)}</span>
                    <span className="text-xs opacity-80 ml-1">({item.savings_percent?.toFixed(0)}%)</span>
                  </td>
                  <td className="text-gray-300">{item.tflops?.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 p-4 bg-gradient-to-r from-brand-500/10 to-teal-500/10 border border-brand-500/20 rounded-xl">
          <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Cpu size={16} className="text-brand-400" />
            Dicas para Economia
          </h4>
          <ul className="text-xs text-gray-300 space-y-2 pl-5 list-disc marker:text-brand-400">
            <li>Use checkpointing para salvar progresso a cada hora</li>
            <li>Prefira horários de baixa demanda (madrugada UTC)</li>
            <li>Considere GPUs menos populares para menores preços</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
