import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  DollarSign,
  Server,
  Shield,
  ChevronRight
} from 'lucide-react';

/**
 * DashboardReports - 3 Relatórios Principais (TailAdmin Style)
 */

const mockData = {
  economia: {
    economiaTotal: 102000,
    economiaPercentual: 87,
    custoHora: 0.42,
    custoHoraAws: 3.20,
  },
  maquinas: {
    gpusAtivas: 4,
    gpusTotal: 6,
    usoMedioGpu: 78,
    horasUtilizadas: 1247,
  },
  confiabilidade: {
    uptime: 99.94,
    failoversRealizados: 3,
    tempoMedioRecuperacao: 12,
    latenciaMedia: 45,
  }
};

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

// Helper para base path
function getBasePath(pathname) {
  return pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
}

// Card de Economia
function EconomiaCard({ data, basePath }) {
  return (
    <Link to={`${basePath}/metrics-hub`} className="stat-card group">
      <div className="flex items-center justify-between mb-4">
        <div className="stat-card-icon stat-card-icon-primary">
          <DollarSign className="w-5 h-5" />
        </div>
        <span className="text-xs text-gray-500">vs AWS/GCP</span>
      </div>

      <div className="stat-card-value mb-1">
        {formatCurrency(data.economiaTotal)}
        <span className="text-sm font-normal text-gray-500 ml-1">/ano</span>
      </div>

      <div className="stat-card-label mb-3">Economia Total</div>

      <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-white/5">
        <span>${data.custoHora}/h <span className="line-through ml-1">${data.custoHoraAws}</span></span>
        <span className="flex items-center gap-1 text-gray-400 group-hover:text-brand-500 transition-colors">
          Detalhes <ChevronRight className="w-3 h-3" />
        </span>
      </div>
    </Link>
  );
}

// Card de Máquinas
function MaquinasCard({ data, basePath }) {
  return (
    <Link to={`${basePath}/machines-report`} className="stat-card group">
      <div className="flex items-center justify-between mb-4">
        <div className="stat-card-icon stat-card-icon-primary">
          <Server className="w-5 h-5" />
        </div>
        <span className="text-xs text-gray-500">{data.usoMedioGpu}% uso</span>
      </div>

      <div className="stat-card-value mb-1">
        {data.gpusAtivas}
        <span className="text-sm font-normal text-gray-500 ml-1">/{data.gpusTotal} GPUs</span>
      </div>

      <div className="stat-card-label mb-3">Máquinas Ativas</div>

      <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-white/5">
        <span>{data.horasUtilizadas.toLocaleString()}h este mês</span>
        <span className="flex items-center gap-1 text-gray-400 group-hover:text-brand-500 transition-colors">
          Detalhes <ChevronRight className="w-3 h-3" />
        </span>
      </div>
    </Link>
  );
}

// Card de Confiabilidade
function ConfiabilidadeCard({ data, basePath }) {
  return (
    <Link to={`${basePath}/failover-report`} className="stat-card group">
      <div className="flex items-center justify-between mb-4">
        <div className="stat-card-icon stat-card-icon-primary">
          <Shield className="w-5 h-5" />
        </div>
        <span className="text-xs text-gray-500">{data.latenciaMedia}ms latência</span>
      </div>

      <div className="stat-card-value mb-1">
        {data.uptime}%
        <span className="text-sm font-normal text-gray-500 ml-1">uptime</span>
      </div>

      <div className="stat-card-label mb-3">Confiabilidade</div>

      <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-white/5">
        <span>{data.failoversRealizados} failovers • {data.tempoMedioRecuperacao}s recuperação</span>
        <span className="flex items-center gap-1 text-gray-400 group-hover:text-brand-500 transition-colors">
          Detalhes <ChevronRight className="w-3 h-3" />
        </span>
      </div>
    </Link>
  );
}

// Componente Principal
export default function DashboardReports({ data = mockData }) {
  const location = useLocation();
  const basePath = getBasePath(location.pathname);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <EconomiaCard data={data.economia} basePath={basePath} />
      <MaquinasCard data={data.maquinas} basePath={basePath} />
      <ConfiabilidadeCard data={data.confiabilidade} basePath={basePath} />
    </div>
  );
}

export { EconomiaCard, MaquinasCard, ConfiabilidadeCard };
