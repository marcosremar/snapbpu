import { useState } from 'react'
import { X, ChevronRight, Rocket, Cpu, Shield, Zap, Sparkles } from 'lucide-react'

export default function OnboardingWizard({ user, onClose, onComplete }) {
    const [step, setStep] = useState(1)
    const totalSteps = 4

    const nextStep = () => setStep(s => Math.min(s + 1, totalSteps))
    const prevStep = () => setStep(s => Math.max(s - 1, 1))

    const handleSkip = () => {
        if (onComplete) {
            onComplete()
        }
        if (onClose) {
            onClose()
        }
    }

    const handleFinish = () => {
        if (onComplete) {
            onComplete()
        }
        if (onClose) {
            onClose()
        }
    }

    return (
        <div className="onboarding-overlay" onClick={onClose}>
            <div className="onboarding-modal" onClick={e => e.stopPropagation()}>
                <button className="close-btn" onClick={onClose}><X size={20} /></button>
                
                <div className="onboarding-progress">
                    {[...Array(totalSteps)].map((_, i) => (
                        <div 
                            key={i} 
                            className={`progress-dot ${step > i ? 'active' : ''}`}
                        />
                    ))}
                </div>

                <div className="onboarding-content">
                    {step === 1 && (
                        <div className="step-content animate-in">
                            <div className="icon-wrap-green"><Rocket size={48} /></div>
                            <h2>Bem-vindo à Dumont Cloud, {user?.username?.split('@')[0]}!</h2>
                            <p>Estamos felizes em ter você aqui. Vamos configurar seu ambiente de desenvolvimento GPU em menos de 2 minutos.</p>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="step-content animate-in">
                            <div className="icon-wrap-purple"><Sparkles size={48} /></div>
                            <h2>Economize até 89% em GPU</h2>
                            <p>Nossa plataforma usa instâncias spot inteligentes com auto-hibernação. Você paga apenas pelo tempo que realmente usar a GPU.</p>
                            <div className="feature-mini-list">
                                <div className="feature-mini-item">
                                    <Zap size={16} />
                                    <span>Auto-hibernação em 3 min de inatividade</span>
                                </div>
                                <div className="feature-mini-item">
                                    <Shield size={16} />
                                    <span>Snapshots automáticos e seguros</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="step-content animate-in">
                            <div className="icon-wrap-blue"><Cpu size={48} /></div>
                            <h2>Escolha sua GPU Ideal</h2>
                            <p>Não sabe qual GPU escolher? Use nosso <strong>AI Advisor</strong>. Ele analisa seu projeto e recomenda a melhor máquina para seu bolso.</p>
                        </div>
                    )}

                    {step === 4 && (
                        <div className="step-content animate-in">
                            <div className="icon-wrap-green"><Shield size={48} /></div>
                            <h2>Tudo Pronto!</h2>
                            <p>Agora você pode criar sua primeira máquina e começar a desenvolver diretamente no VS Code pelo browser.</p>
                            <button className="finish-btn" onClick={handleFinish}>
                                Vamos Começar!
                            </button>
                        </div>
                    )}
                </div>

                {step < totalSteps && (
                    <div className="onboarding-footer">
                        <button className="skip-link" onClick={handleSkip}>Pular tudo</button>
                        <button className="next-btn" onClick={nextStep}>
                            {step === 1 ? 'Começar' : 'Próximo'}
                            <ChevronRight size={18} />
                        </button>
                    </div>
                )}
            </div>

            <style jsx>{`
                .onboarding-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.85);
                    backdrop-filter: blur(10px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 3000;
                    padding: 20px;
                }
                .onboarding-modal {
                    background: var(--bg-secondary);
                    border: 2px solid var(--border);
                    border-radius: 16px;
                    width: 100%;
                    max-width: 500px;
                    padding: 40px;
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    gap: 32px;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
                }
                .close-btn {
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: transparent;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                    transition: all 0.2s;
                    padding: 4px;
                    border-radius: 4px;
                }
                .close-btn:hover {
                    background: var(--bg-tertiary);
                    color: var(--text-primary);
                }
                .onboarding-progress {
                    display: flex;
                    gap: 8px;
                    justify-content: center;
                }
                .progress-dot {
                    flex: 1;
                    height: 4px;
                    background: var(--bg-tertiary);
                    border-radius: 2px;
                    transition: all 0.3s ease;
                }
                .progress-dot.active {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    box-shadow: 0 0 8px rgba(34, 197, 94, 0.4);
                }

                .step-content {
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 20px;
                }
                .icon-wrap-green { 
                    color: #22c55e; 
                    filter: drop-shadow(0 0 8px rgba(34, 197, 94, 0.3));
                }
                .icon-wrap-purple { 
                    color: #a855f7; 
                    filter: drop-shadow(0 0 8px rgba(168, 85, 247, 0.3));
                }
                .icon-wrap-blue { 
                    color: #3b82f6; 
                    filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.3));
                }

                h2 { 
                    font-size: 24px; 
                    font-weight: 700; 
                    margin: 0; 
                    background: linear-gradient(135deg, #22c55e, #16a34a);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
                p { 
                    font-size: 16px; 
                    color: var(--text-secondary); 
                    line-height: 1.6; 
                    margin: 0; 
                }

                .feature-mini-list {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    text-align: left;
                    margin-top: 10px;
                    width: 100%;
                }
                .feature-mini-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-size: 14px;
                    color: var(--text-primary);
                    padding: 8px;
                    background: var(--bg-primary);
                    border-radius: 8px;
                    border: 1px solid var(--border);
                }
                .feature-mini-item svg { 
                    color: #22c55e; 
                    flex-shrink: 0;
                }

                .onboarding-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 10px;
                }
                .skip-link {
                    background: transparent;
                    border: none;
                    color: var(--text-muted);
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                .skip-link:hover {
                    color: var(--text-primary);
                    background: var(--bg-tertiary);
                }
                .next-btn {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 14px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    cursor: pointer;
                    transition: all 0.3s;
                    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
                }
                .next-btn:hover {
                    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4);
                }
                .finish-btn {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    color: white;
                    border: none;
                    padding: 14px 40px;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 16px;
                    cursor: pointer;
                    margin-top: 20px;
                    transition: all 0.3s;
                    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
                }
                .finish-btn:hover {
                    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4);
                }

                .animate-in {
                    animation: slideIn 0.4s ease-out;
                }
                @keyframes slideIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    )
}

