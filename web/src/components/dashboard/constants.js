// Dashboard Constants - GPU Options, Categories, Regions, etc.

export const GPU_OPTIONS = [
  { value: 'any', label: 'Qualquer GPU' },
  // Consumer
  { value: 'RTX_3060', label: 'RTX 3060' },
  { value: 'RTX_3060_Ti', label: 'RTX 3060 Ti' },
  { value: 'RTX_3070', label: 'RTX 3070' },
  { value: 'RTX_3070_Ti', label: 'RTX 3070 Ti' },
  { value: 'RTX_3080', label: 'RTX 3080' },
  { value: 'RTX_3080_Ti', label: 'RTX 3080 Ti' },
  { value: 'RTX_3090', label: 'RTX 3090' },
  { value: 'RTX_3090_Ti', label: 'RTX 3090 Ti' },
  { value: 'RTX_4060', label: 'RTX 4060' },
  { value: 'RTX_4060_Ti', label: 'RTX 4060 Ti' },
  { value: 'RTX_4070', label: 'RTX 4070' },
  { value: 'RTX_4070_Ti', label: 'RTX 4070 Ti' },
  { value: 'RTX_4070_Ti_Super', label: 'RTX 4070 Ti Super' },
  { value: 'RTX_4080', label: 'RTX 4080' },
  { value: 'RTX_4080_Super', label: 'RTX 4080 Super' },
  { value: 'RTX_4090', label: 'RTX 4090' },
  { value: 'RTX_5090', label: 'RTX 5090' },
  // Datacenter
  { value: 'A100', label: 'A100' },
  { value: 'A100_PCIE', label: 'A100 PCIe' },
  { value: 'A100_SXM4', label: 'A100 SXM4' },
  { value: 'A100_80GB', label: 'A100 80GB' },
  { value: 'H100', label: 'H100' },
  { value: 'H100_PCIe', label: 'H100 PCIe' },
  { value: 'H100_SXM5', label: 'H100 SXM5' },
  { value: 'A6000', label: 'RTX A6000' },
  { value: 'A5000', label: 'RTX A5000' },
  { value: 'A4000', label: 'RTX A4000' },
  { value: 'A4500', label: 'RTX A4500' },
  { value: 'L40', label: 'L40' },
  { value: 'L40S', label: 'L40S' },
  { value: 'V100', label: 'V100' },
  { value: 'V100_SXM2', label: 'V100 SXM2' },
  { value: 'Tesla_T4', label: 'Tesla T4' },
  { value: 'P100', label: 'P100' },
];

export const GPU_CATEGORIES = [
  {
    id: 'any',
    name: 'Automático',
    icon: 'auto',
    description: 'Melhor custo-benefício',
    gpus: []
  },
  {
    id: 'inference',
    name: 'Inferência',
    icon: 'inference',
    description: 'Deploy de modelos / APIs',
    gpus: ['RTX_4060', 'RTX_4060_Ti', 'RTX_4070', 'RTX_3060', 'RTX_3060_Ti', 'RTX_3070', 'RTX_3070_Ti', 'Tesla_T4', 'A4000', 'L40']
  },
  {
    id: 'training',
    name: 'Treinamento',
    icon: 'training',
    description: 'Fine-tuning / ML Training',
    gpus: ['RTX_4080', 'RTX_4080_Super', 'RTX_4090', 'RTX_3080', 'RTX_3080_Ti', 'RTX_3090', 'RTX_3090_Ti', 'RTX_5090', 'A5000', 'A6000', 'L40S']
  },
  {
    id: 'hpc',
    name: 'HPC / LLMs',
    icon: 'hpc',
    description: 'Modelos grandes / Multi-GPU',
    gpus: ['A100', 'A100_PCIE', 'A100_SXM4', 'A100_80GB', 'H100', 'H100_PCIe', 'H100_SXM5', 'V100', 'V100_SXM2']
  },
];

export const REGION_OPTIONS = [
  { value: 'any', label: 'Todas as Regiões' },
  { value: 'US', label: 'Estados Unidos' },
  { value: 'EU', label: 'Europa' },
  { value: 'ASIA', label: 'Ásia' },
  { value: 'SA', label: 'América do Sul' },
  { value: 'OC', label: 'Oceania' },
  { value: 'AF', label: 'África' },
];

export const CUDA_OPTIONS = [
  { value: 'any', label: 'Qualquer versão' },
  { value: '11.0', label: 'CUDA 11.0+' },
  { value: '11.7', label: 'CUDA 11.7+' },
  { value: '11.8', label: 'CUDA 11.8+' },
  { value: '12.0', label: 'CUDA 12.0+' },
  { value: '12.1', label: 'CUDA 12.1+' },
  { value: '12.2', label: 'CUDA 12.2+' },
  { value: '12.4', label: 'CUDA 12.4+' },
];

export const ORDER_OPTIONS = [
  { value: 'dph_total', label: 'Preço (menor primeiro)' },
  { value: 'dlperf', label: 'DL Performance (maior)' },
  { value: 'gpu_ram', label: 'GPU RAM (maior)' },
  { value: 'inet_down', label: 'Download (maior)' },
  { value: 'reliability', label: 'Confiabilidade' },
  { value: 'pcie_bw', label: 'PCIe Bandwidth' },
];

export const RENTAL_TYPE_OPTIONS = [
  { value: 'on-demand', label: 'On-Demand' },
  { value: 'bid', label: 'Bid/Interruptible' },
];

export const PERFORMANCE_TIERS = [
  {
    name: 'Lento',
    level: 1,
    color: 'slate',
    speed: '100-250 Mbps',
    time: '~5 min',
    gpu: 'RTX 3070/3080',
    vram: '8-12GB VRAM',
    priceRange: '$0.05 - $0.25/hr',
    description: 'Econômico. Ideal para tarefas básicas e testes.',
    filter: { max_price: 0.25, min_gpu_ram: 8 }
  },
  {
    name: 'Medio',
    level: 2,
    color: 'amber',
    speed: '500-1000 Mbps',
    time: '~2 min',
    gpu: 'RTX 4070/4080',
    vram: '12-16GB VRAM',
    priceRange: '$0.25 - $0.50/hr',
    description: 'Balanceado. Bom para desenvolvimento diário.',
    filter: { max_price: 0.50, min_gpu_ram: 12 }
  },
  {
    name: 'Rapido',
    level: 3,
    color: 'lime',
    speed: '1000-2000 Mbps',
    time: '~30s',
    gpu: 'RTX 4090',
    vram: '24GB VRAM',
    priceRange: '$0.50 - $1.00/hr',
    description: 'Alta performance. Treinamentos e workloads pesados.',
    filter: { max_price: 1.00, min_gpu_ram: 24 }
  },
  {
    name: 'Ultra',
    level: 4,
    color: 'green',
    speed: '2000+ Mbps',
    time: '~10s',
    gpu: 'A100/H100',
    vram: '40-80GB VRAM',
    priceRange: '$1.00 - $10.00/hr',
    description: 'Máxima potência. Para as tarefas mais exigentes.',
    filter: { max_price: 10.0, min_gpu_ram: 40 }
  }
];

export const COUNTRY_DATA = {
  // Regiões (selecionam múltiplos países)
  'eua': { codes: ['US', 'CA', 'MX'], name: 'EUA', isRegion: true },
  'europa': { codes: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'], name: 'Europa', isRegion: true },
  'asia': { codes: ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'], name: 'Ásia', isRegion: true },
  'america do sul': { codes: ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'], name: 'América do Sul', isRegion: true },

  // Países individuais
  'estados unidos': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
  'usa': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
  'united states': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
  'canada': { codes: ['CA'], name: 'Canadá', isRegion: false },
  'canadá': { codes: ['CA'], name: 'Canadá', isRegion: false },
  'mexico': { codes: ['MX'], name: 'México', isRegion: false },
  'méxico': { codes: ['MX'], name: 'México', isRegion: false },
  'brasil': { codes: ['BR'], name: 'Brasil', isRegion: false },
  'brazil': { codes: ['BR'], name: 'Brasil', isRegion: false },
  'argentina': { codes: ['AR'], name: 'Argentina', isRegion: false },
  'chile': { codes: ['CL'], name: 'Chile', isRegion: false },
  'colombia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
  'colômbia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
  'reino unido': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
  'uk': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
  'united kingdom': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
  'england': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
  'inglaterra': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
  'frança': { codes: ['FR'], name: 'França', isRegion: false },
  'france': { codes: ['FR'], name: 'França', isRegion: false },
  'alemanha': { codes: ['DE'], name: 'Alemanha', isRegion: false },
  'germany': { codes: ['DE'], name: 'Alemanha', isRegion: false },
  'espanha': { codes: ['ES'], name: 'Espanha', isRegion: false },
  'spain': { codes: ['ES'], name: 'Espanha', isRegion: false },
  'itália': { codes: ['IT'], name: 'Itália', isRegion: false },
  'italia': { codes: ['IT'], name: 'Itália', isRegion: false },
  'italy': { codes: ['IT'], name: 'Itália', isRegion: false },
  'portugal': { codes: ['PT'], name: 'Portugal', isRegion: false },
  'japão': { codes: ['JP'], name: 'Japão', isRegion: false },
  'japao': { codes: ['JP'], name: 'Japão', isRegion: false },
  'japan': { codes: ['JP'], name: 'Japão', isRegion: false },
  'china': { codes: ['CN'], name: 'China', isRegion: false },
  'coreia do sul': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
  'south korea': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
  'korea': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
  'singapura': { codes: ['SG'], name: 'Singapura', isRegion: false },
  'singapore': { codes: ['SG'], name: 'Singapura', isRegion: false },
  'índia': { codes: ['IN'], name: 'Índia', isRegion: false },
  'india': { codes: ['IN'], name: 'Índia', isRegion: false },
};

export const COUNTRY_NAMES = {
  'US': 'Estados Unidos', 'CA': 'Canadá', 'MX': 'México',
  'GB': 'Reino Unido', 'FR': 'França', 'DE': 'Alemanha', 'ES': 'Espanha', 'IT': 'Itália', 'PT': 'Portugal',
  'JP': 'Japão', 'CN': 'China', 'KR': 'Coreia do Sul', 'SG': 'Singapura', 'IN': 'Índia',
  'BR': 'Brasil', 'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colômbia',
};

export const DEMO_OFFERS = [
  { id: 1001, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24000, cpu_cores: 16, cpu_ram: 64000, disk_space: 200, dph_total: 0.45, inet_down: 2000, verified: true, geolocation: 'US' },
  { id: 1002, gpu_name: 'RTX 5090', num_gpus: 1, gpu_ram: 32000, cpu_cores: 24, cpu_ram: 128000, disk_space: 500, dph_total: 0.89, inet_down: 5000, verified: true, geolocation: 'EU' },
  { id: 1003, gpu_name: 'A100 80GB', num_gpus: 1, gpu_ram: 80000, cpu_cores: 32, cpu_ram: 256000, disk_space: 1000, dph_total: 2.10, inet_down: 10000, verified: true, geolocation: 'US' },
  { id: 1004, gpu_name: 'H100 80GB', num_gpus: 1, gpu_ram: 80000, cpu_cores: 64, cpu_ram: 512000, disk_space: 2000, dph_total: 3.50, inet_down: 25000, verified: true, geolocation: 'EU' },
];

export const DEFAULT_FILTERS = {
  // GPU
  gpu_name: 'any',
  num_gpus: 1,
  min_gpu_ram: 0,
  gpu_frac: 1,
  gpu_mem_bw: 0,
  gpu_max_power: 0,
  bw_nvlink: 0,
  // CPU & Memória & Armazenamento
  min_cpu_cores: 1,
  min_cpu_ram: 1,
  min_disk: 50,
  cpu_ghz: 0,
  // Performance
  min_dlperf: 0,
  min_pcie_bw: 0,
  total_flops: 0,
  cuda_vers: 'any',
  compute_cap: 0,
  // Rede
  min_inet_down: 100,
  min_inet_up: 50,
  direct_port_count: 0,
  // Preço
  max_price: 5.0,
  rental_type: 'on-demand',
  // Qualidade & Localização
  min_reliability: 0,
  region: 'any',
  verified_only: false,
  datacenter: false,
  // Opções avançadas
  static_ip: false,
  // Ordenação
  order_by: 'dph_total',
  limit: 100
};
