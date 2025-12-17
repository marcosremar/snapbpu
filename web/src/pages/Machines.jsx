import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Line } from 'react-chartjs-2'
import { apiGet, apiPost, apiDelete } from '../utils/api'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog'
import { ChevronDown, MoreVertical, Play, Plus, Server, Cpu, Clock, Activity, Code, Settings, Trash2, Download, Copy, Key, Terminal } from 'lucide-react'
import HibernationConfigModal from '../components/HibernationConfigModal'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler)

// Mini sparkline chart component
function SparklineChart({ data, color }) {
  const chartData = {
    labels: data.map((_, i) => i),
    datasets: [{
      data,
      borderColor: color,
      backgroundColor: `${color}15`,
      borderWidth: 1.5,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
    }]
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { display: false },
      y: { display: false, min: 0, max: 100 }
    },
    elements: { line: { borderCapStyle: 'round' } }
  }

  return (
    <div className="h-8 w-full">
      <Line data={chartData} options={options} />
    </div>
  )
}

// Stat Card Component
function StatCard({ icon: Icon, value, label, color }) {
  const colorClasses = {
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  }

  return (
    <div className={`flex items-center gap-4 p-4 rounded-xl border ${colorClasses[color]}`} style={{ backgroundColor: '#1a1f1a' }}>
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  )
}

// Machine Card Component - Dashboard Style
function MachineCard({ machine, onDestroy, onStart, onRestoreToNew }) {
  const [showMenu, setShowMenu] = useState(false)
  const [hibernateTime, setHibernateTime] = useState(10)
  const [smartIdle, setSmartIdle] = useState(false)
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showSSHInstructions, setShowSSHInstructions] = useState(false)
  const [alertDialog, setAlertDialog] = useState({ open: false, title: '', description: '', action: null })

  // Historical data for sparklines
  const [gpuHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 40 + 30))
  const [memHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 30 + 40))
  const [cpuHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 20 + 10))
  const [tempHistory] = useState(() => Array.from({ length: 20 }, () => Math.random() * 15 + 55))

  const gpuUtil = machine.gpu_util ? Number(machine.gpu_util).toFixed(1) : Math.round(gpuHistory[gpuHistory.length - 1])
  const memUtil = machine.mem_usage ? Number(machine.mem_usage).toFixed(1) : Math.round(memHistory[memHistory.length - 1])
  const cpuUtil = machine.cpu_util ? Number(machine.cpu_util).toFixed(1) : Math.round(cpuHistory[cpuHistory.length - 1])
  const temp = machine.gpu_temp ? Number(machine.gpu_temp).toFixed(1) : Math.round(tempHistory[tempHistory.length - 1])

  const gpuName = machine.gpu_name || 'GPU'
  const isRunning = machine.actual_status === 'running'
  const costPerHour = machine.dph_total || 0
  const status = machine.actual_status || 'stopped'

  // SSH functions
  const generateSSHConfig = () => {
    return `Host dumont-${machine.id}
  HostName ${machine.ssh_host || 'ssh.vast.ai'}
  Port ${machine.ssh_port || 22}
  User root
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  IdentityFile ~/.ssh/vast_rsa`
  }

  const copySSHConfig = () => {
    navigator.clipboard.writeText(generateSSHConfig())
    setShowSSHInstructions(true)
    setTimeout(() => setShowSSHInstructions(false), 5000)
  }

  const openSSHGuide = () => {
    window.open('https://cloud.vast.ai/account/', '_blank')
  }

  const openIDE = (ideName, protocol) => {
    const sshAlias = `dumont-${machine.id}`
    const url = `${protocol}://vscode-remote/ssh-remote+${sshAlias}/workspace`
    window.open(url, '_blank')
  }

  const openVSCodeOnline = async () => {
    const ports = machine.ports || {}
    const publicIp = machine.public_ipaddr
    const port8080Mapping = ports['8080/tcp']

    if (!port8080Mapping || !port8080Mapping[0]) {
      setAlertDialog({
        open: true,
        title: 'VS Code Online não disponível',
        description: 'A porta 8080 (code-server) não está mapeada.',
        action: null
      })
      return
    }

    const hostPort = port8080Mapping[0].HostPort
    const directUrl = `http://${publicIp}:${hostPort}/`
    window.open(directUrl, '_blank')
  }

  return (
    <div
      className={`rounded-xl border transition-all duration-300 overflow-hidden ${
        isRunning
          ? 'border-gray-800/50 hover:border-green-500/30'
          : 'border-gray-800/30 opacity-80 hover:opacity-100'
      }`}
      style={{ backgroundColor: '#131713' }}
    >
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-gray-800/30">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            isRunning ? 'bg-green-500/20' : 'bg-gray-700/30'
          }`}>
            <Cpu className={`w-5 h-5 ${isRunning ? 'text-green-400' : 'text-gray-500'}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-semibold text-sm">{gpuName}</span>
              <span className={`flex items-center gap-1 text-xs ${isRunning ? 'text-green-400' : 'text-gray-500'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? 'bg-green-400' : 'bg-gray-500'}`} />
                {isRunning ? 'Online' : status}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {machine.public_ipaddr && (
                <a
                  href={`http://${machine.public_ipaddr}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
                >
                  {machine.public_ipaddr}
                </a>
              )}
              <span className="text-[10px] px-2 py-0.5 rounded bg-gray-700/30 text-gray-400 border border-gray-700/30">
                {Math.round((machine.gpu_ram || 24000) / 1024)}GB VRAM
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-gray-700/30 text-gray-400 border border-gray-700/30">
                {machine.cpu_cores || 4} CPU
              </span>
            </div>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="p-2 rounded-lg hover:bg-gray-800/50 text-gray-500 hover:text-gray-300 transition-colors">
              <MoreVertical className="w-4 h-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => setShowConfigModal(true)}>
              <Settings className="w-4 h-4 mr-2" />
              Auto-Hibernation
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onDestroy(machine.id)} className="text-red-400 focus:text-red-400">
              <Trash2 className="w-4 h-4 mr-2" />
              Destruir Máquina
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Content */}
      <div className="p-4">
        {isRunning ? (
          <>
            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              {/* GPU */}
              <div className="p-3 rounded-lg border border-green-500/20" style={{ backgroundColor: '#1a2418' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-semibold text-green-400 uppercase tracking-wider">GPU</span>
                  <span className="text-lg font-bold text-green-400">{gpuUtil}%</span>
                </div>
                <SparklineChart data={gpuHistory} color="#4ade80" />
              </div>

              {/* VRAM */}
              <div className="p-3 rounded-lg border border-yellow-500/20" style={{ backgroundColor: '#1f1d18' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-semibold text-yellow-400 uppercase tracking-wider">VRAM</span>
                  <span className="text-lg font-bold text-yellow-400">{memUtil}%</span>
                </div>
                <SparklineChart data={memHistory} color="#eab308" />
              </div>

              {/* CPU */}
              <div className="p-3 rounded-lg border border-blue-500/20" style={{ backgroundColor: '#181a1f' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider">CPU</span>
                  <span className="text-lg font-bold text-blue-400">{cpuUtil}%</span>
                </div>
                <SparklineChart data={cpuHistory} color="#3b82f6" />
              </div>

              {/* Temp */}
              <div className="p-3 rounded-lg border border-gray-700/30" style={{ backgroundColor: '#1a1f1a' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">TEMP</span>
                  <span className={`text-lg font-bold ${temp > 75 ? 'text-red-400' : temp > 65 ? 'text-yellow-400' : 'text-green-400'}`}>
                    {temp}°C
                  </span>
                </div>
                <SparklineChart data={tempHistory} color={temp > 75 ? '#f87171' : temp > 65 ? '#eab308' : '#4ade80'} />
              </div>
            </div>

            {/* Cost Badge */}
            <div className="flex justify-center mb-4">
              <div className="px-4 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20">
                <span className="text-xs text-gray-400">Custo/hora: </span>
                <span className="text-sm font-bold text-yellow-400">${costPerHour.toFixed(3)}</span>
              </div>
            </div>

            {/* IDEs Section */}
            <div className="p-3 rounded-lg border border-green-500/20 mb-3" style={{ backgroundColor: '#1a2418' }}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-green-400 uppercase tracking-wider flex items-center gap-2">
                  <Code className="w-3.5 h-3.5" />
                  Abrir IDE
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium hover:bg-blue-500/20 transition-colors">
                      <Code className="w-3.5 h-3.5" />
                      VS Code
                      <ChevronDown className="w-3 h-3 opacity-50" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={openVSCodeOnline}>
                      VS Code Online (Web)
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => openIDE('VS Code', 'vscode')}>
                      VS Code Desktop (SSH)
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <button
                  onClick={() => openIDE('Cursor', 'cursor')}
                  className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-medium hover:bg-purple-500/20 transition-colors"
                >
                  Cursor
                </button>

                <button
                  onClick={() => openIDE('Windsurf', 'windsurf')}
                  className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium hover:bg-cyan-500/20 transition-colors"
                >
                  Windsurf
                </button>

                <button
                  onClick={() => openIDE('Antigravity', 'antigravity')}
                  className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs font-medium hover:bg-orange-500/20 transition-colors"
                >
                  Antigravity
                </button>
              </div>
            </div>

            {/* SSH Section - Collapsible */}
            <details className="rounded-lg border border-gray-800/30 overflow-hidden" style={{ backgroundColor: '#161a16' }}>
              <summary className="px-3 py-2 cursor-pointer text-xs text-gray-500 hover:text-gray-300 flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5" />
                Configuração SSH
              </summary>
              <div className="px-3 pb-3 pt-1">
                <div className="flex gap-2">
                  <button
                    onClick={copySSHConfig}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded bg-gray-800/50 text-gray-400 text-[10px] hover:bg-gray-700/50 transition-colors"
                  >
                    <Copy className="w-3 h-3" />
                    Copiar Config
                  </button>
                  <button
                    onClick={openSSHGuide}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded bg-gray-800/50 text-gray-400 text-[10px] hover:bg-gray-700/50 transition-colors"
                  >
                    <Key className="w-3 h-3" />
                    Chave SSH
                  </button>
                </div>
                {showSSHInstructions && (
                  <div className="mt-2 p-2 rounded bg-blue-500/10 border border-blue-500/20 text-[10px] text-blue-300">
                    Config copiada! Cole em ~/.ssh/config
                  </div>
                )}
              </div>
            </details>

            {/* Settings Section - Collapsible */}
            <details className="mt-2 rounded-lg border border-gray-800/30 overflow-hidden" style={{ backgroundColor: '#161a16' }}>
              <summary className="px-3 py-2 cursor-pointer text-xs text-gray-500 hover:text-gray-300 flex items-center gap-2">
                <Settings className="w-3.5 h-3.5" />
                Auto-hibernação
              </summary>
              <div className="px-3 pb-3 pt-1 space-y-2">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Clock className="w-3 h-3" />
                  <span>Hibernar após:</span>
                  <select
                    value={hibernateTime}
                    onChange={(e) => setHibernateTime(e.target.value)}
                    className="px-2 py-1 rounded bg-gray-800/50 border border-gray-700/30 text-gray-300 text-xs"
                  >
                    <option value={5}>5 min</option>
                    <option value={10}>10 min</option>
                    <option value={15}>15 min</option>
                    <option value={30}>30 min</option>
                    <option value={60}>1 hora</option>
                  </select>
                </div>
                <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={smartIdle}
                    onChange={(e) => setSmartIdle(e.target.checked)}
                    className="w-3.5 h-3.5 rounded accent-green-500"
                  />
                  Smart Idle (GPU &lt; 5%)
                </label>
              </div>
            </details>
          </>
        ) : (
          /* Inactive Machine Content */
          <>
            {/* Cost Highlight */}
            <div className="p-4 rounded-lg border border-yellow-500/20 text-center mb-4" style={{ backgroundColor: '#1f1d18' }}>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Custo por Hora</div>
              <div className="text-2xl font-bold text-yellow-400">${costPerHour.toFixed(3)}/h</div>
            </div>

            {/* Specs Grid */}
            <div className="grid grid-cols-2 gap-2 mb-4">
              <div className="p-3 rounded-lg border border-gray-700/30 text-center" style={{ backgroundColor: '#1a1f1a' }}>
                <div className="text-[10px] text-gray-500 uppercase">GPU RAM</div>
                <div className="text-lg font-bold text-white">{Math.round((machine.gpu_ram || 24000) / 1024)} GB</div>
              </div>
              <div className="p-3 rounded-lg border border-gray-700/30 text-center" style={{ backgroundColor: '#1a1f1a' }}>
                <div className="text-[10px] text-gray-500 uppercase">CPU</div>
                <div className="text-lg font-bold text-white">{machine.cpu_cores || 4} cores</div>
              </div>
              <div className="p-3 rounded-lg border border-gray-700/30 text-center" style={{ backgroundColor: '#1a1f1a' }}>
                <div className="text-[10px] text-gray-500 uppercase">RAM</div>
                <div className="text-lg font-bold text-white">{Math.round((machine.cpu_ram || 16000) / 1024)} GB</div>
              </div>
              <div className="p-3 rounded-lg border border-gray-700/30 text-center" style={{ backgroundColor: '#1a1f1a' }}>
                <div className="text-[10px] text-gray-500 uppercase">Disk</div>
                <div className="text-lg font-bold text-white">{machine.disk_space || 100} GB</div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2">
              <button
                onClick={() => onStart && onStart(machine.id)}
                className="w-full py-3 rounded-lg bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-green-500/20"
              >
                <Play className="w-4 h-4" />
                Iniciar Máquina
              </button>
              <button
                onClick={() => onRestoreToNew && onRestoreToNew(machine)}
                className="w-full py-2.5 rounded-lg border border-gray-700/50 text-gray-400 text-xs font-medium flex items-center justify-center gap-2 hover:border-gray-600 hover:text-gray-300 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Restaurar em Nova Máquina
              </button>
            </div>
          </>
        )}
      </div>

      {/* Modals */}
      <HibernationConfigModal
        instance={{ id: machine.id, name: machine.gpu_name || `Instance ${machine.id}` }}
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onSave={(config) => console.log('Config saved:', config)}
      />

      <AlertDialog open={alertDialog.open} onOpenChange={(open) => setAlertDialog({ ...alertDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{alertDialog.title}</AlertDialogTitle>
            <AlertDialogDescription>{alertDialog.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction>OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// Main Machines Page
export default function Machines() {
  const [machines, setMachines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [balance, setBalance] = useState(null)

  useEffect(() => {
    fetchMachines()
    fetchBalance()
    const interval = setInterval(() => {
      fetchMachines()
      fetchBalance()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchMachines = async () => {
    try {
      const res = await apiGet('/api/instances')
      if (!res.ok) throw new Error('Erro ao buscar máquinas')
      const data = await res.json()
      setMachines(data.instances || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchBalance = async () => {
    try {
      const res = await apiGet('/api/balance')
      if (res.ok) {
        const data = await res.json()
        setBalance(data.credit || 0)
      }
    } catch (err) {
      console.error('Error fetching balance:', err)
    }
  }

  const handleDestroy = async (machineId) => {
    if (!confirm('Tem certeza que deseja destruir esta máquina?')) return
    try {
      const res = await apiDelete(`/api/instances/${machineId}`)
      if (!res.ok) throw new Error('Erro ao destruir máquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleStartMachine = async (machineId) => {
    if (!confirm('Deseja iniciar esta máquina?')) return
    try {
      const res = await apiPost(`/api/instances/${machineId}/resume`)
      if (!res.ok) throw new Error('Erro ao iniciar máquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleRestoreToNew = (machine) => {
    window.location.href = `/?restore_from=${machine.id}`
  }

  const activeMachines = machines.filter(m => m.actual_status === 'running')
  const inactiveMachines = machines.filter(m => m.actual_status !== 'running')
  const totalGpuMem = activeMachines.reduce((acc, m) => acc + (m.gpu_ram || 24000), 0)
  const totalUptime = activeMachines.reduce((acc, m) => {
    if (m.start_date) {
      const uptimeHours = (Date.now() / 1000 - m.start_date) / 3600
      return acc + uptimeHours
    }
    return acc
  }, 0)
  const totalCostToday = activeMachines.reduce((acc, m) => acc + (m.dph_total || 0) * Math.min(totalUptime, 24), 0)

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#0e110e' }}>
        <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8" style={{ backgroundColor: '#0e110e', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
      `}</style>

      <div className="max-w-7xl mx-auto">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-6 md:mb-8">
          <StatCard icon={Server} value={activeMachines.length} label="Máquinas Ativas" color="green" />
          <StatCard icon={Cpu} value={`${Math.round(totalGpuMem / 1024)} GB`} label="VRAM Total" color="yellow" />
          <StatCard icon={Clock} value={`${totalUptime.toFixed(1)}h`} label="Uptime Hoje" color="blue" />
          <StatCard icon={Activity} value={`$${totalCostToday.toFixed(2)}`} label="Custo Hoje" color="purple" />
        </div>

        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <h1 className="text-xl md:text-2xl font-bold text-white">Minhas Máquinas</h1>
            <div className="flex gap-2">
              {activeMachines.length > 0 && (
                <span className="px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-xs font-medium text-green-400">
                  {activeMachines.length} Online
                </span>
              )}
              {inactiveMachines.length > 0 && (
                <span className="px-3 py-1 rounded-full bg-gray-700/30 border border-gray-700/30 text-xs font-medium text-gray-400">
                  {inactiveMachines.length} Offline
                </span>
              )}
            </div>
          </div>
          <Link
            to="/"
            className="px-4 py-2.5 rounded-lg bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white text-sm font-semibold flex items-center gap-2 transition-all shadow-lg shadow-green-500/20"
          >
            <Plus className="w-4 h-4" />
            Nova Máquina
          </Link>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Machines Grid */}
        {machines.length === 0 ? (
          <div className="text-center py-16 rounded-xl border border-gray-800/30" style={{ backgroundColor: '#131713' }}>
            <Server className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">Nenhuma máquina no momento</p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-green-600 to-green-500 text-white text-sm font-semibold"
            >
              <Plus className="w-4 h-4" />
              Criar primeira máquina
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
            {activeMachines.map((machine) => (
              <MachineCard
                key={machine.id}
                machine={machine}
                onDestroy={handleDestroy}
                onStart={handleStartMachine}
                onRestoreToNew={handleRestoreToNew}
              />
            ))}
            {inactiveMachines.map((machine) => (
              <MachineCard
                key={machine.id}
                machine={machine}
                onDestroy={handleDestroy}
                onStart={handleStartMachine}
                onRestoreToNew={handleRestoreToNew}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
