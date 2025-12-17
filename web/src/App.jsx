import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Machines from './pages/Machines'
import GPUMetrics from './pages/GPUMetrics'

const API_BASE = ''

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if demo mode
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('demo') === 'true') {
      setUser({ username: 'marcosremar@gmail.com' })
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
      const token = localStorage.getItem('auth_token')
      if (!token) {
        setLoading(false)
        return
      }
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        credentials: 'include',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()
      if (data.authenticated) {
        setUser(data.user)
      } else {
        localStorage.removeItem('auth_token')
      }
    } catch (e) {
      console.error('Auth check failed:', e)
    }
    setLoading(false)
  }

  const handleLogin = async (username, password) => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
      })
      const data = await res.json()
      if (data.success) {
        if (data.token) {
          localStorage.setItem('auth_token', data.token)
        }
        setUser(data.user)
        return { success: true }
      }
      return { error: data.error || 'Login failed' }
    } catch (e) {
      return { error: 'Erro de conexao' }
    }
  }

  const handleLogout = async () => {
    const token = localStorage.getItem('auth_token')
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    })
    localStorage.removeItem('auth_token')
    setUser(null)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div className="spinner" />
      </div>
    )
  }

  if (!user) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <Layout user={user} onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/machines" element={<Machines />} />
        <Route path="/metrics" element={<GPUMetrics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
