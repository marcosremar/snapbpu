import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Server, Cpu, Clock, Activity, TrendingUp, BarChart3 } from 'lucide-react'

/**
 * MachinesReportPage - Relatório de Métricas de Máquinas
 * Mostra estatísticas de uso de GPUs, utilização, uptime, etc.
 */

// Dados mock para demo
const MOCK_DATA = {
  summary: {
    gpusAtivas: 4,
    gpusTotal: 6,
    usoMedioGpu: 78,
    horasUtilizadas: 1247,
    custoTotal: 156.80,
    uptimeMedio: 99.2,
  },
  gpuBreakdown: [
    { name: 'RTX 4090', count: 2, usage: 85, hours: 480, cost: 43.20 },
    { name: 'A100 80GB', count: 1, usage: 92, hours: 312, cost: 65.50 },
    { name: 'H100 80GB', count: 1, usage: 78, hours: 455, cost: 48.10 },
  ],
  usageHistory: [
    { date: '2024-01', hours: 890, cost: 112.50 },
    { date: '2024-02', hours: 1020, cost: 134.20 },
    { date: '2024-03', hours: 1247, cost: 156.80 },
  ]
}

// Componente de métrica
function MetricCard({ icon: Icon, label, value, subValue }) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <div>
          <p className="stat-card-label">{label}</p>
          <p className="stat-card-value">{value}</p>
          {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}
        </div>
        <div className="stat-card-icon stat-card-icon-primary">
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}

export default function MachinesReportPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app'
  const data = MOCK_DATA

  return (
    <div className="page-container">
      {/* Header com botão de voltar */}
      <div className="page-header">
        <button
          onClick={() => navigate(`${basePath}/metrics-hub`)}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Voltar para Relatórios</span>
        </button>

        <div className="flex items-center gap-3">
          <div className="stat-card-icon stat-card-icon-primary">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h1 className="page-title">Relatório de Máquinas</h1>
            <p className="page-subtitle">Métricas de uso e desempenho das GPUs</p>
          </div>
        </div>
      </div>

      {/* Métricas Principais */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
          icon={Server}
          label="GPUs Ativas"
          value={`${data.summary.gpusAtivas}/${data.summary.gpusTotal}`}
          subValue="Disponíveis"
        />
        <MetricCard
          icon={Activity}
          label="Uso Médio GPU"
          value={`${data.summary.usoMedioGpu}%`}
          subValue="Utilização"
        />
        <MetricCard
          icon={Clock}
          label="Horas Utilizadas"
          value={data.summary.horasUtilizadas.toLocaleString()}
          subValue="Este mês"
        />
        <MetricCard
          icon={TrendingUp}
          label="Uptime Médio"
          value={`${data.summary.uptimeMedio}%`}
          subValue="Disponibilidade"
        />
      </div>

      {/* Breakdown por GPU */}
      <div className="ta-card mb-6">
        <div className="ta-card-header">
          <h2 className="ta-card-title flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-400" />
            Uso por Tipo de GPU
          </h2>
        </div>
        <div className="ta-card-body">
          <div className="overflow-x-auto">
            <table className="ta-table">
              <thead>
                <tr>
                  <th>GPU</th>
                  <th>Quantidade</th>
                  <th>Uso Médio</th>
                  <th>Horas</th>
                  <th>Custo</th>
                </tr>
              </thead>
              <tbody>
                {data.gpuBreakdown.map((gpu, idx) => (
                  <tr key={idx}>
                    <td className="font-medium text-white">{gpu.name}</td>
                    <td>{gpu.count}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-brand-500 rounded-full"
                            style={{ width: `${gpu.usage}%` }}
                          />
                        </div>
                        <span className="text-brand-400">{gpu.usage}%</span>
                      </div>
                    </td>
                    <td>{gpu.hours}h</td>
                    <td className="text-yellow-400">${gpu.cost.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Histórico de Uso */}
      <div className="ta-card">
        <div className="ta-card-header">
          <h2 className="ta-card-title flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-brand-400" />
            Histórico de Uso
          </h2>
        </div>
        <div className="ta-card-body">
          <div className="space-y-4">
            {data.usageHistory.map((month, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5">
                <div>
                  <span className="text-white font-medium">{month.date}</span>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <span className="text-gray-400">
                    <Clock className="w-3 h-3 inline mr-1" />
                    {month.hours}h
                  </span>
                  <span className="text-yellow-400 font-medium">
                    ${month.cost.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
