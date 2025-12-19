import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Zap, Cloud, DollarSign, Shield, Clock, Cpu, Globe, 
  ChevronRight, Check, Play, ArrowRight, Sparkles, 
  Server, Smartphone, Code, TrendingUp, PiggyBank,
  Lock, Rocket, BarChart3, Users, Star, Calculator
} from 'lucide-react'

// Componente de comparação de preços em tempo real
const PriceComparison = () => {
  const [selectedGPU, setSelectedGPU] = useState('RTX 4090')
  const [hoursPerMonth, setHoursPerMonth] = useState(160)
  
  const gpuData = {
    'RTX 4090': {
      dumont: 0.44,
      aws: 4.10,      // p4d.24xlarge equivalent hourly
      gcp: 3.67,      // a2-highgpu-1g equivalent
      azure: 3.95     // NC24ads A100 v4 equivalent
    },
    'A100 80GB': {
      dumont: 1.89,
      aws: 32.77,     // p4d.24xlarge
      gcp: 29.13,     // a2-ultragpu-1g
      azure: 27.20    // ND96asr A100 v4
    },
    'H100': {
      dumont: 2.49,
      aws: 65.00,     // p5.48xlarge estimate
      gcp: 52.00,     // a3-highgpu-8g
      azure: 48.00    // ND H100 v5
    },
    'RTX 3090': {
      dumont: 0.25,
      aws: 2.10,
      gcp: 1.89,
      azure: 2.05
    }
  }

  const gpu = gpuData[selectedGPU]
  const monthlySavingsAWS = (gpu.aws - gpu.dumont) * hoursPerMonth
  const monthlySavingsGCP = (gpu.gcp - gpu.dumont) * hoursPerMonth
  const monthlySavingsAzure = (gpu.azure - gpu.dumont) * hoursPerMonth
  const avgSavings = ((monthlySavingsAWS + monthlySavingsGCP + monthlySavingsAzure) / 3)
  const percentSavingsAWS = ((gpu.aws - gpu.dumont) / gpu.aws * 100)
  const percentSavingsGCP = ((gpu.gcp - gpu.dumont) / gpu.gcp * 100)
  const percentSavingsAzure = ((gpu.azure - gpu.dumont) / gpu.azure * 100)

  return (
    <div className="price-comparison-card">
      <div className="comparison-header">
        <Calculator size={24} />
        <h3>Calculadora de Economia</h3>
        <p>Compare quanto você economiza vs. big cloud providers</p>
      </div>

      <div className="comparison-controls">
        <div className="control-group">
          <label>Selecione a GPU</label>
          <select value={selectedGPU} onChange={(e) => setSelectedGPU(e.target.value)}>
            {Object.keys(gpuData).map(gpu => (
              <option key={gpu} value={gpu}>{gpu}</option>
            ))}
          </select>
        </div>
        <div className="control-group">
          <label>Horas por mês: {hoursPerMonth}h</label>
          <input 
            type="range" 
            min="40" 
            max="720" 
            step="40"
            value={hoursPerMonth} 
            onChange={(e) => setHoursPerMonth(parseInt(e.target.value))}
          />
        </div>
      </div>

      <div className="comparison-table">
        <div className="comparison-row header">
          <div className="provider">Provider</div>
          <div className="price">Preço/hora</div>
          <div className="monthly">Custo/mês</div>
          <div className="savings">Economia</div>
        </div>
        
        <div className="comparison-row dumont highlight">
          <div className="provider">
            <Cloud size={18} />
            <span>Dumont Cloud</span>
            <span className="badge">VOCÊ</span>
          </div>
          <div className="price">${gpu.dumont.toFixed(2)}</div>
          <div className="monthly">${(gpu.dumont * hoursPerMonth).toFixed(0)}</div>
          <div className="savings reference">—</div>
        </div>

        <div className="comparison-row aws">
          <div className="provider">
            <img src="https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg" alt="AWS" className="cloud-logo" />
            <span>Amazon AWS</span>
          </div>
          <div className="price">${gpu.aws.toFixed(2)}</div>
          <div className="monthly">${(gpu.aws * hoursPerMonth).toFixed(0)}</div>
          <div className="savings positive">
            <TrendingUp size={14} />
            ${monthlySavingsAWS.toFixed(0)} ({percentSavingsAWS.toFixed(0)}%)
          </div>
        </div>

        <div className="comparison-row gcp">
          <div className="provider">
            <img src="https://www.gstatic.com/devrel-devsite/prod/v0e0f589edd85502a40d78d7d0825db8ea5ef3b99b39e0b21d87f7c0b76f7b3b0/cloud/images/favicons/onecloud/super_cloud.png" alt="GCP" className="cloud-logo" />
            <span>Google Cloud</span>
          </div>
          <div className="price">${gpu.gcp.toFixed(2)}</div>
          <div className="monthly">${(gpu.gcp * hoursPerMonth).toFixed(0)}</div>
          <div className="savings positive">
            <TrendingUp size={14} />
            ${monthlySavingsGCP.toFixed(0)} ({percentSavingsGCP.toFixed(0)}%)
          </div>
        </div>

        <div className="comparison-row azure">
          <div className="provider">
            <img src="https://upload.wikimedia.org/wikipedia/commons/f/fa/Microsoft_Azure.svg" alt="Azure" className="cloud-logo" />
            <span>Microsoft Azure</span>
          </div>
          <div className="price">${gpu.azure.toFixed(2)}</div>
          <div className="monthly">${(gpu.azure * hoursPerMonth).toFixed(0)}</div>
          <div className="savings positive">
            <TrendingUp size={14} />
            ${monthlySavingsAzure.toFixed(0)} ({percentSavingsAzure.toFixed(0)}%)
          </div>
        </div>
      </div>

      <div className="total-savings">
        <div className="savings-amount">
          <PiggyBank size={32} />
          <div>
            <span className="label">Economia média mensal</span>
            <span className="value">${avgSavings.toFixed(0)}</span>
          </div>
        </div>
        <div className="annual-projection">
          <span className="label">Projeção anual</span>
          <span className="value annual">${(avgSavings * 12).toFixed(0)}</span>
        </div>
      </div>
    </div>
  )
}

// Feature Card Component
const FeatureCard = ({ icon: Icon, title, description, highlight }) => (
  <div className={`feature-card ${highlight ? 'highlight' : ''}`}>
    <div className="feature-icon">
      <Icon size={28} />
    </div>
    <h3>{title}</h3>
    <p>{description}</p>
  </div>
)

// Pricing Card Component
const PricingCard = ({ tier, price, description, features, popular, cta }) => (
  <div className={`pricing-card ${popular ? 'popular' : ''}`}>
    {popular && <div className="popular-badge">Mais Popular</div>}
    <div className="pricing-header">
      <h3>{tier}</h3>
      <div className="price">
        {price === 'custom' ? (
          <span className="custom">Sob consulta</span>
        ) : (
          <>
            <span className="currency">$</span>
            <span className="amount">{price}</span>
            <span className="period">/hora</span>
          </>
        )}
      </div>
      <p className="description">{description}</p>
    </div>
    <ul className="pricing-features">
      {features.map((feature, i) => (
        <li key={i}>
          <Check size={16} />
          <span>{feature}</span>
        </li>
      ))}
    </ul>
    <button className={`pricing-cta ${popular ? 'primary' : 'secondary'}`}>
      {cta}
    </button>
  </div>
)

// Main Landing Page Component
export default function LandingPage({ onLogin }) {
  const navigate = useNavigate()
  const [isScrolled, setIsScrolled] = useState(false)
  const [showLogin, setShowLogin] = useState(false)
  const [animatedStats, setAnimatedStats] = useState({
    savings: 0,
    uptime: 0,
    gpus: 0
  })

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Animate stats on mount
  useEffect(() => {
    const duration = 2000
    const steps = 60
    const increment = duration / steps
    
    let current = 0
    const interval = setInterval(() => {
      current++
      setAnimatedStats({
        savings: Math.min(Math.round((current / steps) * 89), 89),
        uptime: Math.min(99.9 * (current / steps), 99.9),
        gpus: Math.min(Math.round((current / steps) * 50), 50)
      })
      if (current >= steps) clearInterval(interval)
    }, increment)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className={`landing-nav ${isScrolled ? 'scrolled' : ''}`}>
        <div className="nav-container">
          <div className="nav-brand">
            <Cloud size={32} className="brand-icon" />
            <span>Dumont Cloud</span>
          </div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#pricing">Preços</a>
            <a href="#calculator">Calculadora</a>
          </div>
          <div className="nav-actions">
            <button className="nav-login" onClick={() => setShowLogin(true)}>
              Login
            </button>
            <button className="nav-cta" onClick={() => setShowLogin(true)}>
              Começar Grátis
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-bg">
          <div className="hero-gradient" />
          <div className="hero-grid" />
        </div>
        
        <div className="hero-content">
          <div className="hero-badge">
            <Sparkles size={14} />
            <span>Economize até 89% em GPU Cloud</span>
          </div>
          
          <h1>
            Desenvolvimento com GPU
            <span className="gradient-text"> até 10x mais barato</span>
            que AWS, GCP e Azure
          </h1>
          
          <p className="hero-description">
            Acesse GPUs de alta performance de qualquer lugar. 
            Deploy em segundos, pague apenas pelo que usar. 
            Com IA integrada para escolher a melhor máquina para seu workload.
          </p>

          <div className="hero-stats">
            <div className="stat">
              <span className="stat-value">{animatedStats.savings}%</span>
              <span className="stat-label">Economia média</span>
            </div>
            <div className="stat">
              <span className="stat-value">{animatedStats.uptime.toFixed(1)}%</span>
              <span className="stat-label">Uptime</span>
            </div>
            <div className="stat">
              <span className="stat-value">{animatedStats.gpus}+</span>
              <span className="stat-label">Modelos de GPU</span>
            </div>
          </div>

          <div className="hero-ctas">
            <button className="cta-primary" onClick={() => setShowLogin(true)}>
              <Rocket size={18} />
              Começar 7 Dias Grátis
            </button>
            <button className="cta-secondary">
              <Play size={18} />
              Ver Demo
            </button>
          </div>

          <div className="hero-trust">
            <span>Confiado por desenvolvedores de:</span>
            <div className="trust-logos">
              <span className="trust-item">Startups AI</span>
              <span className="trust-item">Pesquisadores ML</span>
              <span className="trust-item">Empresas</span>
            </div>
          </div>
        </div>

        <div className="hero-visual">
          <div className="dashboard-preview">
            <div className="preview-header">
              <div className="preview-dots">
                <span /><span /><span />
              </div>
              <span className="preview-title">Dumont Cloud Dashboard</span>
            </div>
            <div className="preview-content">
              <div className="preview-sidebar">
                <div className="preview-menu-item active">
                  <Server size={14} /> Deploy
                </div>
                <div className="preview-menu-item">
                  <BarChart3 size={14} /> Métricas
                </div>
                <div className="preview-menu-item">
                  <DollarSign size={14} /> Economia
                </div>
              </div>
              <div className="preview-main">
                <div className="preview-gpu-card">
                  <div className="gpu-info">
                    <Cpu size={20} />
                    <span>RTX 4090</span>
                  </div>
                  <div className="gpu-price">$0.44/h</div>
                  <div className="gpu-savings">-89% vs AWS</div>
                </div>
                <div className="preview-gpu-card">
                  <div className="gpu-info">
                    <Cpu size={20} />
                    <span>A100 80GB</span>
                  </div>
                  <div className="gpu-price">$1.89/h</div>
                  <div className="gpu-savings">-94% vs GCP</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pain Points Section */}
      <section className="pain-section">
        <div className="pain-container">
          <h2>Por que desenvolvedores estão migrando para Dumont Cloud?</h2>
          <div className="pain-grid">
            <div className="pain-item crossed">
              <span className="pain-icon">💸</span>
              <span className="pain-text">Custos exorbitantes com AWS/GCP</span>
            </div>
            <div className="pain-item crossed">
              <span className="pain-icon">⏰</span>
              <span className="pain-text">Setup complexo que demora horas</span>
            </div>
            <div className="pain-item crossed">
              <span className="pain-icon">🔒</span>
              <span className="pain-text">Lock-in com grandes provedores</span>
            </div>
            <div className="pain-item crossed">
              <span className="pain-icon">📱</span>
              <span className="pain-text">Sem acesso mobile ao ambiente</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <div className="section-header">
          <span className="section-badge">Core Features</span>
          <h2>Tudo que você precisa para desenvolver com GPU</h2>
          <p>Focamos em 4 funcionalidades principais que fazem toda a diferença</p>
        </div>

        <div className="features-grid">
          <FeatureCard 
            icon={DollarSign}
            title="Economia Real"
            description="Comparamos preços em tempo real com AWS, GCP e Azure. Economize até 89% automaticamente."
            highlight
          />
          <FeatureCard 
            icon={Smartphone}
            title="Acesso de Qualquer Lugar"
            description="Desenvolva do celular, tablet ou qualquer computador. VS Code integrado no browser."
          />
          <FeatureCard 
            icon={Sparkles}
            title="IA para Escolher GPU"
            description="Descreva seu projeto e nossa IA recomenda a GPU ideal para seu workload e orçamento."
          />
          <FeatureCard 
            icon={Zap}
            title="Auto-Hibernação Inteligente"
            description="Economize automaticamente. Máquinas hibernam quando ociosas e acordam quando você precisa."
          />
        </div>

        <div className="features-extra">
          <div className="extra-item">
            <Check size={18} />
            <span>Snapshots instantâneos</span>
          </div>
          <div className="extra-item">
            <Check size={18} />
            <span>Multi-região global</span>
          </div>
          <div className="extra-item">
            <Check size={18} />
            <span>SSH e VS Code integrado</span>
          </div>
          <div className="extra-item">
            <Check size={18} />
            <span>Suporte 24/7</span>
          </div>
        </div>
      </section>

      {/* Calculator Section */}
      <section id="calculator" className="calculator-section">
        <div className="section-header">
          <span className="section-badge">Calculadora</span>
          <h2>Veja quanto você pode economizar</h2>
          <p>Compare preços reais com os principais cloud providers</p>
        </div>
        <PriceComparison />
      </section>

      {/* AI Feature Section */}
      <section className="ai-section">
        <div className="ai-container">
          <div className="ai-content">
            <span className="section-badge purple">Powered by AI</span>
            <h2>Deixe a IA escolher a melhor GPU para você</h2>
            <p>
              Descreva seu projeto em linguagem natural e nossa IA analisa 
              seu workload, compara preços e recomenda a configuração ideal.
            </p>
            <ul className="ai-features">
              <li>
                <Sparkles size={18} />
                <span>Análise de workload em tempo real</span>
              </li>
              <li>
                <TrendingUp size={18} />
                <span>Otimização de custo-benefício</span>
              </li>
              <li>
                <Cpu size={18} />
                <span>Sugestões de GPU baseadas em benchmarks</span>
              </li>
            </ul>
            <button className="ai-cta">
              Experimentar AI Advisor
              <ArrowRight size={16} />
            </button>
          </div>
          <div className="ai-visual">
            <div className="ai-chat-preview">
              <div className="chat-message user">
                Preciso treinar um modelo LLaMA 7B com fine-tuning
              </div>
              <div className="chat-message bot">
                <Sparkles size={14} />
                <div>
                  <strong>Recomendação:</strong> RTX 4090 (24GB VRAM)
                  <br />
                  <span className="chat-details">
                    $0.44/hora • Economia de 89% vs AWS
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="pricing-section">
        <div className="section-header">
          <span className="section-badge">Preços</span>
          <h2>Escolha seu plano</h2>
          <p>Quanto maior o plano, mais horas de GPU você tem. Use qualquer GPU disponível.</p>
        </div>

        <div className="pricing-plans-grid">
          {/* Plano Starter */}
          <div className="plan-card">
            <div className="plan-header">
              <h3>Starter</h3>
              <div className="plan-price">
                <span className="currency">$</span>
                <span className="amount">20</span>
                <span className="period">/mês</span>
              </div>
              <p className="plan-subtitle">Ideal para começar</p>
            </div>
            
            <div className="plan-hours">
              <h4><Clock size={16} /> Horas incluídas:</h4>
              <div className="hours-list">
                <div className="hours-item">
                  <span className="gpu">RTX 3060</span>
                  <span className="hours">100h</span>
                </div>
                <div className="hours-item">
                  <span className="gpu">RTX 4070</span>
                  <span className="hours">50h</span>
                </div>
                <div className="hours-item">
                  <span className="gpu">RTX 4090</span>
                  <span className="hours">25h</span>
                </div>
                <div className="hours-item">
                  <span className="gpu">A100 80GB</span>
                  <span className="hours">8h</span>
                </div>
              </div>
              <p className="hours-note">ou combinação equivalente</p>
            </div>

            <div className="plan-features">
              <ul>
                <li><Check size={14} /> Todas as facilidades incluídas</li>
                <li><Check size={14} /> Auto-hibernação</li>
                <li><Check size={14} /> VS Code no browser</li>
              </ul>
            </div>

            <button className="plan-cta" onClick={() => setShowLogin(true)}>
              Começar Agora
            </button>
          </div>

          {/* Plano Pro - Popular */}
          <div className="plan-card popular">
            <div className="popular-tag">Mais Popular</div>
            <div className="plan-header">
              <h3>Pro</h3>
              <div className="plan-price">
                <span className="currency">$</span>
                <span className="amount">50</span>
                <span className="period">/mês</span>
              </div>
              <p className="plan-subtitle">Para projetos sérios</p>
            </div>
            
            <div className="plan-hours">
              <h4><Clock size={16} /> Horas incluídas:</h4>
              <div className="hours-list">
                <div className="hours-item">
                  <span className="gpu">RTX 3060</span>
                  <span className="hours">250h</span>
                </div>
                <div className="hours-item">
                  <span className="gpu">RTX 4070</span>
                  <span className="hours">125h</span>
                </div>
                <div className="hours-item highlight">
                  <span className="gpu">RTX 4090</span>
                  <span className="hours">62h</span>
                </div>
                <div className="hours-item">
                  <span className="gpu">A100 80GB</span>
                  <span className="hours">20h</span>
                </div>
                <div className="hours-item">
                  <span className="gpu">H100</span>
                  <span className="hours">12h</span>
                </div>
              </div>
              <p className="hours-note">ou combinação equivalente</p>
            </div>

            <div className="plan-features">
              <ul>
                <li><Check size={14} /> Tudo do Starter</li>
                <li><Check size={14} /> AI GPU Advisor</li>
                <li><Check size={14} /> Snapshots ilimitados</li>
                <li><Check size={14} /> Suporte prioritário</li>
              </ul>
            </div>

            <button className="plan-cta primary" onClick={() => setShowLogin(true)}>
              <Rocket size={16} />
              Começar 7 Dias Grátis
            </button>
          </div>

          {/* Plano Business */}
          <div className="plan-card">
            <div className="plan-header">
              <h3>Business</h3>
              <div className="plan-price">
                <span className="currency">$</span>
                <span className="amount">150</span>
                <span className="period">/mês</span>
              </div>
              <p className="plan-subtitle">Para equipes e produção</p>
            </div>
            
            <div className="plan-hours">
              <h4><Clock size={16} /> Horas incluídas:</h4>
              <div className="hours-list">
                <div className="hours-item">
                  <span className="gpu">RTX 4070</span>
                  <span className="hours">375h</span>
                </div>
                <div className="hours-item highlight">
                  <span className="gpu">RTX 4090</span>
                  <span className="hours">187h</span>
                </div>
                <div className="hours-item highlight">
                  <span className="gpu">A100 80GB</span>
                  <span className="hours">60h</span>
                </div>
                <div className="hours-item">
                  <span className="gpu">H100</span>
                  <span className="hours">37h</span>
                </div>
              </div>
              <p className="hours-note">ou combinação equivalente</p>
            </div>

            <div className="plan-features">
              <ul>
                <li><Check size={14} /> Tudo do Pro</li>
                <li><Check size={14} /> Multi-GPU clusters</li>
                <li><Check size={14} /> API dedicada</li>
                <li><Check size={14} /> SLA 99.9%</li>
              </ul>
            </div>

            <button className="plan-cta" onClick={() => setShowLogin(true)}>
              Começar Agora
            </button>
          </div>
        </div>

        {/* GPU Price Reference */}
        <div className="gpu-reference">
          <div className="reference-header">
            <Cpu size={18} />
            <h4>Tabela de referência - Preço por hora</h4>
          </div>
          <div className="reference-grid">
            <div className="ref-item">
              <span className="ref-gpu">RTX 3060</span>
              <span className="ref-price">$0.20/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">RTX 4070</span>
              <span className="ref-price">$0.40/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">RTX 4080</span>
              <span className="ref-price">$0.60/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">RTX 4090</span>
              <span className="ref-price">$0.80/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">RTX 5090</span>
              <span className="ref-price">$1.20/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">A100 80GB</span>
              <span className="ref-price">$2.50/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">H100</span>
              <span className="ref-price">$4.00/h</span>
            </div>
          </div>
          <p className="reference-note">
            <TrendingUp size={14} />
            Use qualquer GPU - o valor é descontado proporcionalmente do seu plano
          </p>
        </div>

        {/* O que está incluso */}
        <div className="included-features">
          <h4>Todos os planos incluem:</h4>
          <div className="included-grid">
            <div className="included-item">
              <Zap size={18} />
              <span>Auto-hibernação inteligente</span>
            </div>
            <div className="included-item">
              <Code size={18} />
              <span>VS Code no browser</span>
            </div>
            <div className="included-item">
              <Smartphone size={18} />
              <span>Acesso de qualquer dispositivo</span>
            </div>
            <div className="included-item">
              <Shield size={18} />
              <span>Snapshots automáticos</span>
            </div>
            <div className="included-item">
              <Sparkles size={18} />
              <span>AI GPU Advisor</span>
            </div>
            <div className="included-item">
              <Globe size={18} />
              <span>Multi-região global</span>
            </div>
          </div>
        </div>

        <div className="pricing-guarantee">
          <Shield size={20} />
          <span>7 dias de teste grátis • Cancele quando quiser • Reembolso garantido</span>
        </div>
      </section>

      {/* Portability Section */}
      <section className="portability-section">
        <div className="portability-container">
          <div className="portability-visual">
            <div className="device-showcase">
              <div className="device desktop">
                <div className="device-screen">
                  <Code size={24} />
                  <span>VS Code</span>
                </div>
              </div>
              <div className="device tablet">
                <div className="device-screen">
                  <Code size={18} />
                </div>
              </div>
              <div className="device mobile">
                <div className="device-screen">
                  <Code size={14} />
                </div>
              </div>
            </div>
          </div>
          <div className="portability-content">
            <span className="section-badge green">Portabilidade</span>
            <h2>Desenvolva de qualquer dispositivo</h2>
            <p>
              Acesse seu ambiente de desenvolvimento do celular, tablet ou 
              qualquer computador. VS Code no browser com todas as extensões.
            </p>
            <ul className="portability-features">
              <li>
                <Globe size={18} />
                <span>Acesso via browser - sem instalação</span>
              </li>
              <li>
                <Smartphone size={18} />
                <span>Interface responsiva para mobile</span>
              </li>
              <li>
                <Lock size={18} />
                <span>Conexão segura via SSH</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Social Proof Section */}
      <section className="social-proof-section">
        <div className="section-header">
          <h2>O que nossos usuários dizem</h2>
        </div>
        <div className="testimonials-grid">
          <div className="testimonial-card">
            <div className="testimonial-content">
              <div className="testimonial-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#fbbf24" color="#fbbf24" />)}
              </div>
              <p>"Estava pagando $2000/mês na AWS. Com Dumont Cloud, pago menos de $300 pelo mesmo workload. Impressionante."</p>
            </div>
            <div className="testimonial-author">
              <div className="author-avatar">ML</div>
              <div>
                <strong>Marco Lima</strong>
                <span>ML Engineer @ Startup AI</span>
              </div>
            </div>
          </div>
          <div className="testimonial-card">
            <div className="testimonial-content">
              <div className="testimonial-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#fbbf24" color="#fbbf24" />)}
              </div>
              <p>"A IA que recomenda GPU é genial. Descrevo o projeto e ela já me dá a configuração ideal. Economizo tempo e dinheiro."</p>
            </div>
            <div className="testimonial-author">
              <div className="author-avatar">AS</div>
              <div>
                <strong>Ana Santos</strong>
                <span>Data Scientist</span>
              </div>
            </div>
          </div>
          <div className="testimonial-card">
            <div className="testimonial-content">
              <div className="testimonial-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#fbbf24" color="#fbbf24" />)}
              </div>
              <p>"A auto-hibernação é perfeita. Não preciso me preocupar em desligar máquinas. O sistema faz tudo sozinho."</p>
            </div>
            <div className="testimonial-author">
              <div className="author-avatar">RC</div>
              <div>
                <strong>Rafael Costa</strong>
                <span>Full Stack Developer</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="final-cta-section">
        <div className="cta-container">
          <h2>Pronto para economizar até 89% em GPU Cloud?</h2>
          <p>Comece grátis por 7 dias. Sem cartão de crédito para trial.</p>
          <div className="cta-buttons">
            <button className="cta-primary large" onClick={() => setShowLogin(true)}>
              <Rocket size={20} />
              Começar 7 Dias Grátis
            </button>
            <button className="cta-secondary large">
              Agendar Demo
            </button>
          </div>
          <div className="cta-features">
            <span><Check size={14} /> Setup em 2 minutos</span>
            <span><Check size={14} /> Sem lock-in</span>
            <span><Check size={14} /> Suporte brasileiro</span>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-container">
          <div className="footer-brand">
            <Cloud size={24} />
            <span>Dumont Cloud</span>
            <p>GPU Cloud para desenvolvedores que valorizam seu tempo e dinheiro.</p>
          </div>
          <div className="footer-links">
            <div className="footer-column">
              <h4>Produto</h4>
              <a href="#features">Features</a>
              <a href="#pricing">Preços</a>
              <a href="#calculator">Calculadora</a>
            </div>
            <div className="footer-column">
              <h4>Recursos</h4>
              <a href="#">Documentação</a>
              <a href="#">API</a>
              <a href="#">Status</a>
            </div>
            <div className="footer-column">
              <h4>Empresa</h4>
              <a href="#">Sobre</a>
              <a href="#">Blog</a>
              <a href="#">Contato</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2024 Dumont Cloud. Todos os direitos reservados.</span>
        </div>
      </footer>

      {/* Login Modal */}
      {showLogin && (
        <div className="login-modal-overlay" onClick={() => setShowLogin(false)}>
          <div className="login-modal-container" onClick={e => e.stopPropagation()}>
            {/* Left Panel - Branding */}
            <div className="login-modal-branding">
              <div className="branding-content">
                <div className="branding-logo">
                  <Cloud size={32} />
                  <span>Dumont Cloud</span>
                </div>
                <h2>Desenvolvimento com GPU na nuvem</h2>
                <p>Economize até 89% comparado com AWS, GCP e Azure</p>
                <div className="branding-features">
                  <div className="branding-feature">
                    <Zap size={16} />
                    <span>Deploy em segundos</span>
                  </div>
                  <div className="branding-feature">
                    <DollarSign size={16} />
                    <span>Pague só o que usar</span>
                  </div>
                  <div className="branding-feature">
                    <Sparkles size={16} />
                    <span>IA para escolher GPU</span>
                  </div>
                </div>
              </div>
              <div className="branding-decoration">
                <div className="decoration-circle c1"></div>
                <div className="decoration-circle c2"></div>
                <div className="decoration-circle c3"></div>
              </div>
            </div>

            {/* Right Panel - Login Form */}
            <div className="login-modal-form-panel">
              <button className="modal-close-btn" onClick={() => setShowLogin(false)}>
                ×
              </button>
              
              <div className="form-panel-content">
                <div className="form-header">
                  <h3>Entrar na sua conta</h3>
                  <p>Acesse seu ambiente de desenvolvimento</p>
                </div>

                <LoginForm onLogin={onLogin} onClose={() => setShowLogin(false)} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Login Form Component
function LoginForm({ onLogin, onClose }) {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    console.log('[LoginForm] handleSubmit - calling onLogin with:', username)

    const result = await onLogin(username, password)
    console.log('[LoginForm] onLogin result:', result)

    if (result.error) {
      setError(result.error)
      setLoading(false)
    } else {
      console.log('[LoginForm] Login successful, closing modal and redirecting')
      onClose()

      // Aguardar mais tempo para garantir que o token foi salvo em localStorage
      // e que o estado React foi atualizado
      setTimeout(() => {
        console.log('[LoginForm] Verificando token antes de navegar')
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
        console.log('[LoginForm] Token presente:', !!token)

        console.log('[LoginForm] Navegando para /app')
        navigate('/app')
      }, 1000)  // Aumentado de 500ms para 1000ms
    }
  }

  return (
    <form onSubmit={handleSubmit} className="login-form-v2">
      {error && (
        <div className="login-error">
          <Shield size={16} />
          <span>{error}</span>
        </div>
      )}
      
      <div className="form-field">
        <label htmlFor="email">Email</label>
        <div className="field-input-wrap">
          <Users size={18} className="field-icon" />
          <input
            id="email"
            type="email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="seu@email.com"
            autoComplete="email"
            required
          />
        </div>
      </div>
      
      <div className="form-field">
        <div className="field-label-row">
          <label htmlFor="password">Senha</label>
          <a href="#" className="forgot-link">Esqueceu?</a>
        </div>
        <div className="field-input-wrap">
          <Lock size={18} className="field-icon" />
          <input
            id="password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
          <button 
            type="button" 
            className="password-toggle"
            onClick={() => setShowPassword(!showPassword)}
            tabIndex={-1}
          >
            {showPassword ? '🙈' : '👁️'}
          </button>
        </div>
      </div>
      
      <button type="submit" className="login-submit" disabled={loading}>
        {loading ? (
          <>
            <span className="btn-spinner" />
            Entrando...
          </>
        ) : (
          <>
            Entrar
            <ArrowRight size={18} />
          </>
        )}
      </button>
      
      <div className="login-footer">
        <p>Não tem conta? <a href="#">Criar conta grátis</a></p>
      </div>
      
      <div className="demo-credentials">
        <div className="demo-label">
          <Sparkles size={12} />
          <span>Credenciais de demo</span>
        </div>
        <code>marcosremar@gmail.com / 123456</code>
      </div>
    </form>
  )
}

