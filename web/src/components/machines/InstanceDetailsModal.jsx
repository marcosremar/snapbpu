import { useState, useEffect, useRef } from 'react'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../tailadmin-ui'
import {
  X,
  MessageSquare,
  Info,
  Cpu,
  HardDrive,
  Globe,
  Clock,
  DollarSign,
  Server,
  Zap,
  Send,
  RefreshCw,
  Terminal,
  Copy,
  Check,
} from 'lucide-react'

export default function InstanceDetailsModal({ machine, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('details')
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [ollamaStatus, setOllamaStatus] = useState('checking') // checking, available, unavailable
  const [ollamaModels, setOllamaModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [copiedField, setCopiedField] = useState(null)
  const messagesEndRef = useRef(null)

  // Get Ollama URL from machine ports
  const getOllamaUrl = () => {
    if (!machine) return null

    // Check for mapped port 11434 (Ollama default)
    const ports = machine.ports || {}
    const ollamaPort = ports['11434/tcp']

    if (ollamaPort && ollamaPort[0]?.HostPort && machine.public_ipaddr) {
      return `http://${machine.public_ipaddr}:${ollamaPort[0].HostPort}`
    }

    // Check if direct_port_end is set (Vast.ai uses this for port mapping range)
    // Port mapping: internal 11434 maps to public_ipaddr:direct_port_start + offset
    if (machine.direct_port_end && machine.public_ipaddr) {
      const portOffset = 11434 - 8080 // Assuming ports start at 8080 internal
      const mappedPort = (machine.direct_port_start || 10000) + portOffset
      return `http://${machine.public_ipaddr}:${mappedPort}`
    }

    // Fallback: try common port mappings
    if (machine.public_ipaddr) {
      // For Vast.ai instances, Ollama on 11434 is often mapped to 11434 + (ssh_port - 22000) range
      // Try direct port first
      return `http://${machine.public_ipaddr}:11434`
    }

    return null
  }

  // Try multiple ports for Ollama
  const tryOllamaPorts = async () => {
    if (!machine?.public_ipaddr) return null

    // Common port mappings to try
    const portsToTry = [
      11434, // Default Ollama port
      14367, // Common mapped port (offset from ssh port)
      machine.ssh_port ? (machine.ssh_port - 22000 + 11434) : null, // Calculated from SSH port
      machine.ssh_port ? (machine.ssh_port - 10000 + 11434) : null,
    ].filter(p => p && p > 0)

    for (const port of portsToTry) {
      try {
        const url = `http://${machine.public_ipaddr}:${port}`
        const response = await fetch(`${url}/api/tags`, {
          signal: AbortSignal.timeout(3000)
        })
        if (response.ok) {
          return url
        }
      } catch (e) {
        // Continue to next port
      }
    }
    return null
  }

  // Check Ollama availability and fetch models
  const checkOllama = async () => {
    const url = getOllamaUrl()
    if (!url) {
      setOllamaStatus('unavailable')
      return
    }

    try {
      setOllamaStatus('checking')
      const response = await fetch(`${url}/api/tags`, {
        signal: AbortSignal.timeout(5000)
      })

      if (response.ok) {
        const data = await response.json()
        if (data.models && data.models.length > 0) {
          setOllamaModels(data.models)
          setSelectedModel(data.models[0].name)
          setOllamaStatus('available')
        } else {
          setOllamaStatus('no_models')
        }
      } else {
        setOllamaStatus('unavailable')
      }
    } catch (err) {
      console.error('Failed to check Ollama:', err)
      setOllamaStatus('unavailable')
    }
  }

  // Check Ollama when modal opens or machine changes
  useEffect(() => {
    if (isOpen && machine && machine.actual_status === 'running') {
      checkOllama()
    }
    return () => {
      setMessages([])
      setOllamaStatus('checking')
    }
  }, [isOpen, machine?.id])

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputText.trim() || !selectedModel || loading) return

    const userMsg = { role: 'user', content: inputText }
    setMessages(prev => [...prev, userMsg])
    setInputText('')
    setLoading(true)

    try {
      const url = getOllamaUrl()
      if (!url) throw new Error('Ollama URL not available')

      const response = await fetch(`${url}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          messages: [...messages, userMsg],
          stream: false
        })
      })

      if (!response.ok) {
        throw new Error(`Request failed: ${response.statusText}`)
      }

      const data = await response.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.message.content }])

    } catch (error) {
      console.error('Send failed:', error)
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error: ${error.message}`
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const formatUptime = (startTime) => {
    if (!startTime) return 'N/A'
    const start = new Date(startTime).getTime()
    const now = Date.now()
    const diff = now - start
    const hours = Math.floor(diff / 3600000)
    const minutes = Math.floor((diff % 3600000) / 60000)
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  if (!machine) return null

  const isRunning = machine.actual_status === 'running'
  const gpuRam = Math.round((machine.gpu_ram || 24000) / 1024)
  const cpuCores = machine.cpu_cores || 4
  const ram = machine.cpu_ram ? (machine.cpu_ram > 1000 ? Math.round(machine.cpu_ram / 1024) : Math.round(machine.cpu_ram)) : 16
  const disk = Math.round(machine.disk_space || 100)
  const costPerHour = machine.dph_total || machine.total_dph || 0

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-4xl w-[90vw] max-h-[85vh] overflow-hidden flex flex-col">
        <AlertDialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <AlertDialogTitle className="flex items-center gap-3">
              <div className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
              <span>{machine.gpu_name || 'GPU Instance'}</span>
              <span className="text-xs font-normal text-gray-500">#{machine.id}</span>
            </AlertDialogTitle>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4 border-b border-gray-700">
            <button
              onClick={() => setActiveTab('details')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === 'details'
                  ? 'text-green-400 border-green-400'
                  : 'text-gray-400 border-transparent hover:text-gray-300'
              }`}
            >
              <Info className="w-4 h-4" />
              Detalhes
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === 'chat'
                  ? 'text-green-400 border-green-400'
                  : 'text-gray-400 border-transparent hover:text-gray-300'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              Chat
              {ollamaStatus === 'available' && (
                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              )}
            </button>
          </div>
        </AlertDialogHeader>

        <div className="flex-1 overflow-y-auto mt-4">
          {activeTab === 'details' && (
            <div className="space-y-6 p-1">
              {/* Status Card */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                  <Server className="w-4 h-4 text-green-400" />
                  Status da Instância
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-gray-500">Status</span>
                    <p className={`font-medium ${isRunning ? 'text-green-400' : 'text-gray-400'}`}>
                      {isRunning ? 'Running' : machine.actual_status || 'Offline'}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Uptime</span>
                    <p className="font-medium text-white flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-gray-400" />
                      {isRunning ? formatUptime(machine.start_date || machine.created_at) : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Custo/Hora</span>
                    <p className="font-medium text-green-400 flex items-center gap-1.5">
                      <DollarSign className="w-3.5 h-3.5" />
                      ${costPerHour.toFixed(3)}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Provider</span>
                    <p className="font-medium text-white">Vast.ai</p>
                  </div>
                </div>
              </div>

              {/* Hardware Card */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-blue-400" />
                  Hardware
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-gray-500">GPU</span>
                    <p className="font-medium text-white">{machine.gpu_name || 'Unknown'}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">VRAM</span>
                    <p className="font-medium text-white">{gpuRam} GB</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">CPU Cores</span>
                    <p className="font-medium text-white">{cpuCores}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">RAM</span>
                    <p className="font-medium text-white">{ram} GB</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Disk</span>
                    <p className="font-medium text-white flex items-center gap-1.5">
                      <HardDrive className="w-3.5 h-3.5 text-gray-400" />
                      {disk} GB
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">GPU Utilization</span>
                    <p className="font-medium text-white">
                      {machine.gpu_util ? `${Number(machine.gpu_util).toFixed(0)}%` : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Network Card */}
              {isRunning && (
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <Globe className="w-4 h-4 text-purple-400" />
                    Conexão
                  </h3>
                  <div className="space-y-3">
                    {machine.public_ipaddr && (
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-xs text-gray-500">IP Público</span>
                          <p className="font-mono text-sm text-white">{machine.public_ipaddr}</p>
                        </div>
                        <button
                          onClick={() => copyToClipboard(machine.public_ipaddr, 'ip')}
                          className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white"
                        >
                          {copiedField === 'ip' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                        </button>
                      </div>
                    )}
                    {machine.ssh_host && machine.ssh_port && (
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-xs text-gray-500">SSH</span>
                          <p className="font-mono text-sm text-white">ssh -p {machine.ssh_port} root@{machine.ssh_host}</p>
                        </div>
                        <button
                          onClick={() => copyToClipboard(`ssh -p ${machine.ssh_port} root@${machine.ssh_host}`, 'ssh')}
                          className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white"
                        >
                          {copiedField === 'ssh' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Ollama Status Card */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-400" />
                  Ollama / LLM
                </h3>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs text-gray-500">Status</span>
                    <p className={`font-medium ${
                      ollamaStatus === 'available' ? 'text-green-400' :
                      ollamaStatus === 'checking' ? 'text-yellow-400' : 'text-gray-400'
                    }`}>
                      {ollamaStatus === 'checking' && 'Verificando...'}
                      {ollamaStatus === 'available' && `Disponível (${ollamaModels.length} modelo${ollamaModels.length > 1 ? 's' : ''})`}
                      {ollamaStatus === 'no_models' && 'Sem modelos instalados'}
                      {ollamaStatus === 'unavailable' && 'Não disponível'}
                    </p>
                  </div>
                  <button
                    onClick={checkOllama}
                    className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white"
                  >
                    <RefreshCw className={`w-4 h-4 ${ollamaStatus === 'checking' ? 'animate-spin' : ''}`} />
                  </button>
                </div>
                {ollamaStatus === 'available' && ollamaModels.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {ollamaModels.map(model => (
                      <div key={model.name} className="text-xs font-mono text-gray-400 bg-black/20 px-2 py-1 rounded flex items-center gap-2">
                        <Terminal className="w-3 h-3" />
                        {model.name}
                        <span className="text-gray-600">({(model.size / 1024 / 1024 / 1024).toFixed(1)} GB)</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="flex flex-col h-[400px]">
              {ollamaStatus === 'available' ? (
                <>
                  {/* Model Selector */}
                  <div className="flex items-center gap-3 mb-3 p-3 bg-white/5 rounded-lg border border-white/10">
                    <Terminal className="w-4 h-4 text-gray-400" />
                    <select
                      value={selectedModel || ''}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="flex-1 bg-transparent text-white text-sm focus:outline-none"
                    >
                      {ollamaModels.map(model => (
                        <option key={model.name} value={model.name} className="bg-gray-800">
                          {model.name}
                        </option>
                      ))}
                    </select>
                    <span className="text-xs text-gray-500">{getOllamaUrl()}</span>
                  </div>

                  {/* Messages Area */}
                  <div className="flex-1 overflow-y-auto space-y-3 mb-3 p-1">
                    {messages.length === 0 && (
                      <div className="text-center py-10 text-gray-500">
                        <MessageSquare className="w-8 h-8 mx-auto mb-3 opacity-50" />
                        <p>Comece uma conversa com o modelo...</p>
                      </div>
                    )}
                    {messages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[85%] rounded-xl p-3 text-sm ${
                            msg.role === 'user'
                              ? 'bg-green-600 text-white rounded-br-none'
                              : msg.role === 'system'
                              ? 'bg-red-900/50 text-red-300 border border-red-700/50'
                              : 'bg-gray-800 text-gray-200 border border-gray-700 rounded-bl-none'
                          }`}
                        >
                          {msg.content}
                        </div>
                      </div>
                    ))}
                    {loading && (
                      <div className="flex justify-start">
                        <div className="bg-gray-800 border border-gray-700 rounded-xl rounded-bl-none p-3 flex gap-1">
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" />
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.1s' }} />
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.2s' }} />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>

                  {/* Input Area */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Digite sua mensagem..."
                      disabled={loading}
                      className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-500/50 placeholder-gray-500"
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={loading || !inputText.trim()}
                      className="px-4 py-2.5 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  {ollamaStatus === 'checking' ? (
                    <>
                      <RefreshCw className="w-8 h-8 animate-spin mb-3" />
                      <p>Verificando disponibilidade do Ollama...</p>
                    </>
                  ) : (
                    <>
                      <MessageSquare className="w-12 h-12 mb-4 opacity-30" />
                      <p className="text-lg font-medium text-gray-400 mb-2">Chat não disponível</p>
                      <p className="text-sm text-center max-w-xs">
                        {!isRunning
                          ? 'A instância precisa estar rodando para usar o chat.'
                          : 'Ollama não está rodando nesta instância ou não está acessível.'}
                      </p>
                      {isRunning && (
                        <button
                          onClick={checkOllama}
                          className="mt-4 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors"
                        >
                          Tentar novamente
                        </button>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}
