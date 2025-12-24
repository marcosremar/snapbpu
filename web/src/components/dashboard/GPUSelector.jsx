import React, { useState } from 'react';
import { Cpu, Zap, Activity, Gauge, Server } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Label,
} from '../tailadmin-ui';
import { GPU_OPTIONS, GPU_CATEGORIES } from './constants';

const GPUSelector = ({ selectedGPU, onSelectGPU, selectedCategory, onSelectCategory }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getCategoryIcon = (iconType, isActive) => {
    const colorClass = isActive ? 'text-white' : 'text-gray-700 dark:text-gray-300';
    switch (iconType) {
      case 'auto':
        return <Zap className={`w-4 h-4 ${colorClass}`} />;
      case 'inference':
        return <Activity className={`w-4 h-4 ${colorClass}`} />;
      case 'training':
        return <Gauge className={`w-4 h-4 ${colorClass}`} />;
      case 'hpc':
        return <Server className={`w-4 h-4 ${colorClass}`} />;
      default:
        return <Cpu className={`w-4 h-4 ${colorClass}`} />;
    }
  };

  const currentCategory = GPU_CATEGORIES.find(c => c.id === selectedCategory) || GPU_CATEGORIES[0];
  const availableGPUs = currentCategory.gpus.length > 0
    ? GPU_OPTIONS.filter(g => currentCategory.gpus.includes(g.value))
    : [];

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <CardTitle className="text-sm">GPU</CardTitle>
            <CardDescription className="text-[10px]">Selecione o tipo</CardDescription>
          </div>
        </div>
        {selectedGPU !== 'any' && (
          <span className="px-2 py-1 rounded-full bg-brand-100 dark:bg-brand-500/20 text-brand-600 dark:text-brand-400 text-[10px] font-medium">
            {GPU_OPTIONS.find(g => g.value === selectedGPU)?.label}
          </span>
        )}
      </CardHeader>

      {/* Category Grid */}
      <CardContent className="p-3">
        <div className="grid grid-cols-2 gap-2">
          {GPU_CATEGORIES.map((cat) => {
            const isActive = selectedCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => {
                  onSelectCategory(cat.id);
                  if (cat.id === 'any') {
                    onSelectGPU('any');
                    setIsExpanded(false);
                  } else {
                    setIsExpanded(true);
                  }
                }}
                className={`relative p-3 rounded-lg border transition-all text-left overflow-hidden ${
                  isActive
                    ? 'border-brand-500/50 bg-brand-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                }`}
              >
                {/* Left accent when active */}
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-brand-500" />
                )}
                <div className="flex items-center gap-2.5 mb-1.5">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${isActive ? 'bg-brand-500/20' : 'bg-white/10'}`}>
                    {getCategoryIcon(cat.icon, isActive)}
                  </div>
                  <span className={`text-sm font-bold ${isActive ? 'text-white' : 'text-gray-100'}`}>
                    {cat.name}
                  </span>
                </div>
                <p className={`text-[10px] pl-9 ${isActive ? 'text-brand-300' : 'text-gray-400'}`}>
                  {cat.description}
                </p>
              </button>
            );
          })}
        </div>

        {/* GPU Dropdown - aparece quando categoria específica selecionada */}
        {isExpanded && selectedCategory !== 'any' && availableGPUs.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50">
            <Label className="text-[10px] text-gray-500 dark:text-gray-400 mb-2 block">
              Modelo Específico (opcional)
            </Label>
            <Select value={selectedGPU} onValueChange={onSelectGPU}>
              <SelectTrigger className="bg-gray-100 dark:bg-dark-surface-secondary border-gray-200 dark:border-gray-800 h-9 text-xs">
                <SelectValue placeholder="Qualquer modelo da categoria" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Qualquer {currentCategory.name}</SelectItem>
                {availableGPUs.map(gpu => (
                  <SelectItem key={gpu.value} value={gpu.value}>{gpu.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default GPUSelector;
