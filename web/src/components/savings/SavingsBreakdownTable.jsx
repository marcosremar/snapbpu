import { List, Download } from 'lucide-react'

export default function SavingsBreakdownTable({ data, loading }) {
    if (loading || !data) {
        return <div className="savings-breakdown-table skeleton" />
    }

    const breakdown = data.breakdown || []

    return (
        <div className="savings-breakdown-table">
            <div className="table-header">
                <h3>
                    <List size={18} />
                    Detalhamento por GPU
                </h3>
                <button className="export-btn">
                    <Download size={14} />
                    Exportar
                </button>
            </div>

            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>GPU</th>
                            <th>Horas</th>
                            <th>Você Pagou</th>
                            <th>AWS</th>
                            <th>Economia</th>
                        </tr>
                    </thead>
                    <tbody>
                        {breakdown.length > 0 ? (
                            breakdown.map((item, i) => (
                                <tr key={i}>
                                    <td><strong>{item.gpu}</strong></td>
                                    <td>{item.hours}h</td>
                                    <td>${item.cost.toFixed(2)}</td>
                                    <td>${item.aws.toFixed(2)}</td>
                                    <td className="savings-cell">${item.savings.toFixed(2)}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="5" className="empty-row">Nenhum dado de uso no período.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <style jsx>{`
                .savings-breakdown-table {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                .table-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .table-header h3 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .export-btn {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    background: transparent;
                    border: 1px solid #30363d;
                    color: #9ca3af;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .export-btn:hover {
                    background: #2a352a;
                    color: #fff;
                    border-color: #4b5563;
                }

                .table-container {
                    overflow-x: auto;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                }
                th {
                    text-align: left;
                    padding: 12px;
                    color: #9ca3af;
                    font-weight: 500;
                    border-bottom: 1px solid #30363d;
                }
                td {
                    padding: 12px;
                    color: #e5e7eb;
                    border-bottom: 1px solid #161a16;
                }
                tr:last-child td {
                    border-bottom: none;
                }
                .savings-cell {
                    color: #22c55e;
                    font-weight: 600;
                }
                .empty-row {
                    text-align: center;
                    color: #4b5563;
                    padding: 40px !important;
                }
                strong { color: #fff; }

                .skeleton {
                    min-height: 200px;
                    background: linear-gradient(90deg, #1c211c 25%, #2a352a 50%, #1c211c 75%);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s infinite;
                }
            `}</style>
        </div>
    )
}

