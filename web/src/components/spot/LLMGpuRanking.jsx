import { useState, useEffect } from 'react'
import { Cpu, Zap, DollarSign, Award } from 'lucide-react'

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
        // Map API response to expected format
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

  const formatPrice = (price) => `$${price?.toFixed(6) || '0.000000'}`

  if (loading) {
    return <div className="spot-card loading">Analisando GPUs para LLM...</div>
  }

  return (
    <div className="spot-card llm-gpu-ranking">
      <div className="spot-card-header">
        <h3><Cpu size={20} /> Melhor GPU para LLM ($/Token)</h3>
      </div>

      {data?.compatible_models && (
        <div className="model-selector">
          <label>Modelo LLM:</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            <option value="">Todos os modelos</option>
            {data.compatible_models.map(model => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>
      )}

      {data?.best_gpu && (
        <div className="best-gpu-highlight">
          <Award size={24} className="award-icon" />
          <div className="best-gpu-info">
            <span className="best-label">Melhor Custo-Benefício</span>
            <span className="best-gpu-name">{data.best_gpu.gpu_name}</span>
            <span className="best-price">{formatPrice(data.best_gpu.cost_per_token)}/token</span>
          </div>
        </div>
      )}

      <div className="gpu-rankings">
        <table>
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
              <tr key={idx} className={idx === 0 ? 'top-rank' : ''}>
                <td className="rank">{idx + 1}</td>
                <td className="gpu-name">
                  <Cpu size={14} />
                  {gpu.gpu_name}
                </td>
                <td>{gpu.vram_gb}GB</td>
                <td className="tokens">{gpu.estimated_tokens_per_sec?.toFixed(0)}</td>
                <td className="cost">
                  ${(gpu.cost_per_token * 1000000)?.toFixed(2)}
                </td>
                <td>
                  <div className="score-badge" style={{
                    backgroundColor: `hsl(${gpu.efficiency_score}, 70%, 45%)`
                  }}>
                    {gpu.efficiency_score?.toFixed(0)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="llm-info">
        <p>
          <Zap size={14} /> Baseado em preços Spot atuais e benchmarks de inferência LLM
        </p>
      </div>
    </div>
  )
}
