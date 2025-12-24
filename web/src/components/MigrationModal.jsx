import { useState, useEffect } from 'react';
import { RefreshCw, Cpu, Server, DollarSign, Info, ArrowRight, Check, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { apiPost } from '../utils/api';

// GPU options available
const GPU_OPTIONS = [
  { value: 'RTX_5090', label: 'RTX 5090', vram: '32GB' },
  { value: 'RTX_4090', label: 'RTX 4090', vram: '24GB' },
  { value: 'RTX_4080', label: 'RTX 4080', vram: '16GB' },
  { value: 'RTX_3090', label: 'RTX 3090', vram: '24GB' },
  { value: 'RTX_3080', label: 'RTX 3080', vram: '10GB' },
  { value: 'A100_PCIE', label: 'A100', vram: '40GB' },
  { value: 'RTX_A6000', label: 'RTX A6000', vram: '48GB' },
];

/**
 * Modal de Migração GPU <-> CPU
 */
export default function MigrationModal({ instance, isOpen, onClose, onSuccess }) {
  const isCurrentlyGpu = instance?.num_gpus > 0;
  const defaultTargetType = isCurrentlyGpu ? 'cpu' : 'gpu';

  const [targetType, setTargetType] = useState(defaultTargetType);
  const [gpuName, setGpuName] = useState('RTX_4090');
  const [maxPrice, setMaxPrice] = useState(2.0);
  const [loading, setLoading] = useState(false);
  const [estimating, setEstimating] = useState(false);
  const [error, setError] = useState(null);
  const [estimate, setEstimate] = useState(null);
  const [progress, setProgress] = useState(null);
  const [migrationStarted, setMigrationStarted] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen && instance) {
      setTargetType(instance.num_gpus > 0 ? 'cpu' : 'gpu');
      setError(null);
      setEstimate(null);
      setProgress(null);
      setMigrationStarted(false);
      fetchEstimate();
    }
  }, [isOpen, instance]);

  // Fetch estimate when target changes
  useEffect(() => {
    if (isOpen && instance && !migrationStarted) {
      fetchEstimate();
    }
  }, [targetType, gpuName, maxPrice]);

  const fetchEstimate = async () => {
    if (!instance) return;

    try {
      setEstimating(true);
      setError(null);

      const body = {
        target_type: targetType,
        max_price: maxPrice,
      };
      if (targetType === 'gpu') {
        body.gpu_name = gpuName;
      }

      const res = await apiPost(`/api/instances/${instance.id}/migrate/estimate`, body);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Erro ao buscar estimativa');
      }

      const data = await res.json();
      setEstimate(data);
    } catch (err) {
      console.error('Erro ao buscar estimativa:', err);
      setEstimate(null);
    } finally {
      setEstimating(false);
    }
  };

  const handleMigrate = async () => {
    if (!instance) return;

    try {
      setLoading(true);
      setError(null);
      setMigrationStarted(true);
      setProgress('Iniciando migração...');

      const body = {
        target_type: targetType,
        max_price: maxPrice,
        disk_size: 100,
        auto_destroy_source: true,
      };
      if (targetType === 'gpu') {
        body.gpu_name = gpuName;
      }

      setProgress('Criando snapshot...');

      const res = await apiPost(`/api/instances/${instance.id}/migrate`, body);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Erro na migração');
      }

      if (data.success) {
        setProgress('Migração concluída!');
        setTimeout(() => {
          onSuccess && onSuccess(data);
          onClose();
        }, 1500);
      } else {
        throw new Error(data.error || 'Migração falhou');
      }
    } catch (err) {
      console.error('Erro na migração:', err);
      setError(err.message);
      setMigrationStarted(false);
    } finally {
      setLoading(false);
    }
  };

  const currentGpuName = instance?.gpu_name || 'GPU';
  const currentCost = instance?.dph_total || 0;
  const targetCost = estimate?.target?.cost_per_hour || 0;
  const savings = currentCost - targetCost;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <RefreshCw className="w-5 h-5 text-brand-400" />
            Migrar Instância
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            {currentGpuName} (ID: {instance?.id})
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-start gap-2">
              <Info className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Migration Direction */}
          <div className="flex items-center justify-center gap-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700/50">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-gray-700 flex items-center justify-center mx-auto mb-2">
                {isCurrentlyGpu ? (
                  <Server className="w-6 h-6 text-green-400" />
                ) : (
                  <Cpu className="w-6 h-6 text-brand-400" />
                )}
              </div>
              <p className="text-sm text-gray-300">{isCurrentlyGpu ? 'GPU' : 'CPU'}</p>
              <p className="text-xs text-gray-500">{currentGpuName}</p>
            </div>

            <ArrowRight className="w-6 h-6 text-brand-400" />

            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-brand-500/20 flex items-center justify-center mx-auto mb-2">
                {targetType === 'cpu' ? (
                  <Cpu className="w-6 h-6 text-brand-400" />
                ) : (
                  <Server className="w-6 h-6 text-green-400" />
                )}
              </div>
              <p className="text-sm text-gray-300">{targetType === 'cpu' ? 'CPU' : 'GPU'}</p>
              <p className="text-xs text-gray-500">
                {targetType === 'cpu' ? 'CPU-only' : gpuName.replace('_', ' ')}
              </p>
            </div>
          </div>

          {/* Target Type Selection (only show if can switch both ways) */}
          {!migrationStarted && (
            <div className="space-y-3">
              <Label className="text-sm font-medium">Tipo de Destino</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setTargetType('cpu')}
                  className={`p-3 rounded-lg border transition-all ${
                    targetType === 'cpu'
                      ? 'border-brand-500 bg-brand-500/10'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <Cpu className={`w-5 h-5 mx-auto mb-1 ${targetType === 'cpu' ? 'text-brand-400' : 'text-gray-500'}`} />
                  <p className={`text-sm font-medium ${targetType === 'cpu' ? 'text-white' : 'text-gray-400'}`}>CPU</p>
                  <p className="text-xs text-gray-500">~$0.02/h</p>
                </button>
                <button
                  onClick={() => setTargetType('gpu')}
                  className={`p-3 rounded-lg border transition-all ${
                    targetType === 'gpu'
                      ? 'border-green-500 bg-green-500/10'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <Server className={`w-5 h-5 mx-auto mb-1 ${targetType === 'gpu' ? 'text-green-400' : 'text-gray-500'}`} />
                  <p className={`text-sm font-medium ${targetType === 'gpu' ? 'text-white' : 'text-gray-400'}`}>GPU</p>
                  <p className="text-xs text-gray-500">~$0.30+/h</p>
                </button>
              </div>
            </div>
          )}

          {/* GPU Selection (only if migrating to GPU) */}
          {targetType === 'gpu' && !migrationStarted && (
            <div className="space-y-3">
              <Label className="text-sm font-medium">Modelo da GPU</Label>
              <select
                value={gpuName}
                onChange={(e) => setGpuName(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-dark-surface-secondary border border-gray-200 dark:border-gray-800 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:border-brand-500"
              >
                {GPU_OPTIONS.map((gpu) => (
                  <option key={gpu.value} value={gpu.value}>
                    {gpu.label} ({gpu.vram})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Cost Comparison */}
          {estimate?.available && !migrationStarted && (
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
              <div className="flex items-center gap-2 mb-3">
                <DollarSign className="w-4 h-4 text-yellow-400" />
                <span className="text-sm font-medium">Comparação de Custos</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Atual</p>
                  <p className="text-lg font-bold text-white">${currentCost.toFixed(3)}/h</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Novo</p>
                  <p className="text-lg font-bold text-green-400">${targetCost.toFixed(3)}/h</p>
                </div>
              </div>
              {savings > 0 && (
                <p className="text-center text-xs text-green-400 mt-2">
                  Economia de ${savings.toFixed(3)}/h ({((savings / currentCost) * 100).toFixed(0)}%)
                </p>
              )}
            </div>
          )}

          {/* Estimating loader */}
          {estimating && !migrationStarted && (
            <div className="flex items-center justify-center gap-2 text-gray-400 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Buscando ofertas...
            </div>
          )}

          {/* No offers available */}
          {estimate && !estimate.available && !migrationStarted && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
              <p className="text-yellow-400 text-sm">{estimate.error || 'Nenhuma oferta disponível'}</p>
            </div>
          )}

          {/* Migration Progress */}
          {migrationStarted && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-brand-400">
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Check className="w-5 h-5 text-green-400" />
                )}
                <span className="font-medium">{progress}</span>
              </div>
              {loading && (
                <div className="space-y-2 text-sm text-gray-400">
                  <p>1. Criando snapshot do workspace...</p>
                  <p>2. Provisionando nova instância...</p>
                  <p>3. Aguardando SSH ficar pronto...</p>
                  <p>4. Restaurando snapshot...</p>
                  <p>5. Destruindo instância antiga...</p>
                </div>
              )}
            </div>
          )}

          {/* Warning */}
          {!migrationStarted && (
            <div className="bg-brand-500/10 border border-brand-500/30 rounded-lg p-3">
              <p className="text-xs text-gray-600 dark:text-gray-300">
                <strong className="text-brand-500 dark:text-brand-400">Processo:</strong> Cria snapshot {'->'} Nova instância {'->'} Restaura {'->'} Destrói antiga
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Tempo estimado: ~5 minutos. Seu workspace será preservado.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={loading}
            className="text-gray-400 hover:text-white"
          >
            Cancelar
          </Button>
          <Button
            onClick={handleMigrate}
            disabled={loading || !estimate?.available || migrationStarted}
            className="bg-brand-500 hover:bg-brand-600 text-white gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Migrando...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                Migrar para {targetType === 'cpu' ? 'CPU' : 'GPU'}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
