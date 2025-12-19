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
  AlertDialogTrigger,
} from '../components/ui/alert-dialog'
import { ChevronDown, MoreVertical, Play, Plus, Server, Cpu, Clock, Activity, Code, Settings, Trash2, Copy, Key, Terminal, Pause, Save, RefreshCw, Upload, Database, ArrowLeftRight, Check, Cloud, Shield, Layers, X, MapPin, Globe, DollarSign } from 'lucide-react'
import HibernationConfigModal from '../components/HibernationConfigModal'
import MigrationModal from '../components/MigrationModal'
import { ErrorState } from '../components/ErrorState'
import { EmptyState } from '../components/EmptyState'
import { SkeletonList } from '../components/Skeleton'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler)

// Mini sparkline chart - more compact
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
    <div className="h-6 w-full">
      <Line data={chartData} options={options} />
    </div>
  )
}

// Compact Machine Card - Similar to Dashboard tier cards
function MachineCard({ machine, onDestroy, onStart, onPause, onRestoreToNew, onSnapshot, onRestore, onMigrate, syncStatus, syncStats }) {
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showSSHInstructions, setShowSSHInstructions] = useState(false)
  const [alertDialog, setAlertDialog] = useState({ open: false, title: '', description: '', action: null })
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false)
  const [copiedField, setCopiedField] = useState(null) // Track which field was copied
  const [showBackupInfo, setShowBackupInfo] = useState(false) // Show CPU backup info popover

  // Historical data for sparklines
  const [gpuHistory] = useState(() => Array.from({ length: 15 }, () => Math.random() * 40 + 30))
  const [memHistory] = useState(() => Array.from({ length: 15 }, () => Math.random() * 30 + 40))

  const gpuUtil = machine.gpu_util ? Number(machine.gpu_util).toFixed(0) : Math.round(gpuHistory[gpuHistory.length - 1])
  const memUtil = machine.mem_usage ? Number(machine.mem_usage).toFixed(0) : Math.round(memHistory[memHistory.length - 1])
  const temp = machine.gpu_temp ? Number(machine.gpu_temp).toFixed(0) : Math.round(Math.random() * 15 + 55)

  const gpuName = machine.gpu_name || 'GPU'
  const isRunning = machine.actual_status === 'running'
  const costPerHour = machine.dph_total || 0
  const status = machine.actual_status || 'stopped'

  // CPU Standby info
  const cpuStandby = machine.cpu_standby
  const hasCpuStandby = cpuStandby?.enabled
  const cpuCostPerHour = cpuStandby?.dph_total || 0
  const totalCostPerHour = machine.total_dph || (costPerHour + cpuCostPerHour)

  // Calcular uptime
  const formatUptime = (startTime) => {
    if (!startTime) return null
    const start = new Date(startTime).getTime()
    const now = Date.now()
    const diff = now - start
    const hours = Math.floor(diff / 3600000)
    const minutes = Math.floor((diff % 3600000) / 60000)
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }
  const uptime = isRunning ? formatUptime(machine.start_date || machine.created_at) : null

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
    setCopiedField('ssh')
    setShowSSHInstructions(true)
    setTimeout(() => {
      setShowSSHInstructions(false)
      setCopiedField(null)
    }, 2000)
  }

  const copyToClipboard = (text, fieldName) => {
    navigator.clipboard.writeText(text)
    setCopiedField(fieldName)
    setTimeout(() => setCopiedField(null), 1500)
  }

  const openIDE = (ideName, protocol) => {
    const sshAlias = `dumont-${machine.id}`
    const url = `${protocol}://vscode-remote/ssh-remote+${sshAlias}/workspace`
    window.open(url, '_blank')
  }

  const openVSCodeOnline = () => {
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
    window.open(`http://${publicIp}:${hostPort}/`, '_blank')
  }

  const gpuRam = Math.round((machine.gpu_ram || 24000) / 1024)
  const cpuCores = machine.cpu_cores || 4
  const ram = machine.cpu_ram ? (machine.cpu_ram > 1000 ? Math.round(machine.cpu_ram / 1024) : Math.round(machine.cpu_ram)) : 16
  const disk = Math.round(machine.disk_space || 100)

  return (
    <div
      className={`flex flex-col p-3 md:p-4 rounded-lg border transition-all ${
        isRunning
          ? 'border-green-500/30 bg-[#1a2418]'
          : 'border-gray-700/30 bg-[#161a16] hover:border-gray-600/50'
      }`}
    >
      {/* Header Row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-white font-semibold text-sm">{gpuName}</span>
          <span className={`status-badge ${isRunning ? 'status-badge-online' : 'status-badge-offline'}`}>
            <span className="status-indicator" />
            {isRunning ? 'Online' : status === 'stopped' ? 'Offline' : status}
          </span>
          {/* Provider badges */}
          <span className="px-1.5 py-0.5 rounded text-[9px] bg-purple-500/20 text-purple-400 border border-purple-500/30">
            Vast.ai
          </span>
          {/* CPU Backup Mirror Icon - clickable */}
          <div className="relative">
            <button
              onClick={() => setShowBackupInfo(!showBackupInfo)}
              className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] border transition-all ${
                hasCpuStandby
                  ? 'bg-blue-500/20 text-blue-400 border-blue-500/30 hover:bg-blue-500/30'
                  : 'bg-gray-700/30 text-gray-500 border-gray-600/30 hover:bg-gray-700/50'
              }`}
              title={hasCpuStandby ? 'Ver backup CPU' : 'Backup CPU não configurado'}
            >
              <Layers className="w-2.5 h-2.5" />
              {hasCpuStandby ? 'Backup' : 'Sem backup'}
            </button>

            {/* Backup Info Popover */}
            {showBackupInfo && (
              <div className="absolute top-full left-0 mt-2 z-50 w-64 p-3 rounded-lg border border-gray-700/50 bg-[#1a1f1a] shadow-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-white flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-blue-400" />
                    CPU Backup (Espelho)
                  </span>
                  <button
                    onClick={() => setShowBackupInfo(false)}
                    className="p-0.5 rounded hover:bg-gray-700/50 text-gray-500 hover:text-gray-300"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {hasCpuStandby ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs">
                      <Cloud className="w-3.5 h-3.5 text-blue-400" />
                      <span className="text-gray-400">Provider:</span>
                      <span className="text-white font-medium">{cpuStandby.provider?.toUpperCase() || 'GCP'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Server className="w-3.5 h-3.5 text-green-400" />
                      <span className="text-gray-400">Máquina:</span>
                      <span className="text-white font-medium">{cpuStandby.name || 'Provisionando...'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <MapPin className="w-3.5 h-3.5 text-yellow-400" />
                      <span className="text-gray-400">Zona:</span>
                      <span className="text-white font-medium">{cpuStandby.zone || 'europe-west1-b'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Globe className="w-3.5 h-3.5 text-purple-400" />
                      <span className="text-gray-400">IP:</span>
                      <span className="text-white font-medium font-mono">{cpuStandby.ip || 'Aguardando...'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Cpu className="w-3.5 h-3.5 text-orange-400" />
                      <span className="text-gray-400">Tipo:</span>
                      <span className="text-white font-medium">{cpuStandby.machine_type || 'e2-medium'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <DollarSign className="w-3.5 h-3.5 text-green-400" />
                      <span className="text-gray-400">Custo:</span>
                      <span className="text-green-400 font-medium">${cpuStandby.dph_total?.toFixed(3) || '0.010'}/h</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="text-gray-400">Syncs:</span>
                      <span className="text-white font-medium">{cpuStandby.sync_count || 0}</span>
                    </div>
                    <div className="mt-2 pt-2 border-t border-gray-700/50">
                      <div className={`text-xs px-2 py-1 rounded text-center ${
                        cpuStandby.state === 'ready' ? 'bg-green-500/20 text-green-400' :
                        cpuStandby.state === 'syncing' ? 'bg-blue-500/20 text-blue-400' :
                        cpuStandby.state === 'failover_active' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-gray-700/30 text-gray-400'
                      }`}>
                        {cpuStandby.state === 'ready' ? '✓ Pronto para failover' :
                         cpuStandby.state === 'syncing' ? '↻ Sincronizando...' :
                         cpuStandby.state === 'failover_active' ? '⚡ Failover ativo' :
                         '○ Provisionando...'}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-3">
                    <Shield className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                    <p className="text-xs text-gray-400 mb-2">
                      Nenhum backup CPU configurado para esta máquina.
                    </p>
                    <p className="text-[10px] text-gray-500">
                      Ative o auto-standby nas configurações para criar backups automáticos.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="p-1 rounded hover:bg-gray-800/50 text-gray-500 hover:text-gray-300">
              <MoreVertical className="w-4 h-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {isRunning && (
              <>
                <DropdownMenuItem onClick={() => onSnapshot && onSnapshot(machine.id)} disabled={isCreatingSnapshot}>
                  <Save className="w-3.5 h-3.5 mr-2" />
                  {isCreatingSnapshot ? 'Criando...' : 'Criar Snapshot'}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem onClick={() => onRestoreToNew && onRestoreToNew(machine)}>
              <Upload className="w-3.5 h-3.5 mr-2" />
              Restaurar em Nova
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setShowConfigModal(true)}>
              <Settings className="w-3.5 h-3.5 mr-2" />
              Auto-Hibernation
            </DropdownMenuItem>
            <DropdownMenuItem onClick={copySSHConfig}>
              {copiedField === 'ssh' ? (
                <Check className="w-3.5 h-3.5 mr-2 text-green-400" />
              ) : (
                <Copy className="w-3.5 h-3.5 mr-2" />
              )}
              {copiedField === 'ssh' ? 'Copiado!' : 'Copiar SSH Config'}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onDestroy(machine.id)} className="text-red-400 focus:text-red-400">
              <Trash2 className="w-3.5 h-3.5 mr-2" />
              Destruir
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Specs Row */}
      <div className="flex items-center gap-2 mb-3 text-[10px] text-gray-400">
        {machine.public_ipaddr && (
          <button
            onClick={() => copyToClipboard(machine.public_ipaddr, 'ip')}
            className={`px-1.5 py-0.5 rounded border transition-all ${
              copiedField === 'ip'
                ? 'bg-green-500/20 text-green-400 border-green-500/30'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20'
            }`}
            title="Clique para copiar IP"
          >
            {copiedField === 'ip' ? 'Copiado!' : machine.public_ipaddr}
          </button>
        )}
        <span className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30">{gpuRam}GB</span>
        <span className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30">{cpuCores}CPU</span>
        <span className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30">{ram}GB RAM</span>
        {isRunning && syncStatus && (
          <span
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded border cursor-help ${
              syncStatus === 'syncing'
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                : syncStatus === 'synced'
                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                : 'bg-gray-700/30 text-gray-400 border-gray-700/30'
            }`}
            title={syncStats ? `Último sync: ${syncStats.files_changed || 0} modificados, ${syncStats.data_added || '0 B'} enviados` : 'Clique em "Criar Snapshot" para sincronizar'}
          >
            <RefreshCw className={`w-2.5 h-2.5 ${syncStatus === 'syncing' ? 'animate-spin' : ''}`} />
            {syncStatus === 'syncing' ? 'Sincronizando...' : syncStatus === 'synced' ? (syncStats?.data_added || 'Synced') : 'Sync'}
          </span>
        )}
      </div>

      {isRunning ? (
        <>
          {/* Metrics Row - Compact */}
          <div className="grid grid-cols-5 gap-2 mb-3">
            <div className="text-center">
              <div className="text-green-400 font-mono text-sm font-bold">{gpuUtil}%</div>
              <div className="text-[9px] text-gray-500 uppercase">GPU</div>
              <SparklineChart data={gpuHistory} color="#4ade80" />
            </div>
            <div className="text-center">
              <div className="text-yellow-400 font-mono text-sm font-bold">{memUtil}%</div>
              <div className="text-[9px] text-gray-500 uppercase">VRAM</div>
              <SparklineChart data={memHistory} color="#eab308" />
            </div>
            <div className="text-center">
              <div className={`font-mono text-sm font-bold ${temp > 75 ? 'text-red-400' : temp > 65 ? 'text-yellow-400' : 'text-green-400'}`}>
                {temp}°C
              </div>
              <div className="text-[9px] text-gray-500 uppercase">TEMP</div>
            </div>
            <div className="text-center">
              <div className="text-yellow-400 font-mono text-sm font-bold" title={hasCpuStandby ? `GPU: $${costPerHour.toFixed(2)} + CPU: $${cpuCostPerHour.toFixed(3)}` : ''}>
                ${totalCostPerHour.toFixed(2)}
              </div>
              <div className="text-[9px] text-gray-500 uppercase">/hora</div>
              {hasCpuStandby && (
                <div className="text-[8px] text-blue-400 mt-0.5">+backup</div>
              )}
            </div>
            {uptime && (
              <div className="text-center">
                <div className="text-blue-400 font-mono text-sm font-bold">{uptime}</div>
                <div className="text-[9px] text-gray-500 uppercase">UPTIME</div>
              </div>
            )}
          </div>

          {/* IDE Buttons - Single Row */}
          <div className="flex gap-1.5 mb-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded bg-gray-700/40 border border-gray-600/40 text-gray-300 text-[10px] font-medium hover:bg-gray-600/40">
                  <Code className="w-3 h-3" />
                  VS Code
                  <ChevronDown className="w-2.5 h-2.5 opacity-50" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={openVSCodeOnline}>Online (Web)</DropdownMenuItem>
                <DropdownMenuItem onClick={() => openIDE('VS Code', 'vscode')}>Desktop (SSH)</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <button onClick={() => openIDE('Cursor', 'cursor')} className="flex-1 px-2 py-1.5 rounded bg-gray-700/40 border border-gray-600/40 text-gray-300 text-[10px] font-medium hover:bg-gray-600/40">
              Cursor
            </button>
            <button onClick={() => openIDE('Windsurf', 'windsurf')} className="flex-1 px-2 py-1.5 rounded bg-gray-700/40 border border-gray-600/40 text-gray-300 text-[10px] font-medium hover:bg-gray-600/40">
              Windsurf
            </button>
          </div>

          {/* Action Buttons Row */}
          <div className="flex gap-2">
            {/* Migration Button */}
            <button
              onClick={() => onMigrate && onMigrate(machine)}
              className="flex-1 py-2 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 text-xs font-medium flex items-center justify-center gap-1.5 hover:bg-blue-600/30 transition-colors"
            >
              <ArrowLeftRight className="w-3.5 h-3.5" />
              Migrar p/ CPU
            </button>

            {/* Pause Button with Confirmation */}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <button
                  className="flex-1 py-2 rounded-lg border border-gray-600/40 text-gray-400 text-xs font-medium flex items-center justify-center gap-1.5 hover:bg-gray-700/30 transition-colors"
                >
                  <Pause className="w-3.5 h-3.5" />
                  Pausar
                </button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Pausar máquina?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Isso irá pausar a máquina {gpuName}. Processos em execução serão interrompidos.
                    Você poderá reiniciá-la depois.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction onClick={() => onPause && onPause(machine.id)}>
                    Pausar
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </>
      ) : (
        <>
          {/* Offline: Specs + Cost */}
          <div className="grid grid-cols-4 gap-2 mb-3 text-center">
            <div>
              <div className="text-white font-mono text-sm font-bold">{gpuRam}GB</div>
              <div className="text-[9px] text-gray-500 uppercase">VRAM</div>
            </div>
            <div>
              <div className="text-white font-mono text-sm font-bold">{cpuCores}</div>
              <div className="text-[9px] text-gray-500 uppercase">CPU</div>
            </div>
            <div>
              <div className="text-white font-mono text-sm font-bold">{disk}GB</div>
              <div className="text-[9px] text-gray-500 uppercase">DISK</div>
            </div>
            <div>
              <div className="text-yellow-400 font-mono text-sm font-bold" title={hasCpuStandby ? `GPU: $${costPerHour.toFixed(2)} + CPU: $${cpuCostPerHour.toFixed(3)}` : ''}>
                ${totalCostPerHour.toFixed(2)}
              </div>
              <div className="text-[9px] text-gray-500 uppercase">/hora</div>
              {hasCpuStandby && (
                <div className="text-[8px] text-blue-400 mt-0.5">+backup</div>
              )}
            </div>
          </div>

          {/* Action Buttons Row for Offline */}
          <div className="flex gap-2">
            {/* Migration Button (CPU -> GPU) */}
            {machine.num_gpus === 0 && (
              <button
                onClick={() => onMigrate && onMigrate(machine)}
                className="flex-1 py-2.5 rounded-lg bg-green-600/20 border border-green-500/30 text-green-400 text-xs font-medium flex items-center justify-center gap-1.5 hover:bg-green-600/30 transition-all"
              >
                <ArrowLeftRight className="w-3.5 h-3.5" />
                Migrar p/ GPU
              </button>
            )}

            {/* Start Button */}
            <button
              onClick={() => onStart && onStart(machine.id)}
              className={`${machine.num_gpus === 0 ? 'flex-1' : 'w-full'} py-2.5 rounded-lg bg-gray-600/50 hover:bg-gray-600/70 text-gray-200 text-xs font-medium flex items-center justify-center gap-1.5 transition-all border border-gray-500/40`}
            >
              <Play className="w-3.5 h-3.5" />
              Iniciar
            </button>
          </div>
        </>
      )}

      {/* SSH copied notification */}
      {showSSHInstructions && (
        <div className="mt-2 p-2 rounded bg-blue-500/10 border border-blue-500/20 text-[10px] text-blue-300 text-center">
          SSH Config copiado! Cole em ~/.ssh/config
        </div>
      )}

      {/* Modals */}
      <HibernationConfigModal
        instance={{ id: machine.id, name: gpuName }}
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
  const [filter, setFilter] = useState('all') // all, online, offline
  const [syncStatus, setSyncStatus] = useState({}) // machineId -> 'idle' | 'syncing' | 'synced'
  const [lastSyncTime, setLastSyncTime] = useState({}) // machineId -> timestamp
  const [destroyDialog, setDestroyDialog] = useState({ open: false, machineId: null, machineName: '' })
  const [migrationTarget, setMigrationTarget] = useState(null) // machine to migrate
  const [syncStats, setSyncStats] = useState({}) // machineId -> { files_new, files_changed, data_added, ... }

  useEffect(() => {
    fetchMachines()
    const interval = setInterval(fetchMachines, 5000)
    return () => clearInterval(interval)
  }, [])

  // Auto-sync every 30 seconds for running machines
  useEffect(() => {
    const syncInterval = setInterval(() => {
      const runningMachines = machines.filter(m => m.actual_status === 'running')
      runningMachines.forEach(m => {
        const lastSync = lastSyncTime[m.id] || 0
        const now = Date.now()
        // Auto-sync every 30 seconds
        if (now - lastSync > 30000) {
          handleAutoSync(m.id)
        }
      })
    }, 10000) // Check every 10 seconds
    return () => clearInterval(syncInterval)
  }, [machines, lastSyncTime])

  const fetchMachines = async () => {
    try {
      const res = await apiGet('/api/v1/instances')
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

  const openDestroyDialog = (machineId, machineName) => {
    setDestroyDialog({ open: true, machineId, machineName })
  }

  const confirmDestroy = async () => {
    const { machineId } = destroyDialog
    setDestroyDialog({ open: false, machineId: null, machineName: '' })
    try {
      const res = await apiDelete(`/api/v1/instances/${machineId}`)
      if (!res.ok) throw new Error('Erro ao destruir máquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleStart = async (machineId) => {
    try {
      const res = await apiPost(`/api/v1/instances/${machineId}/resume`)
      if (!res.ok) throw new Error('Erro ao iniciar máquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  const handlePause = async (machineId) => {
    try {
      const res = await apiPost(`/api/v1/instances/${machineId}/pause`)
      if (!res.ok) throw new Error('Erro ao pausar máquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  // Create manual snapshot (using new incremental sync endpoint)
  const handleSnapshot = async (machineId) => {
    try {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'syncing' }))
      // Use new sync endpoint with force=true for manual sync
      const res = await apiPost(`/api/v1/instances/${machineId}/sync?force=true`)
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || errorData.error || 'Erro ao sincronizar')
      }
      const data = await res.json()
      setSyncStatus(prev => ({ ...prev, [machineId]: 'synced' }))
      setLastSyncTime(prev => ({ ...prev, [machineId]: Date.now() }))
      setSyncStats(prev => ({ ...prev, [machineId]: data }))

      // Show sync result
      const syncType = data.is_incremental ? 'Sync incremental' : 'Sync inicial'
      alert(`${syncType} concluído em ${data.duration_seconds.toFixed(1)}s!\n\n` +
        `Arquivos novos: ${data.files_new}\n` +
        `Arquivos modificados: ${data.files_changed}\n` +
        `Arquivos inalterados: ${data.files_unmodified}\n` +
        `Dados enviados: ${data.data_added}`)
    } catch (err) {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
      alert(err.message)
    }
  }

  // Auto-sync (using new incremental sync endpoint)
  const handleAutoSync = async (machineId) => {
    // Check if already syncing
    if (syncStatus[machineId] === 'syncing') return

    try {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'syncing' }))
      // Use new sync endpoint (without force - respects 30s minimum interval)
      const res = await apiPost(`/api/v1/instances/${machineId}/sync`)

      if (res.ok) {
        const data = await res.json()
        if (data.success) {
          setSyncStatus(prev => ({ ...prev, [machineId]: 'synced' }))
          setLastSyncTime(prev => ({ ...prev, [machineId]: Date.now() }))
          setSyncStats(prev => ({ ...prev, [machineId]: data }))
          // Reset to idle after 5 seconds
          setTimeout(() => {
            setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
          }, 5000)
        } else {
          // Sync skipped (too soon or error)
          setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
        }
      } else {
        setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
      }
    } catch (err) {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
      console.error('Auto-sync failed:', err)
    }
  }

  // Restore to new machine - redirect to dashboard with restore param
  const handleRestoreToNew = (machine) => {
    window.location.href = `/?restore_from=${machine.id}`
  }

  // Handle migration
  const handleMigrate = (machine) => {
    setMigrationTarget(machine)
  }

  // Handle migration success
  const handleMigrationSuccess = (result) => {
    fetchMachines()
    setMigrationTarget(null)
  }

  const activeMachines = machines.filter(m => m.actual_status === 'running')
  const inactiveMachines = machines.filter(m => m.actual_status !== 'running')

  const filteredMachines = filter === 'online'
    ? activeMachines
    : filter === 'offline'
      ? inactiveMachines
      : [...activeMachines, ...inactiveMachines]

  const totalGpuMem = activeMachines.reduce((acc, m) => acc + (m.gpu_ram || 24000), 0)
  const totalCostPerHour = activeMachines.reduce((acc, m) => acc + (m.total_dph || m.dph_total || 0), 0)
  const totalCpuStandbyCount = activeMachines.filter(m => m.cpu_standby?.enabled).length

  if (loading) {
    return (
      <div className="min-h-screen p-4 md:p-6 lg:p-8" style={{ backgroundColor: '#0e110e' }}>
        <div className="w-full max-w-6xl mx-auto rounded-xl overflow-hidden border border-gray-800/50 shadow-2xl p-6" style={{ backgroundColor: '#131713' }}>
          <SkeletonList count={4} type="machine" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8" style={{ backgroundColor: '#0e110e', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        .font-mono { font-family: 'JetBrains Mono', monospace; }
      `}</style>

      <div className="w-full max-w-6xl mx-auto rounded-xl overflow-hidden border border-gray-800/50 shadow-2xl" style={{ backgroundColor: '#131713' }}>
        {/* Header - Like Dashboard */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center px-4 md:px-6 py-3 md:py-4 border-b border-gray-800/50 gap-3 sm:gap-0">
          <div className="flex items-center gap-2 mr-4">
            <div className="w-6 h-6 md:w-7 md:h-7 rounded-md bg-green-500/20 flex items-center justify-center">
              <Server className="w-4 h-4 md:w-5 md:h-5 text-green-400" />
            </div>
            <span className="text-white text-base md:text-lg font-semibold tracking-tight">Minhas Máquinas</span>
          </div>

          {/* Filter Tabs - Like Dashboard region tabs */}
          <div className="flex flex-wrap gap-1 sm:ml-auto">
            {[
              { id: 'all', label: 'Todas', count: machines.length },
              { id: 'online', label: 'Online', count: activeMachines.length },
              { id: 'offline', label: 'Offline', count: inactiveMachines.length },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilter(tab.id)}
                className={`px-3 py-1.5 md:px-4 md:py-2 text-xs md:text-sm font-medium transition-all rounded border ${
                  filter === tab.id
                    ? 'text-gray-200 bg-gray-600/30 border-gray-500/40'
                    : 'text-gray-500 hover:text-gray-300 border-transparent'
                }`}
              >
                {tab.label} ({tab.count})
              </button>
            ))}
            <Link
              to="/"
              className="ml-2 px-3 py-1.5 md:px-4 md:py-2 rounded-lg bg-gray-600/50 hover:bg-gray-600/70 text-gray-200 text-xs md:text-sm font-medium flex items-center gap-1.5 transition-all border border-gray-500/40"
            >
              <Plus className="w-3.5 h-3.5" />
              Nova
            </Link>
          </div>
        </div>

        <div className="p-4 md:p-6">
          {/* Summary Stats - Compact inline */}
          <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-green-400" />
              <span className="text-gray-400">{activeMachines.length} GPU ativas</span>
            </div>
            {totalCpuStandbyCount > 0 && (
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-400" />
                <span className="text-gray-400">{totalCpuStandbyCount} CPU backup</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-yellow-400" />
              <span className="text-gray-400">{Math.round(totalGpuMem / 1024)} GB VRAM</span>
            </div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-400" />
              <span className="text-gray-400">${totalCostPerHour.toFixed(2)}/h</span>
            </div>
          </div>

          {/* Error */}
          {error && (
            <ErrorState
              message={error}
              onRetry={fetchMachines}
              retryText="Tentar novamente"
              autoRetry={true}
              autoRetryDelay={10000}
            />
          )}

          {/* Machines Grid - Like Dashboard tier cards */}
          {!error && filteredMachines.length === 0 ? (
            <EmptyState
              icon="server"
              title={filter === 'all' ? 'Nenhuma máquina' : filter === 'online' ? 'Nenhuma máquina online' : 'Nenhuma máquina offline'}
              description={filter === 'all'
                ? 'Crie sua primeira máquina GPU para começar a trabalhar.'
                : filter === 'online'
                  ? 'Todas as suas máquinas estão offline. Inicie uma para começar.'
                  : 'Todas as suas máquinas estão online.'}
              action={() => window.location.href = '/'}
              actionText="Criar máquina"
            />
          ) : !error && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredMachines.map((machine) => (
                <MachineCard
                  key={machine.id}
                  machine={machine}
                  onDestroy={(id) => openDestroyDialog(id, machine.gpu_name || 'GPU')}
                  onStart={handleStart}
                  onPause={handlePause}
                  onRestoreToNew={handleRestoreToNew}
                  onSnapshot={handleSnapshot}
                  onMigrate={handleMigrate}
                  syncStatus={syncStatus[machine.id] || 'idle'}
                  syncStats={syncStats[machine.id]}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Destroy Confirmation Dialog */}
      <AlertDialog open={destroyDialog.open} onOpenChange={(open) => setDestroyDialog({ ...destroyDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-red-400">Destruir máquina?</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja destruir a máquina <strong>{destroyDialog.machineName}</strong>?
              Esta ação é irreversível e todos os dados não salvos serão perdidos.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDestroy}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Destruir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Migration Modal */}
      <MigrationModal
        instance={migrationTarget}
        isOpen={!!migrationTarget}
        onClose={() => setMigrationTarget(null)}
        onSuccess={handleMigrationSuccess}
      />
    </div>
  )
}
