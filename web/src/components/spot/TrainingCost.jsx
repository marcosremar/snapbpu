import { useState, useEffect } from 'react'
import { DollarSign, Clock, Cpu, Award } from 'lucide-react'

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
        // Map API response to expected format
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
    return <div className="spot-card loading">Calculando custos de treinamento...</div>
  }

  return (
    <div className="spot-card training-cost">
      <div className="spot-card-header">
        <h3><Clock size={20} /> Custo por Hora de Treinamento</h3>
      </div>

      <div className="hours-config">
        <label>Horas de Treinamento:</label>
        <div className="hours-input">
          <input
            type="number"
            min="1"
            max="1000"
            value={trainingHours}
            onChange={(e) => setTrainingHours(parseInt(e.target.value) || 1)}
          />
          <span>horas</span>
        </div>
      </div>

      {data?.best_option && (
        <div className="best-option">
          <Award size={24} className="award-icon" />
          <div className="best-info">
            <span className="best-label">Melhor Opção</span>
            <span className="best-gpu">{data.best_option.gpu_name}</span>
            <span className="best-total">
              Total: {formatPrice(data.best_option.total_cost)}
            </span>
          </div>
        </div>
      )}

      <div className="cost-comparison">
        <table>
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
              <tr key={idx} className={idx === 0 ? 'best-row' : ''}>
                <td className="gpu-name">
                  <Cpu size={14} />
                  {item.gpu_name}
                </td>
                <td className="price">${item.spot_price_per_hour?.toFixed(3)}</td>
                <td className="total-cost">{formatPrice(item.total_spot_cost)}</td>
                <td className="savings">
                  <span className="savings-amount">
                    -{formatPrice(item.savings_vs_ondemand)}
                  </span>
                  <span className="savings-percent">
                    ({item.savings_percent?.toFixed(0)}%)
                  </span>
                </td>
                <td className="tflops">{item.tflops?.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="training-tips">
        <h4>Dicas para Economia</h4>
        <ul>
          <li>Use checkpointing para salvar progresso a cada hora</li>
          <li>Prefira horários de baixa demanda (madrugada UTC)</li>
          <li>Considere GPUs menos populares para menores preços</li>
        </ul>
      </div>
    </div>
  )
}
