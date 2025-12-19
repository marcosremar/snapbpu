import { useState } from 'react'
import { Search, Sparkles, Loader2, AlertCircle } from 'lucide-react'
import QuickSuggestions from './QuickSuggestions'
import RecommendationCard from './RecommendationCard'

const API_BASE = ''

export default function GPUAdvisor({ getAuthHeaders }) {
    const [description, setDescription] = useState('')
    const [budget, setBudget] = useState('')
    const [loading, setLoading] = useState(false)
    const [recommendation, setRecommendation] = useState(null)
    const [error, setError] = useState(null)

    const handleAnalyze = async () => {
        if (!description.trim()) return

        setLoading(true)
        setError(null)
        try {
            const headers = getAuthHeaders ? { ...getAuthHeaders(), 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
            
            const res = await fetch(`${API_BASE}/api/v1/advisor/recommend`, {
                method: 'POST',
                headers,
                credentials: 'include',
                body: JSON.stringify({
                    project_description: description,
                    budget_limit: budget ? parseFloat(budget) : null
                })
            })

            if (!res.ok) {
                throw new Error('Falha ao obter recomendação da IA')
            }

            const data = await res.json()
            setRecommendation(data)
        } catch (err) {
            console.error('Advisor error:', err)
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="gpu-advisor-container">
            <div className="advisor-input-panel">
                <div className="input-header">
                    <Sparkles size={20} className="icon-sparkle" />
                    <h2>AI GPU Advisor</h2>
                    <p>Descreva seu projeto e nossa IA recomenda a melhor configuração.</p>
                </div>

                <div className="input-field">
                    <label>O que você pretende rodar?</label>
                    <textarea 
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Ex: Preciso treinar um modelo LLaMA 7B usando LoRA com um dataset de 50k exemplos..."
                        rows={4}
                    />
                </div>

                <div className="input-row">
                    <div className="input-field">
                        <label>Orçamento máx./hora (opcional)</label>
                        <input 
                            type="number" 
                            value={budget}
                            onChange={(e) => setBudget(e.target.value)}
                            placeholder="0.00"
                            step="0.1"
                        />
                    </div>
                    <button 
                        className="analyze-btn" 
                        onClick={handleAnalyze}
                        disabled={loading || !description.trim()}
                    >
                        {loading ? (
                            <Loader2 size={18} className="spinning" />
                        ) : (
                            <Search size={18} />
                        )}
                        Analisar Projeto
                    </button>
                </div>

                <QuickSuggestions onSelect={setDescription} />
            </div>

            <div className="advisor-result-panel">
                {loading ? (
                    <div className="loading-state">
                        <Loader2 size={40} className="spinning" />
                        <p>Nossa IA está analisando seu projeto...</p>
                        <p className="sub">Isso pode levar alguns segundos.</p>
                    </div>
                ) : recommendation ? (
                    <RecommendationCard data={recommendation} />
                ) : error ? (
                    <div className="error-state">
                        <AlertCircle size={40} />
                        <p>{error}</p>
                        <button onClick={handleAnalyze}>Tentar novamente</button>
                    </div>
                ) : (
                    <div className="empty-state">
                        <Sparkles size={48} />
                        <h3>Aguardando sua descrição</h3>
                        <p>Preencha os dados ao lado para receber uma recomendação personalizada.</p>
                    </div>
                )}
            </div>

            <style jsx>{`
                .gpu-advisor-container {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 32px;
                    background: #161a16;
                    border: 1px solid #30363d;
                    border-radius: 16px;
                    padding: 32px;
                    min-height: 500px;
                }

                .advisor-input-panel {
                    display: flex;
                    flex-direction: column;
                    gap: 24px;
                }
                .input-header h2 {
                    font-size: 20px;
                    font-weight: 700;
                    margin: 0 0 4px 0;
                    color: #fff;
                }
                .input-header p {
                    font-size: 14px;
                    color: #9ca3af;
                    margin: 0;
                }
                .icon-sparkle { color: #22c55e; margin-bottom: 8px; }

                .input-field {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .input-field label {
                    font-size: 13px;
                    font-weight: 600;
                    color: #e5e7eb;
                }
                textarea, input {
                    background: #1c211c;
                    border: 1.5px solid #30363d;
                    border-radius: 8px;
                    padding: 12px;
                    color: #fff;
                    font-size: 14px;
                    outline: none;
                    transition: all 0.2s;
                }
                textarea:focus, input:focus {
                    border-color: #22c55e;
                    background: rgba(34, 197, 94, 0.02);
                }

                .input-row {
                    display: flex;
                    align-items: flex-end;
                    gap: 16px;
                }
                .input-row .input-field { flex: 1; }

                .analyze-btn {
                    background: #22c55e;
                    color: #000;
                    border: none;
                    height: 46px;
                    padding: 0 24px;
                    border-radius: 8px;
                    font-weight: 700;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .analyze-btn:hover:not(:disabled) {
                    background: #4ade80;
                    transform: translateY(-1px);
                }
                .analyze-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .advisor-result-panel {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }

                .loading-state, .empty-state, .error-state {
                    text-align: center;
                    color: #9ca3af;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 16px;
                }
                .spinning { animation: spin 1s linear infinite; }
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

                .empty-state h3 { color: #fff; margin: 0; }
                .sub { font-size: 12px; opacity: 0.7; }

                @media (max-width: 900px) {
                    .gpu-advisor-container {
                        grid-template-columns: 1fr;
                    }
                }
            `}</style>
        </div>
    )
}

