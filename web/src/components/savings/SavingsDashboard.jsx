import { useState, useEffect } from 'react'
import { PageHeader, StatCard, Card, Button, Badge, Progress, EmptyState, StatsGrid } from '../tailadmin-ui/index'
import { DollarSign, TrendingUp, TrendingDown, PiggyBank, Zap, Clock, Server, RefreshCw, BarChart3, ArrowUpRight, Calculator, CheckCircle, Sparkles } from 'lucide-react'

const API_BASE = ''

// Dados demo para quando não há dados reais
const DEMO_DATA = {
    summary: {
        total_cost_dumont: 247.50,
        total_cost_aws: 892.30,
        total_cost_gcp: 756.80,
        total_cost_azure: 823.40,
        savings_vs_aws: 644.80,
        savings_vs_gcp: 509.30,
        savings_vs_azure: 575.90,
        savings_percentage_avg: 72,
        total_gpu_hours: 186,
        machines_used: 4,
        auto_hibernate_savings: 89.50,
    },
    history: {
        months: ['Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
        dumont: [180, 210, 195, 230, 220, 247],
        aws: [650, 720, 680, 780, 750, 892],
        gcp: [550, 610, 580, 660, 640, 756],
    },
    breakdown: [
        { name: 'RTX 4090 - Training', hours: 72, cost_dumont: 108.00, cost_aws: 432.00, savings: 324.00 },
        { name: 'A100 80GB - LLM', hours: 48, cost_dumont: 86.40, cost_aws: 288.00, savings: 201.60 },
        { name: 'RTX 3090 - Inference', hours: 42, cost_dumont: 33.60, cost_aws: 126.00, savings: 92.40 },
        { name: 'RTX 4080 - Development', hours: 24, cost_dumont: 19.50, cost_aws: 46.30, savings: 26.80 },
    ]
}

export default function SavingsDashboard({ getAuthHeaders }) {
    const [period, setPeriod] = useState('month')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [data, setData] = useState(null)
    const [useDemo, setUseDemo] = useState(false)

    const periods = [
        { id: 'day', label: 'Hoje' },
        { id: 'week', label: '7 dias' },
        { id: 'month', label: '30 dias' },
        { id: 'year', label: '1 ano' }
    ]

    useEffect(() => {
        loadAllData()
    }, [period])

    const loadAllData = async () => {
        setLoading(true)
        setError(null)
        try {
            const headers = getAuthHeaders ? getAuthHeaders() : {}

            const summaryRes = await fetch(`${API_BASE}/api/v1/savings/summary?period=${period}`, {
                headers,
                credentials: 'include'
            })

            if (!summaryRes.ok) {
                throw new Error('Erro ao carregar dados do dashboard')
            }

            const summaryData = await summaryRes.json()
            setData({
                summary: summaryData,
                history: DEMO_DATA.history,
                breakdown: DEMO_DATA.breakdown
            })
            setUseDemo(false)
        } catch (err) {
            console.error('Error loading savings dashboard:', err)
            // Use demo data on error
            setData({
                summary: DEMO_DATA.summary,
                history: DEMO_DATA.history,
                breakdown: DEMO_DATA.breakdown
            })
            setUseDemo(true)
        } finally {
            setLoading(false)
        }
    }

    const summary = data?.summary || DEMO_DATA.summary

    return (
        <div className="p-4 md:p-6 lg:p-8">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <nav className="flex items-center gap-2 text-sm text-gray-500 mb-3">
                        <a href="/app" className="hover:text-emerald-400 transition-colors">Home</a>
                        <span className="text-gray-600">/</span>
                        <span className="text-white font-medium">Economia</span>
                    </nav>
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
                                <div className="stat-card-icon stat-card-icon-success">
                                    <PiggyBank size={24} />
                                </div>
                                Dashboard de Economia
                            </h1>
                            <p className="text-gray-400 mt-1">Compare seus custos reais com grandes cloud providers</p>
                        </div>
                        <div className="flex items-center gap-3">
                            {/* Period Tabs */}
                            <div className="ta-tabs">
                                {periods.map(p => (
                                    <button
                                        key={p.id}
                                        className={`ta-tab ${period === p.id ? 'ta-tab-active' : ''}`}
                                        onClick={() => setPeriod(p.id)}
                                    >
                                        {p.label}
                                    </button>
                                ))}
                            </div>
                            <button
                                onClick={loadAllData}
                                disabled={loading}
                                className="ta-btn ta-btn-outline ta-btn-sm"
                            >
                                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                                {loading ? 'Atualizando...' : 'Atualizar'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Demo Mode Alert */}
                {useDemo && (
                    <div className="ta-alert ta-alert-info mb-6 animate-fade-in">
                        <BarChart3 size={20} />
                        <div>
                            <p className="font-medium">Modo Demonstração</p>
                            <p className="text-sm opacity-80">Os dados exibidos são simulados para fins de demonstração.</p>
                        </div>
                    </div>
                )}

                {/* Big Savings Highlight */}
                <div className="spot-highlight mb-8 animate-fade-in">
                    <div className="flex flex-col md:flex-row items-center justify-center gap-6 relative z-10">
                        <div className="flex items-center gap-4">
                            <Sparkles size={40} className="text-emerald-400" />
                            <div className="text-center md:text-left">
                                <span className="block text-xs text-emerald-300/70 uppercase font-semibold tracking-wide">Economia Total Este Mês</span>
                                <span className="block text-4xl md:text-5xl font-extrabold text-white">${summary.savings_vs_aws.toFixed(2)}</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 px-6 py-3 bg-white/10 rounded-xl">
                            <CheckCircle size={24} className="text-emerald-400" />
                            <div>
                                <span className="block text-2xl font-bold text-emerald-300">{summary.savings_percentage_avg}%</span>
                                <span className="block text-xs text-emerald-200/60">mais barato que AWS</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    <div className="stat-card animate-fade-in" style={{ animationDelay: '0ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Você Pagou</p>
                                <p className="text-2xl font-bold text-emerald-400">${summary.total_cost_dumont.toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Este mês na Dumont Cloud</p>
                            </div>
                            <div className="stat-card-icon stat-card-icon-success">
                                <DollarSign size={20} />
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                                <TrendingDown size={12} />
                                -{summary.savings_percentage_avg}% vs AWS
                            </span>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '50ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">AWS Pagaria</p>
                                <p className="text-2xl font-bold text-orange-400">${summary.total_cost_aws.toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Mesmo workload na AWS</p>
                            </div>
                            <div className="stat-card-icon bg-orange-500/10 text-orange-400">
                                <Server size={20} />
                            </div>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '100ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">GCP Pagaria</p>
                                <p className="text-2xl font-bold text-blue-400">${(summary.total_cost_gcp || 756.80).toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Mesmo workload no GCP</p>
                            </div>
                            <div className="stat-card-icon bg-blue-500/10 text-blue-400">
                                <Server size={20} />
                            </div>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '150ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Auto-Hibernate</p>
                                <p className="text-2xl font-bold text-yellow-400">${(summary.auto_hibernate_savings || 0).toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Economia por hibernação</p>
                            </div>
                            <div className="stat-card-icon stat-card-icon-warning">
                                <Zap size={20} />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Comparison Chart - Large */}
                    <div className="ta-card hover-glow lg:col-span-2">
                        <div className="ta-card-header">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="stat-card-icon bg-purple-500/10 text-purple-400">
                                        <BarChart3 size={18} />
                                    </div>
                                    <div>
                                        <h3 className="ta-card-title">Comparativo de Custos</h3>
                                        <p className="text-sm text-gray-400">Dumont Cloud vs Big Cloud Providers</p>
                                    </div>
                                </div>
                                <span className="ta-badge ta-badge-success">{summary.savings_percentage_avg}% mais barato</span>
                            </div>
                        </div>
                        <div className="ta-card-body">
                            {/* Visual Comparison Bars */}
                            <div className="space-y-5">
                                {/* Dumont */}
                                <div className="animate-fade-in" style={{ animationDelay: '0ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/30"></div>
                                            <span className="text-sm font-medium text-white">Dumont Cloud</span>
                                            <span className="ta-badge ta-badge-success text-[10px]">Você</span>
                                        </div>
                                        <span className="text-sm font-bold text-emerald-400">${summary.total_cost_dumont.toFixed(2)}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: `${(summary.total_cost_dumont / summary.total_cost_aws) * 100}%` }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">{Math.round((summary.total_cost_dumont / summary.total_cost_aws) * 100)}%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* AWS */}
                                <div className="animate-fade-in" style={{ animationDelay: '100ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-orange-500 shadow-lg shadow-orange-500/30"></div>
                                            <span className="text-sm font-medium text-white">Amazon AWS</span>
                                        </div>
                                        <span className="text-sm font-bold text-orange-400">${summary.total_cost_aws.toFixed(2)}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-orange-600 to-orange-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: '100%' }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">100%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* GCP */}
                                <div className="animate-fade-in" style={{ animationDelay: '200ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-blue-500 shadow-lg shadow-blue-500/30"></div>
                                            <span className="text-sm font-medium text-white">Google Cloud</span>
                                        </div>
                                        <span className="text-sm font-bold text-blue-400">${(summary.total_cost_gcp || 756.80).toFixed(2)}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: `${((summary.total_cost_gcp || 756.80) / summary.total_cost_aws) * 100}%` }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">{Math.round(((summary.total_cost_gcp || 756.80) / summary.total_cost_aws) * 100)}%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Azure */}
                                <div className="animate-fade-in" style={{ animationDelay: '300ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-sky-500 shadow-lg shadow-sky-500/30"></div>
                                            <span className="text-sm font-medium text-white">Microsoft Azure</span>
                                        </div>
                                        <span className="text-sm font-bold text-sky-400">${(summary.total_cost_azure || 823.40).toFixed(2)}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-sky-600 to-sky-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: `${((summary.total_cost_azure || 823.40) / summary.total_cost_aws) * 100}%` }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">{Math.round(((summary.total_cost_azure || 823.40) / summary.total_cost_aws) * 100)}%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Savings Summary Card */}
                    <div className="ta-card hover-glow">
                        <div className="ta-card-header">
                            <h3 className="ta-card-title flex items-center gap-2">
                                <div className="stat-card-icon stat-card-icon-success">
                                    <TrendingUp size={18} />
                                </div>
                                Resumo de Economia
                            </h3>
                        </div>
                        <div className="ta-card-body">
                            <div className="text-center py-4 mb-4 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 rounded-xl border border-emerald-500/20">
                                <div className="text-5xl font-extrabold text-emerald-400 mb-1">
                                    {summary.savings_percentage_avg}%
                                </div>
                                <p className="text-sm text-emerald-300/70">de economia média</p>
                            </div>

                            <div className="space-y-3 mb-4">
                                <div className="flex justify-between items-center p-3 bg-white/[0.03] rounded-lg hover:bg-white/[0.05] transition-colors">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                                        <span className="text-sm text-gray-400">vs AWS</span>
                                    </div>
                                    <span className="text-sm font-bold text-emerald-400">
                                        +${summary.savings_vs_aws.toFixed(2)}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center p-3 bg-white/[0.03] rounded-lg hover:bg-white/[0.05] transition-colors">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                                        <span className="text-sm text-gray-400">vs GCP</span>
                                    </div>
                                    <span className="text-sm font-bold text-emerald-400">
                                        +${(summary.savings_vs_gcp || 509.30).toFixed(2)}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center p-3 bg-white/[0.03] rounded-lg hover:bg-white/[0.05] transition-colors">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-sky-500"></div>
                                        <span className="text-sm text-gray-400">vs Azure</span>
                                    </div>
                                    <span className="text-sm font-bold text-emerald-400">
                                        +${(summary.savings_vs_azure || 575.90).toFixed(2)}
                                    </span>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-white/10 grid grid-cols-2 gap-3">
                                <div className="text-center p-3 bg-white/[0.02] rounded-lg">
                                    <Clock size={18} className="mx-auto text-blue-400 mb-1" />
                                    <span className="block text-lg font-bold text-white">{summary.total_gpu_hours}h</span>
                                    <span className="block text-[10px] text-gray-500 uppercase">GPU Hours</span>
                                </div>
                                <div className="text-center p-3 bg-white/[0.02] rounded-lg">
                                    <Server size={18} className="mx-auto text-purple-400 mb-1" />
                                    <span className="block text-lg font-bold text-white">{summary.machines_used}</span>
                                    <span className="block text-[10px] text-gray-500 uppercase">Máquinas</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Usage Breakdown Table */}
                <div className="ta-card hover-glow mt-6">
                    <div className="ta-card-header">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="stat-card-icon bg-blue-500/10 text-blue-400">
                                    <Calculator size={18} />
                                </div>
                                <div>
                                    <h3 className="ta-card-title">Detalhamento por Máquina</h3>
                                    <p className="text-sm text-gray-400">Análise de uso e economia por recurso</p>
                                </div>
                            </div>
                            <button className="ta-btn ta-btn-ghost ta-btn-sm">
                                <Calculator size={16} />
                                Exportar CSV
                            </button>
                        </div>
                    </div>
                    <div className="ta-card-body">
                        <div className="overflow-x-auto">
                            <table className="ta-table">
                                <thead>
                                    <tr>
                                        <th>Recurso</th>
                                        <th>Horas</th>
                                        <th>Custo Dumont</th>
                                        <th>Custo AWS</th>
                                        <th>Economia</th>
                                        <th>%</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(data?.breakdown || DEMO_DATA.breakdown).map((item, idx) => (
                                        <tr key={idx} className="animate-fade-in hover:bg-white/[0.02] transition-colors" style={{ animationDelay: `${idx * 50}ms` }}>
                                            <td>
                                                <span className="gpu-badge">{item.name}</span>
                                            </td>
                                            <td>
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 text-xs text-gray-300">
                                                    <Clock size={12} className="text-blue-400" />
                                                    {item.hours}h
                                                </span>
                                            </td>
                                            <td className="font-mono text-emerald-400 font-semibold">${item.cost_dumont.toFixed(2)}</td>
                                            <td className="font-mono text-gray-400">${item.cost_aws.toFixed(2)}</td>
                                            <td className="font-mono text-emerald-400 font-bold">${item.savings.toFixed(2)}</td>
                                            <td>
                                                <span className="ta-badge ta-badge-success">
                                                    {Math.round((item.savings / item.cost_aws) * 100)}%
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Summary Footer */}
                        <div className="mt-4 pt-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-4">
                            <div className="flex items-center gap-6">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                                    <span className="text-xs text-gray-400">Dumont Cloud</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                                    <span className="text-xs text-gray-400">AWS (Comparação)</span>
                                </div>
                            </div>
                            <div className="text-xs text-gray-500">
                                Total de {(data?.breakdown || DEMO_DATA.breakdown).reduce((sum, item) => sum + item.hours, 0)} horas de GPU utilizadas
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
