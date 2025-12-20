import { useState } from 'react'
import { Moon, Sun, ArrowRight, Shield, Zap, Server, User, Lock, Eye, EyeOff } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import DumontLogo from '../components/DumontLogo'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { theme, toggleTheme } = useTheme()

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
    <div className="flex min-h-screen w-full bg-[#0a0d0a] text-white overflow-hidden font-sans">
      {/* Absolute Theme Toggle */}
      <button
        onClick={toggleTheme}
        className="fixed top-6 right-6 z-50 p-2 rounded-full bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-all backdrop-blur-sm border border-white/5"
        aria-label="Toggle Dark Mode"
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      {/* Left Side - Branding & Visuals (Hidden on mobile) */}
      <div className="hidden lg:flex relative w-1/2 flex-col justify-between p-12 lg:p-16 border-r border-white/5 bg-[#0f1210]">
        {/* Background Effects */}
        <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
          <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-emerald-500/5 rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-emerald-900/10 rounded-full blur-[100px]" />
        </div>

        {/* Logo Area */}
        <div className="relative z-10 flex items-center gap-3">
          <DumontLogo size={40} />
          <span className="text-2xl font-bold tracking-tight text-white">Dumont Cloud</span>
        </div>

        {/* Hero Content */}
        <div className="relative z-10 max-w-lg">
          <h1 className="text-4xl font-bold leading-tight mb-6">
            Intelligence <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-emerald-600">
              Accelerated
            </span>
          </h1>
          <p className="text-lg text-gray-400 leading-relaxed mb-8">
            Gerencie clusters de GPU de alta performance com failover automático e provisionamento instantâneo. A infraestrutura para a próxima geração de IA.
          </p>

          <div className="space-y-4">
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <Zap size={16} />
              </div>
              <span className="text-sm">Provisionamento em segundos</span>
            </div>
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <Shield size={16} />
              </div>
              <span className="text-sm">Failover automático 24/7</span>
            </div>
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <Server size={16} />
              </div>
              <span className="text-sm">Acesso direto via SSH & Jupyter</span>
            </div>
          </div>
        </div>

        {/* Footer/Testimonial */}
        <div className="relative z-10 pt-8 border-t border-white/5">
          <p className="text-sm text-gray-500 font-mono">
            v2.5.0-stable • System Status: <span className="text-emerald-500">Operational</span>
          </p>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 relative z-10">
        <div className="w-full max-w-sm space-y-8">

          {/* Mobile Logo (visible only on small screens) */}
          <div className="lg:hidden flex justify-center mb-8">
            <DumontLogo size={48} />
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
                    className="w-full h-14 pl-12 pr-4 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20 transition-all text-sm"
                    placeholder="seu@email.com"
                    autoFocus
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between ml-1">
                  <label className="text-sm font-medium text-white">Senha</label>
                  <a href="#" className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors">Esqueceu?</a>
                </div>
                <div className="relative">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                    <Lock size={20} className="text-gray-500" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-14 pl-12 pr-12 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20 transition-all text-sm"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-400 transition-colors"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group relative w-full h-14 flex items-center justify-center gap-2.5 rounded-xl bg-emerald-300 hover:bg-emerald-400 text-gray-900 font-semibold transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-gray-900/30 border-t-gray-900 rounded-full animate-spin" />
              ) : (
                <>
                  <span>Entrar</span>
                  <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
            <div className="text-center">
              <a href="/demo-app" className="text-xs text-gray-500 hover:text-emerald-400 transition-colors">Acessar Demonstração (Sem Login)</a>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
