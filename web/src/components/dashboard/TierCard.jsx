import React from 'react';
import { Cpu } from 'lucide-react';
import {
  Card,
  Popover,
  PopoverTrigger,
  PopoverContent,
} from '../tailadmin-ui';

// Speed indicator bars usando Tailwind colors
export const SpeedBars = ({ level, color }) => {
  // Mapeamento de cores para classes Tailwind
  const colorClasses = {
    gray: 'bg-gray-500',
    slate: 'bg-slate-500',
    yellow: 'bg-yellow-500',
    amber: 'bg-amber-500',
    orange: 'bg-orange-500',
    lime: 'bg-lime-500',
    green: 'bg-brand-600'
  };

  const activeColor = colorClasses[color] || 'bg-brand-600';

  // Heights: 7px, 10px, 13px, 16px
  const heights = ['h-[7px]', 'h-[10px]', 'h-[13px]', 'h-[16px]'];

  return (
    <div className="flex items-end gap-px">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`w-[3px] rounded-sm ${heights[i-1]} ${i <= level ? activeColor : 'bg-gray-700 dark:bg-gray-600'}`}
        />
      ))}
    </div>
  );
};

// Performance tier selection card - usando apenas classes Tailwind do tema
const TierCard = ({ tier, isSelected, onClick }) => {
  // Classes de seleção usando apenas o tema TailAdmin
  const selectedClasses = isSelected
    ? 'border-2 border-brand-500 dark:border-brand-500 bg-brand-50/50 dark:bg-brand-900/20 ring-2 ring-brand-500/20'
    : 'border border-gray-200 dark:border-gray-800 hover:border-brand-400 dark:hover:border-brand-600';

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Card
          onClick={onClick}
          className={`relative cursor-pointer text-left transition-all overflow-hidden ${selectedClasses}`}
          noPadding
        >
          <div className="p-3 md:p-4 min-h-[160px]">
            {/* Accent bar on left when selected */}
            {isSelected && (
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-brand-500" />
            )}

            <div className="flex items-center justify-between mb-2">
              <span className={`font-bold text-sm md:text-base tracking-tight transition-colors ${
                isSelected
                  ? 'text-brand-700 dark:text-brand-300'
                  : 'text-gray-800 dark:text-gray-100'
              }`}>
                {tier.name}
              </span>
              <SpeedBars level={tier.level} color={tier.color} />
            </div>
          <div className="text-xs md:text-sm font-mono font-semibold tracking-tight text-brand-600 dark:text-brand-400">
            {tier.speed}
          </div>
          <div className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs mb-2">{tier.time}</div>
          <div className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs leading-relaxed">{tier.gpu}</div>
          <div className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs leading-relaxed">{tier.vram}</div>
          <div className="text-xs md:text-sm font-mono font-semibold mt-2 text-yellow-600 dark:text-yellow-400">
            {tier.priceRange}
          </div>
            <div className="mt-auto pt-3 border-t border-gray-200 dark:border-gray-700">
              <p className="text-gray-500 dark:text-gray-400 text-[9px] md:text-[10px] leading-relaxed">{tier.description}</p>
            </div>
          </div>
        </Card>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64">
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-3">
            <Cpu className="w-5 h-5 text-brand-500" />
            <span className="text-sm font-semibold text-gray-900 dark:text-white">{tier.name}</span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500 dark:text-gray-400">GPU:</span>
              <span className="text-gray-900 dark:text-white font-medium">{tier.gpu}</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500 dark:text-gray-400">VRAM:</span>
              <span className="text-gray-900 dark:text-white font-medium">{tier.vram}</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500 dark:text-gray-400">Velocidade:</span>
              <span className="text-brand-500 font-medium">{tier.speed}</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-500 dark:text-gray-400">Tempo Treino:</span>
              <span className="text-gray-900 dark:text-white font-medium">{tier.time}</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Preço:</span>
              <span className="text-yellow-400 font-medium">{tier.priceRange}</span>
            </div>
          </div>

          <div className="pt-2 border-t border-gray-200 dark:border-gray-700/30">
            <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{tier.description}</p>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
};

export default TierCard;
