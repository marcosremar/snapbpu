import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Line } from 'react-chartjs-2'
import { apiGet, apiPost, apiDelete, isDemoMode } from '../utils/api'
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
import { StatusBadge, ConfirmModal, Popover, PopoverTrigger, PopoverContent } from '../components/ui/dumont-ui'
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
function MachineCard({ machine, onDestroy, onStart, onPause, onRestoreToNew, onSnapshot, onRestore, onMigrate, onSimulateFailover, syncStatus, syncStats, failoverProgress }) {
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showSSHInstructions, setShowSSHInstructions] = useState(false)
  const [alertDialog, setAlertDialog] = useState({ open: false, title: '', description: '', action: null })
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false)
  const [copiedField, setCopiedField] = useState(null) // Track which field was copied
  const [showBackupInfo, setShowBackupInfo] = useState(false) // Show CPU backup info popover

  // Failover progress from parent
  const isInFailover = failoverProgress && failoverProgress.phase !== 'idle'

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

  // Get border color based on failover phase
  const getFailoverBorderColor = () => {
    if (!isInFailover) return ''
    if (failoverProgress.phase === 'gpu_lost') return 'border-red-500/50 bg-[#1f1414]'
    if (failoverProgress.phase === 'failover_active') return 'border-yellow-500/50 bg-[#1f1a14]'
    if (failoverProgress.phase === 'searching') return 'border-cyan-500/50 bg-[#14171f]'
    if (failoverProgress.phase === 'provisioning') return 'border-purple-500/50 bg-[#1a141f]'
    if (failoverProgress.phase === 'restoring') return 'border-cyan-500/50 bg-[#141f1f]'
    if (failoverProgress.phase === 'complete') return 'border-green-500/50 bg-[#141f14]'
    return ''
  }

  return (
    <div
      className={`flex flex-col p-4 md:p-5 rounded-xl border transition-all bg-white dark:bg-dark-surface-card shadow-theme-sm ${
        isInFailover
          ? getFailoverBorderColor()
          : isRunning
            ? 'border-success-200 dark:border-success-500/30'
            : 'border-gray-200 dark:border-dark-surface-border hover:border-gray-300 dark:hover:border-dark-surface-hover'
      }`}
    >
      {/* Failover Progress Panel - Shows during failover */}
      {isInFailover && (
        <div className="mb-3 p-3 rounded-lg bg-dark-surface-secondary border border-dark-surface-border" data-testid="failover-progress-panel">
          <div className="flex items-center gap-2 mb-3">
            <Zap className={`w-4 h-4 ${
              failoverProgress.phase === 'gpu_lost' ? 'text-red-400 animate-pulse' :
              failoverProgress.phase === 'complete' ? 'text-green-400' :
              'text-yellow-400 animate-pulse'
            }`} />
            <span className="text-sm font-semibold text-white">Failover em Progresso</span>
          </div>

          {/* Progress Steps */}
          <div className="space-y-1.5 text-xs">
            <div className={`flex items-center gap-2 ${
              failoverProgress.phase === 'gpu_lost' ? 'text-red-400' :
              ['failover_active', 'searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'text-green-400' :
              'text-gray-500'
            }`} data-testid="failover-step-gpu-lost">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                failoverProgress.phase === 'gpu_lost' ? 'border-red-400 bg-red-500/20' :
                ['failover_active', 'searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'border-green-400 bg-green-500/20' :
                'border-gray-600'
              }`}>
                {['failover_active', 'searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '1'}
              </div>
              <span>GPU Interrompida</span>
              {failoverProgress.phase === 'gpu_lost' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.detection_time_ms && <span className="ml-auto text-gray-500">{failoverProgress.metrics.detection_time_ms}ms</span>}
            </div>

            <div className={`flex items-center gap-2 ${
              failoverProgress.phase === 'failover_active' ? 'text-yellow-400' :
              ['searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'text-green-400' :
              'text-gray-500'
            }`} data-testid="failover-step-active">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                failoverProgress.phase === 'failover_active' ? 'border-yellow-400 bg-yellow-500/20' :
                ['searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'border-green-400 bg-green-500/20' :
                'border-gray-600'
              }`}>
                {['searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '2'}
              </div>
              <span>Failover para CPU Standby</span>
              {failoverProgress.phase === 'failover_active' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.failover_time_ms && <span className="ml-auto text-gray-500">{failoverProgress.metrics.failover_time_ms}ms</span>}
            </div>

            <div className={`flex items-center gap-2 ${
              failoverProgress.phase === 'searching' ? 'text-cyan-400' :
              ['provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'text-green-400' :
              'text-gray-500'
            }`} data-testid="failover-step-searching">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                failoverProgress.phase === 'searching' ? 'border-blue-400 bg-cyan-500/20' :
                ['provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'border-green-400 bg-green-500/20' :
                'border-gray-600'
              }`}>
                {['provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '3'}
              </div>
              <span>Buscando Nova GPU</span>
              {failoverProgress.phase === 'searching' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.search_time_ms && <span className="ml-auto text-gray-500">{(failoverProgress.metrics.search_time_ms / 1000).toFixed(1)}s</span>}
            </div>

            <div className={`flex items-center gap-2 ${
              failoverProgress.phase === 'provisioning' ? 'text-purple-400' :
              ['restoring', 'complete'].includes(failoverProgress.phase) ? 'text-green-400' :
              'text-gray-500'
            }`} data-testid="failover-step-provisioning">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                failoverProgress.phase === 'provisioning' ? 'border-purple-400 bg-purple-500/20' :
                ['restoring', 'complete'].includes(failoverProgress.phase) ? 'border-green-400 bg-green-500/20' :
                'border-gray-600'
              }`}>
                {['restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '4'}
              </div>
              <span>Provisionando {failoverProgress.newGpu || 'Nova GPU'}</span>
              {failoverProgress.phase === 'provisioning' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.provisioning_time_ms && <span className="ml-auto text-gray-500">{(failoverProgress.metrics.provisioning_time_ms / 1000).toFixed(1)}s</span>}
            </div>

            <div className={`flex items-center gap-2 ${
              failoverProgress.phase === 'restoring' ? 'text-cyan-400' :
              failoverProgress.phase === 'complete' ? 'text-green-400' :
              'text-gray-500'
            }`} data-testid="failover-step-restoring">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                failoverProgress.phase === 'restoring' ? 'border-cyan-400 bg-cyan-500/20' :
                failoverProgress.phase === 'complete' ? 'border-green-400 bg-green-500/20' :
                'border-gray-600'
              }`}>
                {failoverProgress.phase === 'complete' ? '✓' : '5'}
              </div>
              <span>Restaurando Dados</span>
              {failoverProgress.phase === 'restoring' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.restore_time_ms && <span className="ml-auto text-gray-500">{(failoverProgress.metrics.restore_time_ms / 1000).toFixed(1)}s</span>}
            </div>

            <div className={`flex items-center gap-2 ${
              failoverProgress.phase === 'complete' ? 'text-green-400' : 'text-gray-500'
            }`} data-testid="failover-step-complete">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                failoverProgress.phase === 'complete' ? 'border-green-400 bg-green-500/20' : 'border-gray-600'
              }`}>
                {failoverProgress.phase === 'complete' ? '✓' : '6'}
              </div>
              <span>Recuperação Completa</span>
              {failoverProgress.metrics?.total_time_ms && failoverProgress.phase === 'complete' && (
                <span className="ml-auto text-green-400 font-medium">{(failoverProgress.metrics.total_time_ms / 1000).toFixed(1)}s total</span>
              )}
            </div>
          </div>

          {/* Status Message */}
          {failoverProgress.message && (
            <div className="mt-3 pt-2 border-t border-gray-700/50">
              <p className="text-xs text-gray-300" data-testid="failover-message">{failoverProgress.message}</p>
            </div>
          )}

          {/* Detailed Metrics (when complete) */}
          {failoverProgress.phase === 'complete' && failoverProgress.metrics && (
            <div className="mt-3 pt-2 border-t border-gray-700/50 grid grid-cols-3 gap-2 text-[10px]">
              <div className="text-center">
                <div className="text-gray-500">Arquivos</div>
                <div className="text-white font-medium">{failoverProgress.metrics.files_synced?.toLocaleString() || '0'}</div>
              </div>
              <div className="text-center">
                <div className="text-gray-500">Dados</div>
                <div className="text-white font-medium">{failoverProgress.metrics.data_restored_mb || '0'} MB</div>
              </div>
              <div className="text-center">
                <div className="text-gray-500">Status</div>
                <div className="text-green-400 font-medium">Sucesso</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Header Row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-gray-900 dark:text-white font-semibold text-base">{gpuName}</span>
          <span className={`ta-badge ${isRunning ? 'ta-badge-success' : 'ta-badge-gray'}`}>
            {isRunning ? 'Online' : 'Offline'}
          </span>
          {/* Provider badges */}
          <span className="ta-badge ta-badge-primary">
            Vast.ai
          </span>
          {/* CPU Backup Mirror Icon - clickable */}
          <div className="relative">
            <button
              onClick={() => setShowBackupInfo(!showBackupInfo)}
              className={`ta-badge ${hasCpuStandby ? 'ta-badge-primary' : 'ta-badge-gray'} cursor-pointer hover:opacity-80`}
              title={hasCpuStandby ? 'Ver backup CPU' : 'Backup CPU não configurado'}
            >
              <Layers className="w-3 h-3 mr-1" />
              {hasCpuStandby ? 'Backup' : 'Sem backup'}
            </button>

            {/* Backup Info Popover */}
            {showBackupInfo && (
              <div className="absolute top-full left-0 mt-2 z-50 w-72 p-4 bg-white dark:bg-dark-surface-card border border-gray-200 dark:border-dark-surface-border rounded-xl shadow-xl">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-brand-500" />
                    CPU Backup (Espelho)
                  </span>
                  <button
                    onClick={() => setShowBackupInfo(false)}
                    className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-surface-hover text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {hasCpuStandby ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs">
                      <Cloud className="w-3.5 h-3.5 text-cyan-400" />
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
                        cpuStandby.state === 'syncing' ? 'bg-cyan-500/20 text-cyan-400' :
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
                : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20 hover:bg-cyan-500/20'
            }`}
            title="Clique para copiar IP"
          >
            {copiedField === 'ip' ? 'Copiado!' : machine.public_ipaddr}
          </button>
        )}

        {/* GPU RAM Popover */}
        <Popover>
          <PopoverTrigger asChild>
            <button className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30 hover:bg-gray-700/50 hover:border-gray-600/50 transition-all cursor-help">
              {gpuRam}GB
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-56">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-green-400" />
                <span className="text-sm font-semibold text-white">GPU Memory</span>
              </div>
              <p className="text-xs text-gray-400">
                <span className="text-green-400 font-semibold">{gpuRam}GB</span> VRAM disponível para processamento de IA e computação paralela.
              </p>
              {machine.gpu_name && (
                <p className="text-xs text-gray-500 pt-1 border-t border-gray-700/30">
                  <span className="text-gray-400">Modelo:</span> {machine.gpu_name}
                </p>
              )}
            </div>
          </PopoverContent>
        </Popover>

        {/* CPU Cores Popover */}
        <Popover>
          <PopoverTrigger asChild>
            <button className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30 hover:bg-gray-700/50 hover:border-gray-600/50 transition-all cursor-help">
              {cpuCores}CPU
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-56">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-orange-400" />
                <span className="text-sm font-semibold text-white">CPU Cores</span>
              </div>
              <p className="text-xs text-gray-400">
                <span className="text-orange-400 font-semibold">{cpuCores}</span> núcleos de processamento disponíveis para aplicações gerais.
              </p>
              <p className="text-xs text-gray-500 pt-1 border-t border-gray-700/30">
                Ideal para tarefas multi-thread e processamento paralelo de dados.
              </p>
            </div>
          </PopoverContent>
        </Popover>

        {/* System RAM Popover */}
        <Popover>
          <PopoverTrigger asChild>
            <button className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30 hover:bg-gray-700/50 hover:border-gray-600/50 transition-all cursor-help">
              {ram}GB RAM
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-56">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-semibold text-white">System RAM</span>
              </div>
              <p className="text-xs text-gray-400">
                <span className="text-cyan-400 font-semibold">{ram}GB</span> de memória do sistema para aplicações e dados em tempo de execução.
              </p>
              <p className="text-xs text-gray-500 pt-1 border-t border-gray-700/30">
                Separado da VRAM - usado para código de aplicação, frameworks e datasets.
              </p>
            </div>
          </PopoverContent>
        </Popover>
        {isRunning && syncStatus && (
          <span
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded border cursor-help ${
              syncStatus === 'syncing'
                ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
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
                <div className="text-[8px] text-cyan-400 mt-0.5">+backup</div>
              )}
            </div>
            {uptime && (
              <div className="text-center">
                <div className="text-cyan-400 font-mono text-sm font-bold">{uptime}</div>
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
            {/* Simulate Failover Button (Demo only, requires CPU Standby) */}
            {onSimulateFailover && hasCpuStandby && !isInFailover && (
              <button
                onClick={() => onSimulateFailover(machine)}
                className="flex-1 py-2 rounded-lg bg-red-600/20 border border-red-500/30 text-red-400 text-xs font-medium flex items-center justify-center gap-1.5 hover:bg-red-600/30 transition-colors"
                title="Simular roubo de GPU e failover automático"
              >
                <Zap className="w-3.5 h-3.5" />
                Simular Failover
              </button>
            )}

            {/* Migration Button */}
            <button
              onClick={() => onMigrate && onMigrate(machine)}
              className="flex-1 py-2 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 text-xs font-medium flex items-center justify-center gap-1.5 hover:bg-cyan-600/30 transition-colors"
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
                <div className="text-[8px] text-cyan-400 mt-0.5">+backup</div>
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
        <div className="mt-2 p-2 rounded bg-cyan-500/10 border border-cyan-500/20 text-[10px] text-cyan-300 text-center">
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

// Demo machines data with rich details
const DEMO_MACHINES = [
  {
    id: 12345678,
    gpu_name: 'RTX 4090',
    actual_status: 'running',
    status: 'running',
    gpu_ram: 24576,
    cpu_cores: 16,
    cpu_ram: 64,
    disk_space: 500,
    dph_total: 0.45,
    total_dph: 0.46,
    public_ipaddr: '203.0.113.45',
    ssh_host: 'ssh4.vast.ai',
    ssh_port: 22345,
    start_date: new Date(Date.now() - 3600000 * 5).toISOString(),
    label: 'dev-workspace-01',
    gpu_util: 45.2,
    gpu_temp: 62,
    ports: { '22': 22345, '8080': 8080 },
    provider: 'vast.ai',
    cpu_standby: {
      enabled: true,
      provider: 'gcp',
      name: 'standby-dev-us',
      zone: 'us-central1-a',
      ip: '35.192.45.123',
      machine_type: 'e2-medium',
      status: 'running',
      dph_total: 0.01,
      sync_enabled: true,
      sync_count: 234,
      state: 'ready'
    }
  },
  {
    id: 23456789,
    gpu_name: 'A100 80GB',
    actual_status: 'running',
    status: 'running',
    gpu_ram: 81920,
    cpu_cores: 32,
    cpu_ram: 128,
    disk_space: 1000,
    dph_total: 2.10,
    total_dph: 2.11,
    public_ipaddr: '198.51.100.78',
    ssh_host: 'ssh7.vast.ai',
    ssh_port: 22789,
    start_date: new Date(Date.now() - 3600000 * 12).toISOString(),
    label: 'ml-training-large',
    gpu_util: 92.5,
    gpu_temp: 71,
    ports: { '22': 22789, '8080': 8080, '6006': 6006 },
    provider: 'vast.ai',
    cpu_standby: {
      enabled: true,
      provider: 'gcp',
      name: 'standby-ml-eu',
      zone: 'europe-west1-b',
      ip: '35.204.123.45',
      machine_type: 'e2-medium',
      status: 'running',
      dph_total: 0.01,
      sync_enabled: true,
      sync_count: 567,
      state: 'syncing'
    }
  },
  {
    id: 34567890,
    gpu_name: 'RTX 3090',
    actual_status: 'stopped',
    status: 'stopped',
    gpu_ram: 24576,
    cpu_cores: 12,
    cpu_ram: 48,
    disk_space: 250,
    dph_total: 0.35,
    total_dph: 0.35,
    ssh_host: 'ssh2.vast.ai',
    ssh_port: 22123,
    label: 'stable-diffusion-dev',
    provider: 'vast.ai',
    cpu_standby: null
  },
  {
    id: 45678901,
    gpu_name: 'RTX 4080',
    actual_status: 'stopped',
    status: 'stopped',
    gpu_ram: 16384,
    cpu_cores: 8,
    cpu_ram: 32,
    disk_space: 200,
    dph_total: 0.28,
    total_dph: 0.28,
    ssh_host: 'ssh5.vast.ai',
    ssh_port: 22456,
    label: 'inference-api',
    provider: 'vast.ai',
    cpu_standby: null
  },
  {
    id: 56789012,
    gpu_name: 'H100 80GB',
    actual_status: 'running',
    status: 'running',
    gpu_ram: 81920,
    cpu_cores: 64,
    cpu_ram: 256,
    disk_space: 2000,
    dph_total: 3.50,
    total_dph: 3.51,
    public_ipaddr: '192.0.2.100',
    ssh_host: 'ssh9.vast.ai',
    ssh_port: 22999,
    start_date: new Date(Date.now() - 3600000 * 2).toISOString(),
    label: 'llm-finetuning',
    gpu_util: 78.3,
    gpu_temp: 68,
    ports: { '22': 22999, '8080': 8080 },
    provider: 'vast.ai',
    cpu_standby: {
      enabled: true,
      provider: 'gcp',
      name: 'standby-llm-us',
      zone: 'us-east1-b',
      ip: '35.231.89.123',
      machine_type: 'e2-standard-4',
      status: 'running',
      dph_total: 0.02,
      sync_enabled: true,
      sync_count: 89,
      state: 'ready'
    }
  }
]

// Main Machines Page
export default function Machines() {
  const location = useLocation()
  const isDemo = isDemoMode()

  const [machines, setMachines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all') // all, online, offline
  const [syncStatus, setSyncStatus] = useState({}) // machineId -> 'idle' | 'syncing' | 'synced'
  const [lastSyncTime, setLastSyncTime] = useState({}) // machineId -> timestamp
  const [destroyDialog, setDestroyDialog] = useState({ open: false, machineId: null, machineName: '' })
  const [migrationTarget, setMigrationTarget] = useState(null) // machine to migrate
  const [syncStats, setSyncStats] = useState({}) // machineId -> { files_new, files_changed, data_added, ... }
  const [demoToast, setDemoToast] = useState(null) // Toast message for demo actions
  const [failoverProgress, setFailoverProgress] = useState({}) // machineId -> { phase, message, newGpu, metrics }
  const [failoverHistory, setFailoverHistory] = useState([]) // Array of completed failover events

  // Create machine modal state
  const [createModal, setCreateModal] = useState({ open: false, offer: null, creating: false, error: null })

  // Show demo toast
  const showDemoToast = (message, type = 'success') => {
    setDemoToast({ message, type })
    setTimeout(() => setDemoToast(null), 3000)
  }

  useEffect(() => {
    fetchMachines()
    if (!isDemo) {
      const interval = setInterval(fetchMachines, 5000)
      return () => clearInterval(interval)
    }
  }, [])

  // Handle selectedOffer from Dashboard navigation
  useEffect(() => {
    console.log('[Machines] location.state:', location.state, 'isDemo:', isDemo)
    if (location.state?.selectedOffer) {
      console.log('[Machines] Opening create modal for offer:', location.state.selectedOffer)
      setCreateModal({ open: true, offer: location.state.selectedOffer, creating: false, error: null })
      // Clear the state to prevent reopening on refresh
      window.history.replaceState({}, document.title)
    }
  }, [location.state])

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
      // In demo mode, use local demo data for more interactivity
      if (isDemo) {
        // Simulate loading delay
        await new Promise(r => setTimeout(r, 500))
        setMachines(DEMO_MACHINES)
        setError(null)
        setLoading(false)
        return
      }

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
    const { machineId, machineName } = destroyDialog
    setDestroyDialog({ open: false, machineId: null, machineName: '' })

    if (isDemo) {
      // Demo mode: simulate destruction with animation
      showDemoToast(`Destruindo ${machineName}...`, 'warning')
      await new Promise(r => setTimeout(r, 1500))
      setMachines(prev => prev.filter(m => m.id !== machineId))
      showDemoToast(`${machineName} destruída com sucesso!`, 'success')
      return
    }

    try {
      const res = await apiDelete(`/api/v1/instances/${machineId}`)
      if (!res.ok) throw new Error('Erro ao destruir máquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  // Create instance from offer (called from Dashboard or Nova Máquina)
  const handleCreateInstance = async (offer) => {
    if (isDemo) {
      showDemoToast('Criando máquina demo...', 'info')
      await new Promise(r => setTimeout(r, 2000))
      const newMachine = {
        id: Date.now(),
        gpu_name: offer.gpu_name,
        num_gpus: offer.num_gpus || 1,
        gpu_ram: offer.gpu_ram,
        cpu_cores: offer.cpu_cores,
        cpu_ram: offer.cpu_ram,
        disk_space: offer.disk_space,
        dph_total: offer.dph_total,
        actual_status: 'running',
        status: 'running',
        start_date: new Date().toISOString(),
        public_ipaddr: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
        ssh_host: 'ssh.vast.ai',
        ssh_port: 22000 + Math.floor(Math.random() * 1000),
        cpu_standby: { enabled: true, state: 'syncing' }
      }
      setMachines(prev => [newMachine, ...prev])
      setCreateModal({ open: false, offer: null, creating: false, error: null })
      showDemoToast(`${offer.gpu_name} criada com CPU Standby!`, 'success')
      return
    }

    setCreateModal(prev => ({ ...prev, creating: true, error: null }))
    try {
      const res = await apiPost('/api/v1/instances', {
        offer_id: offer.id,
        disk_size: offer.disk_space || 100,
        label: `${offer.gpu_name} - ${new Date().toLocaleDateString()}`
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || data.error || 'Erro ao criar instância')
      }

      const data = await res.json()
      setCreateModal({ open: false, offer: null, creating: false, error: null })
      fetchMachines()

      // Show success message
      showDemoToast(`${offer.gpu_name} criada! CPU Standby sendo provisionado...`, 'success')

    } catch (err) {
      setCreateModal(prev => ({ ...prev, creating: false, error: err.message }))
    }
  }

  const handleStart = async (machineId) => {
    if (isDemo) {
      // Demo mode: simulate starting
      const machine = machines.find(m => m.id === machineId)
      showDemoToast(`Iniciando ${machine?.gpu_name || 'máquina'}...`, 'info')
      await new Promise(r => setTimeout(r, 2000))
      setMachines(prev => prev.map(m =>
        m.id === machineId
          ? {
              ...m,
              actual_status: 'running',
              status: 'running',
              start_date: new Date().toISOString(),
              public_ipaddr: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
              gpu_util: Math.floor(Math.random() * 30) + 10,
              gpu_temp: Math.floor(Math.random() * 15) + 55
            }
          : m
      ))
      showDemoToast(`${machine?.gpu_name || 'Máquina'} iniciada!`, 'success')
      return
    }

    try {
      const res = await apiPost(`/api/v1/instances/${machineId}/resume`)
      if (!res.ok) throw new Error('Erro ao iniciar máquina')
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  const handlePause = async (machineId) => {
    if (isDemo) {
      // Demo mode: simulate pausing
      const machine = machines.find(m => m.id === machineId)
      showDemoToast(`Pausando ${machine?.gpu_name || 'máquina'}...`, 'info')
      await new Promise(r => setTimeout(r, 1500))
      setMachines(prev => prev.map(m =>
        m.id === machineId
          ? {
              ...m,
              actual_status: 'stopped',
              status: 'stopped',
              public_ipaddr: null,
              gpu_util: 0,
              gpu_temp: 0
            }
          : m
      ))
      showDemoToast(`${machine?.gpu_name || 'Máquina'} pausada!`, 'success')
      return
    }

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
    if (isDemo) {
      // Demo mode: simulate snapshot
      const machine = machines.find(m => m.id === machineId)
      setSyncStatus(prev => ({ ...prev, [machineId]: 'syncing' }))
      showDemoToast(`Criando snapshot de ${machine?.gpu_name}...`, 'info')
      await new Promise(r => setTimeout(r, 2500))

      const demoStats = {
        files_new: Math.floor(Math.random() * 50) + 5,
        files_changed: Math.floor(Math.random() * 100) + 20,
        files_unmodified: Math.floor(Math.random() * 500) + 200,
        data_added: `${(Math.random() * 500 + 50).toFixed(1)} MB`,
        duration_seconds: (Math.random() * 10 + 2).toFixed(1),
        is_incremental: true
      }

      setSyncStatus(prev => ({ ...prev, [machineId]: 'synced' }))
      setLastSyncTime(prev => ({ ...prev, [machineId]: Date.now() }))
      setSyncStats(prev => ({ ...prev, [machineId]: demoStats }))
      showDemoToast(`Snapshot concluído! ${demoStats.data_added} sincronizados`, 'success')
      return
    }

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

  // Simulate GPU failover (demo mode only) - with enriched metrics
  const handleSimulateFailover = async (machine) => {
    if (!machine.cpu_standby?.enabled) {
      showDemoToast('Esta máquina não tem CPU Standby configurado', 'error')
      return
    }

    // Initialize failover metrics
    const failoverMetrics = {
      id: `fo-${Date.now()}`,
      machine_id: machine.id,
      gpu_name: machine.gpu_name,
      started_at: new Date().toISOString(),
      detection_time_ms: 0,
      failover_time_ms: 0,
      search_time_ms: 0,
      provisioning_time_ms: 0,
      restore_time_ms: 0,
      total_time_ms: 0,
      files_synced: 0,
      data_restored_mb: 0,
      new_gpu_name: null,
      cpu_standby_ip: machine.cpu_standby.ip,
      reason: 'spot_preemption',
      status: 'in_progress',
      phases: []
    }

    // Helper to update failover progress with metrics
    const updateProgress = (phase, message, newGpu = null, phaseMetrics = {}) => {
      const timestamp = Date.now()
      failoverMetrics.phases.push({ phase, timestamp, ...phaseMetrics })

      setFailoverProgress(prev => ({
        ...prev,
        [machine.id]: {
          phase,
          message,
          newGpu,
          metrics: { ...failoverMetrics, ...phaseMetrics }
        }
      }))
    }

    // Phase 1: GPU Lost - Detect the interruption
    const phaseStart = Date.now()
    const detectionTime = Math.floor(Math.random() * 500) + 500 // 500-1000ms
    updateProgress('gpu_lost', `GPU ${machine.gpu_name} foi interrompida (Spot Preemption)`)
    showDemoToast(`⚠️ GPU ${machine.gpu_name} foi interrompida!`, 'warning')

    // Update machine status
    setMachines(prev => prev.map(m =>
      m.id === machine.id ? {
        ...m,
        actual_status: 'failover',
        status: 'failover',
        cpu_standby: { ...m.cpu_standby, state: 'failover_active' }
      } : m
    ))

    await new Promise(r => setTimeout(r, 2000))
    failoverMetrics.detection_time_ms = detectionTime

    // Phase 2: Failover to CPU Standby
    const failoverTime = Math.floor(Math.random() * 300) + 800 // 800-1100ms
    updateProgress('failover_active', `Redirecionando tráfego para CPU Standby (${machine.cpu_standby.ip})`, null, { detection_time_ms: detectionTime })
    showDemoToast(`🔄 Failover automático: usando CPU Standby (${machine.cpu_standby.ip})`, 'info')
    await new Promise(r => setTimeout(r, 2500))
    failoverMetrics.failover_time_ms = failoverTime

    // Phase 3: Searching for new GPU
    const searchTime = Math.floor(Math.random() * 2000) + 2000 // 2-4 seconds
    updateProgress('searching', 'Pesquisando GPUs disponíveis em Vast.ai...', null, { failover_time_ms: failoverTime })
    showDemoToast('🔍 Buscando nova GPU disponível...', 'info')
    await new Promise(r => setTimeout(r, 3000))
    failoverMetrics.search_time_ms = searchTime

    // Phase 4: Provisioning new GPU
    const gpuOptions = ['RTX 4090', 'RTX 4080', 'RTX 3090', 'A100 40GB', 'A100 80GB', 'H100 80GB']
    const newGpu = gpuOptions[Math.floor(Math.random() * gpuOptions.length)]
    const provisioningTime = Math.floor(Math.random() * 20000) + 30000 // 30-50 seconds
    failoverMetrics.new_gpu_name = newGpu
    updateProgress('provisioning', `Provisionando ${newGpu}...`, newGpu, { search_time_ms: searchTime })
    showDemoToast(`🚀 Provisionando nova GPU: ${newGpu}`, 'info')
    await new Promise(r => setTimeout(r, 3500))
    failoverMetrics.provisioning_time_ms = provisioningTime

    // Phase 5: Restoring data
    const filesCount = Math.floor(Math.random() * 3000) + 1000
    const dataSize = Math.floor(Math.random() * 2000) + 500 // 500-2500 MB
    const restoreTime = Math.floor(Math.random() * 20000) + 20000 // 20-40 seconds
    failoverMetrics.files_synced = filesCount
    failoverMetrics.data_restored_mb = dataSize
    failoverMetrics.restore_time_ms = restoreTime
    updateProgress('restoring', `Restaurando ${filesCount.toLocaleString()} arquivos (${dataSize} MB) do CPU Standby...`, newGpu, { provisioning_time_ms: provisioningTime })
    showDemoToast(`📦 Restaurando ${filesCount.toLocaleString()} arquivos para nova GPU...`, 'info')
    await new Promise(r => setTimeout(r, 4000))

    // Phase 6: Complete
    const totalTime = Date.now() - phaseStart
    failoverMetrics.total_time_ms = totalTime
    failoverMetrics.status = 'success'
    failoverMetrics.completed_at = new Date().toISOString()

    updateProgress('complete', `Recuperação completa! Nova GPU ${newGpu} operacional.`, newGpu, {
      restore_time_ms: restoreTime,
      total_time_ms: totalTime,
      files_synced: filesCount,
      data_restored_mb: dataSize
    })

    // Update machine with new GPU
    setMachines(prev => prev.map(m =>
      m.id === machine.id ? {
        ...m,
        gpu_name: newGpu,
        actual_status: 'running',
        status: 'running',
        cpu_standby: { ...m.cpu_standby, state: 'ready', sync_count: (m.cpu_standby.sync_count || 0) + 1 },
        public_ipaddr: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`
      } : m
    ))

    showDemoToast(`✅ Recuperação completa em ${(totalTime / 1000).toFixed(1)}s! Nova GPU: ${newGpu}`, 'success')

    // Save to failover history
    setFailoverHistory(prev => [...prev, failoverMetrics])

    // Also save to localStorage for persistence
    try {
      const existingHistory = JSON.parse(localStorage.getItem('failover_history') || '[]')
      existingHistory.push(failoverMetrics)
      // Keep only last 100 entries
      if (existingHistory.length > 100) existingHistory.shift()
      localStorage.setItem('failover_history', JSON.stringify(existingHistory))
    } catch (e) {
      console.error('Failed to save failover history:', e)
    }

    // Clear progress after 5 seconds
    setTimeout(() => {
      setFailoverProgress(prev => ({
        ...prev,
        [machine.id]: { phase: 'idle' }
      }))
    }, 5000)
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
      <div className="page-container">
        <div className="ta-card p-6">
          <SkeletonList count={4} type="machine" />
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Page Header - TailAdmin Style */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <div className="stat-card-icon stat-card-icon-success">
                <Server className="w-5 h-5" />
              </div>
              Minhas Máquinas
            </h1>
            <p className="page-subtitle">Gerencie suas instâncias de GPU e CPU</p>
          </div>
          <Link
            to={isDemo ? "/demo-app" : "/app"}
            className="ta-btn ta-btn-primary"
          >
            <Plus className="w-4 h-4" />
            Nova Máquina
          </Link>
        </div>
      </div>

      {/* Stats Summary - TailAdmin Cards */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-card-label">GPUs Ativas</p>
              <p className="stat-card-value">{activeMachines.length}</p>
            </div>
            <div className="stat-card-icon stat-card-icon-success">
              <Server className="w-5 h-5" />
            </div>
          </div>
        </div>
        {totalCpuStandbyCount > 0 && (
          <div className="stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-card-label">CPU Backup</p>
                <p className="stat-card-value">{totalCpuStandbyCount}</p>
              </div>
              <div className="stat-card-icon stat-card-icon-primary">
                <Shield className="w-5 h-5" />
              </div>
            </div>
          </div>
        )}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-card-label">VRAM Total</p>
              <p className="stat-card-value">{Math.round(totalGpuMem / 1024)} GB</p>
            </div>
            <div className="stat-card-icon stat-card-icon-warning">
              <Cpu className="w-5 h-5" />
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-card-label">Custo/Hora</p>
              <p className="stat-card-value">${totalCostPerHour.toFixed(2)}</p>
            </div>
            <div className="stat-card-icon stat-card-icon-error">
              <Activity className="w-5 h-5" />
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs - TailAdmin Style */}
      <div className="ta-card">
        <div className="ta-card-header">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="ta-tabs">
              {[
                { id: 'all', label: 'Todas', count: machines.length },
                { id: 'online', label: 'Online', count: activeMachines.length },
                { id: 'offline', label: 'Offline', count: inactiveMachines.length },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFilter(tab.id)}
                  className={`ta-tab ${filter === tab.id ? 'ta-tab-active' : ''}`}
                >
                  {tab.label} ({tab.count})
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="ta-card-body">

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
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
                  onSimulateFailover={isDemo ? handleSimulateFailover : null}
                  syncStatus={syncStatus[machine.id] || 'idle'}
                  syncStats={syncStats[machine.id]}
                  failoverProgress={failoverProgress[machine.id] || { phase: 'idle' }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Destroy Confirmation Modal */}
      <ConfirmModal
        isOpen={destroyDialog.open}
        onClose={() => setDestroyDialog({ open: false, machineId: null, machineName: '' })}
        onConfirm={confirmDestroy}
        title="Destruir máquina?"
        message={`Tem certeza que deseja destruir a máquina ${destroyDialog.machineName}? Esta ação é irreversível e todos os dados não salvos serão perdidos.`}
        variant="danger"
      />

      {/* Migration Modal */}
      <MigrationModal
        instance={migrationTarget}
        isOpen={!!migrationTarget}
        onClose={() => setMigrationTarget(null)}
        onSuccess={handleMigrationSuccess}
      />

      {/* Create Instance Modal */}
      <AlertDialog open={createModal.open} onOpenChange={(open) => !createModal.creating && setCreateModal(prev => ({ ...prev, open }))}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-green-400" />
              Criar Máquina GPU
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4 pt-2">
                {createModal.offer && (
                  <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/50">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-white font-semibold">{createModal.offer.gpu_name}</span>
                      <span className="text-green-400 font-mono">${createModal.offer.dph_total?.toFixed(3)}/hr</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                      <div>VRAM: {Math.round((createModal.offer.gpu_ram || 24000) / 1024)} GB</div>
                      <div>CPU: {createModal.offer.cpu_cores || 4} cores</div>
                      <div>RAM: {Math.round((createModal.offer.cpu_ram || 16000) / 1024)} GB</div>
                      <div>Disk: {Math.round(createModal.offer.disk_space || 100)} GB</div>
                    </div>
                  </div>
                )}
                <div className="p-3 rounded-lg border border-cyan-700/50 bg-cyan-900/20">
                  <div className="flex items-center gap-2 text-cyan-300 text-sm">
                    <Shield className="w-4 h-4" />
                    <span>CPU Standby será criado automaticamente</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1 ml-6">
                    Uma VM de backup será provisionada para proteção contra interrupções.
                  </p>
                </div>
                {createModal.error && (
                  <div className="p-3 rounded-lg border border-red-700/50 bg-red-900/20 text-red-300 text-sm">
                    {createModal.error}
                  </div>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={createModal.creating}>Cancelar</AlertDialogCancel>
            <button
              onClick={() => handleCreateInstance(createModal.offer)}
              disabled={createModal.creating}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:cursor-not-allowed rounded-md transition-colors"
              data-testid="confirm-create-instance"
            >
              {createModal.creating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Criando...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Criar Máquina
                </>
              )}
            </button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Demo Toast Notification */}
      {demoToast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-xl border flex items-center gap-3 animate-slide-up ${
          demoToast.type === 'success' ? 'bg-green-900/90 border-green-500/50 text-green-100' :
          demoToast.type === 'warning' ? 'bg-yellow-900/90 border-yellow-500/50 text-yellow-100' :
          demoToast.type === 'error' ? 'bg-red-900/90 border-red-500/50 text-red-100' :
          'bg-cyan-900/90 border-cyan-500/50 text-cyan-100'
        }`}>
          {demoToast.type === 'success' && <Check className="w-5 h-5" />}
          {demoToast.type === 'warning' && <RefreshCw className="w-5 h-5 animate-spin" />}
          {demoToast.type === 'info' && <RefreshCw className="w-5 h-5 animate-spin" />}
          <span className="text-sm font-medium">{demoToast.message}</span>
        </div>
      )}

      <style>{`
        @keyframes slide-up {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}
