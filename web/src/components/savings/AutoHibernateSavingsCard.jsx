import { Zap, HelpCircle } from 'lucide-react'

export default function AutoHibernateSavingsCard({ data, loading }) {
    if (loading || !data) {
        return <div className="auto-hibernate-savings-card skeleton" />
    }

    return (
        <div className="auto-hibernate-savings-card">
            <div className="card-header">
                <h3>
                    <Zap size={18} className="icon-purple" />
                    Economia com Auto-Hibernação
                </h3>
                <HelpCircle size={14} className="icon-muted" />
            </div>

            <div className="savings-content">
                <div className="main-stat">
                    <span className="value">${data.auto_hibernate_savings.toFixed(2)}</span>
                    <span className="label">economizados automaticamente</span>
                </div>
                
                <div className="info-box">
                    <p>
                        "Se não hibernasse, você pagaria <strong>${data.auto_hibernate_savings.toFixed(2)}</strong> a mais 
                        este mês por máquinas ociosas"
                    </p>
                </div>
            </div>

            <style jsx>{`
                .auto-hibernate-savings-card {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
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
                    font-size: 16px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .icon-purple { color: #a855f7; }
                .icon-muted { color: #4b5563; cursor: help; }

                .savings-content {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                .main-stat {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    text-align: center;
                }
                .main-stat .value {
                    font-size: 32px;
                    font-weight: 800;
                    color: #a855f7;
                }
                .main-stat .label {
                    font-size: 13px;
                    color: #9ca3af;
                }

                .info-box {
                    background: rgba(168, 85, 247, 0.05);
                    border: 1px dashed rgba(168, 85, 247, 0.3);
                    border-radius: 8px;
                    padding: 16px;
                }
                .info-box p {
                    font-size: 13px;
                    color: #d1d5db;
                    margin: 0;
                    line-height: 1.5;
                    text-align: center;
                }
                .info-box strong { color: #a855f7; }

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

