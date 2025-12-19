import { Cpu, DollarSign, Clock, TrendingUp, Sparkles, CheckCircle2 } from 'lucide-react'

export default function RecommendationCard({ data }) {
    if (!data) return null

    return (
        <div className="recommendation-card">
            <div className="rec-header">
                <Sparkles size={20} className="icon-sparkle" />
                <h3>🎯 Recomendação da IA</h3>
            </div>

            <div className="main-recommendation">
                <div className="gpu-badge">
                    <Cpu size={24} />
                    <div className="gpu-info">
                        <span className="gpu-name">{data.recommended_gpu}</span>
                        <span className="gpu-vram">{data.vram_gb}GB VRAM</span>
                    </div>
                    <div className="gpu-price">
                        <span className="price">${data.hourly_price.toFixed(2)}</span>
                        <span className="unit">/hora</span>
                    </div>
                </div>

                <div className="estimates-grid">
                    <div className="est-item">
                        <Clock size={16} />
                        <span>Tempo est.: ~{data.estimated_hours}h</span>
                    </div>
                    <div className="est-item">
                        <DollarSign size={16} />
                        <span>Custo est.: ${data.estimated_total_cost.toFixed(2)}</span>
                    </div>
                    <div className="est-item highlight">
                        <TrendingUp size={16} />
                        <span>Economia: {data.savings_percentage}%</span>
                    </div>
                </div>

                <div className="reasoning">
                    <p>{data.reasoning}</p>
                </div>

                {data.technical_notes && data.technical_notes.length > 0 && (
                    <ul className="notes-list">
                        {data.technical_notes.map((note, i) => (
                            <li key={i}>
                                <CheckCircle2 size={14} />
                                {note}
                            </li>
                        ))}
                    </ul>
                )}

                <button className="cta-btn">
                    Criar Máquina com {data.recommended_gpu}
                </button>
            </div>

            <style jsx>{`
                .recommendation-card {
                    background: linear-gradient(145deg, #1c211c 0%, #141814 100%);
                    border: 1px solid #22c55e;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    box-shadow: 0 10px 30px rgba(34, 197, 94, 0.1);
                }
                .rec-header {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .rec-header h3 {
                    font-size: 18px;
                    font-weight: 700;
                    margin: 0;
                    color: #fff;
                }
                .icon-sparkle { color: #22c55e; }

                .gpu-badge {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    background: rgba(34, 197, 94, 0.1);
                    border: 1px solid rgba(34, 197, 94, 0.2);
                    padding: 16px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }
                .gpu-info {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                }
                .gpu-name {
                    font-size: 18px;
                    font-weight: 800;
                    color: #fff;
                }
                .gpu-vram {
                    font-size: 12px;
                    color: #9ca3af;
                }
                .gpu-price {
                    text-align: right;
                    display: flex;
                    flex-direction: column;
                }
                .price {
                    font-size: 20px;
                    font-weight: 700;
                    color: #22c55e;
                }
                .unit {
                    font-size: 10px;
                    color: #9ca3af;
                }

                .estimates-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                    margin-bottom: 20px;
                }
                .est-item {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 12px;
                    color: #9ca3af;
                    background: #1c211c;
                    padding: 8px;
                    border-radius: 6px;
                    border: 1px solid #30363d;
                }
                .est-item.highlight {
                    color: #22c55e;
                    border-color: rgba(34, 197, 94, 0.3);
                    background: rgba(34, 197, 94, 0.05);
                }

                .reasoning {
                    font-size: 14px;
                    color: #d1d5db;
                    line-height: 1.6;
                    margin-bottom: 20px;
                }

                .notes-list {
                    list-style: none;
                    padding: 0;
                    margin: 0 0 24px 0;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .notes-list li {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 13px;
                    color: #9ca3af;
                }
                .notes-list li svg { color: #22c55e; }

                .cta-btn {
                    width: 100%;
                    background: #22c55e;
                    color: #000;
                    border: none;
                    padding: 12px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .cta-btn:hover {
                    background: #4ade80;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
                }
            `}</style>
        </div>
    )
}

