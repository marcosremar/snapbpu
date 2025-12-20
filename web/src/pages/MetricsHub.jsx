import { useNavigate, useLocation } from 'react-router-dom'
import {
  BarChart3,
  Sparkles,
  TrendingUp,
  Shield,
  Zap,
  DollarSign,
  Clock,
  Cpu,
  Server,
  AlertTriangle,
  Target,
  Activity,
  PieChart,
  ArrowRight
} from 'lucide-react'

// Helper to get the base path (demo-app or app)
const getBasePath = (pathname) => {
  if (pathname.startsWith('/demo-app')) return '/demo-app'
  return '/app'
}

const getMetricsCategories = (basePath) => [
  {
    title: 'Visão Geral',
    description: 'Métricas gerais do mercado de GPUs',
    items: [
      {
        id: 'market',
        icon: BarChart3,
        title: 'Mercado de GPUs',
        description: 'Histórico de preços, tendências e comparação entre tipos de máquinas (On-Demand, Spot, Bid)',
        color: 'brand',
        link: `${basePath}/metrics?tab=market`
      },
      {
        id: 'providers',
        icon: Shield,
        title: 'Ranking de Provedores',
        description: 'Classificação de provedores por confiabilidade, disponibilidade e estabilidade de preços',
        color: 'primary',
        link: `${basePath}/metrics?tab=providers`
      },
      {
        id: 'efficiency',
        icon: Zap,
        title: 'Eficiência de Custo',
        description: 'Rankings de custo-benefício considerando $/TFLOPS, $/VRAM e performance',
        color: 'warning',
        link: `${basePath}/metrics?tab=efficiency`
      }
    ]
  },
  {
    title: 'Relatórios Spot',
    description: 'Maximize suas economias com instâncias Spot',
    items: [
      {
        id: 'spot-monitor',
        icon: TrendingUp,
        title: 'Monitor de Preços Spot',
        description: 'Acompanhamento em tempo real dos preços Spot com tendências e comparação vs On-Demand',
        color: 'success',
        link: `${basePath}/metrics?tab=spot&report=monitor`
      },
      {
        id: 'savings',
        icon: DollarSign,
        title: 'Calculadora de Economia',
        description: 'Calcule quanto você pode economizar usando Spot ao invés de On-Demand por GPU',
        color: 'success',
        link: `${basePath}/metrics?tab=spot&report=savings`
      },
      {
        id: 'availability',
        icon: Activity,
        title: 'Disponibilidade Instantânea',
        description: 'Visualize quais GPUs estão disponíveis agora no mercado Spot com preços atuais',
        color: 'primary',
        link: `${basePath}/metrics?tab=spot&report=availability`
      },
      {
        id: 'prediction',
        icon: Target,
        title: 'Previsão de Preços',
        description: 'Previsões de preço por hora e dia da semana usando Machine Learning para encontrar o melhor momento',
        color: 'primary',
        link: `${basePath}/metrics?tab=spot&report=prediction`
      },
      {
        id: 'safe-windows',
        icon: Clock,
        title: 'Janelas Seguras',
        description: 'Identifique os horários com menor risco de interrupção para rodar workloads Spot',
        color: 'brand',
        link: `${basePath}/metrics?tab=spot&report=safe-windows`
      }
    ]
  },
  {
    title: 'Confiabilidade & Performance',
    description: 'Análise de provedores e otimização para LLM',
    items: [
      {
        id: 'reliability',
        icon: Shield,
        title: 'Score de Confiabilidade',
        description: 'Avaliação detalhada de provedores com scores de disponibilidade, estabilidade e verificação',
        color: 'success',
        link: `${basePath}/metrics?tab=spot&report=reliability`
      },
      {
        id: 'interruption',
        icon: AlertTriangle,
        title: 'Taxa de Interrupção',
        description: 'Histórico de interrupções por provedor para escolher os mais estáveis para Spot',
        color: 'warning',
        link: `${basePath}/metrics?tab=spot&report=interruption`
      },
      {
        id: 'llm',
        icon: Cpu,
        title: 'Melhor GPU para LLM',
        description: 'Ranking de GPUs por $/token para inferência de modelos como Llama, Mistral e outros',
        color: 'error',
        link: `${basePath}/metrics?tab=spot&report=llm`
      },
      {
        id: 'training',
        icon: PieChart,
        title: 'Custo por Treinamento',
        description: 'Estime o custo total de treinamento por horas, comparando Spot vs On-Demand',
        color: 'primary',
        link: `${basePath}/metrics?tab=spot&report=training`
      },
      {
        id: 'fleet',
        icon: Server,
        title: 'Estratégia de Fleet',
        description: 'Recomendações de composição de fleet Spot com diversificação e análise de risco',
        color: 'gray',
        link: `${basePath}/metrics?tab=spot&report=fleet`
      }
    ]
  },
  {
    title: 'CPU Failover & Backup',
    description: 'Monitoramento e relatórios do sistema de failover automático',
    items: [
      {
        id: 'failover-report',
        icon: Shield,
        title: 'Relatório de Failover',
        description: 'Histórico completo de failovers: taxa de sucesso, MTTR, latências e detalhes de cada recuperação',
        color: 'error',
        link: `${basePath}/failover-report`
      },
      {
        id: 'cpu-standby',
        icon: Cpu,
        title: 'CPU Standby Status',
        description: 'Status das máquinas CPU backup: sincronização, custos e prontidão para failover',
        color: 'brand',
        link: `${basePath}/machines`
      },
      {
        id: 'failover-config',
        icon: Zap,
        title: 'Configurar Failover',
        description: 'Configure auto-failover, auto-recovery e políticas de backup para suas máquinas GPU',
        color: 'warning',
        link: `${basePath}/failover-report`
      }
    ]
  }
]

const getIconColorClass = (color) => {
  switch (color) {
    case 'brand': return 'stat-card-icon-primary'
    case 'primary': return 'stat-card-icon-primary'
    case 'success': return 'stat-card-icon-success'
    case 'warning': return 'stat-card-icon-warning'
    case 'error': return 'stat-card-icon-error'
    default: return 'bg-white/10 text-gray-400'
  }
}

export default function MetricsHub() {
  const navigate = useNavigate()
  const location = useLocation()
  const basePath = getBasePath(location.pathname)
  const metricsCategories = getMetricsCategories(basePath)

  return (
    <div className="page-container">
      {/* Page Header - TailAdmin Style */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <div className="stat-card-icon stat-card-icon-primary">
                <BarChart3 className="w-5 h-5" />
              </div>
              Central de Métricas
            </h1>
            <p className="page-subtitle">Explore relatórios detalhados do mercado de GPUs VAST.ai para tomar decisões inteligentes</p>
          </div>
        </div>
      </div>

      {/* Metrics Categories */}
      <div className="space-y-8">
        {metricsCategories.map((category, catIdx) => (
          <div key={catIdx} className="ta-card">
            <div className="ta-card-header">
              <h2 className="ta-card-title">{category.title}</h2>
              <p className="ta-card-subtitle">{category.description}</p>
            </div>

            <div className="ta-card-body">
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {category.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <div
                      key={item.id}
                      onClick={() => navigate(item.link)}
                      className="group p-4 rounded-xl border border-white/10 bg-white/5 hover:border-emerald-500/50 hover:shadow-lg transition-all cursor-pointer"
                    >
                      <div className="flex items-start gap-4">
                        <div className={`stat-card-icon ${getIconColorClass(item.color)} flex-shrink-0`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-semibold text-white mb-1 group-hover:text-emerald-400 transition-colors">
                            {item.title}
                          </h3>
                          <p className="text-xs text-gray-400 line-clamp-2">
                            {item.description}
                          </p>
                        </div>
                        <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-emerald-500 group-hover:translate-x-1 transition-all flex-shrink-0" />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Stats */}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-sm text-gray-400">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-500" />
          <span>10 Relatórios Spot disponíveis</span>
        </div>
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-success-500" />
          <span>Dados atualizados em tempo real</span>
        </div>
      </div>
    </div>
  )
}
