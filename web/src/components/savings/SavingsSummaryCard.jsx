import { DollarSign, TrendingUp, PiggyBank, HelpCircle } from 'lucide-react'

export default function SavingsSummaryCard({ data, loading }) {
    if (loading || !data) {
        return <div className="savings-summary-card skeleton" />
    }

    const savingsPercent = data.savings_percentage_avg
    const barWidth = Math.min(Math.max(100 - savingsPercent, 10), 90) // Mínimo 10%, Máximo 90% para Dumont

    return (
        <div className="savings-summary-card">
            <div className="card-header">
                <h3>
                    <PiggyBank size={18} className="icon-green" />
                    Sua Economia Este Mês
                </h3>
                <div className="header-actions">
                    <HelpCircle size={14} className="icon-muted" />
                </div>
            </div>

            <div className="stats-grid">
                <div className="stat-item main">
                    <span className="label">Você pagou</span>
                    <span className="value">${data.total_cost_dumont.toFixed(2)}</span>
                </div>
                <div className="stat-item">
                    <span className="label">AWS pagaria</span>
                    <span className="value">${data.total_cost_aws.toFixed(2)}</span>
                </div>
                <div className="stat-item highlight">
                    <span className="label">Economia ({savingsPercent}%)</span>
                    <span className="value-green">
                        <TrendingUp size={14} />
                        ${data.savings_vs_aws.toFixed(2)}
                    </span>
                </div>
            </div>

            <div className="progress-container">
                <div className="progress-track">
                    <div 
                        className="progress-bar-dumont" 
                        style={{ width: `${barWidth}%` }}
                    >
                        <span>Dumont: {100 - savingsPercent}%</span>
                    </div>
                    <div className="progress-bar-aws" style={{ width: `${100 - barWidth}%` }}>
                        <span>AWS: 100%</span>
                    </div>
                </div>
                <p className="progress-label">Você paga apenas {100 - savingsPercent}% do que pagaria na AWS</p>
            </div>

            <style jsx>{`
                .savings-summary-card {
                    background: var(--bg-primary);
                    border: 2px solid var(--border);
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    transition: all 0.3s;
                    position: relative;
                    overflow: hidden;
                }

                .savings-summary-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                }

                .savings-summary-card:hover {
                    border-color: #22c55e;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 24px rgba(34, 197, 94, 0.2);
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
                    font-size: 18px;
                    font-weight: 700;
                    margin: 0;
                    color: var(--text-primary);
                }

                .icon-green { 
                    color: #22c55e; 
                }

                .icon-muted { 
                    color: var(--text-muted); 
                    cursor: help; 
                }
                
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 16px;
                    border-bottom: 1px solid var(--border);
                    padding-bottom: 20px;
                }

                .stat-item {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .stat-item .label {
                    font-size: 12px;
                    color: var(--text-secondary);
                    font-weight: 500;
                }

                .stat-item .value {
                    font-size: 20px;
                    font-weight: 700;
                    color: var(--text-primary);
                }

                .stat-item.main .value {
                    font-size: 32px;
                    background: linear-gradient(135deg, #22c55e, #16a34a);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .stat-item.highlight {
                    background: rgba(34, 197, 94, 0.1);
                    padding: 12px;
                    border-radius: 8px;
                    margin: -12px;
                }

                .stat-item.highlight .value-green {
                    font-size: 22px;
                    font-weight: 700;
                    color: #22c55e;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }

                .progress-container {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                .progress-track {
                    height: 16px;
                    background: var(--bg-secondary);
                    border-radius: 8px;
                    display: flex;
                    overflow: hidden;
                    position: relative;
                    border: 1px solid var(--border);
                }

                .progress-bar-dumont {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    height: 100%;
                    display: flex;
                    align-items: center;
                    padding-left: 10px;
                    transition: width 0.3s ease;
                }

                .progress-bar-dumont span {
                    font-size: 9px;
                    color: #000;
                    font-weight: 700;
                    white-space: nowrap;
                }

                .progress-bar-aws {
                    background: linear-gradient(135deg, #ff9900 0%, #ff8800 100%);
                    opacity: 0.4;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    padding-right: 10px;
                }

                .progress-bar-aws span {
                    font-size: 9px;
                    color: #fff;
                    font-weight: 700;
                    white-space: nowrap;
                }

                .progress-label {
                    font-size: 13px;
                    color: var(--text-secondary);
                    text-align: center;
                    margin: 0;
                }

                .skeleton {
                    min-height: 200px;
                    background: linear-gradient(90deg, var(--bg-primary) 25%, var(--bg-secondary) 50%, var(--bg-primary) 75%);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s infinite;
                    border-radius: 12px;
                }

                @keyframes shimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
            `}</style>
        </div>
    )
}

