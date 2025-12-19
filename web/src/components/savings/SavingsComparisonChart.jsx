import { BarChart3, Cloud } from 'lucide-react'

export default function SavingsComparisonChart({ data, loading }) {
    if (loading || !data) {
        return <div className="savings-comparison-chart skeleton" />
    }

    const providers = [
        { name: 'Dumont', value: data.total_cost_dumont, color: '#22c55e', logo: <Cloud size={14} /> },
        { name: 'AWS', value: data.total_cost_aws, color: '#ff9900' },
        { name: 'GCP', value: data.total_cost_gcp, color: '#4285f4' },
        { name: 'Azure', value: data.total_cost_azure, color: '#0078d4' }
    ]

    const maxValue = Math.max(...providers.map(p => p.value))

    return (
        <div className="savings-comparison-chart">
            <div className="chart-header">
                <h3>
                    <BarChart3 size={18} />
                    Comparação com Cloud Providers
                </h3>
            </div>

            <div className="chart-body">
                {providers.map(p => (
                    <div key={p.name} className="provider-row">
                        <div className="provider-label">
                            {p.logo || <div className="provider-dot" style={{ background: p.color }} />}
                            <span>{p.name}</span>
                        </div>
                        <div className="bar-container">
                            <div 
                                className="bar" 
                                style={{ 
                                    width: `${maxValue > 0 ? (p.value / maxValue) * 100 : 0}%`,
                                    background: p.color 
                                }}
                            />
                            <span className="value">${p.value.toFixed(2)}</span>
                        </div>
                    </div>
                ))}
            </div>

            <div className="chart-footer">
                <p>Economia média: <strong>{data.savings_percentage_avg}%</strong> | Economia total: <strong>${data.savings_vs_aws.toFixed(2)}</strong></p>
            </div>

            <style jsx>{`
                .savings-comparison-chart {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                .chart-header h3 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .chart-body {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }
                .provider-row {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                }
                .provider-label {
                    width: 80px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 13px;
                    color: #9ca3af;
                }
                .provider-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                }
                .bar-container {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                .bar {
                    height: 24px;
                    border-radius: 4px;
                    transition: width 1s ease-out;
                    min-width: 4px;
                }
                .value {
                    font-size: 13px;
                    font-weight: 600;
                    color: #fff;
                    font-family: monospace;
                }
                .chart-footer {
                    margin-top: 10px;
                    padding-top: 16px;
                    border-top: 1px solid #30363d;
                    text-align: center;
                }
                .chart-footer p {
                    font-size: 13px;
                    color: #9ca3af;
                    margin: 0;
                }
                .chart-footer strong { color: #22c55e; }

                .skeleton {
                    min-height: 200px;
                    background: linear-gradient(90deg, #1c211c 25%, #2a352a 50%, #1c211c 75%);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s infinite;
                }
                @keyframes shimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
            `}</style>
        </div>
    )
}

