import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { apiGet, apiPost, apiDelete, isDemoMode } from '../utils/api'
import { ConfirmModal } from '../components/ui/dumont-ui'
import { Plus, Server, Shield, Cpu, Activity, Check, RefreshCw } from 'lucide-react'
import MigrationModal from '../components/MigrationModal'
import { ErrorState } from '../components/ErrorState'
import { EmptyState } from '../components/EmptyState'
import { SkeletonList } from '../components/Skeleton'
import MachineCard from '../components/machines/MachineCard'
import { DEMO_MACHINES } from '../constants/demoData'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from '../components/tailadmin-ui'


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
    if (location.state?.selectedOffer) {
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
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-xl border flex items-center gap-3 animate-slide-up ${demoToast.type === 'success' ? 'bg-green-900/90 border-green-500/50 text-green-100' :
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
