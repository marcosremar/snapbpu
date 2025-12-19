import { TrendingUp, BarChart3 } from 'lucide-react'
import { Line } from 'react-chartjs-2'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip as ChartTooltip,
    Legend,
    Filler,
} from 'chart.js'

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    ChartTooltip,
    Legend,
    Filler
)

export default function SavingsHistoryGraph({ data, loading }) {
    if (loading || !data) {
        return <div className="savings-history-graph skeleton" />
    }

    const history = data.history || []
    
    const chartData = {
        labels: history.map(h => h.month),
        datasets: [
            {
                label: 'Economia ($)',
                data: history.map(h => h.savings),
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: '#22c55e',
            },
            {
                label: 'AWS ($)',
                data: history.map(h => h.aws),
                borderColor: '#ff9900',
                borderDash: [5, 5],
                fill: false,
                tension: 0.4,
                pointRadius: 0,
            }
        ]
    }

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#9ca3af', usePointStyle: true, boxWidth: 6, padding: 20 }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`
                }
            }
        },
        scales: {
            y: {
                ticks: { color: '#6b7280', font: { size: 10 }, callback: (v) => `$${v}` },
                grid: { color: '#1f2937' }
            },
            x: {
                ticks: { color: '#6b7280', font: { size: 10 } },
                grid: { display: false }
            }
        }
    }

    const totalYear = history.reduce((acc, curr) => acc + curr.savings, 0)

    return (
        <div className="savings-history-graph">
            <div className="graph-header">
                <h3>
                    <TrendingUp size={18} />
                    Histórico de Economia
                </h3>
            </div>

            <div className="chart-container" style={{ height: '220px' }}>
                <Line data={chartData} options={chartOptions} />
            </div>

            <div className="graph-footer">
                <p>Total economizado no período: <strong>${totalYear.toFixed(2)}</strong></p>
            </div>

            <style jsx>{`
                .savings-history-graph {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                .graph-header h3 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .graph-footer {
                    text-align: center;
                    font-size: 13px;
                    color: #9ca3af;
                    padding-top: 10px;
                    border-top: 1px solid #30363d;
                }
                .graph-footer strong { color: #22c55e; }

                .skeleton {
                    min-height: 300px;
                    background: linear-gradient(90deg, #1c211c 25%, #2a352a 50%, #1c211c 75%);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s infinite;
                }
            `}</style>
        </div>
    )
}

