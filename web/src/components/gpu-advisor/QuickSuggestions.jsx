export default function QuickSuggestions({ onSelect }) {
    const suggestions = [
        "Treinar LLaMA 7B com LoRA",
        "Inferência Stable Diffusion XL",
        "Fine-tuning de BERT",
        "Treinamento de GPT-2",
        "Whisper Inference",
        "Clone do Midjourney"
    ]

    return (
        <div className="quick-suggestions">
            <span className="label">⚡ Sugestões Rápidas:</span>
            <div className="chips">
                {suggestions.map(s => (
                    <button key={s} className="chip" onClick={() => onSelect(s)}>
                        {s}
                    </button>
                ))}
            </div>
            <style jsx>{`
                .quick-suggestions {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .label {
                    font-size: 12px;
                    color: #9ca3af;
                    font-weight: 600;
                }
                .chips {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                }
                .chip {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    color: #e5e7eb;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .chip:hover {
                    border-color: #22c55e;
                    background: rgba(34, 197, 94, 0.05);
                }
            `}</style>
        </div>
    )
}

