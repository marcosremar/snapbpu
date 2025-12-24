import { useState } from 'react'
import { ArrowLeft, Mail, CheckCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import Logo from '../components/Logo'
import '../styles/landing.css'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // TODO: Implementar chamada à API de recuperação de senha
      // const res = await fetch('/api/v1/auth/forgot-password', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ email })
      // })

      // Simular envio por enquanto
      await new Promise(resolve => setTimeout(resolve, 1500))
      setSent(true)
    } catch (e) {
      setError('Erro ao enviar email. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen w-full bg-[#0a0d0a] text-white overflow-hidden font-sans relative">
      {/* Left Side - Branding (Hidden on mobile) */}
      <div className="hidden lg:flex relative w-1/2 flex-col justify-between p-12 lg:p-16 border-r border-white/5 bg-[#0a0d0a] z-10">
        {/* Background with decoration circles */}
        <div className="hero-decoration">
          <div className="decoration-circle c1"></div>
          <div className="decoration-circle c2"></div>
          <div className="decoration-circle c3"></div>
          <div className="decoration-circle c4"></div>
          <div className="decoration-circle c5"></div>
        </div>

        {/* Logo */}
        <div className="relative z-10">
          <Logo size={44} />
        </div>

        {/* Content */}
        <div className="relative z-10 max-w-lg">
          <h1 className="text-4xl font-bold leading-tight mb-6">
            Recupere seu <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-500 to-brand-300">
              Acesso
            </span>
          </h1>
          <p className="text-lg text-gray-400 leading-relaxed">
            Não se preocupe, acontece com todo mundo. Vamos te ajudar a voltar para sua conta.
          </p>
        </div>

        {/* Footer */}
        <div className="relative z-10 pt-8 border-t border-white/5">
          <p className="text-sm text-gray-500 font-mono">
            Dumont Cloud • Suporte 24/7
          </p>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 relative z-10 bg-[#0a0d0a]">
        <div className="w-full max-w-sm space-y-8">

          {/* Mobile Logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <Logo size={48} />
          </div>

          {/* Back to login */}
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-brand-500 transition-colors"
          >
            <ArrowLeft size={16} />
            Voltar para o login
          </Link>

          {!sent ? (
            <>
              <div className="text-center lg:text-left">
                <h2 className="text-2xl font-semibold text-white tracking-tight">Esqueceu sua senha?</h2>
                <p className="text-sm text-gray-400 mt-2">
                  Digite seu email e enviaremos um link para redefinir sua senha.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                {error && (
                  <div className="p-3 text-sm rounded-lg bg-red-900/10 border border-red-900/20 text-red-400">
                    {error}
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-sm font-medium text-white ml-1">Email</label>
                  <div className="relative">
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                      <Mail size={20} className="text-gray-500" />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full h-14 pl-12 pr-4 rounded-xl bg-gray-900 border border-gray-800 text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all text-sm"
                      placeholder="seu@email.com"
                      autoFocus
                      required
                    />
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
                    <span>Enviar link de recuperação</span>
                  )}
                </button>
              </form>
            </>
          ) : (
            <div className="text-center space-y-6">
              <div className="w-16 h-16 mx-auto rounded-full bg-brand-500/20 flex items-center justify-center">
                <CheckCircle size={32} className="text-brand-500" />
              </div>
              <div>
                <h2 className="text-2xl font-semibold text-white tracking-tight">Email enviado!</h2>
                <p className="text-sm text-gray-400 mt-2">
                  Enviamos um link de recuperação para <span className="text-brand-500">{email}</span>.
                  Verifique sua caixa de entrada e spam.
                </p>
              </div>
              <Link
                to="/login"
                className="inline-flex items-center justify-center gap-2 w-full h-14 rounded-xl bg-[#131713] border border-[#2a352a] text-white font-semibold hover:bg-[#1a1f1a] transition-all"
              >
                <ArrowLeft size={18} />
                Voltar para o login
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
