import React from 'react';
import { Cpu, Loader2, Check, X } from 'lucide-react';
import { Card, CardContent, Button } from '../tailadmin-ui';

const ProvisioningRaceScreen = ({ candidates, winner, onCancel, onComplete }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-4xl mx-4">
        <Card className="border border-gray-700 bg-gray-800">
          <CardContent className="p-8">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-900/40 border border-brand-700 mb-4">
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
                  : 'Testando conexão com 5 máquinas simultaneamente. A primeira que responder será selecionada.'}
              </p>
            </div>

            {/* Race Track */}
            <div className="space-y-3 mb-8">
              {candidates.map((candidate, index) => {
                const isWinner = winner?.id === candidate.id;
                const isCancelled = winner && !isWinner;
                const status = candidate.status;

                // Card styles based on state
                const cardClasses = isWinner
                  ? 'border-brand-600 bg-brand-900/30'
                  : isCancelled
                  ? 'border-gray-700 bg-gray-800/50 opacity-50'
                  : status === 'failed'
                  ? 'border-red-800 bg-red-900/20'
                  : 'border-gray-700 bg-gray-800';

                // Icon container styles based on state
                const iconClasses = isWinner
                  ? 'bg-brand-500 text-white'
                  : isCancelled
                  ? 'bg-gray-700 text-gray-500'
                  : status === 'failed'
                  ? 'bg-red-500/20 text-red-400'
                  : 'bg-gray-700 text-gray-300';

                return (
                  <div
                    key={candidate.id}
                    className={`relative overflow-hidden rounded-md border transition-colors ${cardClasses}`}
                  >
                    {/* Progress bar animation for connecting */}
                    {status === 'connecting' && !winner && (
                      <div
                        className="absolute bottom-0 left-0 h-1 bg-brand-500 transition-all duration-300 ease-out"
                        style={{ width: `${candidate.progress || 0}%` }}
                      />
                    )}

                    <div className="p-4 flex items-center gap-4">
                      {/* Position/Status Icon */}
                      <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg ${iconClasses}`}>
                        {isWinner ? (
                          <Check className="w-5 h-5" />
                        ) : isCancelled ? (
                          <X className="w-5 h-5" />
                        ) : status === 'failed' ? (
                          <X className="w-5 h-5" />
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
                            <span className="text-xs text-gray-500">x{candidate.num_gpus}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                          <span>{candidate.gpu_ram?.toFixed(0)} GB VRAM</span>
                          <span>•</span>
                          <span>{candidate.geolocation || 'Unknown'}</span>
                          <span>•</span>
                          <span className="text-brand-400 font-medium">${candidate.dph_total?.toFixed(2)}/hr</span>
                        </div>
                      </div>

                      {/* Status */}
                      <div className="flex-shrink-0">
                        {isWinner ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-500/20 text-brand-400 text-sm font-semibold">
                            <span className="w-2 h-2 rounded-full bg-brand-400" />
                            Conectado
                          </span>
                        ) : isCancelled ? (
                          <span className="text-sm text-gray-600">Cancelado</span>
                        ) : status === 'failed' ? (
                          <span className="text-sm text-red-400">Falhou</span>
                        ) : (
                          <span className="inline-flex items-center gap-2 text-sm text-gray-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Conectando...
                          </span>
                        )}
                      </div>
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
                    Buscar Outras
                  </Button>
                  <Button
                    onClick={() => onComplete(winner)}
                    className="bg-brand-700 hover:bg-brand-600 text-white px-8"
                  >
                    <Check className="w-4 h-4 mr-2" />
                    Usar Esta Máquina
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  onClick={onCancel}
                  className="border-gray-700 text-gray-400 hover:bg-gray-800"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancelar
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
