import { useState } from 'react'
import { X, ChevronRight, ChevronLeft, Rocket, Cpu, Shield, Zap, Sparkles, CheckCircle2 } from 'lucide-react'

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

    const userName = user?.username?.split('@')[0] || 'usuário'

    return (
        <div className="onboarding-overlay" onClick={onClose}>
            <div className="onboarding-modal" onClick={e => e.stopPropagation()}>
                {/* Decorative background elements */}
                <div className="modal-glow"></div>
                <div className="modal-grid"></div>

                <button className="close-btn" onClick={onClose} title="Fechar">
                    <X size={18} />
                </button>

                {/* Progress indicator */}
                <div className="onboarding-progress">
                    {[...Array(totalSteps)].map((_, i) => (
                        <div key={i} className="progress-step">
                            <div className={`progress-dot ${step > i ? 'completed' : ''} ${step === i + 1 ? 'active' : ''}`}>
                                {step > i + 1 ? <CheckCircle2 size={14} /> : <span>{i + 1}</span>}
                            </div>
                            {i < totalSteps - 1 && <div className={`progress-line ${step > i + 1 ? 'completed' : ''}`} />}
                        </div>
                    ))}
                </div>

                <div className="onboarding-content">
                    {step === 1 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-green">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <div className="icon-ring delay-2"></div>
                                <Rocket size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Bem-vindo à <span className="highlight">Dumont Cloud</span></h2>
                                <p className="welcome-name">{userName}!</p>
                                <p className="description">
                                    Estamos felizes em ter você aqui. Vamos configurar seu ambiente de
                                    desenvolvimento GPU em menos de <strong>2 minutos</strong>.
                                </p>
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-purple">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <Sparkles size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Economize até <span className="highlight-purple">89%</span> em GPU</h2>
                                <p className="description">
                                    Nossa plataforma usa instâncias spot inteligentes com auto-hibernação.
                                    Você paga apenas pelo tempo que realmente usar.
                                </p>
                            </div>
                            <div className="feature-cards">
                                <div className="feature-card">
                                    <div className="feature-icon"><Zap size={20} /></div>
                                    <div className="feature-text">
                                        <strong>Auto-hibernação</strong>
                                        <span>Desliga em 3 min de inatividade</span>
                                    </div>
                                </div>
                                <div className="feature-card">
                                    <div className="feature-icon"><Shield size={20} /></div>
                                    <div className="feature-text">
                                        <strong>Snapshots automáticos</strong>
                                        <span>Seus dados sempre seguros</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-blue">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <Cpu size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Escolha sua <span className="highlight-blue">GPU Ideal</span></h2>
                                <p className="description">
                                    Não sabe qual GPU escolher? Use nosso <strong>AI Advisor</strong>.
                                    Ele analisa seu projeto e recomenda a melhor máquina para seu bolso.
                                </p>
                            </div>
                            <div className="gpu-preview">
                                <div className="gpu-chip">RTX 4090</div>
                                <div className="gpu-chip">A100</div>
                                <div className="gpu-chip">H100</div>
                                <div className="gpu-chip">RTX 3090</div>
                            </div>
                        </div>
                    )}

                    {step === 4 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-green success">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <div className="icon-ring delay-2"></div>
                                <CheckCircle2 size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Tudo <span className="highlight">Pronto!</span></h2>
                                <p className="description">
                                    Agora você pode criar sua primeira máquina e começar a desenvolver
                                    diretamente no VS Code pelo browser.
                                </p>
                            </div>
                            <button className="finish-btn" onClick={handleFinish}>
                                <Rocket size={20} />
                                <span>Vamos Começar!</span>
                            </button>
                        </div>
                    )}
                </div>

                {step < totalSteps && (
                    <div className="onboarding-footer">
                        <button className="skip-link" onClick={handleSkip}>Pular</button>
                        <div className="nav-buttons">
                            {step > 1 && (
                                <button className="back-btn" onClick={prevStep}>
                                    <ChevronLeft size={18} />
                                    Voltar
                                </button>
                            )}
                            <button className="next-btn" onClick={nextStep}>
                                {step === 1 ? 'Começar' : 'Próximo'}
                                <ChevronRight size={18} />
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <style jsx>{`
                .onboarding-overlay {
                    position: fixed;
                    inset: 0;
                    background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.8) 0%, rgba(0, 0, 0, 0.95) 100%);
                    backdrop-filter: blur(12px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1500;
                    padding: 20px;
                    cursor: pointer;
                }

                .onboarding-modal {
                    background: linear-gradient(145deg, #1a1f2e 0%, #0f1419 100%);
                    border: 1px solid rgba(34, 197, 94, 0.3);
                    border-radius: 24px;
                    width: 100%;
                    max-width: 520px;
                    padding: 48px;
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    gap: 32px;
                    box-shadow:
                        0 0 0 1px rgba(255, 255, 255, 0.05),
                        0 25px 50px -12px rgba(0, 0, 0, 0.8),
                        0 0 100px -20px rgba(34, 197, 94, 0.3);
                    overflow: hidden;
                    cursor: default;
                }

                .modal-glow {
                    position: absolute;
                    top: -50%;
                    left: -50%;
                    width: 200%;
                    height: 200%;
                    background: radial-gradient(circle at 30% 30%, rgba(34, 197, 94, 0.08) 0%, transparent 50%);
                    pointer-events: none;
                    animation: glowPulse 6s ease-in-out infinite;
                }

                .modal-grid {
                    position: absolute;
                    inset: 0;
                    background-image:
                        linear-gradient(rgba(34, 197, 94, 0.03) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(34, 197, 94, 0.03) 1px, transparent 1px);
                    background-size: 40px 40px;
                    pointer-events: none;
                    opacity: 0.5;
                }

                @keyframes glowPulse {
                    0%, 100% { opacity: 0.5; transform: translate(0, 0); }
                    50% { opacity: 0.8; transform: translate(5%, 5%); }
                }

                .close-btn {
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    color: rgba(255, 255, 255, 0.5);
                    cursor: pointer;
                    transition: all 0.2s ease;
                    padding: 10px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10;
                }

                .close-btn:hover {
                    background: rgba(239, 68, 68, 0.2);
                    border-color: rgba(239, 68, 68, 0.5);
                    color: #ef4444;
                    transform: scale(1.05);
                }

                /* Progress Steps */
                .onboarding-progress {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0;
                    position: relative;
                    z-index: 1;
                }

                .progress-step {
                    display: flex;
                    align-items: center;
                }

                .progress-dot {
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.05);
                    border: 2px solid rgba(255, 255, 255, 0.1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: 600;
                    color: rgba(255, 255, 255, 0.3);
                    transition: all 0.3s ease;
                }

                .progress-dot.active {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    border-color: #22c55e;
                    color: white;
                    box-shadow: 0 0 20px rgba(34, 197, 94, 0.5);
                    transform: scale(1.1);
                }

                .progress-dot.completed {
                    background: rgba(34, 197, 94, 0.2);
                    border-color: #22c55e;
                    color: #22c55e;
                }

                .progress-line {
                    width: 60px;
                    height: 2px;
                    background: rgba(255, 255, 255, 0.1);
                    transition: all 0.3s ease;
                }

                .progress-line.completed {
                    background: linear-gradient(90deg, #22c55e, #16a34a);
                }

                /* Content */
                .onboarding-content {
                    position: relative;
                    z-index: 1;
                    min-height: 320px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .step-content {
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 24px;
                    width: 100%;
                }

                /* Icon Containers with rings */
                .icon-container {
                    position: relative;
                    width: 100px;
                    height: 100px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 8px;
                }

                .icon-container svg {
                    position: relative;
                    z-index: 2;
                }

                .icon-ring {
                    position: absolute;
                    inset: 0;
                    border-radius: 50%;
                    border: 2px solid currentColor;
                    opacity: 0.2;
                    animation: ringPulse 2s ease-out infinite;
                }

                .icon-ring.delay-1 {
                    animation-delay: 0.5s;
                }

                .icon-ring.delay-2 {
                    animation-delay: 1s;
                }

                @keyframes ringPulse {
                    0% { transform: scale(0.8); opacity: 0.4; }
                    100% { transform: scale(1.4); opacity: 0; }
                }

                .icon-green { color: #22c55e; }
                .icon-purple { color: #a855f7; }
                .icon-blue { color: #3b82f6; }

                .icon-green.success .icon-ring {
                    animation: successRing 1.5s ease-out infinite;
                }

                @keyframes successRing {
                    0% { transform: scale(0.8); opacity: 0.6; }
                    100% { transform: scale(1.6); opacity: 0; }
                }

                /* Text Content */
                .text-content {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                h2 {
                    font-size: 28px;
                    font-weight: 700;
                    margin: 0;
                    color: #ffffff;
                    line-height: 1.2;
                }

                .highlight {
                    background: linear-gradient(135deg, #22c55e, #4ade80);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .highlight-purple {
                    background: linear-gradient(135deg, #a855f7, #c084fc);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .highlight-blue {
                    background: linear-gradient(135deg, #3b82f6, #60a5fa);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .welcome-name {
                    font-size: 32px;
                    font-weight: 800;
                    color: #ffffff;
                    margin: -8px 0 8px 0;
                }

                .description {
                    font-size: 16px;
                    color: rgba(255, 255, 255, 0.7);
                    line-height: 1.7;
                    margin: 0;
                    max-width: 400px;
                }

                .description strong {
                    color: #ffffff;
                }

                /* Feature Cards */
                .feature-cards {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    width: 100%;
                    margin-top: 8px;
                }

                .feature-card {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    padding: 16px 20px;
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    text-align: left;
                    transition: all 0.2s ease;
                }

                .feature-card:hover {
                    background: rgba(34, 197, 94, 0.05);
                    border-color: rgba(34, 197, 94, 0.2);
                    transform: translateX(4px);
                }

                .feature-icon {
                    width: 40px;
                    height: 40px;
                    border-radius: 10px;
                    background: rgba(34, 197, 94, 0.15);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #22c55e;
                    flex-shrink: 0;
                }

                .feature-text {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }

                .feature-text strong {
                    font-size: 14px;
                    font-weight: 600;
                    color: #ffffff;
                }

                .feature-text span {
                    font-size: 13px;
                    color: rgba(255, 255, 255, 0.5);
                }

                /* GPU Preview Chips */
                .gpu-preview {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    justify-content: center;
                    margin-top: 8px;
                }

                .gpu-chip {
                    padding: 8px 16px;
                    background: rgba(59, 130, 246, 0.1);
                    border: 1px solid rgba(59, 130, 246, 0.3);
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 600;
                    color: #60a5fa;
                    transition: all 0.2s ease;
                }

                .gpu-chip:hover {
                    background: rgba(59, 130, 246, 0.2);
                    transform: translateY(-2px);
                }

                /* Footer Navigation */
                .onboarding-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    position: relative;
                    z-index: 1;
                    padding-top: 8px;
                    border-top: 1px solid rgba(255, 255, 255, 0.05);
                }

                .nav-buttons {
                    display: flex;
                    gap: 12px;
                }

                .skip-link {
                    background: transparent;
                    border: none;
                    color: rgba(255, 255, 255, 0.4);
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    padding: 10px 16px;
                    border-radius: 8px;
                }

                .skip-link:hover {
                    color: rgba(255, 255, 255, 0.7);
                    background: rgba(255, 255, 255, 0.05);
                }

                .back-btn {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    color: rgba(255, 255, 255, 0.7);
                    padding: 12px 20px;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 14px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .back-btn:hover {
                    background: rgba(255, 255, 255, 0.1);
                    color: #ffffff;
                }

                .next-btn {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    color: white;
                    border: none;
                    padding: 12px 28px;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 14px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow:
                        0 4px 14px rgba(34, 197, 94, 0.4),
                        inset 0 1px 0 rgba(255, 255, 255, 0.2);
                }

                .next-btn:hover {
                    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
                    transform: translateY(-2px);
                    box-shadow:
                        0 8px 25px rgba(34, 197, 94, 0.5),
                        inset 0 1px 0 rgba(255, 255, 255, 0.2);
                }

                .finish-btn {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    color: white;
                    border: none;
                    padding: 16px 48px;
                    border-radius: 12px;
                    font-weight: 700;
                    font-size: 16px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    cursor: pointer;
                    margin-top: 16px;
                    transition: all 0.3s ease;
                    box-shadow:
                        0 4px 20px rgba(34, 197, 94, 0.4),
                        inset 0 1px 0 rgba(255, 255, 255, 0.2);
                }

                .finish-btn:hover {
                    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
                    transform: translateY(-3px) scale(1.02);
                    box-shadow:
                        0 10px 30px rgba(34, 197, 94, 0.5),
                        inset 0 1px 0 rgba(255, 255, 255, 0.2);
                }

                /* Animations */
                .animate-in {
                    animation: slideIn 0.5s ease-out;
                }

                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(20px) scale(0.95);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0) scale(1);
                    }
                }
            `}</style>
        </div>
    )
}

