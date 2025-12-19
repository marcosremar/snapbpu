import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import Login from './pages/Login'
import LandingPage from './pages/LandingPage'
import Machines from './pages/Machines'
import GPUMetrics from './pages/GPUMetrics'
import MetricsHub from './pages/MetricsHub'
import SavingsPage from './pages/Savings'
import AdvisorPage from './pages/AdvisorPage'
import { ToastProvider } from './components/Toast'
import './styles/landing.css'

const API_BASE = ''

// Context para modo demo
export const DemoContext = createContext(false)
export const useDemoMode = () => useContext(DemoContext)

// Componente para rotas protegidas (requer login)
function ProtectedRoute({ user, children }) {
  const location = useLocation()

  if (!user) {
    // Redireciona para login, salvando a página que o usuário tentou acessar
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}

// Componente wrapper para rotas demo (não requer login)
function DemoRoute({ children }) {
  return (
    <DemoContext.Provider value={true}>
      {children}
    </DemoContext.Provider>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if demo mode via URL param or /demo-app path
    const urlParams = new URLSearchParams(window.location.search)
    const isDemoPath = window.location.pathname.startsWith('/demo-app')

    if (urlParams.get('demo') === 'true' || isDemoPath) {
      setUser({ username: 'demo@dumont.cloud', isDemo: true })
      setLoading(false)
      return
    }

    checkAuth()
    // Registrar Service Worker para notificações
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('Service Worker registrado'))
        .catch(err => console.error('Erro ao registrar SW:', err))
    }
  }, [])

  const checkAuth = async () => {
    try {
      let token = localStorage.getItem('auth_token')

      // Fallback para sessionStorage
      if (!token) {
        token = sessionStorage.getItem('auth_token')
        if (token) {
          console.log('[App.jsx] Token encontrado em sessionStorage, movendo para localStorage')
          localStorage.setItem('auth_token', token)
        }
      }

      if (!token) {
        console.log('[App.jsx] No token found')
        setLoading(false)
        return
      }

      console.log('[App.jsx] Validando token via /api/auth/me')
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        credentials: 'include',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()
      console.log('[App.jsx] Auth check response:', data)

      if (data.authenticated) {
        console.log('[App.jsx] Usuário autenticado:', data.user)
        setUser(data.user)
      } else {
        console.log('[App.jsx] Auth failed, removendo token')
        localStorage.removeItem('auth_token')
        sessionStorage.removeItem('auth_token')
      }
    } catch (e) {
      console.error('[App.jsx] Auth check failed:', e)
    }
    setLoading(false)
  }

  const handleLogin = async (username, password) => {
    try {
      console.log('[App.jsx] handleLogin called with:', username)
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
      })
      const data = await res.json()
      console.log('[App.jsx] API response:', data)
      if (data.success) {
        if (data.token) {
          console.log('[App.jsx] Saving token to localStorage')
          localStorage.setItem('auth_token', data.token)
          const saved = localStorage.getItem('auth_token')
          console.log('[App.jsx] Token saved. Verification:', saved?.substring(0, 20))

          // Garantir que o token foi salvo
          if (!saved) {
            console.error('[App.jsx] WARNING: Token não foi salvo em localStorage!')
            // Tentar com sessionStorage como fallback
            sessionStorage.setItem('auth_token', data.token)
            console.log('[App.jsx] Token salvo em sessionStorage como fallback')
          }
        }
        console.log('[App.jsx] Setting user:', data.user)
        setUser(data.user)
        return { success: true }
      }
      return { error: data.error || 'Login failed' }
    } catch (e) {
      console.error('[App.jsx] Error:', e)
      return { error: 'Erro de conexao' }
    }
  }

  const handleLogout = async () => {
    console.log('[App.jsx] handleLogout called')
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')

    if (token) {
      try {
        console.log('[App.jsx] Chamando /api/auth/logout')
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Authorization': `Bearer ${token}` },
        })
      } catch (e) {
        console.error('[App.jsx] Logout API call failed:', e)
      }
    }

    console.log('[App.jsx] Removendo tokens do storage')
    localStorage.removeItem('auth_token')
    sessionStorage.removeItem('auth_token')
    setUser(null)
    console.log('[App.jsx] Logout completo')
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#0a0d0a' }}>
        <div className="spinner" />
      </div>
    )
  }

  return (
    <ToastProvider>
      <Routes>
        {/* Rotas Públicas */}
        <Route path="/" element={
          user ? <Navigate to="/app" replace /> : <LandingPage onLogin={handleLogin} />
        } />
        <Route path="/login" element={
          user ? <Navigate to="/app" replace /> : <Login onLogin={handleLogin} />
        } />

        {/* Rotas Protegidas (requer login) */}
        <Route path="/app" element={
          <ProtectedRoute user={user}>
            <Layout user={user} onLogout={handleLogout}>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/app/machines" element={
          <ProtectedRoute user={user}>
            <Layout user={user} onLogout={handleLogout}>
              <Machines />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/app/advisor" element={
          <ProtectedRoute user={user}>
            <AdvisorPage user={user} onLogout={handleLogout} />
          </ProtectedRoute>
        } />
        <Route path="/app/metrics-hub" element={
          <ProtectedRoute user={user}>
            <Layout user={user} onLogout={handleLogout}>
              <MetricsHub />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/app/metrics" element={
          <ProtectedRoute user={user}>
            <Layout user={user} onLogout={handleLogout}>
              <GPUMetrics />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/app/savings" element={
          <ProtectedRoute user={user}>
            <SavingsPage user={user} onLogout={handleLogout} />
          </ProtectedRoute>
        } />
        <Route path="/app/settings" element={
          <ProtectedRoute user={user}>
            <Layout user={user} onLogout={handleLogout}>
              <Settings />
            </Layout>
          </ProtectedRoute>
        } />

        {/* Rotas Demo - não requer login, dados fictícios */}
        <Route path="/demo-app" element={
          <DemoRoute>
            <Layout user={user || { username: 'demo@dumont.cloud', isDemo: true }} onLogout={() => window.location.href = '/'} isDemo={true}>
              <Dashboard />
            </Layout>
          </DemoRoute>
        } />
        <Route path="/demo-app/machines" element={
          <DemoRoute>
            <Layout user={user || { username: 'demo@dumont.cloud', isDemo: true }} onLogout={() => window.location.href = '/'} isDemo={true}>
              <Machines />
            </Layout>
          </DemoRoute>
        } />
        <Route path="/demo-app/advisor" element={
          <DemoRoute>
            <AdvisorPage user={user || { username: 'demo@dumont.cloud', isDemo: true }} onLogout={() => window.location.href = '/'} />
          </DemoRoute>
        } />
        <Route path="/demo-app/metrics-hub" element={
          <DemoRoute>
            <Layout user={user || { username: 'demo@dumont.cloud', isDemo: true }} onLogout={() => window.location.href = '/'} isDemo={true}>
              <MetricsHub />
            </Layout>
          </DemoRoute>
        } />
        <Route path="/demo-app/metrics" element={
          <DemoRoute>
            <Layout user={user || { username: 'demo@dumont.cloud', isDemo: true }} onLogout={() => window.location.href = '/'} isDemo={true}>
              <GPUMetrics />
            </Layout>
          </DemoRoute>
        } />
        <Route path="/demo-app/savings" element={
          <DemoRoute>
            <SavingsPage user={user || { username: 'demo@dumont.cloud', isDemo: true }} onLogout={() => window.location.href = '/'} />
          </DemoRoute>
        } />
        <Route path="/demo-app/settings" element={
          <DemoRoute>
            <Layout user={user || { username: 'demo@dumont.cloud', isDemo: true }} onLogout={() => window.location.href = '/'} isDemo={true}>
              <Settings />
            </Layout>
          </DemoRoute>
        } />

        {/* Fallback - redireciona para landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ToastProvider>
  )
}
