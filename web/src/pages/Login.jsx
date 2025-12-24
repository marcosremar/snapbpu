import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Shield, Zap, Server, User, Lock, Eye, EyeOff } from 'lucide-react'
import Logo from '../components/Logo'
import '../styles/landing.css'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const result = await onLogin(username, password)

    if (result.error) {
      setError(result)
      setLoading(false)
    }
  }

  // Determinar ícone e cor com base no tipo de erro
  const getErrorIcon = (errorType) => {
    switch (errorType) {
      case 'connection':
      case 'timeout':
        return '🔌'
      case 'credentials':
        return '🔒'
      case 'validation':
        return '⚠️'
      case 'server':
        return '⚙️'
      default:
        return '❌'
    }
  }

  const getErrorColor = (errorType) => {
    switch (errorType) {
      case 'connection':
      case 'timeout':
        return 'text-orange-400 bg-orange-900/10 border-orange-900/20'
      case 'credentials':
        return 'text-red-400 bg-red-900/10 border-red-900/20'
      case 'validation':
        return 'text-yellow-400 bg-yellow-900/10 border-yellow-900/20'
      case 'server':
        return 'text-purple-400 bg-purple-900/10 border-purple-900/20'
      default:
        return 'text-red-400 bg-red-900/10 border-red-900/20'
    }
  }

  return (
    <div className="flex min-h-screen w-full bg-[#0a0d0a] text-white overflow-hidden font-sans relative">
      {/* Left Side - Branding & Visuals (Hidden on mobile) */}
      <div className="hidden lg:flex relative w-1/2 flex-col justify-between p-12 lg:p-16 border-r border-white/5 bg-[#0a0d0a] z-10">
        {/* Background with decoration circles - same as landing page */}
        <div className="hero-decoration">
          <div className="decoration-circle c1"></div>
          <div className="decoration-circle c2"></div>
          <div className="decoration-circle c3"></div>
          <div className="decoration-circle c4"></div>
          <div className="decoration-circle c5"></div>
        </div>

        {/* Logo Area - Using Logo component with text */}
        <div className="relative z-10">
          <Logo size={44} />
        </div>

        {/* Hero Content */}
        <div className="relative z-10 max-w-lg">
          <h1 className="text-4xl font-bold leading-tight mb-6">
            Intelligence <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#4caf50] to-[#81c784]">
              Accelerated
            </span>
          </h1>
          <p className="text-lg text-gray-400 leading-relaxed mb-8">
            Gerencie clusters de GPU de alta performance com failover automático e provisionamento instantâneo. A infraestrutura para a próxima geração de IA.
          </p>

          <div className="space-y-4">
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-500">
                <Zap size={16} />
              </div>
              <span className="text-sm">Provisionamento em segundos</span>
            </div>
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-500">
                <Shield size={16} />
              </div>
              <span className="text-sm">Failover automático 24/7</span>
            </div>
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-500">
                <Server size={16} />
              </div>
              <span className="text-sm">Acesso direto via SSH & Jupyter</span>
            </div>
          </div>
        </div>

        {/* Footer/Testimonial */}
        <div className="relative z-10 pt-8 border-t border-white/5">
          <p className="text-sm text-gray-500 font-mono">
            v2.5.0-stable • System Status: <span className="text-[#4caf50]">Operational</span>
          </p>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 relative z-10 bg-[#0a0d0a]">
        <div className="w-full max-w-sm space-y-8">

          {/* Mobile Logo (visible only on small screens) */}
          <div className="lg:hidden flex justify-center mb-8">
            <Logo size={48} showText={false} />
          </div>

          <div className="text-center lg:text-left">
            <h2 className="text-2xl font-semibold text-white tracking-tight">Login</h2>
            <p className="text-sm text-gray-400 mt-2">
              Entre com suas credenciais para acessar o console.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && typeof error === 'object' && error.error && (
              <div className="space-y-2">
                <div className={`p-3 text-sm rounded-lg flex items-start gap-3 border ${getErrorColor(error.errorType)}`}>
                  <span className="text-lg flex-shrink-0 mt-0.5">{getErrorIcon(error.errorType)}</span>
                  <div className="flex-1">
                    <p className="font-medium">{error.error}</p>
                    {error.hint && (
                      <details className="mt-2 text-xs opacity-80">
                        <summary className="cursor-pointer hover:opacity-100 font-mono">
                          💡 Dica para desenvolvedores
                        </summary>
                        <pre className="mt-2 p-2 bg-black/20 rounded overflow-x-auto whitespace-pre-wrap">
                          {error.hint}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-5">
              <div className="space-y-2">
                <label className="text-sm font-medium text-white ml-1">Email</label>
                <div className="relative">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                    <User size={20} className="text-gray-500" />
                  </div>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full h-14 pl-12 pr-4 rounded-xl bg-[#131713] border border-[#2a352a] text-white placeholder-gray-500 focus:outline-none focus:border-[#4caf50] focus:ring-2 focus:ring-[#2e7d32]/20 transition-all text-sm"
                    placeholder="seu@email.com"
                    autoFocus
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between ml-1">
                  <label className="text-sm font-medium text-white">Senha</label>
                  <Link to="/esqueci-senha" className="text-sm text-[#4caf50] hover:text-[#81c784] transition-colors font-medium">Esqueceu?</Link>
                </div>
                <div className="relative">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                    <Lock size={20} className="text-gray-500" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-14 pl-12 pr-12 rounded-xl bg-[#131713] border border-[#2a352a] text-white placeholder-gray-500 focus:outline-none focus:border-[#4caf50] focus:ring-2 focus:ring-[#2e7d32]/20 transition-all text-sm"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-[#4caf50] transition-colors"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group relative w-full h-14 flex items-center justify-center gap-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold transition-all shadow-lg shadow-brand-500/20 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Entrar</span>
                  <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
            <div className="text-center">
              <a href="/demo-app" className="text-xs text-gray-500 hover:text-[#4caf50] transition-colors">Acessar Demonstração (Sem Login)</a>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
