import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Zap, Cloud, DollarSign, Shield, Clock, Cpu, Globe,
  ChevronRight, Check, Play, ArrowRight, Sparkles,
  Server, Smartphone, Code, TrendingUp, PiggyBank,
  Lock, Rocket, BarChart3, Users, Star, Calculator
} from 'lucide-react'
import Logo, { LogoIcon } from '../components/Logo'
import LoginModal from '../components/auth/LoginModal'

// Componente de comparação de preços em tempo real
const PriceComparison = () => {
  const [selectedGPU, setSelectedGPU] = useState('RTX 4090')
  const [hoursPerMonth, setHoursPerMonth] = useState(160)

  const gpuData = {
    'RTX 4090': {
      dumont: 0.40,
      aws: 3.80,
      gcp: 3.40,
      azure: 3.90
    },
    'A100 80GB': {
      dumont: 1.20,
      aws: 5.10,
      gcp: 4.80,
      azure: 5.40
    },
    'H100': {
      dumont: 2.49,
      aws: 7.00,
      gcp: 6.20,
      azure: 8.50
    },
    'RTX 3090': {
      dumont: 0.30,
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
            <LogoIcon size={18} />
            <span className="brand-name"><span className="brand-dumont">Dumont</span> <span className="brand-cloud">Cloud</span></span>
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
            <LogoIcon size={42} className="brand-icon" />
            <span className="brand-name"><span className="brand-dumont">Dumont</span> <span className="brand-cloud">Cloud</span></span>
          </div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#pricing">Preços</a>
            <a href="#calculator">Calculadora</a>
          </div>
          <div className="nav-actions">
            <button className="nav-login" onClick={() => navigate('/login')}>
              Login
            </button>
            <button className="nav-cta" onClick={() => navigate('/login')}>
              Começar Agora
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-bg">
          <div className="hero-decoration">
            <div className="decoration-circle c1"></div>
            <div className="decoration-circle c2"></div>
            <div className="decoration-circle c3"></div>
            <div className="decoration-circle c4"></div>
            <div className="decoration-circle c5"></div>
          </div>
          <div className="hero-gradient" />
          
        </div>

        <div className="hero-content">


          <h1>
            Pare de pagar caro por GPU.{' '}
            <span className="gradient-text">Economize até R$ 102.000/ano</span>{' '}
            com a mesma performance.
          </h1>

          <p className="hero-description">
            Mesmas GPUs que você usa na AWS. <span className="highlight-text">Até 89% mais barato.</span>{' '}
            Deploy em 2 minutos. Sem dor de cabeça. Nossa IA escolhe a GPU certa e você vê a economia em reais, não em planilhas.
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
            <button className="cta-primary" onClick={() => navigate('/login')}>
              <DollarSign size={18} />
              Ver Quanto Eu Economizo
            </button>
            <button className="cta-secondary" onClick={() => document.getElementById('calculator').scrollIntoView({ behavior: 'smooth' })}>
              <Calculator size={18} />
              Calcular Minha Economia
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
            title="Economize com GPU Cloud"
            description="Pague menos por GPU de alta performance. Mesma qualidade da AWS, preço muito menor. A diferença fica com você."
            highlight
          />
          <FeatureCard
            icon={Zap}
            title="Economia automática inteligente"
            description="Máquinas hibernam quando ociosas. Você esquece, o sistema economiza por você. Sem precisar lembrar de desligar nada."
          />
          <FeatureCard
            icon={Sparkles}
            title="IA escolhe a GPU mais barata"
            description="Descreva seu projeto. A IA recomenda a GPU certa e mostra: 'Use RTX 3090, economize R$ 1.200/mês vs RTX 4090'."
          />
          <FeatureCard
            icon={Smartphone}
            title="Acesse de qualquer lugar"
            description="Deploy do celular, tablet ou computador. Tudo no browser, zero instalação. Você não fica preso na mesa."
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
          <p>Todos os planos incluem 7 dias de teste grátis. Cancele quando quiser.</p>
        </div>

        <div className="pricing-plans-grid">
          {/* Standard Membership */}
          <div className="plan-card">
            <div className="plan-header">
              <h3>Standard</h3>
              <div className="plan-price">
                <span className="currency">$</span>
                <span className="amount">19</span>
                <span className="period">/mês</span>
              </div>
              <p className="plan-subtitle">Acesso essencial à plataforma</p>
            </div>

            <div className="plan-usage-highlight">
              <span className="highlight-tag">Créditos Totais</span>
              <p>Sua assinatura <strong>inclui $19 em créditos</strong></p>
              <p className="usage-example">~47h de RTX 4090 ou ~63h de RTX 3090</p>
            </div>

            <div className="plan-features">
              <ul>
                <li><Check size={14} /> 2 máquinas simultâneas</li>
                <li><Check size={14} /> IA GPU Advisor Básico</li>
                <li><Check size={14} /> Auto-hibernação inteligente</li>
                <li><Check size={14} /> Suporte via Discord</li>
              </ul>
            </div>

            <button className="plan-cta" onClick={() => navigate('/login')}>
              Começar 7 Dias Grátis
            </button>
          </div>

          {/* Professional Membership */}
          <div className="plan-card popular">
            <div className="popular-tag">Melhor para Times</div>
            <div className="plan-header">
              <h3>Professional</h3>
              <div className="plan-price">
                <span className="currency">$</span>
                <span className="amount">49</span>
                <span className="period">/mês</span>
              </div>
              <p className="plan-subtitle">Performance e Escala</p>
            </div>

            <div className="plan-usage-highlight">
              <span className="highlight-tag green">Alta Performance</span>
              <p>Sua assinatura <strong>inclui $49 em créditos</strong></p>
              <p className="usage-example">~122h de RTX 4090 ou ~40h de A100</p>
            </div>

            <div className="plan-features">
              <ul>
                <li><Check size={14} /> 10 máquinas simultâneas</li>
                <li><Check size={14} /> IA GPU Advisor Avançado</li>
                <li><Check size={14} /> API Access & Webhooks</li>
                <li><Check size={14} /> Snapshots estendidos (30 dias)</li>
                <li><Check size={14} /> Suporte Prioritário</li>
              </ul>
            </div>

            <button className="plan-cta primary" onClick={() => navigate('/login')}>
              <Rocket size={16} />
              Começar 7 Dias Grátis
            </button>
          </div>

          {/* Enterprise Membership */}
          <div className="plan-card">
            <div className="plan-header">
              <h3>Enterprise</h3>
              <div className="plan-price">
                <span className="amount custom">Sob Consulta</span>
              </div>
              <p className="plan-subtitle">Para escala e corporativo</p>
            </div>

            <div className="plan-usage-highlight">
              <span className="highlight-tag purple">Totalmente Gerenciado</span>
              <p>Infraestrutura dedicada</p>
              <p className="usage-example">SLA Garantido e Contrato</p>
            </div>

            <div className="plan-features">
              <ul>
                <li><Check size={14} /> Máquinas e créditos ilimitados</li>
                <li><Check size={14} /> SLA 99.9% garantido</li>
                <li><Check size={14} /> Gerente de conta dedicado</li>
                <li><Check size={14} /> Faturamento via Invoice</li>
                <li><Check size={14} /> VPC e VPN dedicadas</li>
              </ul>
            </div>

            <button className="plan-cta" onClick={() => window.location.href = 'mailto:enterprise@dumont.cloud'}>
              Falar com Vendas
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
              <span className="ref-gpu">RTX 3090</span>
              <span className="ref-price">$0.30/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">RTX 4090</span>
              <span className="ref-price">$0.40/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">A100 40GB</span>
              <span className="ref-price">$1.20/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">A100 80GB</span>
              <span className="ref-price">$1.89/h</span>
            </div>
            <div className="ref-item">
              <span className="ref-gpu">H100 SXM</span>
              <span className="ref-price">$2.49/h</span>
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
              <p>"Economizei R$ 6.700 no primeiro mês. Rodava 8 A100s na AWS por R$ 8.200/mês. Na Dumont pago R$ 1.500. Mesma performance, deploy mais fácil."</p>
            </div>
            <div className="testimonial-author">
              <div className="author-avatar">ML</div>
              <div>
                <strong>Marco Lima</strong>
                <span>ML Engineer @ Startup IA (São Paulo)</span>
              </div>
            </div>
          </div>
          <div className="testimonial-card">
            <div className="testimonial-content">
              <div className="testimonial-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#fbbf24" color="#fbbf24" />)}
              </div>
              <p>"A IA Advisor me salvou R$ 1.800/mês. Eu ia pegar H100, ela sugeriu RTX 4090 que faz o mesmo job. Fine-tuning de LLaMA 7B roda perfeito."</p>
            </div>
            <div className="testimonial-author">
              <div className="author-avatar">AS</div>
              <div>
                <strong>Ana Santos</strong>
                <span>Data Scientist (Rio de Janeiro)</span>
              </div>
            </div>
          </div>
          <div className="testimonial-card">
            <div className="testimonial-content">
              <div className="testimonial-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#fbbf24" color="#fbbf24" />)}
              </div>
              <p>"Auto-hibernação é dinheiro grátis. Esquecia máquinas ligadas, gastava R$ 500/mês a toa. Agora zero preocupação, economizo R$ 400/mês sem fazer nada."</p>
            </div>
            <div className="testimonial-author">
              <div className="author-avatar">RC</div>
              <div>
                <strong>Rafael Costa</strong>
                <span>Full Stack Developer (Remoto)</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="final-cta-section">
        <div className="cta-container">
          <h2>Pronto para economizar em GPU Cloud?</h2>
          <p>Veja quanto você pode economizar com nossa calculadora. Deploy em 2 minutos. Sem complicação.</p>
          <div className="cta-buttons">
            <button className="cta-primary large" onClick={() => document.getElementById('calculator').scrollIntoView({ behavior: 'smooth' })}>
              <Calculator size={20} />
              Calcular Minha Economia
            </button>
            <button className="cta-secondary large" onClick={() => navigate('/login')}>
              Começar Agora (Trial Grátis)
            </button>
          </div>
          <div className="cta-features">
            <span><Check size={14} /> Deploy em 2 minutos</span>
            <span><Check size={14} /> Cancele quando quiser</span>
            <span><Check size={14} /> Sem cartão no trial</span>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-container">
          <div className="footer-brand">
            <LogoIcon size={24} />
            <span className="brand-name"><span className="brand-dumont">Dumont</span> <span className="brand-cloud">Cloud</span></span>
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
      <LoginModal
        isOpen={showLogin}
        onClose={() => setShowLogin(false)}
        onLogin={onLogin}
      />
    </div>
  )
}

