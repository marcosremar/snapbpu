import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  Button,
  Badge,
} from './tailadmin-ui'
import {
  Shield,
  Server,
  Cloud,
  Zap,
  Check,
  X,
  RefreshCw,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react'

// Recovery times based on real benchmarks (Dec 2024)
// GCP: START 9.78s | VAST Pause/Resume: 7-165s (varies by GPU) | Spot: ~72s
const FAILOVER_TYPES = [
  {
    id: 'cpu_standby',
    name: 'CPU Standby',
    provider: 'GCP',
    icon: Server,
    description: 'VM de backup em GCP com sync contínuo',
    cost: '$0.01/h',
    rto: '~10 seg',  // Real benchmark: 9.78s start
    rtoNote: 'Benchmark: 9.78s',
    features: ['Sync automático', 'Recovery mais rápido', 'Custo baixo'],
  },
  {
    id: 'gpu_warm',
    name: 'GPU Pause/Resume',
    provider: 'Vast.ai',
    icon: Zap,
    description: 'Pausa GPU mantendo disco, resume quando necessário',
    cost: '$0.005/h',
    rto: '7-45 seg',  // Real benchmark: varies by GPU
    rtoNote: 'Varia: A2000 ~7s, 4060Ti ~44s',
    features: ['Menor custo idle', 'Mantém disco', 'Varia por GPU'],
  },
  {
    id: 'spot_failover',
    name: 'Spot Failover',
    provider: 'Vast.ai',
    icon: Zap,
    description: 'GPUs spot 60-70% mais baratas com failover automático',
    cost: '$0.10/h',
    rto: '~72 seg',  // Estimated from benchmarks
    rtoNote: 'Busca ~2s + Deploy ~30s + Restore ~30s',
    features: ['60-70% economia', 'Auto-failover', 'Busca melhor preço'],
  },
  {
    id: 'multi_region',
    name: 'Cloud Storage',
    provider: 'Multi-cloud',
    icon: Cloud,
    description: 'Snapshot em cloud, restore em qualquer região',
    cost: '$0.02/h',
    rto: '45-60 seg',
    rtoNote: 'Depende do tamanho do snapshot',
    features: ['Qualquer região', 'Geo-redundância', 'Backup seguro'],
  },
]

const MIGRATION_PHASES = [
  { id: 'validating', label: 'Validando configuração', duration: 1500 },
  { id: 'provisioning', label: 'Provisionando novo standby', duration: 3000 },
  { id: 'syncing', label: 'Sincronizando dados', duration: 4000 },
  { id: 'switching', label: 'Trocando failover ativo', duration: 2000 },
  { id: 'cleanup', label: 'Limpando recursos antigos', duration: 1500 },
  { id: 'verifying', label: 'Verificando integridade', duration: 1000 },
]

export default function FailoverMigrationModal({
  machine,
  isOpen,
  onClose,
  onSuccess
}) {
  const [selectedType, setSelectedType] = useState(null)
  const [isMigrating, setIsMigrating] = useState(false)
  const [currentPhase, setCurrentPhase] = useState(0)
  const [migrationResult, setMigrationResult] = useState(null) // 'success' | 'error' | null
  const [errorMessage, setErrorMessage] = useState('')

  const currentFailoverType = machine?.cpu_standby?.enabled
    ? 'cpu_standby'
    : 'none'

  const handleStartMigration = async () => {
    if (!selectedType || selectedType === currentFailoverType) return

    setIsMigrating(true)
    setCurrentPhase(0)
    setMigrationResult(null)
    setErrorMessage('')

    // Simulate migration phases
    for (let i = 0; i < MIGRATION_PHASES.length; i++) {
      setCurrentPhase(i)
      await new Promise(r => setTimeout(r, MIGRATION_PHASES[i].duration))

      // Simulate random failure (10% chance) at sync phase for demo
      if (i === 2 && Math.random() < 0.1) {
        setMigrationResult('error')
        setErrorMessage('Falha na sincronização: timeout ao conectar com o servidor de destino')
        setIsMigrating(false)
        return
      }
    }

    // Success
    setMigrationResult('success')
    setIsMigrating(false)

    // Notify parent after delay
    setTimeout(() => {
      if (onSuccess) {
        onSuccess({
          machine_id: machine.id,
          old_type: currentFailoverType,
          new_type: selectedType,
          migrated_at: new Date().toISOString(),
        })
      }
    }, 2000)
  }

  const handleClose = () => {
    if (isMigrating) return // Prevent closing during migration
    setSelectedType(null)
    setMigrationResult(null)
    setCurrentPhase(0)
    onClose()
  }

  const getTypeById = (id) => FAILOVER_TYPES.find(t => t.id === id)

  return (
    <AlertDialog open={isOpen} onOpenChange={handleClose}>
      <AlertDialogContent className="max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-brand-400" />
            Migrar Tipo de Failover
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4 pt-2">
              {/* Current Machine Info */}
              <div className="p-3 rounded-lg border border-gray-700 bg-gray-800/50">
                <div className="flex items-center justify-between">
                  <span className="text-white font-medium">{machine?.gpu_name}</span>
                  <Badge variant="success" dot>Online</Badge>
                </div>
                <div className="mt-2 text-xs text-gray-400">
                  Failover atual: <span className="text-white font-medium">
                    {currentFailoverType === 'cpu_standby' ? 'CPU Standby (GCP)' : 'Nenhum'}
                  </span>
                </div>
              </div>

              {/* Migration in Progress */}
              {isMigrating && (
                <div className="p-4 rounded-lg border border-brand-500/30 bg-brand-900/20">
                  <div className="flex items-center gap-2 mb-3">
                    <RefreshCw className="w-4 h-4 text-brand-400 animate-spin" />
                    <span className="text-sm font-medium text-brand-300">Migração em progresso...</span>
                  </div>
                  <div className="space-y-2">
                    {MIGRATION_PHASES.map((phase, idx) => (
                      <div
                        key={phase.id}
                        className={`flex items-center gap-2 text-xs ${
                          idx < currentPhase
                            ? 'text-brand-400'
                            : idx === currentPhase
                              ? 'text-brand-400'
                              : 'text-gray-500'
                        }`}
                      >
                        <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                          idx < currentPhase
                            ? 'border-brand-400 bg-brand-500/20'
                            : idx === currentPhase
                              ? 'border-brand-400 bg-brand-500/20'
                              : 'border-gray-600'
                        }`}>
                          {idx < currentPhase ? '✓' : idx === currentPhase ? <RefreshCw className="w-2.5 h-2.5 animate-spin" /> : idx + 1}
                        </div>
                        <span>{phase.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Migration Result */}
              {migrationResult === 'success' && (
                <div className="p-4 rounded-lg border border-brand-500/30 bg-brand-900/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Check className="w-5 h-5 text-brand-400" />
                    <span className="text-sm font-medium text-brand-300">Migração concluída com sucesso!</span>
                  </div>
                  <p className="text-xs text-gray-400">
                    O failover foi migrado de <span className="text-white">{getTypeById(currentFailoverType)?.name || 'Nenhum'}</span> para{' '}
                    <span className="text-brand-400">{getTypeById(selectedType)?.name}</span>.
                  </p>
                </div>
              )}

              {migrationResult === 'error' && (
                <div className="p-4 rounded-lg border border-red-500/30 bg-red-900/20">
                  <div className="flex items-center gap-2 mb-2">
                    <X className="w-5 h-5 text-red-400" />
                    <span className="text-sm font-medium text-red-300">Falha na migração</span>
                  </div>
                  <p className="text-xs text-red-300/80">{errorMessage}</p>
                  <button
                    onClick={handleStartMigration}
                    className="mt-2 text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
                  >
                    <RefreshCw className="w-3 h-3" /> Tentar novamente
                  </button>
                </div>
              )}

              {/* Failover Type Selection */}
              {!isMigrating && !migrationResult && (
                <>
                  <div className="text-sm text-gray-300 mb-2">Selecione o novo tipo de failover:</div>
                  <div className="space-y-2">
                    {FAILOVER_TYPES.map((type) => {
                      const Icon = type.icon
                      const isCurrentType = type.id === currentFailoverType
                      const isSelected = type.id === selectedType

                      return (
                        <button
                          key={type.id}
                          onClick={() => !isCurrentType && setSelectedType(type.id)}
                          disabled={isCurrentType}
                          className={`w-full p-3 rounded-lg border text-left transition-all ${
                            isCurrentType
                              ? 'border-gray-700 bg-gray-800/30 opacity-50 cursor-not-allowed'
                              : isSelected
                                ? 'border-brand-500 bg-brand-500/10'
                                : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className={`p-2 rounded-lg ${
                              isSelected ? 'bg-brand-500/20' : 'bg-gray-700/50'
                            }`}>
                              <Icon className={`w-4 h-4 ${
                                isSelected ? 'text-brand-400' : 'text-gray-400'
                              }`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={`font-medium ${isSelected ? 'text-white' : 'text-gray-300'}`}>
                                  {type.name}
                                </span>
                                <Badge variant="gray" className="text-[10px]">{type.provider}</Badge>
                                {isCurrentType && (
                                  <Badge variant="primary" className="text-[10px]">Atual</Badge>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 mt-0.5">{type.description}</p>
                              <div className="flex flex-col gap-0.5 mt-2 text-[10px]">
                                <div className="flex items-center gap-3">
                                  <span className="text-brand-400">{type.cost}</span>
                                  <span className="text-gray-500">•</span>
                                  <span className="text-gray-300">RTO: {type.rto}</span>
                                </div>
                                {type.rtoNote && (
                                  <span className="text-gray-500 italic">{type.rtoNote}</span>
                                )}
                              </div>
                            </div>
                            {isSelected && (
                              <Check className="w-4 h-4 text-brand-400 flex-shrink-0" />
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>

                  {/* Migration Preview */}
                  {selectedType && selectedType !== currentFailoverType && (
                    <div className="p-3 rounded-lg border border-white/10 bg-white/5">
                      <div className="flex items-center gap-2 text-gray-300 text-xs mb-2">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span className="font-medium">Confirmar migração</span>
                      </div>
                      <div className="flex items-center justify-center gap-2 text-sm">
                        <span className="text-gray-400">{getTypeById(currentFailoverType)?.name || 'Nenhum'}</span>
                        <ArrowRight className="w-4 h-4 text-brand-400" />
                        <span className="text-white font-medium">{getTypeById(selectedType)?.name}</span>
                      </div>
                      <p className="text-[10px] text-gray-500 text-center mt-2">
                        A migração pode levar alguns minutos. A máquina continuará operando normalmente.
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter>
          {migrationResult === 'success' ? (
            <Button onClick={handleClose} variant="primary">
              <Check className="w-4 h-4 mr-2" />
              Concluído
            </Button>
          ) : (
            <>
              <AlertDialogCancel disabled={isMigrating}>Cancelar</AlertDialogCancel>
              <Button
                onClick={handleStartMigration}
                disabled={!selectedType || selectedType === currentFailoverType || isMigrating}
                variant="primary"
              >
                {isMigrating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Migrando...
                  </>
                ) : (
                  <>
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Iniciar Migração
                  </>
                )}
              </Button>
            </>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
