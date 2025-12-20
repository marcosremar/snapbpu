import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, Check, X, AlertCircle, Key, Database, Lock, Server, DollarSign, Shield, Cloud, HardDrive } from 'lucide-react'
import { useToast } from '../components/Toast'
import StandbyConfig from '../components/StandbyConfig'
import FailoverReport from '../components/FailoverReport'
import { Alert, Card, Button } from '../components/tailadmin-ui'

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
        <div className="mt-2">
          <Alert variant={validation.valid ? 'success' : 'error'}>
            <span className="text-xs">{validation.message}</span>
          </Alert>
        </div>
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
        <div className="mt-2">
          <Alert variant={validation.valid ? 'success' : 'error'}>
            <span className="text-xs">{validation.message}</span>
          </Alert>
        </div>
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
  { id: 'cloudstorage', label: 'Cloud Storage Failover', icon: Cloud, color: 'purple' },
  { id: 'agent', label: 'Agent Sync', icon: Server, color: 'cyan' },
  { id: 'notifications', label: 'Notificações', icon: AlertCircle, color: 'yellow' },
  { id: 'failover', label: 'CPU Failover', icon: Shield, color: 'red' },
]

// Cloud Storage Providers
const CLOUD_STORAGE_PROVIDERS = [
  {
    id: 'backblaze_b2',
    name: 'Backblaze B2',
    description: 'Armazenamento de baixo custo, ~$0.005/GB/mês',
    icon: '🅱️',
    color: 'red',
    fields: ['key_id', 'app_key', 'bucket']
  },
  {
    id: 'cloudflare_r2',
    name: 'Cloudflare R2',
    description: 'Zero egress fees, ~$0.015/GB/mês',
    icon: '☁️',
    color: 'orange',
    fields: ['access_key', 'secret_key', 'endpoint', 'bucket']
  },
  {
    id: 'aws_s3',
    name: 'Amazon S3',
    description: 'Alta disponibilidade, multi-região',
    icon: '📦',
    color: 'yellow',
    fields: ['access_key', 'secret_key', 'region', 'bucket']
  },
  {
    id: 'google_gcs',
    name: 'Google Cloud Storage',
    description: 'Integração com GCP, multi-região',
    icon: '🔷',
    color: 'blue',
    fields: ['credentials_json', 'bucket']
  },
]

export default function Settings() {
  const toast = useToast()
  const [searchParams] = useSearchParams()
  const tabFromUrl = searchParams.get('tab')
  const [activeTab, setActiveTab] = useState(tabFromUrl || 'apis')
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

  // Cloud Storage Failover settings
  const [cloudStorageSettings, setCloudStorageSettings] = useState({
    enabled: false,
    primary_provider: 'backblaze_b2',
    mount_method: 'rclone',
    mount_path: '/data',
    cache_size_gb: 10,
    // Backblaze B2
    b2_key_id: '',
    b2_app_key: '',
    b2_bucket: '',
    // Cloudflare R2 (já existe no settings principal)
    // AWS S3
    s3_access_key: '',
    s3_secret_key: '',
    s3_region: 'us-east-1',
    s3_bucket: '',
    // Google Cloud Storage
    gcs_credentials_json: '',
    gcs_bucket: '',
  })
  const [savingCloudStorage, setSavingCloudStorage] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)

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
    loadCloudStorageSettings()
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

  // Cloud Storage handlers
  const handleCloudStorageChange = (e) => {
    const { name, value, type, checked } = e.target
    setCloudStorageSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const saveCloudStorageSettings = async () => {
    setSavingCloudStorage(true)
    try {
      const res = await fetch(`${API_BASE}/api/settings/cloud-storage`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cloudStorageSettings),
        credentials: 'include'
      })
      const data = await res.json()
      if (data.success) {
        toast.success('Configurações de Cloud Storage salvas!')
      } else {
        toast.error(data.error || 'Falha ao salvar configurações')
      }
    } catch (e) {
      toast.error('Erro de conexão')
    }
    setSavingCloudStorage(false)
  }

  const testCloudStorageConnection = async () => {
    setTestingConnection(true)
    try {
      const res = await fetch(`${API_BASE}/api/settings/cloud-storage/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cloudStorageSettings),
        credentials: 'include'
      })
      const data = await res.json()
      if (data.success) {
        toast.success(`Conexão com ${cloudStorageSettings.primary_provider} OK!`)
      } else {
        toast.error(data.error || 'Falha ao testar conexão')
      }
    } catch (e) {
      toast.error('Erro ao testar conexão')
    }
    setTestingConnection(false)
  }

  const loadCloudStorageSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/cloud-storage`, { credentials: 'include' })
      const data = await res.json()
      if (data.settings) {
        setCloudStorageSettings(prev => ({ ...prev, ...data.settings }))
      }
    } catch (e) {
      console.error('Failed to load cloud storage settings:', e)
    }
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
      <div className="page-container">
        <div className="flex items-center justify-center py-20">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Toast de notificação */}
      {showToast && (
        <Toast
          title="Teste de Notificação"
          message="As notificações estão funcionando corretamente!"
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}

      {/* Page Header - TailAdmin Style */}
      <div className="page-header">
        <h1 className="page-title">Configurações</h1>
        <p className="page-subtitle">Gerencie suas APIs, armazenamento e preferências</p>
      </div>

      {/* Layout: Sidebar + Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Menu */}
        <div className="lg:col-span-1">
          <div className="ta-card sticky top-6">
            <div className="p-2">
              {SETTINGS_MENU.map((item) => {
                const MenuIcon = item.icon
                const iconColorClasses = {
                  green: 'stat-card-icon-success',
                  blue: 'stat-card-icon-primary',
                  cyan: 'stat-card-icon-primary',
                  purple: 'bg-purple-500/20 text-purple-400',
                  yellow: 'stat-card-icon-warning',
                  red: 'stat-card-icon-error',
                }
                const isActive = activeTab === item.id

                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-left mb-1 ${
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'text-gray-400 hover:bg-white/10 hover:text-gray-200'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconColorClasses[item.color]}`}>
                      <MenuIcon className="w-4 h-4" />
                    </div>
                    <span className="text-sm font-medium">{item.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3">
          <form onSubmit={handleSubmit} className="space-y-6">
          {message && (
            <Alert variant={message.type === 'success' ? 'success' : 'error'}>
              {message.text}
            </Alert>
          )}

          {/* APIs & Credenciais Tab */}
          {activeTab === 'apis' && (
            <div className="space-y-6">
          {/* Vast.ai Configuration */}
          <Card
            className="border-green-500/20 bg-gradient-to-br from-[#1a2418] to-[#161a16]"
            header={
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/20">
                  <Key className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Vast.ai</h3>
                  <p className="text-gray-400 text-sm mt-1">Configuração para acesso à plataforma Vast.ai</p>
                </div>
              </div>
            }
          >
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
          </Card>

          {/* Cloudflare R2 Configuration */}
          <Card
            className="border-cyan-500/20 bg-gradient-to-br from-cyan-900/10 to-dark-surface-card"
            header={
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-500/20">
                  <Database className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Cloudflare R2</h3>
                  <p className="text-gray-400 text-sm mt-1">Armazenamento em nuvem para snapshots e backups</p>
                </div>
              </div>
            }
          >
            <div className="space-y-4">
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
            </div>
          </Card>
            </div>
          )}

          {/* Storage Tab */}
          {activeTab === 'storage' && (
            <div className="space-y-6">
          {/* Restic Configuration */}
          <Card
            className="border-purple-500/20 bg-gradient-to-br from-[#1f1a26] to-[#161617]"
            header={
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/20">
                  <Lock className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Restic</h3>
                  <p className="text-gray-400 text-sm mt-1">Proteção e criptografia de repositórios</p>
                </div>
              </div>
            }
          >
            <div className="form-group">
              <label className="form-label text-gray-300 block mb-2">Repository Password</label>
              <SecretInput
                name="restic_password"
                value={settings.restic_password}
                onChange={handleChange}
                validation={validations.restic_password}
              />
            </div>
          </Card>
            </div>
          )}

          {/* Cloud Storage Failover Tab */}
          {activeTab === 'cloudstorage' && (
            <div className="space-y-6">
              {/* Header Card */}
              <Card
                className="border-purple-500/20 bg-gradient-to-br from-[#1f1a26] to-[#161617]"
                header={
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-purple-500/20">
                      <Cloud className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">Cloud Storage Failover</h3>
                      <p className="text-gray-400 text-sm mt-1">Configure provedores de storage para failover global</p>
                    </div>
                  </div>
                }
              >
                <div className="space-y-4">
                  {/* Enable/Disable Toggle */}
                  <div className="flex items-center justify-between p-4 bg-white/5 border border-white/10 rounded-lg">
                    <div>
                      <h4 className="text-white font-medium">Habilitar Cloud Storage Failover</h4>
                      <p className="text-gray-400 text-sm mt-1">
                        Permite failover para qualquer região global usando cloud storage
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        name="enabled"
                        checked={cloudStorageSettings.enabled}
                        onChange={handleCloudStorageChange}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-500"></div>
                    </label>
                  </div>

                  {/* Provedor Principal */}
                  <div className="form-group">
                    <label className="form-label text-gray-300 block mb-2">Provedor de Storage</label>
                    <select
                      name="primary_provider"
                      className="form-input w-full"
                      value={cloudStorageSettings.primary_provider}
                      onChange={handleCloudStorageChange}
                      style={{ cursor: 'pointer' }}
                    >
                      {CLOUD_STORAGE_PROVIDERS.map(provider => (
                        <option key={provider.id} value={provider.id}>
                          {provider.icon} {provider.name} - {provider.description}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Método de Montagem */}
                  <div className="form-group">
                    <label className="form-label text-gray-300 block mb-2">Método de Montagem</label>
                    <select
                      name="mount_method"
                      className="form-input w-full"
                      value={cloudStorageSettings.mount_method}
                      onChange={handleCloudStorageChange}
                      style={{ cursor: 'pointer' }}
                    >
                      <option value="rclone">rclone mount (FUSE com VFS cache)</option>
                      <option value="restic">restic restore (snapshot completo)</option>
                      <option value="s3fs">s3fs (compatível S3)</option>
                    </select>
                    <small className="text-gray-500 text-xs mt-1 block">
                      rclone é recomendado para melhor performance com cache local
                    </small>
                  </div>

                  {/* Configurações de Cache */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="form-group">
                      <label className="form-label text-gray-300 block mb-2">Caminho de Montagem</label>
                      <input
                        type="text"
                        name="mount_path"
                        className="form-input w-full"
                        value={cloudStorageSettings.mount_path}
                        onChange={handleCloudStorageChange}
                        placeholder="/data"
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label text-gray-300 block mb-2">Tamanho do Cache (GB)</label>
                      <input
                        type="number"
                        name="cache_size_gb"
                        className="form-input w-full"
                        value={cloudStorageSettings.cache_size_gb}
                        onChange={handleCloudStorageChange}
                        min="1"
                        max="100"
                      />
                    </div>
                  </div>
                </div>
              </Card>

              {/* Backblaze B2 Configuration */}
              {cloudStorageSettings.primary_provider === 'backblaze_b2' && (
                <Card
                  className="border-red-500/20 bg-gradient-to-br from-[#261a1a] to-[#171616]"
                  header={
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-red-500/20">
                        <span className="text-xl">🅱️</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">Backblaze B2</h3>
                        <p className="text-gray-400 text-sm mt-1">Armazenamento de baixo custo (~$0.005/GB/mês)</p>
                      </div>
                    </div>
                  }
                >
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="form-group">
                        <label className="form-label text-gray-300 block mb-2">Key ID</label>
                        <SecretInput
                          name="b2_key_id"
                          value={cloudStorageSettings.b2_key_id}
                          onChange={handleCloudStorageChange}
                          placeholder="000xxxxxxxxxxxxx"
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label text-gray-300 block mb-2">Application Key</label>
                        <SecretInput
                          name="b2_app_key"
                          value={cloudStorageSettings.b2_app_key}
                          onChange={handleCloudStorageChange}
                          placeholder="K000xxxxxxxxxxxxxxxxxxxxxxxxxx"
                        />
                      </div>
                    </div>
                    <div className="form-group">
                      <label className="form-label text-gray-300 block mb-2">Bucket Name</label>
                      <input
                        type="text"
                        name="b2_bucket"
                        className="form-input w-full"
                        value={cloudStorageSettings.b2_bucket}
                        onChange={handleCloudStorageChange}
                        placeholder="my-bucket-name"
                      />
                    </div>
                  </div>
                </Card>
              )}

              {/* AWS S3 Configuration */}
              {cloudStorageSettings.primary_provider === 'aws_s3' && (
                <Card
                  className="border-yellow-500/20 bg-gradient-to-br from-[#26251a] to-[#171716]"
                  header={
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-yellow-500/20">
                        <span className="text-xl">📦</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">Amazon S3</h3>
                        <p className="text-gray-400 text-sm mt-1">Alta disponibilidade, multi-região</p>
                      </div>
                    </div>
                  }
                >
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="form-group">
                        <label className="form-label text-gray-300 block mb-2">Access Key ID</label>
                        <SecretInput
                          name="s3_access_key"
                          value={cloudStorageSettings.s3_access_key}
                          onChange={handleCloudStorageChange}
                          placeholder="AKIAIOSFODNN7EXAMPLE"
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label text-gray-300 block mb-2">Secret Access Key</label>
                        <SecretInput
                          name="s3_secret_key"
                          value={cloudStorageSettings.s3_secret_key}
                          onChange={handleCloudStorageChange}
                          placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="form-group">
                        <label className="form-label text-gray-300 block mb-2">Region</label>
                        <select
                          name="s3_region"
                          className="form-input w-full"
                          value={cloudStorageSettings.s3_region}
                          onChange={handleCloudStorageChange}
                          style={{ cursor: 'pointer' }}
                        >
                          <option value="us-east-1">US East (N. Virginia)</option>
                          <option value="us-west-2">US West (Oregon)</option>
                          <option value="eu-west-1">EU (Ireland)</option>
                          <option value="eu-central-1">EU (Frankfurt)</option>
                          <option value="ap-northeast-1">Asia Pacific (Tokyo)</option>
                          <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
                          <option value="sa-east-1">South America (São Paulo)</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label text-gray-300 block mb-2">Bucket Name</label>
                        <input
                          type="text"
                          name="s3_bucket"
                          className="form-input w-full"
                          value={cloudStorageSettings.s3_bucket}
                          onChange={handleCloudStorageChange}
                          placeholder="my-bucket-name"
                        />
                      </div>
                    </div>
                  </div>
                </Card>
              )}

              {/* Google Cloud Storage Configuration */}
              {cloudStorageSettings.primary_provider === 'google_gcs' && (
                <Card
                  className="border-blue-500/20 bg-gradient-to-br from-[#1a1f26] to-[#161617]"
                  header={
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-blue-500/20">
                        <span className="text-xl">🔷</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">Google Cloud Storage</h3>
                        <p className="text-gray-400 text-sm mt-1">Integração com GCP, multi-região</p>
                      </div>
                    </div>
                  }
                >
                  <div className="space-y-4">
                    <div className="form-group">
                      <label className="form-label text-gray-300 block mb-2">Service Account JSON</label>
                      <textarea
                        name="gcs_credentials_json"
                        className="form-input w-full font-mono text-xs"
                        value={cloudStorageSettings.gcs_credentials_json}
                        onChange={handleCloudStorageChange}
                        placeholder='{"type": "service_account", ...}'
                        rows={4}
                      />
                      <small className="text-gray-500 text-xs mt-1 block">
                        Cole o JSON completo da chave de serviço
                      </small>
                    </div>
                    <div className="form-group">
                      <label className="form-label text-gray-300 block mb-2">Bucket Name</label>
                      <input
                        type="text"
                        name="gcs_bucket"
                        className="form-input w-full"
                        value={cloudStorageSettings.gcs_bucket}
                        onChange={handleCloudStorageChange}
                        placeholder="my-gcs-bucket"
                      />
                    </div>
                  </div>
                </Card>
              )}

              {/* Cloudflare R2 - Usa as mesmas settings de R2 */}
              {cloudStorageSettings.primary_provider === 'cloudflare_r2' && (
                <Card
                  className="border-orange-500/20 bg-gradient-to-br from-[#261f1a] to-[#171616]"
                  header={
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-orange-500/20">
                        <span className="text-xl">☁️</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">Cloudflare R2</h3>
                        <p className="text-gray-400 text-sm mt-1">Zero egress fees (~$0.015/GB/mês)</p>
                      </div>
                    </div>
                  }
                >
                  <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                    <p className="text-blue-300 text-sm">
                      <strong>Nota:</strong> As credenciais do Cloudflare R2 são configuradas na aba "APIs & Credenciais".
                      Se você já configurou o R2 lá, ele estará pronto para uso.
                    </p>
                  </div>
                </Card>
              )}

              {/* Comparativo de Tempos */}
              <Card
                className="border-gray-500/20 bg-gradient-to-br from-[#1a1a1f] to-[#161617]"
                header={
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-gray-500/20">
                      <HardDrive className="w-5 h-5 text-gray-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">Comparativo de Estratégias</h3>
                      <p className="text-gray-400 text-sm mt-1">Tempo estimado de failover para cada estratégia</p>
                    </div>
                  </div>
                }
              >
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                    <div className="text-2xl font-bold text-green-400">~6s</div>
                    <div className="text-gray-400 text-sm mt-1">GPU Warm Pool</div>
                    <div className="text-gray-500 text-xs">Mesmo host</div>
                  </div>
                  <div className="text-center p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                    <div className="text-2xl font-bold text-blue-400">~23s</div>
                    <div className="text-gray-400 text-sm mt-1">Regional Volume</div>
                    <div className="text-gray-500 text-xs">Mesma região</div>
                  </div>
                  <div className="text-center p-4 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                    <div className="text-2xl font-bold text-purple-400">~47s</div>
                    <div className="text-gray-400 text-sm mt-1">Cloud Storage</div>
                    <div className="text-gray-500 text-xs">Qualquer região</div>
                  </div>
                  <div className="text-center p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <div className="text-2xl font-bold text-red-400">~600s</div>
                    <div className="text-gray-400 text-sm mt-1">CPU Standby</div>
                    <div className="text-gray-500 text-xs">GCP/AWS</div>
                  </div>
                </div>
              </Card>

              {/* Save Button */}
              <div className="flex flex-col sm:flex-row gap-3 pt-4">
                <button
                  type="button"
                  onClick={testCloudStorageConnection}
                  disabled={testingConnection || !cloudStorageSettings.enabled}
                  className="py-3 px-6 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {testingConnection ? (
                    <>
                      <span className="spinner" />
                      Testando...
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-4 h-4" />
                      Testar Conexão
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={saveCloudStorageSettings}
                  disabled={savingCloudStorage}
                  className="flex-1 py-3 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {savingCloudStorage ? (
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
              </div>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="space-y-6">
          {/* Notificações */}
          <Card
            className="border-yellow-500/20 bg-gradient-to-br from-[#1f1a0f] to-[#161510]"
            header={
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-yellow-500/20">
                  <AlertCircle className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Notificações</h3>
                  <p className="text-gray-400 text-sm mt-1">Alertas visuais e sonoros do sistema</p>
                </div>
              </div>
            }
          >
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
        <Card
          className="border-cyan-500/20 bg-gradient-to-br from-[#1a262f] to-[#161a1f]"
          header={
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-cyan-500/20">
                <Server className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">DumontAgent</h3>
                <p className="text-gray-400 text-sm mt-1">Sincronização automática em máquinas GPU</p>
              </div>
            </div>
          }
        >
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
        </Card>
            </div>
          )}

          {/* Failover Tab */}
          {activeTab === 'failover' && (
            <div className="space-y-6">
        {/* R2 Cost Estimator */}
        <Card
          className="border-orange-500/20 bg-gradient-to-br from-[#1f1510] to-[#161410]"
          header={
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-500/20">
                <DollarSign className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Estimativa de Custo</h3>
                <p className="text-gray-400 text-sm mt-1">Cloudflare R2 - Armazenamento em nuvem</p>
              </div>
            </div>
          }
        >
          <div>
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
          </div>
        </Card>

        {/* CPU Standby / Failover Configuration */}
        <StandbyConfig getAuthHeaders={() => {
          const token = localStorage.getItem('auth_token')
          return token ? { 'Authorization': `Bearer ${token}` } : {}
        }} />

        {/* Failover Report - Histórico e Métricas */}
        <FailoverReport isDemo={localStorage.getItem('demo_mode') === 'true'} />
          </div>
        )}
          </form>
        </div>
      </div>
    </div>
  )
}
