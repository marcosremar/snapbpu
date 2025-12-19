import { useState, useEffect } from 'react'
import { DollarSign, Calculator, TrendingDown } from 'lucide-react'

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
    const colors = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' }
    return colors[risk] || '#6b7280'
  }

  if (loading) {
    return <div className="spot-card loading">Calculando economia...</div>
  }

  return (
    <div className="spot-card savings-calculator">
      <div className="spot-card-header">
        <h3><Calculator size={20} /> Calculadora de Economia Spot</h3>
      </div>

      <div className="savings-summary">
        <div className="savings-big-number">
          <span className="amount">{formatPrice(data?.total_potential_savings_month || 0)}</span>
          <span className="period">economia potencial/mês</span>
        </div>
        <div className="savings-avg">
          Economia média: <strong>{formatPercent(data?.avg_savings_percent)}</strong>
        </div>
      </div>

      <div className="hours-selector">
        <label>Horas de uso por dia:</label>
        <input
          type="range"
          min="1"
          max="24"
          value={hoursPerDay}
          onChange={(e) => setHoursPerDay(parseInt(e.target.value))}
        />
        <span>{hoursPerDay}h/dia</span>
      </div>

      <div className="savings-table">
        <table>
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
                  <td className="gpu-name">{item.gpu_name}</td>
                  <td className="price spot">${item.spot_price?.toFixed(3)}/h</td>
                  <td className="price">${item.ondemand_price?.toFixed(3)}/h</td>
                  <td className="savings">
                    <DollarSign size={14} />
                    {monthlySavings.toFixed(2)}
                  </td>
                  <td>
                    <span
                      className="risk-badge"
                      style={{ backgroundColor: getRiskColor(item.reliability_risk) }}
                    >
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
  )
}
