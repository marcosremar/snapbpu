import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import OnboardingWizard from '../components/onboarding/OnboardingWizard';
import {
  Cpu, Server, Wifi, DollarSign, Shield, HardDrive,
  Activity, Search, RotateCcw, Sliders, Wand2,
  Gauge, Globe, Zap, Monitor, ChevronDown, ChevronLeft, ChevronRight, Sparkles,
  Send, Bot, User, Loader2, Plus, Minus, X, Check, MapPin,
  MessageSquare, Lightbulb, Code, Clock
} from 'lucide-react';

// Dashboard Components
import {
  WorldMap,
  GPUSelector,
  GPUWizardDisplay,
  GPURecommendationCard,
  GPUCarousel,
  TierCard,
  SpeedBars,
  OfferCard,
  FilterSection,
  ProvisioningRaceScreen,
  AIWizardChat,
  AdvancedSearchForm,
  WizardForm,
  GPU_OPTIONS,
  GPU_CATEGORIES,
  REGION_OPTIONS,
  CUDA_OPTIONS,
  ORDER_OPTIONS,
  RENTAL_TYPE_OPTIONS,
  PERFORMANCE_TIERS,
  COUNTRY_DATA,
  COUNTRY_NAMES,
  DEMO_OFFERS,
  DEFAULT_FILTERS,
} from '../components/dashboard';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Input,
  Checkbox,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Button,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Label,
  Slider,
  Switch,
  StatCard as MetricCard,
  StatsGrid as MetricsGrid,
  Avatar,
  AvatarImage,
  AvatarFallback,
  Popover,
  PopoverTrigger,
  PopoverContent,
} from '../components/tailadmin-ui';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { SkeletonList } from '../components/Skeleton';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../components/Toast';
const API_BASE = import.meta.env.VITE_API_URL || '';

const regionToApiRegion = { 'EUA': 'US', 'Europa': 'EU', 'Asia': 'ASIA', 'AmericaDoSul': 'SA', 'Global': '' };

export default function Dashboard({ onStatsUpdate }) {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  // Determine base path for routing (demo vs real)
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
  const [user, setUser] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [mode, setMode] = useState('wizard');
  const [provisioningMode, setProvisioningMode] = useState(false);
  const [raceCandidates, setRaceCandidates] = useState([]);
  const [raceWinner, setRaceWinner] = useState(null);
  const [dashboardStats, setDashboardStats] = useState({
    activeMachines: 0,
    totalMachines: 0,
    dailyCost: 0,
    savings: 0,
    uptime: 0
  });

  // Refs to track intervals and timeouts for cleanup
  const raceIntervalsRef = useRef([]);
  const raceTimeoutsRef = useRef([]);
  const createdInstanceIdsRef = useRef([]);

  useEffect(() => {
    checkOnboarding();
    fetchDashboardStats();
  }, []);

  // Cleanup on unmount - destroy any created instances
  useEffect(() => {
    return () => {
      raceIntervalsRef.current.forEach(clearInterval);
      raceTimeoutsRef.current.forEach(clearTimeout);
      raceIntervalsRef.current = [];
      raceTimeoutsRef.current = [];

      // Destroy any created instances if user navigates away during race
      if (createdInstanceIdsRef.current.length > 0) {
        createdInstanceIdsRef.current.forEach(async (created) => {
          try {
            await fetch(`${API_BASE}/api/v1/instances/${created.instanceId}`, {
              method: 'DELETE',
              headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
            });
            console.log(`Destroyed instance ${created.instanceId} on unmount`);
          } catch (e) {
            console.error(`Failed to destroy instance ${created.instanceId} on unmount:`, e);
          }
        });
        createdInstanceIdsRef.current = [];
      }
    };
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (res.ok) {
        const data = await res.json();
        const instances = data.instances || [];
        const running = instances.filter(i => i.status === 'running');
        const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0);

        const stats = {
          activeMachines: running.length,
          totalMachines: instances.length,
          dailyCost: (totalCost * 24).toFixed(2),
          savings: ((totalCost * 24 * 0.89) * 30).toFixed(0), // 89% economia estimada
          uptime: running.length > 0 ? 99.9 : 0
        };
        console.log('Dashboard stats:', stats);
        setDashboardStats(stats);
        if (onStatsUpdate) {
          console.log('Calling onStatsUpdate with:', stats);
          onStatsUpdate(stats);
        } else {
          console.log('onStatsUpdate is not defined');
        }
      } else {
        // API failed, use demo mode fallback
        console.log('API returned error, using demo stats');
        const stats = {
          activeMachines: 2,
          totalMachines: 3,
          dailyCost: '4.80',
          savings: '127',
          uptime: 99.9
        };
        console.log('Dashboard stats (demo):', stats);
        setDashboardStats(stats);
        if (onStatsUpdate) {
          console.log('Calling onStatsUpdate with (demo):', stats);
          onStatsUpdate(stats);
        } else {
          console.log('onStatsUpdate is not defined (demo)');
        }
      }
    } catch (e) {
      console.error('Error fetching dashboard stats:', e);
      // Demo mode fallback
      const stats = {
        activeMachines: 2,
        totalMachines: 3,
        dailyCost: '4.80',
        savings: '127',
        uptime: 99.9
      };
      console.log('Dashboard stats (demo - catch):', stats);
      setDashboardStats(stats);
      if (onStatsUpdate) {
        console.log('Calling onStatsUpdate with (demo - catch):', stats);
        onStatsUpdate(stats);
      } else {
        console.log('onStatsUpdate is not defined (demo - catch)');
      }
    }
  };

  const checkOnboarding = async () => {
    try {
      // Check localStorage first for quick response
      const localOnboardingDone = localStorage.getItem('onboarding_completed');
      if (localOnboardingDone === 'true') {
        setShowOnboarding(false);
        return;
      }

      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      const data = await res.json();
      if (data.authenticated) {
        setUser(data.user);
        // Verificar se o onboarding já foi completado
        const hasCompleted = data.user?.settings?.has_completed_onboarding;
        if (!hasCompleted) {
          setShowOnboarding(true);
        } else {
          // Sync localStorage with server state
          localStorage.setItem('onboarding_completed', 'true');
          setShowOnboarding(false);
        }
      }
    } catch (e) {
      console.error('Error checking onboarding:', e);
      // Em caso de erro, não mostrar o onboarding
      setShowOnboarding(false);
    }
  };

  const handleCompleteOnboarding = async () => {
    try {
      // Mark as completed in localStorage immediately to prevent re-showing
      localStorage.setItem('onboarding_completed', 'true');
      setShowOnboarding(false);

      const res = await fetch(`${API_BASE}/api/v1/settings/complete-onboarding`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (res.ok) {
        // Atualizar o estado do usuário localmente
        setUser(prev => ({
          ...prev,
          settings: {
            ...prev?.settings,
            has_completed_onboarding: true
          }
        }));
      } else {
        console.error('Failed to complete onboarding:', res.statusText);
      }
    } catch (e) {
      console.error('Error completing onboarding:', e);
    }
  };
  const [activeTab, setActiveTab] = useState('Global');
  const [selectedTier, setSelectedTier] = useState('Rapido');
  const [selectedGPU, setSelectedGPU] = useState('any');
  const [selectedGPUCategory, setSelectedGPUCategory] = useState('any');
  const [searchCountry, setSearchCountry] = useState('');
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showResults, setShowResults] = useState(false);
  const [deployMethod, setDeployMethod] = useState('manual'); // 'ai' | 'manual'

  // Filtros avançados completos do Vast.ai - Organizados por categoria
  const [advancedFilters, setAdvancedFilters] = useState({
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
  });

  const tabs = ['EUA', 'Europa', 'Ásia', 'América do Sul', 'Global'];
  const tabIds = ['EUA', 'Europa', 'Asia', 'AmericaDoSul', 'Global'];

  // Country to ISO code and region mapping
  const countryData = {
    // Regiões (selecionam múltiplos países)
    'eua': { codes: ['US', 'CA', 'MX'], name: 'EUA', isRegion: true },
    'europa': { codes: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'], name: 'Europa', isRegion: true },
    'asia': { codes: ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'], name: 'Ásia', isRegion: true },
    'america do sul': { codes: ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'], name: 'América do Sul', isRegion: true },

    // Países individuais - EUA/América do Norte
    'estados unidos': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'usa': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'united states': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'canada': { codes: ['CA'], name: 'Canadá', isRegion: false },
    'canadá': { codes: ['CA'], name: 'Canadá', isRegion: false },
    'mexico': { codes: ['MX'], name: 'México', isRegion: false },
    'méxico': { codes: ['MX'], name: 'México', isRegion: false },

    // Países individuais - Europa
    'reino unido': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'uk': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'inglaterra': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'franca': { codes: ['FR'], name: 'França', isRegion: false },
    'frança': { codes: ['FR'], name: 'França', isRegion: false },
    'france': { codes: ['FR'], name: 'França', isRegion: false },
    'alemanha': { codes: ['DE'], name: 'Alemanha', isRegion: false },
    'germany': { codes: ['DE'], name: 'Alemanha', isRegion: false },
    'espanha': { codes: ['ES'], name: 'Espanha', isRegion: false },
    'spain': { codes: ['ES'], name: 'Espanha', isRegion: false },
    'italia': { codes: ['IT'], name: 'Itália', isRegion: false },
    'itália': { codes: ['IT'], name: 'Itália', isRegion: false },
    'italy': { codes: ['IT'], name: 'Itália', isRegion: false },
    'portugal': { codes: ['PT'], name: 'Portugal', isRegion: false },
    'holanda': { codes: ['NL'], name: 'Holanda', isRegion: false },
    'netherlands': { codes: ['NL'], name: 'Holanda', isRegion: false },
    'belgica': { codes: ['BE'], name: 'Bélgica', isRegion: false },
    'bélgica': { codes: ['BE'], name: 'Bélgica', isRegion: false },
    'suica': { codes: ['CH'], name: 'Suíça', isRegion: false },
    'suíça': { codes: ['CH'], name: 'Suíça', isRegion: false },
    'austria': { codes: ['AT'], name: 'Áustria', isRegion: false },
    'áustria': { codes: ['AT'], name: 'Áustria', isRegion: false },
    'irlanda': { codes: ['IE'], name: 'Irlanda', isRegion: false },
    'suecia': { codes: ['SE'], name: 'Suécia', isRegion: false },
    'suécia': { codes: ['SE'], name: 'Suécia', isRegion: false },
    'noruega': { codes: ['NO'], name: 'Noruega', isRegion: false },
    'dinamarca': { codes: ['DK'], name: 'Dinamarca', isRegion: false },
    'finlandia': { codes: ['FI'], name: 'Finlândia', isRegion: false },
    'finlândia': { codes: ['FI'], name: 'Finlândia', isRegion: false },
    'polonia': { codes: ['PL'], name: 'Polônia', isRegion: false },
    'polônia': { codes: ['PL'], name: 'Polônia', isRegion: false },

    // Países individuais - Ásia
    'japao': { codes: ['JP'], name: 'Japão', isRegion: false },
    'japão': { codes: ['JP'], name: 'Japão', isRegion: false },
    'japan': { codes: ['JP'], name: 'Japão', isRegion: false },
    'china': { codes: ['CN'], name: 'China', isRegion: false },
    'coreia': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'coréia': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'korea': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'singapore': { codes: ['SG'], name: 'Singapura', isRegion: false },
    'singapura': { codes: ['SG'], name: 'Singapura', isRegion: false },
    'india': { codes: ['IN'], name: 'Índia', isRegion: false },
    'índia': { codes: ['IN'], name: 'Índia', isRegion: false },
    'tailandia': { codes: ['TH'], name: 'Tailândia', isRegion: false },
    'tailândia': { codes: ['TH'], name: 'Tailândia', isRegion: false },
    'vietnam': { codes: ['VN'], name: 'Vietnã', isRegion: false },
    'vietnã': { codes: ['VN'], name: 'Vietnã', isRegion: false },
    'indonesia': { codes: ['ID'], name: 'Indonésia', isRegion: false },
    'indonésia': { codes: ['ID'], name: 'Indonésia', isRegion: false },
    'malasia': { codes: ['MY'], name: 'Malásia', isRegion: false },
    'malásia': { codes: ['MY'], name: 'Malásia', isRegion: false },
    'filipinas': { codes: ['PH'], name: 'Filipinas', isRegion: false },
    'taiwan': { codes: ['TW'], name: 'Taiwan', isRegion: false },

    // Países individuais - América do Sul
    'brasil': { codes: ['BR'], name: 'Brasil', isRegion: false },
    'brazil': { codes: ['BR'], name: 'Brasil', isRegion: false },
    'argentina': { codes: ['AR'], name: 'Argentina', isRegion: false },
    'chile': { codes: ['CL'], name: 'Chile', isRegion: false },
    'colombia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
    'colômbia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
    'peru': { codes: ['PE'], name: 'Peru', isRegion: false },
    'venezuela': { codes: ['VE'], name: 'Venezuela', isRegion: false },
    'equador': { codes: ['EC'], name: 'Equador', isRegion: false },
    'uruguai': { codes: ['UY'], name: 'Uruguai', isRegion: false },
    'paraguai': { codes: ['PY'], name: 'Paraguai', isRegion: false },
    'bolivia': { codes: ['BO'], name: 'Bolívia', isRegion: false },
    'bolívia': { codes: ['BO'], name: 'Bolívia', isRegion: false },
  };

  // State for selected location (can be country or region)
  const [selectedLocation, setSelectedLocation] = useState(null); // { codes: [], name: '', isRegion: bool }

  // Function to find location data from search query
  const findLocationFromSearch = (query) => {
    if (!query || query.length < 2) return null;
    const normalizedQuery = query.toLowerCase().trim();

    // Check exact match first
    if (countryData[normalizedQuery]) {
      return countryData[normalizedQuery];
    }

    // Check partial match
    for (const [key, data] of Object.entries(countryData)) {
      if (key.includes(normalizedQuery) || normalizedQuery.includes(key)) {
        return data;
      }
    }
    return null;
  };

  // Handle search input change with auto-selection
  const handleSearchChange = (value) => {
    setSearchCountry(value);
    const foundLocation = findLocationFromSearch(value);
    if (foundLocation) {
      setSelectedLocation(foundLocation);
    }
  };

  // Handle region button click
  const handleRegionSelect = (regionKey) => {
    const regionData = countryData[regionKey];
    if (regionData) {
      setSelectedLocation(regionData);
      setSearchCountry('');
    }
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedLocation(null);
    setSearchCountry('');
  };

  // Use imported PERFORMANCE_TIERS from constants
  const tiers = PERFORMANCE_TIERS;

  const getToken = () => localStorage.getItem('auth_token');

  // DEMO_OFFERS imported from constants

  const searchOffers = async (filters) => {
    setLoading(true);
    setError(null);
    setShowResults(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });
      const response = await fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (!response.ok) throw new Error('Falha ao buscar ofertas');
      const data = await response.json();
      const realOffers = data.offers || [];

      // Use demo offers as fallback when API returns empty (e.g., no VAST_API_KEY)
      if (realOffers.length === 0) {
        setOffers(DEMO_OFFERS);
        toast.info('Mostrando ofertas de demonstração');
      } else {
        setOffers(realOffers);
        toast.success(`${realOffers.length} máquinas encontradas!`);
      }
    } catch (err) {
      // Use demo offers on API error for testing
      setOffers(DEMO_OFFERS);
      toast.warning('Erro ao buscar ofertas. Mostrando dados de demonstração.');
    } finally {
      setLoading(false);
    }
  };

  const handleWizardSearch = () => {
    const tier = tiers.find(t => t.name === selectedTier);
    if (tier) {
      searchOffers({
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      });
    }
  };

  const handleAdvancedSearch = () => {
    const filters = { ...advancedFilters };
    if (filters.gpu_name === 'any') filters.gpu_name = '';
    if (filters.region === 'any') filters.region = '';
    if (filters.cuda_vers === 'any') filters.cuda_vers = '';
    searchOffers(filters);
  };

  const handleAdvancedFilterChange = (key, value) => {
    setAdvancedFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleSelectOffer = (offer) => {
    toast.success(`Máquina ${offer.gpu_name} selecionada!`);
    navigate(`${basePath}/machines`, { state: { selectedOffer: offer } });
  };

  // Start provisioning race with top 5 offers
  const startProvisioningRace = (selectedOffers) => {
    // Take top 5 offers (or less if not available)
    const top5 = selectedOffers.slice(0, 5).map((offer, index) => ({
      ...offer,
      status: 'connecting',
      progress: 0
    }));

    setRaceCandidates(top5);
    setRaceWinner(null);
    setProvisioningMode(true);

    // Run REAL provisioning race (creates actual instances)
    runRealProvisioningRace(top5);
  };

  // REAL provisioning race - creates actual instances and monitors which one starts first
  const runRealProvisioningRace = async (candidates) => {
    // Clear previous race intervals/timeouts
    raceIntervalsRef.current.forEach(clearInterval);
    raceTimeoutsRef.current.forEach(clearTimeout);
    raceIntervalsRef.current = [];
    raceTimeoutsRef.current = [];
    createdInstanceIdsRef.current = [];

    let winnerFound = false;

    // Create all instances simultaneously
    const createPromises = candidates.map(async (candidate, index) => {
      try {
        // Update status to "creating"
        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = { ...updated[index], status: 'creating', progress: 10 };
          return updated;
        });

        // Create instance via API
        const res = await fetch(`${API_BASE}/api/v1/instances`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            offer_id: candidate.id,
            disk_size: candidate.disk_space || 20,
            label: `Race-${candidate.gpu_name}-${Date.now()}`
          })
        });

        if (!res.ok) {
          throw new Error('Failed to create instance');
        }

        const data = await res.json();
        const instanceId = data.id || data.instance_id;
        createdInstanceIdsRef.current.push({ index, instanceId, offerId: candidate.id });

        // Update with instance ID and status
        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = {
            ...updated[index],
            instanceId,
            status: 'connecting',
            progress: 30
          };
          return updated;
        });

        return { index, instanceId, success: true };
      } catch (error) {
        // Mark as failed with descriptive error message
        let errorMessage = 'Erro desconhecido';
        if (error.message?.includes('balance') || error.message?.includes('insufficient')) {
          errorMessage = 'Saldo insuficiente';
        } else if (error.message?.includes('timeout') || error.message?.includes('Timeout')) {
          errorMessage = 'Timeout de conexão';
        } else if (error.message?.includes('unavailable') || error.message?.includes('not available')) {
          errorMessage = 'Máquina indisponível';
        } else if (error.message?.includes('network') || error.message?.includes('Network')) {
          errorMessage = 'Erro de rede';
        } else if (error.message?.includes('auth') || error.message?.includes('401') || error.message?.includes('403')) {
          errorMessage = 'Erro de autenticação';
        } else if (error.message?.includes('limit') || error.message?.includes('quota')) {
          errorMessage = 'Limite de instâncias atingido';
        } else if (error.message) {
          errorMessage = error.message.slice(0, 30);
        }

        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = { ...updated[index], status: 'failed', progress: 0, errorMessage };
          return updated;
        });
        return { index, success: false, error };
      }
    });

    // Wait for all creation attempts
    await Promise.all(createPromises);

    // Poll for status updates every 3 seconds
    const pollInterval = setInterval(async () => {
      if (winnerFound) {
        clearInterval(pollInterval);
        return;
      }

      try {
        // Fetch all instances to check status
        const res = await fetch(`${API_BASE}/api/v1/instances`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) return;

        const data = await res.json();
        const instances = data.instances || [];

        // Check each created instance
        for (const created of createdInstanceIdsRef.current) {
          const instance = instances.find(i => i.id === created.instanceId);
          if (!instance) continue;

          const status = instance.actual_status;
          const candidateIndex = created.index;

          // Update progress based on status
          setRaceCandidates(prev => {
            const updated = [...prev];
            if (updated[candidateIndex]) {
              let progress = updated[candidateIndex].progress || 30;
              if (status === 'loading') progress = Math.min(progress + 10, 90);
              if (status === 'running') progress = 100;
              updated[candidateIndex] = {
                ...updated[candidateIndex],
                progress,
                actualStatus: status,
                sshHost: instance.ssh_host,
                sshPort: instance.ssh_port
              };
            }
            return updated;
          });

          // Check if this one is running (WINNER!)
          if (status === 'running' && !winnerFound) {
            winnerFound = true;
            clearInterval(pollInterval);

            // Mark winner and cancel others
            setRaceCandidates(prev => {
              return prev.map((c, i) => ({
                ...c,
                status: i === candidateIndex ? 'connected' : 'cancelled',
                progress: i === candidateIndex ? 100 : c.progress
              }));
            });

            // Set winner with full instance data
            const winnerCandidate = candidates[candidateIndex];
            setRaceWinner({
              ...winnerCandidate,
              instanceId: created.instanceId,
              ssh_host: instance.ssh_host,
              ssh_port: instance.ssh_port,
              actual_status: 'running'
            });

            // Destroy the losing instances to save money
            for (const other of createdInstanceIdsRef.current) {
              if (other.instanceId !== created.instanceId) {
                try {
                  await fetch(`${API_BASE}/api/v1/instances/${other.instanceId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${getToken()}` }
                  });
                  console.log(`Destroyed losing instance ${other.instanceId}`);
                } catch (e) {
                  console.error(`Failed to destroy instance ${other.instanceId}:`, e);
                }
              }
            }

            // Clear the ref after cleanup
            createdInstanceIdsRef.current = [];
            toast.success(`🏆 ${winnerCandidate.gpu_name} venceu a corrida!`);
            break;
          }
        }
      } catch (error) {
        console.error('Error polling instance status:', error);
      }
    }, 3000);

    raceIntervalsRef.current.push(pollInterval);

    // Timeout after 5 minutes - if no winner, pick the first one that's furthest along
    const raceTimeout = setTimeout(async () => {
      if (!winnerFound) {
        clearInterval(pollInterval);
        toast.error('Tempo esgotado. Nenhuma máquina inicializou a tempo.');

        // Clean up all created instances
        for (const created of createdInstanceIdsRef.current) {
          try {
            await fetch(`${API_BASE}/api/v1/instances/${created.instanceId}`, {
              method: 'DELETE',
              headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            console.log(`Cleaned up instance ${created.instanceId} after timeout`);
          } catch (e) {
            console.error(`Failed to cleanup instance ${created.instanceId}:`, e);
          }
        }

        createdInstanceIdsRef.current = [];
        setProvisioningMode(false);
      }
    }, 5 * 60 * 1000); // 5 minutes

    raceTimeoutsRef.current.push(raceTimeout);
  };

  const cancelProvisioningRace = async () => {
    // Clean up all intervals and timeouts
    raceIntervalsRef.current.forEach(clearInterval);
    raceTimeoutsRef.current.forEach(clearTimeout);
    raceIntervalsRef.current = [];
    raceTimeoutsRef.current = [];

    // Destroy all created instances to save money
    if (createdInstanceIdsRef.current.length > 0) {
      toast.info('Cancelando e destruindo instâncias criadas...');

      for (const created of createdInstanceIdsRef.current) {
        try {
          await fetch(`${API_BASE}/api/v1/instances/${created.instanceId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
          });
          console.log(`Destroyed instance ${created.instanceId} on cancel`);
        } catch (e) {
          console.error(`Failed to destroy instance ${created.instanceId}:`, e);
        }
      }

      createdInstanceIdsRef.current = [];
      toast.success('Corrida cancelada. Instâncias destruídas.');
    }

    setProvisioningMode(false);
    setRaceCandidates([]);
    setRaceWinner(null);
  };

  const completeProvisioningRace = (winner) => {
    setProvisioningMode(false);
    // Toast já foi mostrado quando o vencedor foi encontrado
    navigate(`${basePath}/machines`, { state: { selectedOffer: winner } });
  };

  // Modified wizard search to start the race
  const handleWizardSearchWithRace = () => {
    const tier = tiers.find(t => t.name === selectedTier);
    if (tier) {
      // First fetch offers, then start race
      setLoading(true);
      const params = new URLSearchParams();
      const filters = {
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      };
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });

      fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
        .then(res => res.json())
        .then(data => {
          const realOffers = data.offers || [];
          const offersToUse = realOffers.length > 0 ? realOffers : DEMO_OFFERS;
          setOffers(offersToUse);
          setLoading(false);
          // Start the race with top offers
          if (offersToUse.length > 0) {
            startProvisioningRace(offersToUse);
          }
        })
        .catch(() => {
          setOffers(DEMO_OFFERS);
          setLoading(false);
          startProvisioningRace(DEMO_OFFERS);
        });
    }
  };

  // Integrated wizard search - starts race within wizard (no overlay)
  const handleWizardSearchWithRaceIntegrated = () => {
    const tier = tiers.find(t => t.name === selectedTier);
    if (tier) {
      setLoading(true);
      const params = new URLSearchParams();
      const filters = {
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      };
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });

      fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
        .then(res => res.json())
        .then(data => {
          const realOffers = data.offers || [];
          const offersToUse = realOffers.length > 0 ? realOffers : DEMO_OFFERS;
          setOffers(offersToUse);
          setLoading(false);
          // Start the race WITHOUT showing the overlay - wizard handles step 4
          if (offersToUse.length > 0) {
            startProvisioningRaceIntegrated(offersToUse);
          }
        })
        .catch(() => {
          setOffers(DEMO_OFFERS);
          setLoading(false);
          startProvisioningRaceIntegrated(DEMO_OFFERS);
        });
    }
  };

  // Start provisioning race integrated into wizard (no overlay)
  const startProvisioningRaceIntegrated = (selectedOffers) => {
    const top5 = selectedOffers.slice(0, 5).map((offer, index) => ({
      ...offer,
      status: 'connecting',
      progress: 0
    }));

    setRaceCandidates(top5);
    setRaceWinner(null);
    // DON'T set provisioningMode to true - wizard handles step 4 display
    // Run REAL provisioning race
    runRealProvisioningRace(top5);
  };

  const resetAdvancedFilters = () => {
    setAdvancedFilters({
      gpu_name: 'any', num_gpus: 1, min_gpu_ram: 0, gpu_frac: 1, gpu_mem_bw: 0, gpu_max_power: 0, bw_nvlink: 0,
      min_cpu_cores: 1, min_cpu_ram: 1, min_disk: 50, cpu_ghz: 0,
      min_dlperf: 0, min_pcie_bw: 0, total_flops: 0, cuda_vers: 'any', compute_cap: 0,
      min_inet_down: 100, min_inet_up: 50, direct_port_count: 0,
      max_price: 5.0, rental_type: 'on-demand',
      min_reliability: 0, region: 'any', verified_only: false, datacenter: false,
      static_ip: false, order_by: 'dph_total', limit: 100
    });
    toast.info('Filtros resetados');
  };

  return (
    <div className="min-h-screen">
      {showOnboarding && (
        <OnboardingWizard
          user={user}
          onClose={() => setShowOnboarding(false)}
          onComplete={handleCompleteOnboarding}
        />
      )}

      {/* Provisioning Race Screen */}
      {provisioningMode && (
        <ProvisioningRaceScreen
          candidates={raceCandidates}
          winner={raceWinner}
          onCancel={cancelProvisioningRace}
          onComplete={completeProvisioningRace}
        />
      )}

      {/* Deploy Wizard */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <Card>
          <CardHeader className="pb-6">
            {/* Header com título */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-brand-500" />
              </div>
              <div>
                <CardTitle className="text-lg">Nova Instância GPU</CardTitle>
                <CardDescription className="text-xs">Provisione sua máquina em minutos</CardDescription>
              </div>
            </div>

            {/* Seletor de Método Unificado */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Opção 1: Configuração Guiada */}
                <button
                  onClick={() => { setDeployMethod('manual'); setMode('wizard'); setShowResults(false); }}
                  data-testid="config-guided"
                  className={`p-6 rounded-lg border transition-all text-left group relative overflow-hidden cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-brand-500/10 active:scale-[0.98] ${
                    deployMethod === 'manual' && mode === 'wizard'
                      ? 'border-brand-500 ring-2 ring-brand-500/20 bg-brand-500/5'
                      : 'border-gray-700 hover:border-brand-400 hover:bg-gray-800/50'
                  }`}
                >
                  {deployMethod === 'manual' && mode === 'wizard' && (
                    <div className="absolute top-0 left-0 w-1 h-full bg-brand-500" />
                  )}
                  <div className="flex items-start gap-3">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 flex-shrink-0 transition-colors ${
                      deployMethod === 'manual' && mode === 'wizard' ? 'border-brand-500 bg-brand-500' : 'border-gray-600 group-hover:border-brand-400'
                    }`}>
                      {deployMethod === 'manual' && mode === 'wizard' && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-sm text-white mb-1.5 group-hover:text-brand-300 transition-colors">Configuração Guiada</p>
                      <p className="text-xs text-gray-400 leading-relaxed mb-3">Escolha região, GPU e performance de forma simples e intuitiva</p>
                      <span className="inline-block text-[10px] font-semibold text-brand-400 bg-brand-500/10 px-2.5 py-1 rounded-md border border-brand-800/20">✓ Recomendado</span>
                    </div>
                  </div>
                </button>

                {/* Opção 2: Configuração Avançada */}
                <button
                  onClick={() => { setDeployMethod('manual'); setMode('advanced'); setShowResults(false); }}
                  data-testid="config-advanced"
                  className={`p-6 rounded-lg border transition-all text-left group relative overflow-hidden cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-brand-500/10 active:scale-[0.98] ${
                    deployMethod === 'manual' && mode === 'advanced'
                      ? 'border-brand-500 ring-2 ring-brand-500/20 bg-brand-500/5'
                      : 'border-gray-700 hover:border-brand-400 hover:bg-gray-800/50'
                  }`}
                >
                  {deployMethod === 'manual' && mode === 'advanced' && (
                    <div className="absolute top-0 left-0 w-1 h-full bg-brand-500" />
                  )}
                  <div className="flex items-start gap-3">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 flex-shrink-0 transition-colors ${
                      deployMethod === 'manual' && mode === 'advanced' ? 'border-brand-500 bg-brand-500' : 'border-gray-600 group-hover:border-brand-400'
                    }`}>
                      {deployMethod === 'manual' && mode === 'advanced' && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-sm text-white mb-1.5 group-hover:text-brand-300 transition-colors">Configuração Avançada</p>
                      <p className="text-xs text-gray-400 leading-relaxed mb-3">Controle total com filtros detalhados de hardware e rede</p>
                      <span className="inline-block text-[10px] font-semibold text-gray-500 bg-gray-800 px-2.5 py-1 rounded-md border border-gray-700">Para especialistas</span>
                    </div>
                  </div>
                </button>

                {/* Opção 3: Assistente IA */}
                <button
                  onClick={() => { setDeployMethod('ai'); setShowResults(false); }}
                  data-testid="config-ai"
                  className={`p-6 rounded-lg border transition-all text-left group relative overflow-hidden cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-purple-500/10 active:scale-[0.98] ${
                    deployMethod === 'ai'
                      ? 'border-purple-500 ring-2 ring-purple-500/20 bg-purple-500/5'
                      : 'border-gray-700 hover:border-purple-400 hover:bg-gray-800/50'
                  }`}
                >
                  {deployMethod === 'ai' && (
                    <div className="absolute top-0 left-0 w-1 h-full bg-purple-500" />
                  )}
                  <div className="flex items-start gap-3">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 flex-shrink-0 transition-colors ${
                      deployMethod === 'ai' ? 'border-purple-500 bg-purple-500' : 'border-gray-600 group-hover:border-purple-400'
                    }`}>
                      {deployMethod === 'ai' && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-sm text-white mb-1.5 group-hover:text-purple-300 transition-colors">Assistente IA</p>
                      <p className="text-xs text-gray-400 leading-relaxed mb-3">Converse e deixe a IA recomendar a melhor configuração</p>
                      <span className="inline-block text-[10px] font-semibold text-purple-400 bg-purple-500/10 px-2.5 py-1 rounded-md border border-purple-500/20">✨ Inteligente</span>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </CardHeader>

          {/* AI MODE */}
          {deployMethod === 'ai' && (
            <CardContent className="h-[600px] p-0 relative animate-fadeIn">
              <AIWizardChat
                compact={false}
                onRecommendation={(rec) => {}}
                onSearchWithFilters={(filters) => {
                  // Logic to jump to search results
                  setDeployMethod('manual');
                  setMode('advanced');
                  // Apply filters...
                }}
              />
            </CardContent>
          )}

          {/* WIZARD MODE (MANUAL) */}
          {deployMethod === 'manual' && mode === 'wizard' && !showResults && (
            <div className="animate-fadeIn">
              <WizardForm
                searchCountry={searchCountry}
                selectedLocation={selectedLocation}
                onSearchChange={handleSearchChange}
                onRegionSelect={handleRegionSelect}
                onCountryClick={(location) => {
                  setSelectedLocation(location);
                  setSearchCountry('');
                }}
                onClearSelection={clearSelection}
                selectedGPU={selectedGPU}
                onSelectGPU={setSelectedGPU}
                selectedGPUCategory={selectedGPUCategory}
                onSelectGPUCategory={setSelectedGPUCategory}
                selectedTier={selectedTier}
                onSelectTier={setSelectedTier}
                loading={loading}
                onSubmit={handleWizardSearchWithRaceIntegrated}
                // Provisioning props (Step 4)
                provisioningCandidates={raceCandidates}
                provisioningWinner={raceWinner}
                isProvisioning={provisioningMode}
                onCancelProvisioning={cancelProvisioningRace}
                onCompleteProvisioning={completeProvisioningRace}
              />
            </div>
          )}

          {/* ADVANCED MODE (MANUAL) */}
          {deployMethod === 'manual' && mode === 'advanced' && !showResults && (
            <div className="animate-fadeIn">
              <AdvancedSearchForm
                filters={advancedFilters}
                onFilterChange={handleAdvancedFilterChange}
                onReset={resetAdvancedFilters}
                onSearch={handleAdvancedSearch}
                onBackToWizard={() => setMode('wizard')}
                loading={loading}
              />
            </div>
          )}

          {/* RESULTS VIEW */}
          {showResults && (
            <CardContent className="pt-6 animate-slideInUp">
              <div className="flex flex-col gap-4 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-gray-900 dark:text-white text-lg font-semibold">Máquinas Disponíveis</h2>
                    <p className="text-gray-500 text-xs">{offers.length} resultados encontrados</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowResults(false)}
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Voltar
                  </Button>
                </div>

                {/* Sorting Controls */}
                {offers.length > 0 && (
                  <div className="flex items-center gap-4 p-3 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Ordenar por:</span>
                    </div>
                    <Select value={advancedFilters.order_by} onValueChange={(v) => handleAdvancedFilterChange('order_by', v)}>
                      <SelectTrigger className="w-[200px] h-9 bg-gray-900">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ORDER_OPTIONS.map(opt => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="flex items-center gap-2 ml-4">
                      <span className="text-sm text-gray-500 dark:text-gray-400">Limite:</span>
                      <Input
                        type="number"
                        min="10"
                        max="500"
                        value={advancedFilters.limit}
                        onChange={(e) => handleAdvancedFilterChange('limit', parseInt(e.target.value) || 100)}
                        className="w-20 h-9 bg-gray-900"
                      />
                    </div>
                  </div>
                )}
              </div>

              {loading && (
                <SkeletonList count={6} type="offer" />
              )}

              {error && !loading && (
                <ErrorState
                  message={error}
                  onRetry={() => {
                    setError(null);
                    setShowResults(false);
                  }}
                  retryText="Tentar novamente"
                />
              )}

              {!loading && !error && offers.length === 0 && (
                <EmptyState
                  icon="search"
                  title="Nenhuma máquina encontrada"
                  description="Não encontramos ofertas com os filtros selecionados. Tente ajustar os critérios de busca."
                  action={() => setShowResults(false)}
                  actionText="Ajustar filtros"
                />
              )}

              {!loading && offers.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {offers.map((offer, index) => (
                    <div
                      key={offer.id || index}
                      className="animate-scaleIn"
                      style={{ animationDelay: `${index * 0.05}s` }}
                    >
                      <OfferCard offer={offer} onSelect={handleSelectOffer} />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          )}
        </Card>
      </div>
    </div >
  );
}
