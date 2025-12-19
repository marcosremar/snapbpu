import { useNavigate } from 'react-router-dom'
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

const metricsCategories = [
  {
    title: 'Visão Geral',
    description: 'Métricas gerais do mercado de GPUs',
    items: [
      {
        id: 'market',
        icon: BarChart3,
        title: 'Mercado de GPUs',
        description: 'Histórico de preços, tendências e comparação entre tipos de máquinas (On-Demand, Spot, Bid)',
        color: '#3b82f6',
        link: '/metrics?tab=market'
      },
      {
        id: 'providers',
        icon: Shield,
        title: 'Ranking de Provedores',
        description: 'Classificação de provedores por confiabilidade, disponibilidade e estabilidade de preços',
        color: '#8b5cf6',
        link: '/metrics?tab=providers'
      },
      {
        id: 'efficiency',
        icon: Zap,
        title: 'Eficiência de Custo',
        description: 'Rankings de custo-benefício considerando $/TFLOPS, $/VRAM e performance',
        color: '#f59e0b',
        link: '/metrics?tab=efficiency'
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
        color: '#22c55e',
        link: '/metrics?tab=spot&report=monitor'
      },
      {
        id: 'savings',
        icon: DollarSign,
        title: 'Calculadora de Economia',
        description: 'Calcule quanto você pode economizar usando Spot ao invés de On-Demand por GPU',
        color: '#10b981',
        link: '/metrics?tab=spot&report=savings'
      },
      {
        id: 'availability',
        icon: Activity,
        title: 'Disponibilidade Instantânea',
        description: 'Visualize quais GPUs estão disponíveis agora no mercado Spot com preços atuais',
        color: '#06b6d4',
        link: '/metrics?tab=spot&report=availability'
      },
      {
        id: 'prediction',
        icon: Target,
        title: 'Previsão de Preços',
        description: 'Previsões de preço por hora e dia da semana usando Machine Learning para encontrar o melhor momento',
        color: '#6366f1',
        link: '/metrics?tab=spot&report=prediction'
      },
      {
        id: 'safe-windows',
        icon: Clock,
        title: 'Janelas Seguras',
        description: 'Identifique os horários com menor risco de interrupção para rodar workloads Spot',
        color: '#0ea5e9',
        link: '/metrics?tab=spot&report=safe-windows'
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
        color: '#14b8a6',
        link: '/metrics?tab=spot&report=reliability'
      },
      {
        id: 'interruption',
        icon: AlertTriangle,
        title: 'Taxa de Interrupção',
        description: 'Histórico de interrupções por provedor para escolher os mais estáveis para Spot',
        color: '#f97316',
        link: '/metrics?tab=spot&report=interruption'
      },
      {
        id: 'llm',
        icon: Cpu,
        title: 'Melhor GPU para LLM',
        description: 'Ranking de GPUs por $/token para inferência de modelos como Llama, Mistral e outros',
        color: '#ec4899',
        link: '/metrics?tab=spot&report=llm'
      },
      {
        id: 'training',
        icon: PieChart,
        title: 'Custo por Treinamento',
        description: 'Estime o custo total de treinamento por horas, comparando Spot vs On-Demand',
        color: '#a855f7',
        link: '/metrics?tab=spot&report=training'
      },
      {
        id: 'fleet',
        icon: Server,
        title: 'Estratégia de Fleet',
        description: 'Recomendações de composição de fleet Spot com diversificação e análise de risco',
        color: '#64748b',
        link: '/metrics?tab=spot&report=fleet'
      }
    ]
  }
]

export default function MetricsHub() {
  const navigate = useNavigate()

  return (
    <div className="metrics-hub">
      <div className="metrics-hub-header">
        <h1>
          <BarChart3 size={32} />
          Central de Métricas
        </h1>
        <p>Explore relatórios detalhados do mercado de GPUs VAST.ai para tomar decisões inteligentes</p>
      </div>

      <div className="metrics-hub-content">
        {metricsCategories.map((category, catIdx) => (
          <div key={catIdx} className="metrics-category">
            <div className="category-header">
              <h2>{category.title}</h2>
              <p>{category.description}</p>
            </div>

            <div className="metrics-cards-grid">
              {category.items.map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.id}
                    className="metric-card"
                    onClick={() => navigate(item.link)}
                    style={{ '--accent-color': item.color }}
                  >
                    <div className="metric-card-icon" style={{ backgroundColor: `${item.color}20` }}>
                      <Icon size={24} style={{ color: item.color }} />
                    </div>
                    <div className="metric-card-content">
                      <h3>{item.title}</h3>
                      <p>{item.description}</p>
                    </div>
                    <div className="metric-card-arrow">
                      <ArrowRight size={20} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="metrics-hub-footer">
        <div className="quick-stats">
          <div className="quick-stat">
            <Sparkles size={20} />
            <span>10 Relatórios Spot disponíveis</span>
          </div>
          <div className="quick-stat">
            <Activity size={20} />
            <span>Dados atualizados em tempo real</span>
          </div>
        </div>
      </div>
    </div>
  )
}
