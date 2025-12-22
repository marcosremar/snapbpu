import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useState, useEffect, createContext, useContext, useMemo, useCallback } from 'react'
import AppLayout from './components/layout/AppLayout'
import { SidebarProvider } from './context/SidebarContext'
import { ThemeProvider } from './context/ThemeContext'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import Login from './pages/Login'
import LandingPage from './pages/LandingPage'
import Machines from './pages/Machines'
import GPUMetrics from './pages/GPUMetrics'
import MetricsHub from './pages/MetricsHub'
import FailoverReportPage from './pages/FailoverReportPage'
import MachinesReportPage from './pages/MachinesReportPage'
import FineTuning from './pages/FineTuning'
import Serverless from './pages/Serverless'
import GpuOffers from './pages/GpuOffers'
import Documentation from './pages/Documentation'
import ButtonShowcase from './pages/ButtonShowcase'
import ForgotPassword from './pages/ForgotPassword'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
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

// Check if demo mode immediately (before component renders)
const getInitialDemoState = () => {
  const urlParams = new URLSearchParams(window.location.search)
  const isDemoPath = window.location.pathname.startsWith('/demo-app') || window.location.pathname.startsWith('/demo-docs')
  if (urlParams.get('demo') === 'true' || isDemoPath) {
    return { username: 'demo@dumont.cloud', isDemo: true }
  }
  return null
}

export default function App() {
  const [user, setUser] = useState(getInitialDemoState)
  const [loading, setLoading] = useState(!getInitialDemoState())
  const [dashboardStats, setDashboardStats] = useState(null)

  // Memoize demo user object to prevent creating new object on every render
  const demoUser = useMemo(() => ({ username: 'demo@dumont.cloud', isDemo: true }), [])

  // Memoize demo logout handler to prevent creating new function on every render
  const handleDemoLogout = useCallback(() => {
    window.location.href = '/'
  }, [])

  useEffect(() => {
    // If already in demo mode, skip auth check
    if (user?.isDemo) {
      return
    }

    checkAuth()

    // Desregistrar Service Workers antigos que podem estar causando cache
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        registrations.forEach(reg => reg.unregister())
      })
    }
  }, [])

  const checkAuth = async () => {
    try {
      let token = localStorage.getItem('auth_token')

      // Fallback para sessionStorage
      if (!token) {
        token = sessionStorage.getItem('auth_token')
        if (token) {
          localStorage.setItem('auth_token', token)
        }
      }

      if (!token) {
        setLoading(false)
        return
      }

      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        credentials: 'include',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()

      if (data.authenticated) {
        setUser(data.user)
      } else {
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
      // Timeout para detectar servidor offline
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 segundos

      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      const data = await res.json()

      // Tratamento de erro HTTP
      if (!res.ok) {
        // 401 - Credenciais inválidas
        if (res.status === 401) {
          return {
            error: data.error || data.detail || 'Usuário ou senha incorretos',
            errorType: 'credentials'
          }
        }

        // 400 - Erro de validação (ex: email inválido)
        if (res.status === 400) {
          // Verificar se é erro de validação de email
          if (data.details && data.details.some(d => d.loc?.includes('username'))) {
            return {
              error: 'Por favor, insira um e-mail válido',
              errorType: 'validation'
            }
          }
          return {
            error: data.error || data.detail || 'Dados inválidos',
            errorType: 'validation'
          }
        }

        // 500 - Erro do servidor
        if (res.status >= 500) {
          return {
            error: 'Erro no servidor. Tente novamente em alguns instantes.',
            errorType: 'server'
          }
        }

        // Outros erros HTTP
        return {
          error: data.error || data.detail || `Erro na autenticação (${res.status})`,
          errorType: 'unknown'
        }
      }

      // Login bem-sucedido
      if (data.success) {
        if (data.token) {
          localStorage.setItem('auth_token', data.token)
          const saved = localStorage.getItem('auth_token')

          // Garantir que o token foi salvo
          if (!saved) {
            // Tentar com sessionStorage como fallback
            sessionStorage.setItem('auth_token', data.token)
          }
        }

        // Check if demo user and set demo_mode flag
        const isDemoUser = username === 'test@test.com' || username === 'demo@dumont.cloud'
        if (isDemoUser) {
          localStorage.setItem('demo_mode', 'true')
        } else {
          localStorage.removeItem('demo_mode')
        }

        setUser(data.user)
        return { success: true }
      }

      return { error: data.error || 'Falha no login', errorType: 'unknown' }

    } catch (e) {
      console.error('[App.jsx] Error:', e)

      // Timeout ou AbortError - servidor não está respondendo
      if (e.name === 'AbortError') {
        return {
          error: '⚠️ Servidor não está respondendo. Verifique se o backend está ativo.',
          errorType: 'timeout',
          hint: 'Execute: cd /home/marcos/dumontcloud && ./venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8766'
        }
      }

      // TypeError: Failed to fetch - servidor offline ou CORS
      if (e.name === 'TypeError' && e.message.includes('fetch')) {
        return {
          error: '🔌 Não foi possível conectar ao servidor. Backend está offline?',
          errorType: 'connection',
          hint: 'Verifique se o servidor está rodando na porta 8766'
        }
      }

      // Erro de rede genérico
      return {
        error: '⚠️ Erro de conexão com o servidor',
        errorType: 'network',
        hint: e.message
      }
    }
  }

  const handleLogout = async () => {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')

    if (token) {
      try {
        await fetch(`${API_BASE}/api/v1/auth/logout`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Authorization': `Bearer ${token}` },
        })
      } catch (e) {
        // Logout API call failed - continue with local cleanup
      }
    }

    localStorage.removeItem('auth_token')
    sessionStorage.removeItem('auth_token')
    localStorage.removeItem('demo_mode')  // Clear demo mode flag
    setUser(null)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#0a0d0a' }}>
        <div className="spinner" />
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <SidebarProvider>
          <ToastProvider>
            <Routes>
            {/* Rotas Públicas */}
            <Route path="/" element={
              user ? <Navigate to="/app" replace /> : <LandingPage onLogin={handleLogin} />
            } />
            <Route path="/botoes" element={<ButtonShowcase />} />
            <Route path="/login" element={
              user ? <Navigate to="/app" replace /> : <Login onLogin={handleLogin} />
            } />
            <Route path="/esqueci-senha" element={<ForgotPassword />} />

            {/* Rotas Protegidas (requer login) */}
            <Route path="/app" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Dashboard onStatsUpdate={setDashboardStats} />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/machines" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <Machines />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/serverless" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <Serverless />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/metrics-hub" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <MetricsHub />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/metrics" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <GPUMetrics />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/settings" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <Settings />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/failover-report" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <FailoverReportPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/machines-report" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <MachinesReportPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/finetune" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <FineTuning />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/gpu-offers" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout}>
                  <GpuOffers />
                </AppLayout>
              </ProtectedRoute>
            } />

            {/* Documentation Routes */}
            <Route path="/docs" element={
              <ProtectedRoute user={user}>
                <Documentation />
              </ProtectedRoute>
            } />
            <Route path="/docs/:docId" element={
              <ProtectedRoute user={user}>
                <Documentation />
              </ProtectedRoute>
            } />

            {/* Rotas Demo - não requer login, dados fictícios */}
            <Route path="/demo-app" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Dashboard onStatsUpdate={setDashboardStats} />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/machines" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <Machines />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/serverless" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <Serverless />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/metrics-hub" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <MetricsHub />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/metrics" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <GPUMetrics />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/settings" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <Settings />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/failover-report" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <FailoverReportPage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/machines-report" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <MachinesReportPage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/finetune" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <FineTuning />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/gpu-offers" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <GpuOffers />
                </AppLayout>
              </DemoRoute>
            } />

            {/* Demo Documentation Routes */}
            <Route path="/demo-docs" element={
              <DemoRoute>
                <AppLayout user={demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <Documentation />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-docs/:docId" element={
              <DemoRoute>
                <AppLayout user={demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <Documentation />
                </AppLayout>
              </DemoRoute>
            } />

            {/* Fallback - redireciona para landing page */}
            <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ToastProvider>
        </SidebarProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
