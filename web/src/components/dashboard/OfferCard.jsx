import React from 'react';
import { Cpu, Wifi, Zap, Check, AlertTriangle, Ban } from 'lucide-react';
import { Card, CardContent, Button, Badge } from '../tailadmin-ui';

const OfferCard = ({ offer, onSelect }) => {
  const reliability = offer.reliability || 0;
  const reliabilityColor = reliability >= 0.9 ? 'text-brand-500' : reliability >= 0.7 ? 'text-yellow-500' : 'text-red-500';
  const reliabilityBg = reliability >= 0.9 ? 'bg-brand-500/10' : reliability >= 0.7 ? 'bg-yellow-500/10' : 'bg-red-500/10';

  // Machine history data (supports both API response and internal annotation formats)
  const machineStats = offer._machine_stats || offer.machine_stats;
  const isBlacklisted = offer._is_blacklisted ?? offer.is_blacklisted ?? false;
  const successRate = offer._success_rate ?? offer.success_rate ?? null;
  const reliabilityStatus = offer._reliability_status ?? offer.reliability_status;

  // Determine if machine is problematic
  const isProblematic = isBlacklisted || (successRate !== null && successRate < 0.5);
  const showWarning = !isBlacklisted && successRate !== null && successRate < 0.7 && successRate >= 0.3;

  return (
    <Card className={`group relative overflow-hidden hover:border-brand-600/50 hover:shadow-lg hover:shadow-brand-600/10 transition-all duration-200 cursor-pointer active:scale-[0.98] ${isBlacklisted ? 'opacity-60 border-red-500/50' : isProblematic ? 'border-orange-500/30' : ''}`}>
      {/* Accent bar - red for blacklisted, orange for problematic */}
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${isBlacklisted ? 'bg-red-500' : isProblematic ? 'bg-orange-500' : 'bg-brand-600'} group-hover:h-1 transition-all`} />

      <CardContent className="p-4 pt-5">
        {/* Header with GPU info and price */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className="p-2 rounded-md bg-brand-900/40">
                <Cpu className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                <h3 className="text-gray-900 dark:text-white font-bold text-base leading-tight">
                  {offer.gpu_name}
                </h3>
                {offer.num_gpus > 1 && (
                  <span className="text-xs font-medium text-brand-600 dark:text-brand-400">
                    x{offer.num_gpus} GPUs
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-brand-600 dark:text-brand-400">
              ${offer.dph_total?.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">por hora</div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="text-center p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
            <div className="text-lg font-bold text-gray-900 dark:text-white">
              {offer.gpu_ram?.toFixed(0) || '-'}
            </div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-medium">
              VRAM GB
            </div>
          </div>
          <div className="text-center p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
            <div className="text-lg font-bold text-gray-900 dark:text-white">
              {offer.cpu_cores_effective || '-'}
            </div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-medium">
              CPU Cores
            </div>
          </div>
          <div className="text-center p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50">
            <div className="text-lg font-bold text-gray-900 dark:text-white">
              {offer.disk_space?.toFixed(0) || '-'}
            </div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 font-medium">
              Disco GB
            </div>
          </div>
        </div>

        {/* Secondary Stats */}
        <div className="flex flex-wrap gap-2 mb-4 text-xs">
          <Badge variant="gray" size="sm">
            <Wifi className="w-3 h-3 mr-1" />
            {offer.inet_down?.toFixed(0) || '-'} Mbps
          </Badge>
          <Badge variant="gray" size="sm">
            <Zap className="w-3 h-3 mr-1" />
            DL {offer.dlperf?.toFixed(1) || '-'}
          </Badge>
          <Badge variant="gray" size="sm">
            PCIe {offer.pcie_bw?.toFixed(1) || '-'} GB/s
          </Badge>
        </div>

        {/* Problematic machine warning */}
        {isBlacklisted && (
          <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
            <Ban className="w-4 h-4 text-red-500 flex-shrink-0" />
            <div className="text-xs text-red-500 font-medium">
              Maquina na blacklist: {offer._blacklist_reason || offer.blacklist_reason || 'Falhas frequentes'}
            </div>
          </div>
        )}
        {!isBlacklisted && isProblematic && (
          <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-orange-500/10 border border-orange-500/20">
            <AlertTriangle className="w-4 h-4 text-orange-500 flex-shrink-0" />
            <div className="text-xs text-orange-500">
              <span className="font-medium">Baixa confiabilidade</span>
              {successRate !== null && ` - ${(successRate * 100).toFixed(0)}% sucesso`}
            </div>
          </div>
        )}
        {showWarning && !isProblematic && (
          <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
            <div className="text-xs text-yellow-600 dark:text-yellow-500">
              Algumas falhas recentes ({(successRate * 100).toFixed(0)}% sucesso)
            </div>
          </div>
        )}

        {/* Footer with reliability and action */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${reliabilityBg}`}>
              <div className={`w-2 h-2 rounded-full ${
                reliability >= 0.9 ? 'bg-brand-500' : reliability >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
              }`} />
              <span className={`text-xs font-semibold ${reliabilityColor}`}>
                {(reliability * 100).toFixed(0)}%
              </span>
            </div>
            {offer.verified && (
              <span className="flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400 px-2 py-1 bg-brand-100 dark:bg-brand-500/10 rounded-full font-medium">
                <Check className="w-3 h-3" />
                Verificado
              </span>
            )}
            {/* Machine history success rate indicator */}
            {successRate !== null && !isBlacklisted && !isProblematic && !showWarning && (
              <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 px-2 py-1 bg-gray-100 dark:bg-gray-800/50 rounded-full">
                Historico: {(successRate * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <Button
            onClick={() => onSelect(offer)}
            size="sm"
            className={isBlacklisted ? "bg-gray-500 cursor-not-allowed" : "bg-brand-700 hover:bg-brand-600 text-white"}
            disabled={isBlacklisted}
          >
            {isBlacklisted ? 'Bloqueada' : 'Selecionar'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default OfferCard;
