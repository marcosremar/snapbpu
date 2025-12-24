import React, { useState } from 'react';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';

// Visual GPU Recommendation Card Component
export const GPURecommendationCard = ({ option, onSearch }) => {
  const tierColors = {
    'mínima': {
      bg: 'bg-gray-100 dark:bg-gray-800/40',
      border: 'border-gray-600/20',
      badge: 'bg-gray-200 dark:bg-gray-700/50 text-gray-400',
      button: 'bg-gray-600/40 hover:bg-gray-600/60'
    },
    'recomendada': {
      bg: 'bg-brand-900/20',
      border: 'border-brand-700/25',
      badge: 'bg-brand-800/40 text-brand-400',
      button: 'bg-brand-700/40 hover:bg-brand-700/60'
    },
    'máxima': {
      bg: 'bg-brand-900/20',
      border: 'border-brand-700/25',
      badge: 'bg-brand-800/40 text-brand-400',
      button: 'bg-brand-700/40 hover:bg-brand-700/60'
    }
  };
  const colors = tierColors[option.tier] || tierColors['recomendada'];

  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} p-3 flex flex-col`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${colors.badge}`}>
          {option.tier}
        </span>
        <span className="text-amber-400/80 text-xs font-mono font-bold">{option.price_per_hour}</span>
      </div>

      {/* GPU Info */}
      <div className="mb-2">
        <div className="text-gray-900 dark:text-white font-semibold text-sm">{option.gpu}</div>
        <div className="text-gray-400 text-[11px]">VRAM: {option.vram}</div>
        {option.quantization && (
          <div className="text-gray-500 text-[10px]">Quantização: {option.quantization}</div>
        )}
      </div>

      {/* Framework Performance Table */}
      {option.frameworks && Object.keys(option.frameworks).length > 0 && (
        <div className="mb-2">
          <div className="text-gray-500 text-[10px] mb-1 font-semibold">Performance por Framework:</div>
          <table className="w-full text-[10px]">
            <tbody>
              {Object.entries(option.frameworks).map(([framework, perf]) => (
                <tr key={framework} className="border-b border-gray-200 dark:border-gray-700/20">
                  <td className="py-0.5 text-gray-400">{framework}</td>
                  <td className="py-0.5 text-brand-400/80 font-mono text-right">{perf}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tokens per second (legacy support) */}
      {option.tokens_per_second && !option.frameworks && (
        <div className="text-brand-400/80 text-[11px] font-mono mb-2">
          ~{option.tokens_per_second} tokens/s
        </div>
      )}

      {/* RAM Offload */}
      {option.ram_offload && (
        <div className="text-amber-500/70 text-[10px] mb-2">
          RAM Offload: {option.ram_offload}
        </div>
      )}

      {/* Observation */}
      {option.observation && (
        <div className="text-gray-500 text-[10px] italic mb-2">{option.observation}</div>
      )}

      {/* Search Button */}
      <button
        onClick={() => onSearch(option)}
        className={`mt-auto py-1.5 px-2 text-[10px] font-medium text-white ${colors.button} rounded transition-colors flex items-center justify-center gap-1`}
      >
        <Search className="w-3 h-3" />
        Buscar {option.gpu}
      </button>
    </div>
  );
};

// Interactive GPU Wizard Component - Main display with model info and slider
const GPUWizardDisplay = ({ recommendation, onSearch }) => {
  const [currentIndex, setCurrentIndex] = useState(1);
  const options = recommendation?.gpu_options || [];
  const currentOption = options[currentIndex];

  if (!currentOption) return null;

  const goLeft = () => setCurrentIndex(prev => Math.max(0, prev - 1));
  const goRight = () => setCurrentIndex(prev => Math.min(options.length - 1, prev + 1));

  const modelName = recommendation?.model_name || 'Modelo';
  const modelSize = recommendation?.model_size || '';
  const isRecommended = currentOption.tier === 'recomendada';

  const getMainToksPerSec = () => {
    if (currentOption.frameworks?.vllm) return currentOption.frameworks.vllm;
    if (currentOption.frameworks?.pytorch) return currentOption.frameworks.pytorch;
    if (currentOption.tokens_per_second) return `${currentOption.tokens_per_second} tok/s`;
    return null;
  };

  return (
    <div className="rounded-md border border-gray-700 bg-gray-800 p-4">
      {/* Model Header */}
      <div className="text-center mb-4 pb-3 border-b border-gray-800">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Modelo</div>
        <div className="text-white font-semibold text-base">{modelName}</div>
        {modelSize && <div className="text-gray-500 text-xs">{modelSize}</div>}
      </div>

      {/* Main Content with Navigation */}
      <div className="flex items-center gap-2">
        {/* Left Arrow */}
        <button
          onClick={goLeft}
          disabled={currentIndex === 0}
          className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center transition-colors ${
            currentIndex === 0
              ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Center Card */}
        <div className="flex-1 text-center">
          {/* Tier Badge */}
          <div className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider mb-2 ${
            isRecommended ? 'bg-brand-900/50 text-brand-400' : 'bg-gray-800 text-gray-400'
          }`}>
            {currentOption.tier}
          </div>

          {/* GPU Name */}
          <div className="text-white font-semibold text-lg mb-1">{currentOption.gpu}</div>

          {/* VRAM & Quantization */}
          <div className="flex items-center justify-center gap-2 text-xs text-gray-500 mb-2">
            <span>{currentOption.vram}</span>
            {currentOption.quantization && (
              <>
                <span className="text-gray-700">•</span>
                <span className="text-gray-400">{currentOption.quantization}</span>
              </>
            )}
          </div>

          {/* Main Performance Display */}
          {getMainToksPerSec() && (
            <div className="mb-2">
              <div className="text-2xl font-semibold text-brand-400">
                {getMainToksPerSec()}
              </div>
              <div className="text-[10px] text-gray-500">tokens/segundo</div>
            </div>
          )}

          {/* Price */}
          <div className="text-amber-400 font-mono text-base font-medium mb-2">
            {currentOption.price_per_hour}
          </div>

          {/* Framework Performance Grid */}
          {currentOption.frameworks && Object.keys(currentOption.frameworks).length > 1 && (
            <div className="grid grid-cols-3 gap-1 mb-2 text-[10px]">
              {Object.entries(currentOption.frameworks).slice(0, 3).map(([fw, perf]) => (
                <div key={fw} className="bg-gray-800 rounded px-2 py-1">
                  <div className="text-gray-500 uppercase text-[8px]">{fw}</div>
                  <div className="font-mono text-gray-300">{perf}</div>
                </div>
              ))}
            </div>
          )}

          {/* RAM Offload Warning */}
          {currentOption.ram_offload && currentOption.ram_offload !== 'Não necessário' && (
            <div className="text-amber-500 text-[10px] mb-2">
              RAM Offload: {currentOption.ram_offload}
            </div>
          )}

          {/* Observation */}
          {currentOption.observation && (
            <div className="text-gray-500 text-[10px] mb-2">{currentOption.observation}</div>
          )}
        </div>

        {/* Right Arrow */}
        <button
          onClick={goRight}
          disabled={currentIndex === options.length - 1}
          className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center transition-colors ${
            currentIndex === options.length - 1
              ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
          }`}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Slider Visual */}
      <div className="mt-3 px-4">
        <div className="flex items-center justify-between text-[9px] text-gray-500 mb-1">
          <span>Economia</span>
          <span>Performance</span>
        </div>
        <div className="relative h-1.5 bg-gray-800 rounded-full">
          <div className="absolute inset-0 flex items-center justify-between px-1">
            {options.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`w-2.5 h-2.5 rounded-full transition-colors ${
                  idx === currentIndex ? 'bg-brand-500' : 'bg-gray-600 hover:bg-gray-500'
                }`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Search Button */}
      <button
        onClick={() => onSearch(currentOption)}
        className="mt-3 w-full py-2 px-3 rounded-md font-medium text-white transition-colors flex items-center justify-center gap-2 bg-brand-700 hover:bg-brand-600"
      >
        <Search className="w-4 h-4" />
        Buscar {currentOption.gpu}
      </button>
    </div>
  );
};

// Legacy GPU Carousel Component (for compact view)
export const GPUCarousel = ({ options, onSearch }) => {
  const [currentIndex, setCurrentIndex] = useState(1);

  const goLeft = () => setCurrentIndex(prev => Math.max(0, prev - 1));
  const goRight = () => setCurrentIndex(prev => Math.min(options.length - 1, prev + 1));

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={goLeft}
          disabled={currentIndex === 0}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-all ${
            currentIndex === 0 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Economia</span>
        </button>

        <div className="flex items-center gap-2">
          {options.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              className={`w-2 h-2 rounded-full transition-all ${
                idx === currentIndex ? 'bg-brand-500 w-4' : 'bg-gray-600 hover:bg-gray-500'
              }`}
            />
          ))}
        </div>

        <button
          onClick={goRight}
          disabled={currentIndex === options.length - 1}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-all ${
            currentIndex === options.length - 1 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
          }`}
        >
          <span>Performance</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <GPURecommendationCard option={options[currentIndex]} onSearch={onSearch} />
    </div>
  );
};

export default GPUWizardDisplay;
