import { useState, useEffect, useMemo } from 'react'
import { Eye, EyeOff, Check, X, AlertCircle, Key, Database, Lock, Server, DollarSign, Shield } from 'lucide-react'
import { useToast } from '../components/Toast'
import StandbyConfig from '../components/StandbyConfig'
import { AlertInline, Card, CardHeader, CardTitle, CardContent, Button } from '../components/ui/dumont-ui'

const API_BASE = ''

// Validadores para campos
const validators = {
  vast_api_key: (value) => {
    if (!value) return null // Não validar vazios
    if (value.length < 20) return { valid: false, message: 'API key muito curta' }
    return { valid: true, message: 'Formato válido' }
  },
  r2_access_key: (value) => {
    if (!value) return null
    if (value.length < 10) return { valid: false, message: 'Access key muito curta' }
    return { valid: true, message: 'Formato válido' }
  },
  r2_secret_key: (value) => {
    if (!value) return null
    if (value.length < 20) return { valid: false, message: 'Secret key muito curta' }
    return { valid: true, message: 'Formato válido' }
  },
  r2_endpoint: (value) => {
    if (!value) return null
    if (!value.startsWith('https://')) return { valid: false, message: 'Deve começar com https://' }
    if (!value.includes('r2.cloudflarestorage.com')) return { valid: false, message: 'Deve ser um endpoint R2 válido' }
    return { valid: true, message: 'URL válida' }
  },
  r2_bucket: (value) => {
    if (!value) return null
    if (value.length < 3) return { valid: false, message: 'Nome muito curto (min. 3 caracteres)' }
    if (!/^[a-z0-9-]+$/.test(value)) return { valid: false, message: 'Apenas letras minúsculas, números e hífens' }
    return { valid: true, message: 'Nome válido' }
  },
  restic_password: (value) => {
    if (!value) return null
    if (value.length < 8) return { valid: false, message: 'Senha muito curta (min. 8 caracteres)' }
    return { valid: true, message: 'Senha válida' }
  }
}


// Componente para inputs de campos sensíveis com toggle show/hide e validação
function SecretInput({ name, value, onChange, placeholder, validation }) {
  const [show, setShow] = useState(false)

  return (
    <div>
      <div className={`secret-input-wrapper ${validation ? (validation.valid ? 'border-green-500/30' : 'border-red-500/30') : ''}`}
        style={validation ? { borderColor: validation.valid ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)' } : {}}>
        <input
          type={show ? "text" : "password"}
          name={name}
          className="form-input"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          style={validation ? { borderColor: 'transparent' } : {}}
        />
        <button
          type="button"
          className="secret-toggle-btn"
          onClick={() => setShow(!show)}
          title={show ? "Ocultar" : "Mostrar"}
        >
          {show ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
      {validation && (
        <AlertInline variant={validation.valid ? 'success' : 'error'}>
          {validation.message}
        </AlertInline>
      )}
    </div>
  )
}

// Input com validação
function ValidatedInput({ name, value, onChange, placeholder, type = 'text', validation }) {
  return (
    <div>
      <input
        type={type}
        name={name}
        className="form-input"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={validation ? { borderColor: validation.valid ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)' } : {}}
      />
      {validation && (
        <AlertInline variant={validation.valid ? 'success' : 'error'}>
          {validation.message}
        </AlertInline>
      )}
    </div>
  )
}

// Precos Cloudflare R2 (dezembro 2024)
const R2_PRICING = {
  storage_per_gb: 0.015,        // $0.015/GB/mes
  class_a_per_million: 4.50,    // $4.50/milhao (writes)
  class_b_per_million: 0.36,    // $0.36/milhao (reads)
}

// Componente Toast para notificações in-app
function Toast({ message, title = 'Saldo Baixo!', type = 'warning', onClose }) {
  const [isVisible, setIsVisible] = useState(false)
  const [isLeaving, setIsLeaving] = useState(false)

  useEffect(() => {
    // Som de notificação
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      oscillator.frequency.value = 880
      oscillator.type = 'sine'
      gainNode.gain.value = 0.3

      oscillator.start()
      setTimeout(() => { oscillator.frequency.value = 1100 }, 100)
      setTimeout(() => { oscillator.frequency.value = 880 }, 200)
      setTimeout(() => { oscillator.stop(); audioContext.close() }, 300)
    } catch (e) {
      console.log('Audio not supported')
    }

    // Animação de entrada
    setTimeout(() => setIsVisible(true), 10)

    // Auto-fechar após 10 segundos
    const timer = setTimeout(() => handleClose(), 10000)
    return () => clearTimeout(timer)
  }, [])

  const handleClose = () => {
    setIsLeaving(true)
    setTimeout(() => onClose(), 300)
  }

  const bgColor = type === 'warning' ? '#f59e0b' : type === 'error' ? '#ef4444' : '#10b981'

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: isVisible && !isLeaving ? '20px' : '-400px',
      width: '360px',
      backgroundColor: '#1c2128',
      borderRadius: '12px',
      border: `2px solid ${bgColor}`,
      boxShadow: `0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px ${bgColor}40`,
      zIndex: 9999,
      transition: 'right 0.3s ease-out',
      overflow: 'hidden'
    }}>
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        height: '3px',
        backgroundColor: bgColor,
        animation: 'shrink 10s linear forwards'
      }} />

      <div style={{ padding: '16px', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          backgroundColor: `${bgColor}20`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill={bgColor}>
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '14px', fontWeight: '600', color: bgColor, marginBottom: '4px' }}>
            {title}
          </div>
          <div style={{ fontSize: '13px', color: '#c9d1d9', lineHeight: '1.4' }}>
            {message}
          </div>
        </div>

        <button
          onClick={handleClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#6e7681',
            cursor: 'pointer',
            padding: '4px',
            fontSize: '18px',
            lineHeight: 1
          }}
        >
          ×
        </button>
      </div>

      <style>{`
        @keyframes shrink {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
    </div>
  )
}

// Menu items para Settings
const SETTINGS_MENU = [
  { id: 'apis', label: 'APIs & Credenciais', icon: Key, color: 'green' },
  { id: 'storage', label: 'Armazenamento', icon: Database, color: 'blue' },
  { id: 'agent', label: 'Agent Sync', icon: Server, color: 'cyan' },
  { id: 'notifications', label: 'Notificações', icon: AlertCircle, color: 'yellow' },
  { id: 'failover', label: 'CPU Failover', icon: Shield, color: 'red' },
]

export default function Settings() {
  const toast = useToast()
  const [activeTab, setActiveTab] = useState('apis')
  const [settings, setSettings] = useState({
    vast_api_key: '',
    r2_access_key: '',
    r2_secret_key: '',
    r2_endpoint: '',
    r2_bucket: '',
    restic_password: ''
  })
  const [agentSettings, setAgentSettings] = useState({
    sync_interval: 30,
    keep_last: 10,
  })
  const [estimatedDataSize, setEstimatedDataSize] = useState(10) // GB
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingAgent, setSavingAgent] = useState(false)
  const [message, setMessage] = useState(null)
  const [showToast, setShowToast] = useState(false)

  // Validação real-time
  const validations = useMemo(() => {
    return {
      vast_api_key: validators.vast_api_key(settings.vast_api_key),
      r2_access_key: validators.r2_access_key(settings.r2_access_key),
      r2_secret_key: validators.r2_secret_key(settings.r2_secret_key),
      r2_endpoint: validators.r2_endpoint(settings.r2_endpoint),
      r2_bucket: validators.r2_bucket(settings.r2_bucket),
      restic_password: validators.restic_password(settings.restic_password),
    }
  }, [settings])

  // Verificar se formulário é válido (campos preenchidos passam validação)
  const isFormValid = useMemo(() => {
    return Object.values(validations).every(v => v === null || v.valid)
  }, [validations])

  const testNotification = () => {
    toast.success('Notificações estão funcionando!')
  }

  useEffect(() => {
    loadSettings()
    loadAgentSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings`, { credentials: 'include' })
      const data = await res.json()
      if (data.settings) {
        setSettings(data.settings)
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
    setLoading(false)
  }

  const loadAgentSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/agent`, { credentials: 'include' })
      const data = await res.json()
      if (data.sync_interval) {
        setAgentSettings(data)
      }
    } catch (e) {
      console.error('Failed to load agent settings:', e)
    }
  }

  const handleAgentChange = (e) => {
    const { name, value } = e.target
    setAgentSettings(prev => ({ ...prev, [name]: parseInt(value) }))
  }

  const saveAgentSettings = async () => {
    setSavingAgent(true)
    setMessage(null)

    try {
      const res = await fetch(`${API_BASE}/api/settings/agent`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentSettings),
        credentials: 'include'
      })
      const data = await res.json()

      if (data.success) {
        toast.success('Configurações do agente salvas!')
        setMessage({ type: 'success', text: 'Configuracoes do agente salvas!' })
      } else {
        toast.error(data.error || 'Falha ao salvar configurações do agente')
        setMessage({ type: 'error', text: data.error || 'Falha ao salvar configuracoes do agente' })
      }
    } catch (e) {
      toast.error('Erro de conexão')
      setMessage({ type: 'error', text: 'Erro de conexao' })
    }
    setSavingAgent(false)
  }

  // Calcular custos estimados do R2
  const r2Costs = useMemo(() => {
    const syncsPerMonth = (30 * 24 * 3600) / agentSettings.sync_interval
    // Estimativa: ~50 operacoes Class A por sync, ~10 Class B
    const classAOps = syncsPerMonth * 50
    const classBOps = syncsPerMonth * 10
    // Storage efetivo (70% deduplicacao pelo Restic)
    const effectiveStorage = estimatedDataSize * 0.3

    const storageCost = effectiveStorage * R2_PRICING.storage_per_gb
    const classACost = (classAOps / 1_000_000) * R2_PRICING.class_a_per_million
    const classBCost = (classBOps / 1_000_000) * R2_PRICING.class_b_per_million

    return {
      storage: storageCost,
      operations: classACost + classBCost,
      total: storageCost + classACost + classBCost,
      syncsPerMonth: Math.round(syncsPerMonth),
      effectiveStorage: effectiveStorage.toFixed(1),
    }
  }, [agentSettings.sync_interval, estimatedDataSize])

  const handleChange = (e) => {
    const { name, value } = e.target
    setSettings(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    try {
      const res = await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
        credentials: 'include'
      })
      const data = await res.json()

      if (data.success) {
        toast.success('Configurações salvas com sucesso!')
        setMessage({ type: 'success', text: 'Settings saved successfully' })
      } else {
        toast.error(data.error || 'Falha ao salvar configurações')
        setMessage({ type: 'error', text: data.error || 'Failed to save settings' })
      }
    } catch (e) {
      toast.error('Erro de conexão')
      setMessage({ type: 'error', text: 'Connection error' })
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="container">
        <div className="empty-state">
          <div className="spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0e110e] to-[#131713]">
      {/* Toast de notificação */}
      {showToast && (
        <Toast
          title="Teste de Notificação"
          message="As notificações estão funcionando corretamente!"
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}

      <div className="max-w-7xl mx-auto p-6 md:p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">Configurações</h1>
          <p className="text-gray-400">Gerencie suas APIs, armazenamento e preferências</p>
        </div>

        {/* Layout: Sidebar + Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Menu */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-2">
              {SETTINGS_MENU.map((item) => {
                const MenuIcon = item.icon
                const colorClasses = {
                  green: 'border-green-500/20 hover:bg-green-500/10',
                  blue: 'border-blue-500/20 hover:bg-blue-500/10',
                  cyan: 'border-cyan-500/20 hover:bg-cyan-500/10',
                  yellow: 'border-yellow-500/20 hover:bg-yellow-500/10',
                  red: 'border-red-500/20 hover:bg-red-500/10',
                }
                const iconColorClasses = {
                  green: 'text-green-400',
                  blue: 'text-blue-400',
                  cyan: 'text-cyan-400',
                  yellow: 'text-yellow-400',
                  red: 'text-red-400',
                }
                const isActive = activeTab === item.id

                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left ${
                      isActive
                        ? `${colorClasses[item.color]} border-opacity-50 bg-opacity-20`
                        : 'border-gray-700/50 hover:border-gray-600/50'
                    }`}
                  >
                    <MenuIcon className={`w-5 h-5 flex-shrink-0 ${isActive ? iconColorClasses[item.color] : 'text-gray-500'}`} />
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${isActive ? 'text-white' : 'text-gray-400'}`}>
                        {item.label}
                      </div>
                    </div>
                    {isActive && (
                      <div className={`w-1.5 h-1.5 rounded-full ${item.color === 'green' ? 'bg-green-400' : item.color === 'blue' ? 'bg-blue-400' : item.color === 'cyan' ? 'bg-cyan-400' : item.color === 'yellow' ? 'bg-yellow-400' : 'bg-red-400'}`} />
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <form onSubmit={handleSubmit} className="space-y-6">
          {message && (
            <AlertInline variant={message.type === 'success' ? 'success' : 'error'}>
              {message.text}
            </AlertInline>
          )}

          {/* APIs & Credenciais Tab */}
          {activeTab === 'apis' && (
            <div className="space-y-6">
          {/* Vast.ai Configuration */}
          <Card className="border-green-500/20 bg-gradient-to-br from-[#1a2418] to-[#161a16]">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/20">
                  <Key className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <CardTitle className="text-white">Vast.ai</CardTitle>
                  <p className="text-gray-400 text-sm mt-1">Configuração para acesso à plataforma Vast.ai</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="form-group">
                <label className="form-label text-gray-300 block mb-2">API Key</label>
                <SecretInput
                  name="vast_api_key"
                  value={settings.vast_api_key}
                  onChange={handleChange}
                  placeholder="Enter your vast.ai API key"
                  validation={validations.vast_api_key}
                />
              </div>
            </CardContent>
          </Card>

          {/* Cloudflare R2 Configuration */}
          <Card className="border-blue-500/20 bg-gradient-to-br from-[#1a1f26] to-[#161a1f]">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Database className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <CardTitle className="text-white">Cloudflare R2</CardTitle>
                  <p className="text-gray-400 text-sm mt-1">Armazenamento em nuvem para snapshots e backups</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-group">
                  <label className="form-label text-gray-300 block mb-2">Access Key</label>
                  <SecretInput
                    name="r2_access_key"
                    value={settings.r2_access_key}
                    onChange={handleChange}
                    validation={validations.r2_access_key}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label text-gray-300 block mb-2">Secret Key</label>
                  <SecretInput
                    name="r2_secret_key"
                    value={settings.r2_secret_key}
                    onChange={handleChange}
                    validation={validations.r2_secret_key}
                  />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label text-gray-300 block mb-2">Endpoint URL</label>
                <ValidatedInput
                  name="r2_endpoint"
                  value={settings.r2_endpoint}
                  onChange={handleChange}
                  placeholder="https://xxx.r2.cloudflarestorage.com"
                  validation={validations.r2_endpoint}
                />
              </div>
              <div className="form-group">
                <label className="form-label text-gray-300 block mb-2">Bucket Name</label>
                <ValidatedInput
                  name="r2_bucket"
                  value={settings.r2_bucket}
                  onChange={handleChange}
                  validation={validations.r2_bucket}
                />
              </div>
            </CardContent>
          </Card>
            </div>
          )}

          {/* Storage Tab */}
          {activeTab === 'storage' && (
            <div className="space-y-6">
          {/* Restic Configuration */}
          <Card className="border-purple-500/20 bg-gradient-to-br from-[#1f1a26] to-[#161617]">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/20">
                  <Lock className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <CardTitle className="text-white">Restic</CardTitle>
                  <p className="text-gray-400 text-sm mt-1">Proteção e criptografia de repositórios</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="form-group">
                <label className="form-label text-gray-300 block mb-2">Repository Password</label>
                <SecretInput
                  name="restic_password"
                  value={settings.restic_password}
                  onChange={handleChange}
                  validation={validations.restic_password}
                />
              </div>
            </CardContent>
          </Card>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="space-y-6">
          {/* Notificações */}
          <Card className="border-yellow-500/20 bg-gradient-to-br from-[#1f1a0f] to-[#161510]">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-yellow-500/20">
                  <AlertCircle className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <CardTitle className="text-white">Notificações</CardTitle>
                  <p className="text-gray-400 text-sm mt-1">Alertas visuais e sonoros do sistema</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="form-group">
                <label className="form-label text-gray-300 block mb-2">Alertas de Saldo Baixo</label>
                <p className="text-gray-400 text-sm mb-4">
                  Receba alertas visuais e sonoros quando seu saldo estiver abaixo de $1.00.
                </p>
                <Button
                  type="button"
                  onClick={testNotification}
                  className="bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 border border-yellow-500/30"
                >
                  Testar Notificação
                </Button>
              </div>
            </CardContent>
          </Card>

              {/* Save Button */}
              <div className="flex flex-col sm:flex-row gap-3 pt-4">
                <button
                  type="submit"
                  disabled={saving || !isFormValid}
                  className="flex-1 py-3 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <span className="spinner" />
                      Salvando...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      Salvar Configurações
                    </>
                  )}
                </button>
                {!isFormValid && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 flex items-center gap-2 text-red-400 text-sm">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>Corrija os erros antes de salvar</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Agent Tab */}
          {activeTab === 'agent' && (
            <div className="space-y-6">
        {/* DumontAgent Configuration */}
        <Card className="border-cyan-500/20 bg-gradient-to-br from-[#1a262f] to-[#161a1f]">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-cyan-500/20">
                <Server className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <CardTitle className="text-white">DumontAgent</CardTitle>
                <p className="text-gray-400 text-sm mt-1">Sincronização automática em máquinas GPU</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-gray-400 text-sm mb-6">
              Configure como o agente de sincronização funciona nas máquinas GPU.
              Estas configurações serão aplicadas em novas máquinas.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="form-group">
                <label className="form-label text-gray-300 block mb-2">Intervalo de Sincronização</label>
                <select
                  name="sync_interval"
                  className="form-input w-full"
                  value={agentSettings.sync_interval}
                  onChange={handleAgentChange}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="30">30 segundos</option>
                  <option value="60">1 minuto</option>
                  <option value="120">2 minutos</option>
                  <option value="300">5 minutos</option>
                  <option value="600">10 minutos</option>
                </select>
                <small className="text-gray-500 text-xs mt-1 block">
                  Tempo entre cada backup automático
                </small>
              </div>
              <div className="form-group">
                <label className="form-label text-gray-300 block mb-2">Retenção de Snapshots</label>
                <select
                  name="keep_last"
                  className="form-input w-full"
                  value={agentSettings.keep_last}
                  onChange={handleAgentChange}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="5">Últimos 5</option>
                  <option value="10">Últimos 10</option>
                  <option value="20">Últimos 20</option>
                  <option value="50">Últimos 50</option>
                </select>
                <small className="text-gray-500 text-xs mt-1 block">
                  Quantidade de snapshots a manter
                </small>
              </div>
            </div>
            <button
              type="button"
              onClick={saveAgentSettings}
              disabled={savingAgent}
              className="py-2 px-4 rounded-lg font-semibold transition-all flex items-center gap-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {savingAgent ? (
                <>
                  <span className="spinner" />
                  Salvando...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Salvar Configurações
                </>
              )}
            </button>
          </CardContent>
        </Card>
            </div>
          )}

          {/* Failover Tab */}
          {activeTab === 'failover' && (
            <div className="space-y-6">
        {/* R2 Cost Estimator */}
        <Card className="border-orange-500/20 bg-gradient-to-br from-[#1f1510] to-[#161410]">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-500/20">
                <DollarSign className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <CardTitle className="text-white">Estimativa de Custo</CardTitle>
                <p className="text-gray-400 text-sm mt-1">Cloudflare R2 - Armazenamento em nuvem</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
          <p style={{ color: '#9ca3af', fontSize: '14px', marginBottom: '16px' }}>
            Calcule o custo mensal estimado do armazenamento no Cloudflare R2.
          </p>

          <div className="form-group" style={{ maxWidth: '300px' }}>
            <label className="form-label">Tamanho Estimado dos Dados (GB)</label>
            <input
              type="number"
              className="form-input"
              value={estimatedDataSize}
              onChange={(e) => setEstimatedDataSize(Math.max(1, parseInt(e.target.value) || 1))}
              min="1"
              max="1000"
            />
          </div>

          <div style={{
            background: '#0d1117',
            borderRadius: '8px',
            padding: '16px',
            marginTop: '16px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ color: '#9ca3af' }}>Storage ({r2Costs.effectiveStorage} GB efetivo)</span>
              <span style={{ color: '#c9d1d9' }}>${r2Costs.storage.toFixed(3)}/mes</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ color: '#9ca3af' }}>Operacoes (~{r2Costs.syncsPerMonth.toLocaleString()} syncs/mes)</span>
              <span style={{ color: '#c9d1d9' }}>${r2Costs.operations.toFixed(3)}/mes</span>
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              borderTop: '1px solid #30363d',
              paddingTop: '12px',
              marginTop: '4px'
            }}>
              <span style={{ color: '#c9d1d9', fontWeight: '600' }}>Total Estimado</span>
              <span style={{ color: '#3fb950', fontWeight: '700', fontSize: '1.1em' }}>
                ${r2Costs.total.toFixed(2)}/mes
              </span>
            </div>
          </div>

          <small style={{ color: '#6e7681', marginTop: '12px', display: 'block' }}>
            * Estimativa baseada em ~70% de deduplicacao pelo Restic e ~50 operacoes por sync.
            Egress (download) e gratuito no R2.
          </small>

          <div style={{
            background: '#1c2128',
            borderRadius: '8px',
            padding: '12px',
            marginTop: '16px',
            fontSize: '13px'
          }}>
            <strong style={{ color: '#58a6ff' }}>Comparativo de Intervalos:</strong>
            <div style={{ marginTop: '8px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#0d1117', borderRadius: '4px' }}>
                <div style={{ color: '#9ca3af', fontSize: '11px' }}>30 segundos</div>
                <div style={{ color: '#3fb950', fontWeight: '600' }}>~$0.25/mes</div>
              </div>
              <div style={{ textAlign: 'center', padding: '8px', background: '#0d1117', borderRadius: '4px' }}>
                <div style={{ color: '#9ca3af', fontSize: '11px' }}>1 minuto</div>
                <div style={{ color: '#3fb950', fontWeight: '600' }}>~$0.15/mes</div>
              </div>
              <div style={{ textAlign: 'center', padding: '8px', background: '#0d1117', borderRadius: '4px' }}>
                <div style={{ color: '#9ca3af', fontSize: '11px' }}>5 minutos</div>
                <div style={{ color: '#3fb950', fontWeight: '600' }}>~$0.07/mes</div>
              </div>
            </div>
            <div style={{ color: '#9ca3af', marginTop: '8px', fontSize: '11px' }}>
              * Valores para 10GB de dados
            </div>
          </div>
          </CardContent>
        </Card>

        {/* CPU Standby / Failover Configuration */}
        <StandbyConfig getAuthHeaders={() => {
          const token = localStorage.getItem('auth_token')
          return token ? { 'Authorization': `Bearer ${token}` } : {}
        }} />
            </div>
          )}
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
