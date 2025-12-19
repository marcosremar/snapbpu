import { useState, useEffect } from 'react';
import { Power, Clock, Gauge, Save, Zap, DollarSign, Info } from 'lucide-react';
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
  });

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
      setConfig(data);
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
