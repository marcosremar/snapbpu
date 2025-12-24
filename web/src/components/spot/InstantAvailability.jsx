import { useState, useEffect } from 'react'
import { Zap, CheckCircle, XCircle, RefreshCw, Cpu, Globe } from 'lucide-react'
import { Card, StatCard, Badge } from '../tailadmin-ui'

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
        const gpus = result.items?.map(item => ({
          gpu_name: item.gpu_name,
          available: item.available_now,
          min_price: item.spot_price,
          max_price: item.spot_price * 1.2,
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
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}/h`

  const getIconColor = (available) => {
    if (available > 20) return 'success'
    if (available > 5) return 'warning'
    return 'error'
  }

  if (loading && !data) {
    return (
      <Card>
        <div className="flex items-center justify-center min-h-[300px]">
          <div className="w-8 h-8 border-4 border-gray-200 border-t-brand-500 rounded-full animate-spin" />
        </div>
      </Card>
    )
  }

  return (
    <Card
      header={
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-yellow-500/10 flex items-center justify-center">
              <Zap size={20} className="text-yellow-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Disponibilidade Instantânea</h3>
              <p className="text-sm text-gray-400">GPUs Spot disponíveis agora</p>
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
      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <StatCard
          title="GPUs Disponíveis"
          value={String(data?.total_available || 0)}
          icon={Cpu}
          iconColor="success"
          subtitle="Prontas para uso"
        />
        <StatCard
          title="Tipos de GPU"
          value={String(data?.gpu_types || 0)}
          icon={Globe}
          iconColor="primary"
          subtitle="Modelos diferentes"
        />
      </div>

      {/* GPU List */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {data?.gpus?.slice(0, 6).map((gpu, idx) => (
          <StatCard
            key={idx}
            title={gpu.gpu_name}
            value={`${gpu.available} disp.`}
            icon={gpu.available > 0 ? CheckCircle : XCircle}
            iconColor={getIconColor(gpu.available)}
            subtitle={`${formatPrice(gpu.min_price)} - ${formatPrice(gpu.max_price)}`}
          />
        ))}
      </div>

      {/* Timestamp */}
      <div className="text-center text-xs text-gray-500 mt-4 pt-4 border-t border-white/10">
        Atualizado: {data?.timestamp ? new Date(data.timestamp).toLocaleTimeString('pt-BR') : '-'}
      </div>
    </Card>
  )
}
