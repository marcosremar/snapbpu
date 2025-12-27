import React, { useEffect, useState } from 'react';
import { Cpu, Loader2, Check, X, Server, Wifi, Zap, Play, Clock, Timer } from 'lucide-react';
import { Card, CardContent, Button } from '../tailadmin-ui';

// Progress stages with labels and icons
const PROGRESS_STAGES = [
  { min: 0, max: 15, label: 'Criando', icon: Server, color: 'text-blue-400' },
  { min: 15, max: 40, label: 'Conectando', icon: Wifi, color: 'text-yellow-400' },
  { min: 40, max: 75, label: 'Inicializando', icon: Zap, color: 'text-orange-400' },
  { min: 75, max: 100, label: 'Pronto', icon: Play, color: 'text-green-400' },
];

const getStage = (progress) => {
  return PROGRESS_STAGES.find(s => progress >= s.min && progress < s.max) || PROGRESS_STAGES[PROGRESS_STAGES.length - 1];
};

const ProgressBar = ({ progress, isWinner, isCancelled, status }) => {
  const [displayProgress, setDisplayProgress] = useState(0);
  const stage = getStage(progress);
  const StageIcon = stage.icon;

  // Smooth animation effect
  useEffect(() => {
    if (progress > displayProgress) {
      // Animate smoothly to target
      const interval = setInterval(() => {
        setDisplayProgress(prev => {
          const diff = progress - prev;
          if (diff <= 0.5) {
            clearInterval(interval);
            return progress;
          }
          // Ease out - slower as it approaches target
          const step = Math.max(0.5, diff * 0.15);
          return Math.min(prev + step, progress);
        });
      }, 50);
      return () => clearInterval(interval);
    }
  }, [progress, displayProgress]);

  if (isWinner || isCancelled || status === 'failed') return null;

  return (
    <div className="mt-3">
      {/* Stage indicators */}
      <div className="flex items-center justify-between mb-2 text-xs">
        {PROGRESS_STAGES.map((s, i) => {
          const isActive = displayProgress >= s.min;
          const isCurrent = displayProgress >= s.min && displayProgress < s.max;
          const Icon = s.icon;
          return (
            <div
              key={i}
              className={`flex items-center gap-1.5 transition-all duration-500 ${
                isCurrent ? s.color + ' font-semibold scale-110' :
                isActive ? 'text-gray-400' : 'text-gray-600'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isCurrent ? 'animate-pulse' : ''}`} />
              <span>{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* Progress bar track */}
      <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden">
        {/* Animated gradient bar */}
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-300 ease-out"
          style={{
            width: `${displayProgress}%`,
            background: `linear-gradient(90deg,
              #3b82f6 0%,
              #eab308 33%,
              #f97316 66%,
              #22c55e 100%
            )`,
            backgroundSize: '300% 100%',
            backgroundPosition: `${100 - displayProgress}% 0`,
          }}
        />

        {/* Shimmer effect */}
        <div
          className="absolute inset-y-0 left-0 w-full opacity-30"
          style={{
            background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)',
            animation: 'shimmer 2s infinite',
            width: `${displayProgress}%`,
          }}
        />
      </div>

      {/* Current stage label with percentage */}
      <div className="flex items-center justify-between mt-1.5">
        <div className={`flex items-center gap-1.5 text-xs ${stage.color}`}>
          <StageIcon className="w-3 h-3 animate-pulse" />
          <span>{stage.label}...</span>
        </div>
        <span className="text-xs text-gray-500">{Math.round(displayProgress)}%</span>
      </div>
    </div>
  );
};

const ProvisioningRaceScreen = ({ candidates, winner, onCancel, onComplete }) => {
  const [elapsedTime, setElapsedTime] = useState(0);

  // Track elapsed time
  useEffect(() => {
    if (winner) return; // Stop timer when we have a winner
    const startTime = Date.now();
    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [winner]);

  // Format time as mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Estimate remaining time based on progress of fastest candidate
  const getETA = () => {
    if (winner) return 'Concluído!';
    const activeCandidates = candidates.filter(c => c.status !== 'failed' && c.status !== 'cancelled');
    if (activeCandidates.length === 0) return 'Sem máquinas ativas';
    const maxProgress = Math.max(...activeCandidates.map(c => c.progress || 0));
    if (maxProgress <= 10) return 'Estimando...';
    const estimatedTotal = (elapsedTime / maxProgress) * 100;
    const remaining = Math.max(0, Math.ceil(estimatedTotal - elapsedTime));
    if (remaining < 60) return `~${remaining}s restantes`;
    return `~${Math.ceil(remaining / 60)}min restantes`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      {/* Shimmer animation keyframes */}
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes pulse-glow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
          50% { box-shadow: 0 0 20px 5px rgba(59, 130, 246, 0.2); }
        }
      `}</style>

      <div className="w-full max-w-4xl mx-4">
        <Card className="border border-gray-700 bg-gray-800">
          <CardContent className="p-8">
            {/* Header */}
            <div className="text-center mb-8">
              <div
                className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-900/40 border border-brand-700 mb-4"
                style={!winner ? { animation: 'pulse-glow 2s infinite' } : {}}
              >
                {winner ? (
                  <Check className="w-8 h-8 text-brand-400" />
                ) : (
                  <Loader2 className="w-8 h-8 text-brand-400 animate-spin" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">
                {winner ? 'Máquina Conectada!' : 'Provisionando Máquinas...'}
              </h2>
              <p className="text-gray-400">
                {winner
                  ? 'Sua máquina está pronta para uso'
                  : 'Criando 5 máquinas simultaneamente. A primeira que ficar pronta será selecionada.'}
              </p>

              {/* Timer and ETA */}
              {!winner && (
                <div className="flex items-center justify-center gap-6 mt-4 text-sm">
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-700/50">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-300 font-mono">{formatTime(elapsedTime)}</span>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-900/30 border border-brand-700">
                    <Timer className="w-4 h-4 text-brand-400" />
                    <span className="text-brand-300">{getETA()}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Race Track */}
            <div className="space-y-4 mb-8">
              {candidates.map((candidate, index) => {
                const isWinner = winner?.id === candidate.id || winner?.instanceId === candidate.instanceId;
                const isCancelled = winner && !isWinner;
                const status = candidate.status;

                // Card styles based on state
                const cardClasses = isWinner
                  ? 'border-brand-500 bg-brand-900/30 ring-2 ring-brand-500/30'
                  : isCancelled
                  ? 'border-gray-700 bg-gray-800/50 opacity-50'
                  : status === 'failed'
                  ? 'border-red-800 bg-red-900/20'
                  : 'border-gray-700 bg-gray-800 hover:border-gray-600';

                // Icon container styles based on state
                const iconClasses = isWinner
                  ? 'bg-brand-500 text-white'
                  : isCancelled
                  ? 'bg-gray-700 text-gray-500'
                  : status === 'failed'
                  ? 'bg-red-500/20 text-red-400'
                  : status === 'creating'
                  ? 'bg-blue-500/20 text-blue-400'
                  : status === 'connecting'
                  ? 'bg-yellow-500/20 text-yellow-400'
                  : 'bg-gray-700 text-gray-300';

                return (
                  <div
                    key={candidate.id || index}
                    className={`rounded-lg border transition-all duration-500 ${cardClasses}`}
                  >
                    <div className="p-4">
                      <div className="flex items-center gap-4">
                        {/* Position/Status Icon */}
                        <div className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg transition-all duration-300 ${iconClasses}`}>
                          {isWinner ? (
                            <Check className="w-6 h-6" />
                          ) : isCancelled ? (
                            <X className="w-5 h-5" />
                          ) : status === 'failed' ? (
                            <X className="w-5 h-5" />
                          ) : status === 'creating' ? (
                            <Server className="w-5 h-5 animate-pulse" />
                          ) : status === 'connecting' ? (
                            <Wifi className="w-5 h-5 animate-pulse" />
                          ) : (
                            <span>{index + 1}</span>
                          )}
                        </div>

                        {/* Machine Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <Cpu className={`w-4 h-4 ${isWinner ? 'text-brand-400' : 'text-gray-400'}`} />
                            <span className={`font-semibold truncate ${isWinner ? 'text-white' : 'text-gray-300'}`}>
                              {candidate.gpu_name}
                            </span>
                            {candidate.num_gpus > 1 && (
                              <span className="text-xs bg-gray-700 px-1.5 py-0.5 rounded text-gray-400">x{candidate.num_gpus}</span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                            <span>{candidate.gpu_ram?.toFixed(0) || '?'} GB VRAM</span>
                            <span>•</span>
                            <span>{candidate.geolocation || 'Unknown'}</span>
                            <span>•</span>
                            <span className="text-brand-400 font-medium">${candidate.dph_total?.toFixed(2) || '?.??'}/hr</span>
                          </div>
                        </div>

                        {/* Status Badge */}
                        <div className="flex-shrink-0">
                          {isWinner ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-500/20 text-brand-400 text-sm font-semibold border border-brand-500/30">
                              <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
                              Vencedor!
                            </span>
                          ) : isCancelled ? (
                            <span className="text-sm text-gray-600 bg-gray-700/50 px-3 py-1.5 rounded-full">Cancelado</span>
                          ) : status === 'failed' ? (
                            <div className="flex flex-col items-end">
                              <span className="text-sm text-red-400 bg-red-900/30 px-3 py-1.5 rounded-full border border-red-800">Falhou</span>
                              {candidate.errorMessage && (
                                <span className="text-[10px] text-red-400/70 mt-1">{candidate.errorMessage}</span>
                              )}
                            </div>
                          ) : status === 'creating' ? (
                            <span className="inline-flex items-center gap-2 text-sm text-blue-400 bg-blue-900/30 px-3 py-1.5 rounded-full border border-blue-800">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Criando...
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-2 text-sm text-yellow-400 bg-yellow-900/30 px-3 py-1.5 rounded-full border border-yellow-800">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Conectando...
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <ProgressBar
                        progress={candidate.progress || 0}
                        isWinner={isWinner}
                        isCancelled={isCancelled}
                        status={status}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-center gap-4">
              {winner ? (
                <>
                  <Button
                    variant="outline"
                    onClick={onCancel}
                    className="border-gray-700 text-gray-400 hover:bg-gray-800"
                  >
                    <X className="w-4 h-4 mr-2" />
                    Buscar Outras
                  </Button>
                  <Button
                    onClick={() => onComplete(winner)}
                    className="bg-brand-600 hover:bg-brand-500 text-white px-8 font-semibold"
                  >
                    <Check className="w-4 h-4 mr-2" />
                    Usar Esta Máquina
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  onClick={onCancel}
                  className="border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-white"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancelar Corrida
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ProvisioningRaceScreen;
