import { useState, useEffect } from 'react'
import { Cpu, Zap, Award } from 'lucide-react'

const API_BASE = ''

export default function LLMGpuRanking({ getAuthHeaders }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedModel, setSelectedModel] = useState('')

  const loadData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (selectedModel) params.append('model_size', selectedModel)

      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/llm-gpus?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const result = await res.json()
        setData({
          best_gpu: result.best_value ? {
            gpu_name: result.best_value.gpu_name,
            cost_per_token: result.best_value.cost_per_million_tokens / 1000000
          } : null,
          rankings: result.items?.map(item => ({
            gpu_name: item.gpu_name,
            vram_gb: item.vram_gb,
            estimated_tokens_per_sec: item.estimated_tokens_per_second,
            cost_per_token: item.cost_per_million_tokens / 1000000,
            efficiency_score: item.efficiency_score
          })) || [],
          compatible_models: ['7B', '13B', '70B']
        })
      }
    } catch (err) {
      console.error('Erro ao carregar LLM GPU ranking:', err)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [selectedModel])

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}`

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
            <Cpu size={18} />
          </div>
          Melhor GPU para LLM ($/Token)
        </h3>
      </div>

      <div className="ta-card-body">
        {data?.compatible_models && (
          <div className="flex items-center gap-3 mb-4 p-3 bg-white/[0.03] rounded-xl border border-white/5">
            <label className="text-sm text-gray-400">Modelo LLM:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="ta-select flex-1 max-w-[300px]"
            >
              <option value="">Todos os modelos</option>
              {data.compatible_models.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>
        )}

        {data?.best_gpu && (
          <div className="spot-highlight mb-5" style={{ background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.15) 0%, rgba(161, 98, 7, 0.1) 100%)', borderColor: 'rgba(234, 179, 8, 0.3)' }}>
            <div className="flex items-center justify-center gap-3 relative z-10">
              <Award size={28} className="text-yellow-400" />
              <div className="text-left">
                <span className="block text-xs text-yellow-300/70 uppercase font-semibold">Melhor Custo-Benefício</span>
                <span className="block text-xl font-bold text-white">{data.best_gpu.gpu_name}</span>
                <span className="block text-sm text-yellow-200/60">
                  <strong className="text-yellow-300">{formatPrice(data.best_gpu.cost_per_token)}</strong>/token
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="ta-table">
            <thead>
              <tr>
                <th>#</th>
                <th>GPU</th>
                <th>VRAM</th>
                <th>Tokens/s</th>
                <th>$/1M Tokens</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {data?.rankings?.slice(0, 8).map((gpu, idx) => (
                <tr key={idx} className={`animate-fade-in ${idx === 0 ? 'bg-yellow-500/10' : ''}`} style={{ animationDelay: `${idx * 50}ms` }}>
                  <td className="text-emerald-400 font-bold">{idx + 1}</td>
                  <td>
                    <span className="gpu-badge">{gpu.gpu_name}</span>
                  </td>
                  <td className="text-gray-300">{gpu.vram_gb}GB</td>
                  <td className="text-emerald-400">{gpu.estimated_tokens_per_sec?.toFixed(0)}</td>
                  <td className="text-orange-400">
                    ${(gpu.cost_per_token * 1000000)?.toFixed(2)}
                  </td>
                  <td>
                    <span
                      className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold text-white"
                      style={{ backgroundColor: `hsl(${gpu.efficiency_score}, 70%, 45%)` }}
                    >
                      {gpu.efficiency_score?.toFixed(0)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 pt-3 border-t border-white/10 text-xs text-gray-500 flex items-center gap-1.5">
          <Zap size={14} />
          Baseado em preços Spot atuais e benchmarks de inferência LLM
        </div>
      </div>
    </div>
  )
}
