import { useState, useEffect } from 'react';
import { Power, Clock, Gauge, Save, Zap, DollarSign, Info, Cloud, ChevronDown, ChevronUp, HardDrive } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Switch } from './ui/switch';
import { Slider } from './ui/slider';
import { Label } from './ui/label';
import { Button } from './ui/button';

// Failover storage providers
const FAILOVER_PROVIDERS = [
  { id: 'user_default', name: 'Usar Config. do Usuário', description: 'Usa as configurações de cloud storage do usuário' },
  { id: 'backblaze_b2', name: 'Backblaze B2', description: '$6/TB - Melhor custo-benefício' },
  { id: 'cloudflare_r2', name: 'Cloudflare R2', description: 'Sem taxa de egress' },
  { id: 'aws_s3', name: 'AWS S3', description: 'Maior disponibilidade regional' },
  { id: 'google_gcs', name: 'Google Cloud Storage', description: 'Integração com GCP' },
];

/**
 * Modal de Configuração de Auto-Hibernação
 * Layout profissional com shadcn/ui
 */
export default function HibernationConfigModal({ instance, isOpen, onClose, onSave }) {
  const [config, setConfig] = useState({
    auto_hibernation_enabled: true,
    pause_after_minutes: 3,
    delete_after_minutes: 30,
    gpu_usage_threshold: 5.0,
    // Failover storage config
    failover_storage: {
      provider: 'user_default',
      bucket: '',
      mount_path: '/data',
    },
  });

  const [showFailoverConfig, setShowFailoverConfig] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && instance) {
      loadConfig();
    }
  }, [isOpen, instance]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/instances/${instance.id}/config`);

      if (!response.ok) {
        throw new Error('Erro ao carregar configuração');
      }

      const data = await response.json();
      // Ensure failover_storage has default values
      setConfig({
        ...data,
        failover_storage: data.failover_storage || {
          provider: 'user_default',
          bucket: '',
          mount_path: '/data',
        },
      });
    } catch (err) {
      console.error('Erro ao carregar config:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/instances/${instance.id}/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Erro ao salvar configuração');
      }

      const data = await response.json();

      if (onSave) {
        onSave(data.config);
      }

      onClose();
    } catch (err) {
      console.error('Erro ao salvar:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Calcular economia estimada
  const calculateSavings = () => {
    if (!config.auto_hibernation_enabled) return null;

    const hoursPerDay = 6; // Assumindo 6h de uso
    const rtx5090Price = 1.50;
    const rtx3090Price = 0.30;

    const monthlyHours = 24 * 30;
    const usageHours = hoursPerDay * 30;
    const idleHours = monthlyHours - usageHours;

    const rtx5090Savings = (idleHours * rtx5090Price).toFixed(0);
    const rtx3090Savings = (idleHours * rtx3090Price).toFixed(0);
    const rtx5090Percent = ((idleHours / monthlyHours) * 100).toFixed(0);

    return { rtx5090Savings, rtx3090Savings, rtx5090Percent };
  };

  const savings = calculateSavings();

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Power className="w-5 h-5 text-emerald-400" />
            Configuração de Auto-Hibernação
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            {instance?.name || instance?.id}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-start gap-2">
              <Info className="w-4 h-4 text-red-400 mt-0.5" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Toggle Principal */}
          <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700/50">
            <div className="space-y-0.5 flex-1">
              <Label className="text-base font-medium text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-emerald-400" />
                Auto-Hibernação Inteligente
              </Label>
              <p className="text-sm text-gray-400">
                Hiberna automaticamente quando a GPU fica ociosa, economizando até 83% dos custos
              </p>
            </div>
            <Switch
              checked={config.auto_hibernation_enabled}
              onCheckedChange={(checked) =>
                setConfig({ ...config, auto_hibernation_enabled: checked })
              }
            />
          </div>

          {/* Configurações Detalhadas */}
          {config.auto_hibernation_enabled && (
            <div className="space-y-6">
              {/* Threshold de GPU */}
              <div className="space-y-3">
                <Label className="text-base font-medium flex items-center gap-2">
                  <Gauge className="w-4 h-4 text-emerald-400" />
                  Threshold de Uso da GPU
                </Label>
                <div className="flex items-center gap-4">
                  <Slider
                    value={[config.gpu_usage_threshold]}
                    onValueChange={([value]) =>
                      setConfig({ ...config, gpu_usage_threshold: value })
                    }
                    min={1}
                    max={50}
                    step={0.5}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-1 min-w-[80px] px-3 py-2 bg-gray-800 rounded-md border border-gray-700">
                    <span className="text-white font-medium">{config.gpu_usage_threshold}</span>
                    <span className="text-gray-400 text-sm">%</span>
                  </div>
                </div>
                <p className="text-xs text-gray-400 flex items-start gap-2">
                  <Info className="w-3 h-3 mt-0.5 text-emerald-400" />
                  GPU considerada ociosa quando utilização ficar abaixo deste valor
                </p>
              </div>

              {/* Tempo para Pausar */}
              <div className="space-y-3">
                <Label className="text-base font-medium flex items-center gap-2">
                  <Clock className="w-4 h-4 text-orange-400" />
                  Tempo Até Hibernar
                </Label>
                <div className="flex items-center gap-4">
                  <Slider
                    value={[config.pause_after_minutes]}
                    onValueChange={([value]) =>
                      setConfig({ ...config, pause_after_minutes: value })
                    }
                    min={1}
                    max={30}
                    step={1}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-1 min-w-[80px] px-3 py-2 bg-gray-800 rounded-md border border-gray-700">
                    <span className="text-white font-medium">{config.pause_after_minutes}</span>
                    <span className="text-gray-400 text-sm">min</span>
                  </div>
                </div>
                <div className="bg-orange-500/10 border border-orange-500/30 rounded-md p-3">
                  <p className="text-xs text-gray-300 mb-2">
                    Após <strong className="text-orange-400">{config.pause_after_minutes} minutos</strong> com GPU {'<'} {config.gpu_usage_threshold}%, o sistema:
                  </p>
                  <ul className="text-xs text-gray-300 space-y-1 ml-4">
                    <li>• Cria snapshot ANS comprimido (~20s)</li>
                    <li>• Destroi instância vast.ai</li>
                    <li>• <span className="text-green-400 font-medium">Economia: 100% do custo/hora</span></li>
                  </ul>
                </div>
              </div>

              {/* Tempo para Deletar */}
              <div className="space-y-3">
                <Label className="text-base font-medium flex items-center gap-2">
                  <Clock className="w-4 h-4 text-red-400" />
                  Tempo Até Marcar como Deletada
                </Label>
                <div className="flex items-center gap-4">
                  <Slider
                    value={[config.delete_after_minutes]}
                    onValueChange={([value]) =>
                      setConfig({ ...config, delete_after_minutes: value })
                    }
                    min={5}
                    max={120}
                    step={5}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-1 min-w-[80px] px-3 py-2 bg-gray-800 rounded-md border border-gray-700">
                    <span className="text-white font-medium">{config.delete_after_minutes}</span>
                    <span className="text-gray-400 text-sm">min</span>
                  </div>
                </div>
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-md p-3">
                  <p className="text-xs text-gray-300">
                    Após <strong className="text-red-400">{config.delete_after_minutes} minutos</strong> hibernada, marca como <span className="text-red-400">deleted</span>
                  </p>
                  <p className="text-xs text-green-400 mt-1">
                    ✓ Snapshot permanece seguro no R2 (custo: ~$0.01/mês)
                  </p>
                </div>
              </div>

              {/* Failover Storage Configuration */}
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => setShowFailoverConfig(!showFailoverConfig)}
                  className="w-full flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 hover:border-purple-500/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Cloud className="w-4 h-4 text-purple-400" />
                    <span className="text-base font-medium text-white">Cloud Storage Failover</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-400">
                      {config.failover_storage?.provider === 'user_default'
                        ? 'Usar Config. do Usuário'
                        : FAILOVER_PROVIDERS.find(p => p.id === config.failover_storage?.provider)?.name || 'Não configurado'}
                    </span>
                    {showFailoverConfig ? (
                      <ChevronUp className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </button>

                {showFailoverConfig && (
                  <div className="space-y-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
                    <p className="text-sm text-gray-400">
                      Configure onde os dados serão armazenados para failover global.
                      Permite restaurar em qualquer região do mundo.
                    </p>

                    {/* Provider Selection */}
                    <div className="space-y-2">
                      <Label className="text-sm text-gray-300">Provedor de Storage</Label>
                      <div className="grid grid-cols-1 gap-2">
                        {FAILOVER_PROVIDERS.map((provider) => (
                          <label
                            key={provider.id}
                            className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                              config.failover_storage?.provider === provider.id
                                ? 'border-purple-500 bg-purple-500/10'
                                : 'border-gray-700 hover:border-gray-600'
                            }`}
                          >
                            <input
                              type="radio"
                              name="failover_provider"
                              value={provider.id}
                              checked={config.failover_storage?.provider === provider.id}
                              onChange={(e) =>
                                setConfig({
                                  ...config,
                                  failover_storage: {
                                    ...config.failover_storage,
                                    provider: e.target.value,
                                  },
                                })
                              }
                              className="sr-only"
                            />
                            <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                              config.failover_storage?.provider === provider.id
                                ? 'border-purple-500'
                                : 'border-gray-600'
                            }`}>
                              {config.failover_storage?.provider === provider.id && (
                                <div className="w-2 h-2 rounded-full bg-purple-500" />
                              )}
                            </div>
                            <div className="flex-1">
                              <p className="text-sm text-white font-medium">{provider.name}</p>
                              <p className="text-xs text-gray-400">{provider.description}</p>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Custom bucket config (only if not using user default) */}
                    {config.failover_storage?.provider !== 'user_default' && (
                      <div className="space-y-3 pt-2 border-t border-gray-700/50">
                        <div className="space-y-2">
                          <Label className="text-sm text-gray-300">Bucket Name</Label>
                          <input
                            type="text"
                            value={config.failover_storage?.bucket || ''}
                            onChange={(e) =>
                              setConfig({
                                ...config,
                                failover_storage: {
                                  ...config.failover_storage,
                                  bucket: e.target.value,
                                },
                              })
                            }
                            placeholder="my-failover-bucket"
                            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                          />
                          <p className="text-xs text-gray-500">
                            Bucket específico para esta máquina. Deixe vazio para usar o bucket padrão das configurações.
                          </p>
                        </div>

                        <div className="space-y-2">
                          <Label className="text-sm text-gray-300">Mount Path</Label>
                          <input
                            type="text"
                            value={config.failover_storage?.mount_path || '/data'}
                            onChange={(e) =>
                              setConfig({
                                ...config,
                                failover_storage: {
                                  ...config.failover_storage,
                                  mount_path: e.target.value,
                                },
                              })
                            }
                            placeholder="/data"
                            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                          />
                        </div>
                      </div>
                    )}

                    {/* Info about failover times */}
                    <div className="bg-purple-500/10 border border-purple-500/30 rounded-md p-3">
                      <div className="flex items-start gap-2">
                        <HardDrive className="w-4 h-4 text-purple-400 mt-0.5" />
                        <div className="text-xs text-gray-300">
                          <p className="mb-1">
                            <strong className="text-purple-400">Cloud Storage Failover</strong> permite restaurar em qualquer região (~45-60s)
                          </p>
                          <p className="text-gray-400">
                            Comparativo: Warm Pool (~6s) → Regional Volume (~23s) → Cloud Storage (~47s)
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Economia Estimada */}
              {savings && (
                <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/30 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <DollarSign className="w-5 h-5 text-green-400" />
                    <h4 className="text-green-400 font-semibold">Economia Estimada</h4>
                  </div>
                  <p className="text-sm text-gray-300 mb-3">
                    Usando GPU <strong>6 horas/dia</strong>, você economiza:
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-black/20 rounded-md p-3 border border-green-500/20">
                      <p className="text-xs text-gray-400 mb-1">RTX 5090 ($1.50/h)</p>
                      <p className="text-lg font-bold text-green-400">${savings.rtx5090Savings}/mês</p>
                      <p className="text-xs text-gray-300">({savings.rtx5090Percent}% economia)</p>
                    </div>
                    <div className="bg-black/20 rounded-md p-3 border border-green-500/20">
                      <p className="text-xs text-gray-400 mb-1">RTX 3090 ($0.30/h)</p>
                      <p className="text-lg font-bold text-green-400">${savings.rtx3090Savings}/mês</p>
                      <p className="text-xs text-gray-300">(83% economia)</p>
                    </div>
                  </div>
                </div>
              )}
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
            onClick={handleSave}
            disabled={loading}
            className="bg-emerald-500 hover:bg-emerald-600 text-white gap-2"
          >
            <Save className="w-4 h-4" />
            {loading ? 'Salvando...' : 'Salvar Configuração'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
