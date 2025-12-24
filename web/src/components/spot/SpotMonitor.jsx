import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Minus, RefreshCw, Cpu, Zap, DollarSign } from 'lucide-react'
import { Card, StatCard, Badge, StatsGrid } from '../tailadmin-ui'

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
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [])

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}/h`
  const formatPercent = (value) => `${Math.abs(value)?.toFixed(1) || '0'}%`

  if (loading && !data) {
    return (
      <Card>
        <div className="flex items-center justify-center min-h-[300px]">
          <div className="w-8 h-8 border-4 border-gray-200 border-t-brand-500 rounded-full animate-spin" />
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-500/50">
        <div className="text-red-400 text-center py-8">{error}</div>
      </Card>
    )
  }

  return (
    <Card
      header={
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center">
              <TrendingUp size={20} className="text-brand-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Monitor de Preços Spot</h3>
              <p className="text-sm text-gray-400">Preços em tempo real</p>
            </div>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors text-gray-400 hover:text-white"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      }
    >
      {/* GPU Stats - Responsive Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {data?.items?.slice(0, 6).map((item, idx) => (
          <StatCard
            key={idx}
            title={item.gpu_name}
            value={formatPrice(item.spot_price)}
            icon={Cpu}
            iconColor="success"
            subtitle={`${item.available_gpus} disponíveis • Min: ${formatPrice(item.min_price)}`}
            change={`-${formatPercent(item.savings_percent)} vs On-Demand`}
            changeType="up"
          />
        ))}
      </div>

      {/* Market Overview */}
      {data?.market_overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 pt-6 border-t border-white/10">
          <StatCard
            title="Total GPUs Spot"
            value={String(data.market_overview.total_spot_gpus || '0')}
            icon={Zap}
            iconColor="warning"
          />
          <StatCard
            title="Economia Média"
            value={`${formatPercent(data.market_overview.avg_savings_percent)}`}
            icon={DollarSign}
            iconColor="success"
            subtitle="comparado com On-Demand"
          />
        </div>
      )}
    </Card>
  )
}
