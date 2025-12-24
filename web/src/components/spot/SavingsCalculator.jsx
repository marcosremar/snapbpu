import { useState, useEffect } from 'react'
import { DollarSign, Calculator } from 'lucide-react'

const API_BASE = ''

export default function SavingsCalculator({ getAuthHeaders, selectedGPU = 'all' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hoursPerDay, setHoursPerDay] = useState(8)

  const loadData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (selectedGPU !== 'all') params.append('gpu_name', selectedGPU)

      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/savings?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        setData(result)
      }
    } catch (err) {
      console.error('Erro ao carregar savings:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [selectedGPU])

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}`
  const formatPercent = (value) => `${value?.toFixed(1) || '0'}%`

  const getRiskColor = (risk) => {
    const colors = { low: 'bg-brand-500', medium: 'bg-yellow-500', high: 'bg-red-500' }
    return colors[risk] || 'bg-gray-500'
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
      <div className="ta-card-header">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-success">
            <Calculator size={18} />
          </div>
          Calculadora de Economia Spot
        </h3>
      </div>

      <div className="ta-card-body">
        <div className="spot-highlight mb-5">
          <div className="spot-highlight-value">
            {formatPrice(data?.total_potential_savings_month || 0)}
          </div>
          <div className="spot-highlight-label">economia potencial/mês</div>
          <div className="text-sm text-brand-300/70 mt-2 relative z-10">
            Economia média: <strong className="text-brand-300">{formatPercent(data?.avg_savings_percent)}</strong>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-4 p-3 bg-white/5 rounded-xl">
          <label className="text-sm text-gray-400">Horas de uso por dia:</label>
          <input
            type="range"
            min="1"
            max="24"
            value={hoursPerDay}
            onChange={(e) => setHoursPerDay(parseInt(e.target.value))}
            className="flex-1 accent-brand-500"
          />
          <span className="text-white font-semibold min-w-[60px]">{hoursPerDay}h/dia</span>
        </div>

        <div className="overflow-x-auto">
          <table className="ta-table">
            <thead>
              <tr>
                <th>GPU</th>
                <th>Spot</th>
                <th>On-Demand</th>
                <th>Economia/Mês</th>
                <th>Risco</th>
              </tr>
            </thead>
            <tbody>
              {data?.items?.slice(0, 6).map((item, idx) => {
                const monthlySavings = item.savings_per_hour * hoursPerDay * 30
                return (
                  <tr key={idx}>
                    <td className="font-semibold text-white">{item.gpu_name}</td>
                    <td className="text-brand-400">${item.spot_price?.toFixed(2)}/h</td>
                    <td className="text-gray-300">${item.ondemand_price?.toFixed(2)}/h</td>
                    <td className="text-brand-400 flex items-center gap-1">
                      <DollarSign size={14} />
                      {monthlySavings.toFixed(2)}
                    </td>
                    <td>
                      <span className={`ta-badge ${getRiskColor(item.reliability_risk)} text-white`}>
                        {item.reliability_risk}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
