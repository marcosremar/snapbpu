import { useState, useEffect } from 'react'
import { DollarSign, TrendingUp, Clock, Zap, BarChart3, Calendar, PiggyBank } from 'lucide-react'
import { Line } from 'react-chartjs-2'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js'

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
)

const API_BASE = ''

export default function RealSavingsDashboard({ getAuthHeaders }) {
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [savings, setSavings] = useState(null)
    const [history, setHistory] = useState([])
    const [period, setPeriod] = useState(30)

    useEffect(() => {
        loadData()
    }, [period])

    const loadData = async () => {
        setLoading(true)
        try {
            const headers = getAuthHeaders ? getAuthHeaders() : {}

            const [savingsRes, historyRes] = await Promise.all([
                fetch(`${API_BASE}/api/v1/metrics/savings/real?days=${period}`, {
                    credentials: 'include',
                    headers
                }),
                fetch(`${API_BASE}/api/v1/metrics/savings/history?days=${period}`, {
                    credentials: 'include',
                    headers
                })
            ])

            if (savingsRes.ok) {
                const data = await savingsRes.json()
                setSavings(data)
            }

            if (historyRes.ok) {
                const data = await historyRes.json()
                setHistory(data.history || [])
            }

            setError(null)
        } catch (err) {
            console.error('Error loading real savings:', err)
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const chartData = {
        labels: history.map(h => {
            const date = new Date(h.date)
            return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
        }),
        datasets: [
            {
                label: 'Economia Acumulada ($)',
                data: history.map(h => h.cumulative_savings_usd),
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                fill: true,
                tension: 0.4,
            },
            {
                label: 'Economia Diária ($)',
                data: history.map(h => h.savings_usd),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: false,
                tension: 0.4,
            },
        ]
    }

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#9ca3af', usePointStyle: true }
            },
            tooltip: {
                callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`
                }
            }
        },
        scales: {
            y: {
                ticks: { color: '#9ca3af', callback: (v) => `$${v}` },
                grid: { color: '#374151' }
            },
            x: {
                ticks: { color: '#9ca3af' },
                grid: { display: false }
            }
        }
    }

    if (loading) {
        return (
            <div className="savings-dashboard loading">
                <div className="spinner" />
                <p>Carregando economia...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="savings-dashboard error">
                <p>Erro ao carregar: {error}</p>
                <button onClick={loadData}>Tentar novamente</button>
            </div>
        )
    }

    const summary = savings?.summary || {}

    return (
        <div className="savings-dashboard">
            {/* Header */}
            <div className="savings-header">
                <div className="savings-title">
                    <PiggyBank className="icon" size={24} />
                    <h2>Economia Real com Auto-Hibernação</h2>
                </div>
                <div className="period-selector">
                    {[7, 30, 90].map(days => (
                        <button
                            key={days}
                            className={period === days ? 'active' : ''}
                            onClick={() => setPeriod(days)}
                        >
                            {days}d
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary Cards */}
            <div className="savings-cards">
                <div className="savings-card green">
                    <div className="card-icon">
                        <DollarSign size={28} />
                    </div>
                    <div className="card-content">
                        <span className="card-value">${summary.total_savings_usd || 0}</span>
                        <span className="card-label">Total Economizado</span>
                    </div>
                </div>

                <div className="savings-card blue">
                    <div className="card-icon">
                        <Clock size={28} />
                    </div>
                    <div className="card-content">
                        <span className="card-value">{summary.total_hours_saved || 0}h</span>
                        <span className="card-label">Horas Economizadas</span>
                    </div>
                </div>

                <div className="savings-card purple">
                    <div className="card-icon">
                        <Zap size={28} />
                    </div>
                    <div className="card-content">
                        <span className="card-value">{summary.hibernation_count || 0}</span>
                        <span className="card-label">Hibernações</span>
                    </div>
                </div>

                <div className="savings-card yellow">
                    <div className="card-icon">
                        <TrendingUp size={28} />
                    </div>
                    <div className="card-content">
                        <span className="card-value">${summary.projected_monthly_savings_usd || 0}</span>
                        <span className="card-label">Projeção Mensal</span>
                    </div>
                </div>
            </div>

            {/* Chart */}
            {history.length > 0 && (
                <div className="savings-chart">
                    <h3>
                        <BarChart3 size={18} />
                        Histórico de Economia
                    </h3>
                    <div className="chart-container" style={{ height: '250px' }}>
                        <Line data={chartData} options={chartOptions} />
                    </div>
                </div>
            )}

            {/* GPU Breakdown */}
            {savings?.gpu_breakdown && Object.keys(savings.gpu_breakdown).length > 0 && (
                <div className="gpu-breakdown">
                    <h3>
                        <Calendar size={18} />
                        Economia por GPU
                    </h3>
                    <div className="breakdown-list">
                        {Object.entries(savings.gpu_breakdown).map(([gpu, data]) => (
                            <div key={gpu} className="breakdown-item">
                                <span className="gpu-name">{gpu}</span>
                                <div className="breakdown-stats">
                                    <span className="stat">{data.hibernations} hibernações</span>
                                    <span className="stat">{data.hours_saved.toFixed(1)}h</span>
                                    <span className="stat green">${data.usd_saved.toFixed(2)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Empty State */}
            {summary.hibernation_count === 0 && (
                <div className="empty-state">
                    <PiggyBank size={48} />
                    <h3>Nenhuma hibernação registrada</h3>
                    <p>
                        Quando a auto-hibernação desligar máquinas ociosas,
                        a economia será exibida aqui.
                    </p>
                </div>
            )}

            <style jsx>{`
        .savings-dashboard {
          background: #161a16;
          border: 1px solid #30363d;
          border-radius: 12px;
          padding: 20px;
        }
        
        .savings-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }
        
        .savings-title {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .savings-title .icon {
          color: #22c55e;
        }
        
        .savings-title h2 {
          color: #fff;
          font-size: 18px;
          font-weight: 600;
          margin: 0;
        }
        
        .period-selector {
          display: flex;
          gap: 4px;
        }
        
        .period-selector button {
          padding: 6px 12px;
          border: 1px solid #30363d;
          background: #1c211c;
          color: #9ca3af;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
        }
        
        .period-selector button.active {
          background: #22c55e;
          color: #000;
          border-color: #22c55e;
        }
        
        .savings-cards {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 20px;
        }
        
        @media (max-width: 900px) {
          .savings-cards {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        
        .savings-card {
          background: #1c211c;
          border: 1px solid #30363d;
          border-radius: 10px;
          padding: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .savings-card.green .card-icon { color: #22c55e; }
        .savings-card.blue .card-icon { color: #3b82f6; }
        .savings-card.purple .card-icon { color: #a855f7; }
        .savings-card.yellow .card-icon { color: #eab308; }
        
        .card-content {
          display: flex;
          flex-direction: column;
        }
        
        .card-value {
          font-size: 22px;
          font-weight: 700;
          color: #fff;
        }
        
        .card-label {
          font-size: 11px;
          color: #9ca3af;
        }
        
        .savings-chart {
          background: #1c211c;
          border: 1px solid #30363d;
          border-radius: 10px;
          padding: 16px;
          margin-bottom: 16px;
        }
        
        .savings-chart h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #fff;
          font-size: 14px;
          margin: 0 0 12px 0;
        }
        
        .gpu-breakdown {
          background: #1c211c;
          border: 1px solid #30363d;
          border-radius: 10px;
          padding: 16px;
        }
        
        .gpu-breakdown h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #fff;
          font-size: 14px;
          margin: 0 0 12px 0;
        }
        
        .breakdown-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .breakdown-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px;
          background: #161a16;
          border-radius: 6px;
        }
        
        .gpu-name {
          color: #fff;
          font-weight: 500;
          font-size: 13px;
        }
        
        .breakdown-stats {
          display: flex;
          gap: 16px;
        }
        
        .stat {
          color: #9ca3af;
          font-size: 12px;
        }
        
        .stat.green {
          color: #22c55e;
          font-weight: 600;
        }
        
        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: #6b7280;
        }
        
        .empty-state h3 {
          color: #9ca3af;
          margin: 12px 0 8px;
        }
        
        .empty-state p {
          font-size: 13px;
          max-width: 300px;
          margin: 0 auto;
        }
        
        .loading, .error {
          text-align: center;
          padding: 40px;
          color: #9ca3af;
        }
        
        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #30363d;
          border-top-color: #22c55e;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto 12px;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
        </div>
    )
}
