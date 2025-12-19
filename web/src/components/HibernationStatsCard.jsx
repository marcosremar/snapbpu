import { useState, useEffect } from 'react'
import { Zap, HelpCircle, Clock, DollarSign } from 'lucide-react'

const API_BASE = ''

export default function HibernationStatsCard({ getAuthHeaders }) {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadStats()
    }, [])

    const loadStats = async () => {
        try {
            const headers = getAuthHeaders ? getAuthHeaders() : {}
            const res = await fetch(`${API_BASE}/api/v1/hibernation/stats`, { headers, credentials: 'include' })
            const data = await res.json()
            setStats(data)
        } catch (e) {
            console.error('Error loading hibernation stats:', e)
        } finally {
            setLoading(false)
        }
    }

    if (loading || !stats) {
        return <div className="hibernation-stats-card skeleton" />
    }

    return (
        <div className="hibernation-stats-card">
            <div className="card-header">
                <h3>
                    <Zap size={18} className="icon-purple" />
                    Auto-Hibernação
                </h3>
                <HelpCircle size={14} className="icon-muted" />
            </div>

            <div className="stats-body">
                <p className="summary-text">
                    Este mês suas máquinas hibernaram automaticamente <strong>{stats.total_hibernations} vezes</strong>
                </p>

                <div className="stats-highlight">
                    <div className="stat-box">
                        <DollarSign size={16} className="icon-green" />
                        <div className="stat-info">
                            <span className="value">${stats.total_savings.toFixed(2)}</span>
                            <span className="label">Economizados</span>
                        </div>
                    </div>
                    <div className="stat-box">
                        <Clock size={16} className="icon-blue" />
                        <div className="stat-info">
                            <span className="value">{stats.total_hours_saved}h</span>
                            <span className="label">Evitadas</span>
                        </div>
                    </div>
                </div>

                <div className="info-tip">
                    <p>💡 Máquinas ociosas por mais de 3 min são hibernadas automaticamente para economizar seu saldo.</p>
                </div>
            </div>

            <style jsx>{`
                .hibernation-stats-card {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }
                .card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .card-header h3 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 15px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .icon-purple { color: #a855f7; }
                .icon-muted { color: #4b5563; }

                .summary-text {
                    font-size: 13px;
                    color: #9ca3af;
                    margin: 0 0 16px 0;
                }
                .summary-text strong { color: #fff; }

                .stats-highlight {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-bottom: 16px;
                }
                .stat-box {
                    background: #161a16;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 12px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .stat-info {
                    display: flex;
                    flex-direction: column;
                }
                .stat-info .value {
                    font-size: 16px;
                    font-weight: 700;
                    color: #fff;
                }
                .stat-info .label {
                    font-size: 10px;
                    color: #6b7280;
                    text-transform: uppercase;
                }
                .icon-green { color: #22c55e; }
                .icon-blue { color: #3b82f6; }

                .info-tip {
                    background: rgba(34, 197, 94, 0.05);
                    border-radius: 6px;
                    padding: 10px;
                }
                .info-tip p {
                    font-size: 11px;
                    color: #9ca3af;
                    margin: 0;
                    line-height: 1.4;
                }

                .skeleton {
                    min-height: 180px;
                    background: #1c211c;
                    position: relative;
                    overflow: hidden;
                }
                .skeleton::after {
                    content: "";
                    position: absolute;
                    inset: 0;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
                    animation: shimmer 1.5s infinite;
                }
                @keyframes shimmer {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }
            `}</style>
        </div>
    )
}

