import React from 'react';
import {
  Cpu, Server, Wifi, DollarSign, Shield, Gauge, Globe, RotateCcw, Search, ChevronLeft, Sliders, Loader2
} from 'lucide-react';
import {
  Button,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Slider,
  Switch,
  CardContent,
} from '../tailadmin-ui';
import { FilterSection } from './';
import { HelpTooltip, GLOSSARY } from '../Tooltip';
import {
  GPU_OPTIONS,
  CUDA_OPTIONS,
  REGION_OPTIONS,
  RENTAL_TYPE_OPTIONS,
} from './constants';

const AdvancedSearchForm = ({
  filters,
  onFilterChange,
  onReset,
  onSearch,
  onBackToWizard,
  loading = false,
}) => {
  return (
    <CardContent className="pt-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-md bg-brand-900/40 border border-brand-700">
              <Sliders className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Busca Avançada</h2>
              <p className="text-gray-500 text-sm mt-0.5">Ajuste os filtros para encontrar as melhores máquinas disponíveis</p>
            </div>
          </div>
          <Button variant="outline" onClick={onReset} className="gap-2">
            <RotateCcw className="w-4 h-4" />
            Resetar Filtros
          </Button>
        </div>
        <div className="h-px bg-gray-800"></div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {/* GPU */}
        <FilterSection title="GPU" icon={Cpu}>
          <div className="space-y-4 mt-3">
            <div>
              <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Modelo da GPU</Label>
              <Select value={filters.gpu_name} onValueChange={(v) => onFilterChange('gpu_name', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {GPU_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Quantidade de GPUs</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.num_gpus}</span>
              </div>
              <Slider
                value={[filters.num_gpus]}
                onValueChange={([v]) => onFilterChange('num_gpus', Math.round(v))}
                max={8} min={1} step={1} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>1</span><span>4</span><span>8</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <div className="flex items-center gap-1.5">
                  <Label className="text-xs text-gray-500 dark:text-gray-400">VRAM Mínima (GB)</Label>
                  <HelpTooltip content={GLOSSARY['VRAM']} size={12} />
                </div>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_gpu_ram.toFixed(0)} GB</span>
              </div>
              <Slider
                value={[filters.min_gpu_ram]}
                onValueChange={([v]) => onFilterChange('min_gpu_ram', Math.round(v))}
                max={80} min={0} step={4} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0 GB</span><span>40 GB</span><span>80 GB</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Fração de GPU</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.gpu_frac.toFixed(1)}</span>
              </div>
              <Slider
                value={[filters.gpu_frac]}
                onValueChange={([v]) => onFilterChange('gpu_frac', v)}
                max={1} min={0.1} step={0.1} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0.1</span><span>0.5</span><span>1.0</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Largura de Banda Memória (GB/s)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.gpu_mem_bw.toFixed(0)}</span>
              </div>
              <Slider
                value={[filters.gpu_mem_bw]}
                onValueChange={([v]) => onFilterChange('gpu_mem_bw', v)}
                max={1000} min={0} step={10} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0 GB/s</span><span>500 GB/s</span><span>1000 GB/s</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Potência Máxima (W)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.gpu_max_power.toFixed(0)} W</span>
              </div>
              <Slider
                value={[filters.gpu_max_power]}
                onValueChange={([v]) => onFilterChange('gpu_max_power', v)}
                max={500} min={0} step={10} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0 W</span><span>250 W</span><span>500 W</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Largura de Banda NVLink (GB/s)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.bw_nvlink.toFixed(0)}</span>
              </div>
              <Slider
                value={[filters.bw_nvlink]}
                onValueChange={([v]) => onFilterChange('bw_nvlink', v)}
                max={600} min={0} step={10} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0 GB/s</span><span>300 GB/s</span><span>600 GB/s</span>
              </div>
            </div>
          </div>
        </FilterSection>

        {/* CPU & Memória */}
        <FilterSection title="CPU & Memória" icon={Server}>
          <div className="space-y-4 mt-3">
            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">CPU Cores Mínimos</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_cpu_cores}</span>
              </div>
              <Slider
                value={[filters.min_cpu_cores]}
                onValueChange={([v]) => onFilterChange('min_cpu_cores', Math.round(v))}
                max={64} min={1} step={1} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>1</span><span>32</span><span>64</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">RAM CPU Mínima (GB)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_cpu_ram.toFixed(0)} GB</span>
              </div>
              <Slider
                value={[filters.min_cpu_ram]}
                onValueChange={([v]) => onFilterChange('min_cpu_ram', Math.round(v))}
                max={256} min={1} step={2} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>1 GB</span><span>128 GB</span><span>256 GB</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Disco Mínimo (GB)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_disk.toFixed(0)} GB</span>
              </div>
              <Slider
                value={[filters.min_disk]}
                onValueChange={([v]) => onFilterChange('min_disk', Math.round(v))}
                max={2000} min={10} step={10} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>10 GB</span><span>1000 GB</span><span>2000 GB</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Velocidade CPU Mínima (GHz)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.cpu_ghz.toFixed(1)} GHz</span>
              </div>
              <Slider
                value={[filters.cpu_ghz]}
                onValueChange={([v]) => onFilterChange('cpu_ghz', v)}
                max={5} min={0} step={0.1} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0 GHz</span><span>2.5 GHz</span><span>5.0 GHz</span>
              </div>
            </div>
          </div>
        </FilterSection>

        {/* Performance */}
        <FilterSection title="Performance" icon={Gauge}>
          <div className="space-y-4 mt-3">
            <div>
              <div className="flex justify-between items-baseline mb-2">
                <div className="flex items-center gap-1.5">
                  <Label className="text-xs text-gray-500 dark:text-gray-400">DLPerf Mínimo</Label>
                  <HelpTooltip content={GLOSSARY['DLPerf']} size={12} />
                </div>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_dlperf.toFixed(1)}</span>
              </div>
              <Slider
                value={[filters.min_dlperf]}
                onValueChange={([v]) => onFilterChange('min_dlperf', v)}
                max={100} min={0} step={1} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0</span><span>50</span><span>100</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <div className="flex items-center gap-1.5">
                  <Label className="text-xs text-gray-500 dark:text-gray-400">PCIe BW Mínima (GB/s)</Label>
                  <HelpTooltip content={GLOSSARY['PCIe BW']} size={12} />
                </div>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_pcie_bw.toFixed(1)} GB/s</span>
              </div>
              <Slider
                value={[filters.min_pcie_bw]}
                onValueChange={([v]) => onFilterChange('min_pcie_bw', v)}
                max={100} min={0} step={1} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0 GB/s</span><span>50 GB/s</span><span>100 GB/s</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">TFLOPs Totais Mínimos</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.total_flops.toFixed(0)} TFLOP</span>
              </div>
              <Slider
                value={[filters.total_flops]}
                onValueChange={([v]) => onFilterChange('total_flops', v)}
                max={10000} min={0} step={100} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0 TFLOP</span><span>5000 TFLOP</span><span>10000 TFLOP</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Compute Capability Mínimo</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{(filters.compute_cap / 10).toFixed(1)}</span>
              </div>
              <Slider
                value={[filters.compute_cap]}
                onValueChange={([v]) => onFilterChange('compute_cap', v)}
                max={900} min={300} step={10} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>3.0</span><span>6.0</span><span>9.0</span>
              </div>
            </div>

            <div>
              <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Versão CUDA Mínima</Label>
              <Select value={filters.cuda_vers} onValueChange={(v) => onFilterChange('cuda_vers', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CUDA_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        </FilterSection>

        {/* Rede */}
        <FilterSection title="Rede" icon={Wifi}>
          <div className="space-y-4 mt-3">
            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Download Mínimo (Mbps)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_inet_down.toFixed(0)} Mbps</span>
              </div>
              <Slider
                value={[filters.min_inet_down]}
                onValueChange={([v]) => onFilterChange('min_inet_down', Math.round(v))}
                max={1000} min={10} step={10} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>10 Mbps</span><span>500 Mbps</span><span>1000 Mbps</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Upload Mínimo (Mbps)</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.min_inet_up.toFixed(0)} Mbps</span>
              </div>
              <Slider
                value={[filters.min_inet_up]}
                onValueChange={([v]) => onFilterChange('min_inet_up', Math.round(v))}
                max={1000} min={10} step={10} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>10 Mbps</span><span>500 Mbps</span><span>1000 Mbps</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Portas Diretas Mínimas</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{filters.direct_port_count}</span>
              </div>
              <Slider
                value={[filters.direct_port_count]}
                onValueChange={([v]) => onFilterChange('direct_port_count', Math.round(v))}
                max={32} min={0} step={1} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0</span><span>16</span><span>32</span>
              </div>
            </div>
          </div>
        </FilterSection>

        {/* Preço */}
        <FilterSection title="Preço" icon={DollarSign}>
          <div className="space-y-4 mt-3">
            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Preço Máximo</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">${filters.max_price.toFixed(2)}/hr</span>
              </div>
              <Slider
                value={[filters.max_price]}
                onValueChange={([v]) => onFilterChange('max_price', v)}
                max={15} min={0.05} step={0.05} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>$0.05</span><span>$7.50</span><span>$15.00</span>
              </div>
            </div>

            <div>
              <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Tipo de Aluguel</Label>
              <Select value={filters.rental_type} onValueChange={(v) => onFilterChange('rental_type', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {RENTAL_TYPE_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        </FilterSection>

        {/* Localização & Qualidade */}
        <FilterSection title="Localização & Qualidade" icon={Globe}>
          <div className="space-y-4 mt-3">
            <div>
              <Label className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">Região Preferida</Label>
              <Select value={filters.region} onValueChange={(v) => onFilterChange('region', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {REGION_OPTIONS.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div>
              <div className="flex justify-between items-baseline mb-2">
                <Label className="text-xs text-gray-500 dark:text-gray-400">Confiabilidade Mínima</Label>
                <span className="text-sm text-gray-700 dark:text-gray-200 font-mono font-medium">{(filters.min_reliability * 100).toFixed(0)}%</span>
              </div>
              <Slider
                value={[filters.min_reliability]}
                onValueChange={([v]) => onFilterChange('min_reliability', v)}
                max={1} min={0} step={0.05} className="w-full"
              />
              <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-600 mt-1.5">
                <span>0%</span><span>50%</span><span>100%</span>
              </div>
            </div>

            <div className="flex items-center justify-between border border-gray-200 dark:border-gray-700/30 rounded-lg p-3 bg-gray-800/20">
              <Label className="text-sm text-gray-300">Apenas Datacenters Certificados</Label>
              <Switch
                checked={filters.datacenter}
                onCheckedChange={(checked) => onFilterChange('datacenter', checked)}
              />
            </div>
          </div>
        </FilterSection>
      </div>

      {/* Opções Adicionais */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <FilterSection title="Opções Adicionais" icon={Shield} defaultOpen={false}>
          <div className="space-y-3 mt-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm text-gray-300">Apenas Hosts Verificados</Label>
              <Switch
                checked={filters.verified_only}
                onCheckedChange={(checked) => onFilterChange('verified_only', checked)}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-sm text-gray-300">IP Estático</Label>
              <Switch
                checked={filters.static_ip}
                onCheckedChange={(checked) => onFilterChange('static_ip', checked)}
              />
            </div>
          </div>
        </FilterSection>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          onClick={onSearch}
          disabled={loading}
          className="flex-1 active:scale-[0.98]"
          size="lg"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Buscando...
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              Buscar Máquinas
            </>
          )}
        </Button>
        <Button variant="outline" onClick={onBackToWizard} size="lg">
          <ChevronLeft className="w-4 h-4" />
          Voltar ao Wizard
        </Button>
      </div>
    </CardContent>
  );
};

export default AdvancedSearchForm;
