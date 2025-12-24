import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, DollarSign, Sparkles, Users, Lock, ArrowRight } from 'lucide-react'
import Logo from '../Logo'

/**
 * LoginModal - Modal de login reutilizável
 *
 * @param {boolean} isOpen - Controla visibilidade do modal
 * @param {function} onClose - Callback para fechar o modal
 * @param {function} onLogin - Callback para fazer login
 */
export default function LoginModal({ isOpen, onClose, onLogin }) {
  if (!isOpen) return null

  return (
    <div className="login-modal-overlay" onClick={onClose}>
      <div className="login-modal-container" onClick={e => e.stopPropagation()}>
        {/* Left Panel - Branding */}
        <div className="login-modal-branding">
          <div className="branding-content">
            <div className="branding-logo">
              <Logo size={32} />
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
          <button className="modal-close-btn" onClick={onClose}>
            ×
          </button>

          <div className="form-panel-content">
            <div className="form-header">
              <h3>Entrar na sua conta</h3>
              <p>Acesse seu ambiente de desenvolvimento</p>
            </div>

            <LoginForm onLogin={onLogin} onClose={onClose} />
          </div>
        </div>
      </div>
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

    const result = await onLogin(username, password)

    if (result.error) {
      setError(result)
      setLoading(false)
    } else {
      onClose()

      setTimeout(() => {
        navigate('/app')
      }, 1000)
    }
  }

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

  return (
    <form onSubmit={handleSubmit} className="login-form-v2">
      {error && typeof error === 'object' && error.error && (
        <div className="login-error">
          <span className="error-icon">{getErrorIcon(error.errorType)}</span>
          <div className="error-content">
            <span className="error-message">{error.error}</span>
            {error.hint && (
              <details className="error-hint">
                <summary>💡 Dica para desenvolvedores</summary>
                <pre>{error.hint}</pre>
              </details>
            )}
          </div>
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
    </form>
  )
}

export { LoginForm }
