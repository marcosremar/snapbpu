import { useState } from 'react'
import {
  X,
  Zap,
  Server,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Cloud,
  MapPin,
  Gauge,
  HardDrive,
  Info
} from 'lucide-react'
import {
  AlertDialog,
  AlertDialogContent,
  Badge,
  Button,
  Input,
} from '../tailadmin-ui'

const GPU_OPTIONS = [
  { name: 'RTX 4090', vram: 24, price_ondemand: 0.31, price_spot: 0.18, available: 'high' },
  { name: 'RTX 4080', vram: 16, price_ondemand: 0.25, price_spot: 0.15, available: 'high' },
  { name: 'RTX 3090', vram: 24, price_ondemand: 0.20, price_spot: 0.12, available: 'medium' },
  { name: 'RTX 3080', vram: 10, price_ondemand: 0.15, price_spot: 0.09, available: 'high' },
  { name: 'A100 40GB', vram: 40, price_ondemand: 0.64, price_spot: 0.38, available: 'medium' },
  { name: 'A100 80GB', vram: 80, price_ondemand: 0.90, price_spot: 0.54, available: 'low' },
  { name: 'H100 PCIe', vram: 80, price_ondemand: 1.20, price_spot: 0.72, available: 'low' },
  { name: 'L40S', vram: 48, price_ondemand: 0.85, price_spot: 0.51, available: 'medium' },
]

const REGIONS = [
  { id: 'US', name: 'United States', latency: '15ms' },
  { id: 'EU', name: 'Europe', latency: '45ms' },
  { id: 'ASIA', name: 'Asia Pacific', latency: '180ms' },
]

export default function CreateServerlessModal({ onClose, onCreate }) {
  const [step, setStep] = useState(1)
  const [config, setConfig] = useState({
    name: '',
    machine_type: 'spot', // padrão: spot
    gpu_name: 'RTX 4090',
    region: 'US',
    min_instances: 0,
    max_instances: 5,
    target_latency_ms: 500,
    timeout_seconds: 300,
    docker_image: '',
    env_vars: {},
  })

  const selectedGpu = GPU_OPTIONS.find(g => g.name === config.gpu_name)
  const selectedRegion = REGIONS.find(r => r.id === config.region)

  const pricePerHour = config.machine_type === 'spot'
    ? selectedGpu?.price_spot
    : selectedGpu?.price_ondemand

  const savingsPercent = selectedGpu
    ? Math.round(((selectedGpu.price_ondemand - selectedGpu.price_spot) / selectedGpu.price_ondemand) * 100)
    : 0

  const handleSubmit = () => {
    onCreate(config)
  }

  return (
    <AlertDialog open={true} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-dark-surface-card border-b border-white/10 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-brand-400" />
              Criar Endpoint Serverless
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Auto-scaling GPU endpoint com pricing otimizado
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content - com scroll */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Step 1: Básico */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">1. Informações Básicas</h3>
            <div className="space-y-4">
              <div>
                <Input
                  label="Nome do Endpoint"
                  value={config.name}
                  onChange={(e) => setConfig({ ...config, name: e.target.value })}
                  placeholder="meu-endpoint-llama2"
                  helper={`URL: https://${config.name || 'meu-endpoint'}.dumont.cloud`}
                />
              </div>

              <div>
                <Input
                  label="Imagem Docker"
                  value={config.docker_image}
                  onChange={(e) => setConfig({ ...config, docker_image: e.target.value })}
                  placeholder="ollama/ollama, pytorch/pytorch, etc"
                />
              </div>
            </div>
          </div>

          {/* Step 2: Machine Type (SPOT vs ON-DEMAND) */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">2. Tipo de Máquina</h3>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Spot Option */}
              <button
                onClick={() => setConfig({ ...config, machine_type: 'spot' })}
                className={`p-4 rounded-xl border-2 transition-all text-left ${
                  config.machine_type === 'spot'
                    ? 'border-brand-500 bg-brand-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Zap className={`w-5 h-5 ${
                      config.machine_type === 'spot' ? 'text-brand-400' : 'text-gray-400'
                    }`} />
                    <span className={`font-bold ${
                      config.machine_type === 'spot' ? 'text-white' : 'text-gray-400'
                    }`}>
                      Spot
                    </span>
                  </div>
                  <Badge className="bg-brand-500/20 text-brand-400 border-brand-500/30">
                    -{savingsPercent}%
                  </Badge>
                </div>
                <p className="text-xs text-gray-500 mb-3">
                  Mais barato, pode ser interrompido. Auto-restart automático.
                </p>
                <div className="flex items-center gap-1 text-sm">
                  <DollarSign className="w-4 h-4 text-brand-400" />
                  <span className="font-bold text-white">
                    ${selectedGpu?.price_spot.toFixed(2)}
                  </span>
                  <span className="text-gray-500">/hora</span>
                </div>
              </button>

              {/* On-Demand Option */}
              <button
                onClick={() => setConfig({ ...config, machine_type: 'on-demand' })}
                className={`p-4 rounded-xl border-2 transition-all text-left ${
                  config.machine_type === 'on-demand'
                    ? 'border-brand-500 bg-brand-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Server className={`w-5 h-5 ${
                      config.machine_type === 'on-demand' ? 'text-brand-400' : 'text-gray-400'
                    }`} />
                    <span className={`font-bold ${
                      config.machine_type === 'on-demand' ? 'text-white' : 'text-gray-400'
                    }`}>
                      On-Demand
                    </span>
                  </div>
                  <Badge className="bg-white/5 text-gray-400 border-white/10">
                    Estável
                  </Badge>
                </div>
                <p className="text-xs text-gray-500 mb-3">
                  Preço fixo, não interruptível. Mais estável e previsível.
                </p>
                <div className="flex items-center gap-1 text-sm">
                  <DollarSign className="w-4 h-4 text-gray-400" />
                  <span className="font-bold text-white">
                    ${selectedGpu?.price_ondemand.toFixed(2)}
                  </span>
                  <span className="text-gray-500">/hora</span>
                </div>
              </button>
            </div>

            {/* Spot Warning */}
            {config.machine_type === 'spot' && (
              <div className="p-4 rounded-lg bg-brand-500/10 border border-brand-500/20">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-brand-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="text-sm font-medium text-brand-300 mb-1">
                      Como funciona o Spot
                    </h4>
                    <ul className="text-xs text-gray-400 space-y-1">
                      <li>• Disco persistente na região escolhida (Regional Volume + R2)</li>
                      <li>• GPU pode ser interrompida a qualquer momento</li>
                      <li>• Auto-restart busca nova GPU e reconecta o disco</li>
                      <li>• Economia de até {savingsPercent}% vs On-Demand</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Step 3: GPU & Region */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">3. GPU e Região</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  <Server className="w-4 h-4 inline mr-1" />
                  GPU
                </label>
                <select
                  value={config.gpu_name}
                  onChange={(e) => setConfig({ ...config, gpu_name: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg bg-dark-surface-secondary border border-white/10 text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                >
                  {GPU_OPTIONS.map((gpu) => (
                    <option key={gpu.name} value={gpu.name}>
                      {gpu.name} - {gpu.vram}GB - ${config.machine_type === 'spot' ? gpu.price_spot : gpu.price_ondemand}/h
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  <MapPin className="w-4 h-4 inline mr-1" />
                  Região
                </label>
                <select
                  value={config.region}
                  onChange={(e) => setConfig({ ...config, region: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg bg-dark-surface-secondary border border-white/10 text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                >
                  {REGIONS.map((region) => (
                    <option key={region.id} value={region.id}>
                      {region.name} ({region.latency})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Step 4: Auto-scaling */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">4. Auto-Scaling</h3>

            <div className="grid grid-cols-2 gap-4">
              <Input
                type="number"
                label="Mín Instâncias"
                value={config.min_instances}
                onChange={(e) => setConfig({ ...config, min_instances: parseInt(e.target.value) || 0 })}
                min="0"
                max="10"
                helper="0 = scale to zero quando sem uso"
              />

              <Input
                type="number"
                label="Máx Instâncias"
                value={config.max_instances}
                onChange={(e) => setConfig({ ...config, max_instances: parseInt(e.target.value) || 1 })}
                min="1"
                max="50"
              />
            </div>
          </div>

          {/* Price Estimate */}
          <div className="p-4 rounded-lg bg-brand-500/10 border border-brand-500/20">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-white">Estimativa de Custo</h4>
              <DollarSign className="w-4 h-4 text-brand-400" />
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Por hora (1 instância):</span>
                <span className="font-bold text-white">${pricePerHour?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Máximo por dia ({config.max_instances}x 24h):</span>
                <span className="font-bold text-white">
                  ${((pricePerHour || 0) * config.max_instances * 24).toFixed(2)}
                </span>
              </div>
              {config.machine_type === 'spot' && (
                <div className="flex justify-between text-brand-400">
                  <span>Economia vs On-Demand:</span>
                  <span className="font-bold">{savingsPercent}%</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-dark-surface-card border-t border-white/10 px-6 py-4 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={onClose}
          >
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!config.name || !config.docker_image}
            icon={CheckCircle2}
          >
            Criar Endpoint
          </Button>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}
