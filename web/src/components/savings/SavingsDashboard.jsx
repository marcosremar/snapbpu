import { useState, useEffect } from 'react'
import SavingsSummaryCard from './SavingsSummaryCard'
import SavingsComparisonChart from './SavingsComparisonChart'
import SavingsBreakdownTable from './SavingsBreakdownTable'
import SavingsHistoryGraph from './SavingsHistoryGraph'
import AutoHibernateSavingsCard from './AutoHibernateSavingsCard'
import { Calendar, RefreshCw } from 'lucide-react'

const API_BASE = ''

export default function SavingsDashboard({ getAuthHeaders }) {
    const [period, setPeriod] = useState('month')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [summary, setSummary] = useState(null)
    const [history, setHistory] = useState(null)
    const [breakdown, setBreakdown] = useState(null)

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
            
            const [summaryRes, historyRes, breakdownRes] = await Promise.all([
                fetch(`${API_BASE}/api/v1/savings/summary?period=${period}`, { headers, credentials: 'include' }),
                fetch(`${API_BASE}/api/v1/savings/history?months=6`, { headers, credentials: 'include' }),
                fetch(`${API_BASE}/api/v1/savings/breakdown?period=${period}`, { headers, credentials: 'include' })
            ])

            if (!summaryRes.ok || !historyRes.ok || !breakdownRes.ok) {
                throw new Error('Erro ao carregar dados do dashboard')
            }

            const [summaryData, historyData, breakdownData] = await Promise.all([
                summaryRes.json(),
                historyRes.json(),
                breakdownRes.json()
            ])

            setSummary(summaryData)
            setHistory(historyData)
            setBreakdown(breakdownData)
        } catch (err) {
            console.error('Error loading savings dashboard:', err)
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="savings-dashboard-v2">
            {/* Header with title */}
            <div className="savings-v2-header">
                <div className="header-title-section">
                    <h2 className="savings-v2-title">Dashboard de Economia</h2>
                    <p className="savings-v2-subtitle">Compare seus custos reais com grandes cloud providers</p>
                </div>
            </div>

            {/* Period tabs */}
            <div className="savings-v2-tabs">
                {periods.map(p => (
                    <button
                        key={p.id}
                        className={`savings-v2-tab ${period === p.id ? 'active' : ''}`}
                        onClick={() => setPeriod(p.id)}
                    >
                        <span className="tab-name">{p.label}</span>
                    </button>
                ))}
                <button 
                    className="savings-v2-refresh" 
                    onClick={loadAllData} 
                    disabled={loading}
                    title="Atualizar dados"
                >
                    <RefreshCw size={16} className={loading ? 'spinning' : ''} />
                </button>
            </div>

            {error && (
                <div className="savings-v2-error">
                    <p>Erro: {error}</p>
                    <button onClick={loadAllData} className="btn-retry">Tentar novamente</button>
                </div>
            )}

            <div className="savings-v2-grid">
                <div className="grid-col-2">
                    <SavingsSummaryCard data={summary} loading={loading} />
                </div>
                <div className="grid-col-1">
                    <AutoHibernateSavingsCard data={summary} loading={loading} />
                </div>
                
                <div className="grid-col-2">
                    <SavingsHistoryGraph data={history} loading={loading} />
                </div>
                <div className="grid-col-1">
                    <SavingsComparisonChart data={summary} loading={loading} />
                </div>

                <div className="grid-col-3">
                    <SavingsBreakdownTable data={breakdown} loading={loading} />
                </div>
            </div>

            <style jsx>{`
                .savings-dashboard-v2 {
                    width: 100%;
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 24px;
                    background: var(--bg-secondary);
                    border-radius: 16px;
                    border: 1px solid var(--border);
                }

                /* Header */
                .savings-v2-header {
                    text-align: center;
                    margin-bottom: 24px;
                }

                .savings-v2-title {
                    font-size: 28px;
                    font-weight: 700;
                    margin: 0 0 8px 0;
                    background: linear-gradient(135deg, #22c55e, #16a34a);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .savings-v2-subtitle {
                    font-size: 14px;
                    color: var(--text-secondary);
                    margin: 0;
                }

                /* Period Tabs */
                .savings-v2-tabs {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 24px;
                    background: var(--bg-primary);
                    padding: 8px;
                    border-radius: 12px;
                    overflow-x: auto;
                    align-items: center;
                }

                .savings-v2-tab {
                    flex: 1;
                    min-width: 100px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 12px 16px;
                    background: transparent;
                    border: 2px solid transparent;
                    border-radius: 8px;
                    color: var(--text-secondary);
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .savings-v2-tab:hover {
                    background: var(--bg-secondary);
                    color: var(--text-primary);
                }

                .savings-v2-tab.active {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    border-color: #22c55e;
                    color: white;
                }

                .savings-v2-refresh {
                    margin-left: auto;
                    padding: 8px;
                    background: transparent;
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    color: var(--text-secondary);
                    cursor: pointer;
                    transition: all 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .savings-v2-refresh:hover:not(:disabled) {
                    background: var(--bg-secondary);
                    color: var(--text-primary);
                    border-color: #22c55e;
                }

                .savings-v2-refresh:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .spinning {
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }

                /* Error Alert */
                .savings-v2-error {
                    background: rgba(239, 68, 68, 0.1);
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    color: #f87171;
                    padding: 16px;
                    border-radius: 8px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 24px;
                }

                .savings-v2-error p {
                    margin: 0;
                }

                .btn-retry {
                    background: #ef4444;
                    color: #fff;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .btn-retry:hover {
                    background: #dc2626;
                }

                /* Grid */
                .savings-v2-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 24px;
                }

                .grid-col-1 { grid-column: span 1; }
                .grid-col-2 { grid-column: span 2; }
                .grid-col-3 { grid-column: span 3; }

                @media (max-width: 1024px) {
                    .savings-dashboard-v2 {
                        padding: 16px;
                    }

                    .savings-v2-grid {
                        grid-template-columns: 1fr;
                    }

                    .grid-col-1, .grid-col-2, .grid-col-3 {
                        grid-column: span 1;
                    }

                    .savings-v2-tabs {
                        flex-wrap: wrap;
                    }

                    .savings-v2-tab {
                        min-width: 80px;
                        font-size: 13px;
                        padding: 10px 12px;
                    }
                }
            `}</style>
        </div>
    )
}

