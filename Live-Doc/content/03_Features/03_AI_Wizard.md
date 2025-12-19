# AI Wizard

## O que e o AI Wizard?

O AI Wizard e um assistente inteligente que analisa seu projeto e recomenda a melhor configuracao de GPU, economizando tempo e dinheiro.

---

## Como Usar

### Passo 1: Descreva seu Projeto
Clique em **"AI Wizard"** e descreva o que voce quer fazer:

**Exemplos:**
- "Quero treinar um modelo LLaMA 7B com dataset de 10GB"
- "Preciso rodar inferencia de Stable Diffusion para 1000 imagens"
- "Vou fazer fine-tuning de BERT para classificacao de texto"

### Passo 2: Revise a Recomendacao
O wizard analisa e sugere:
- **GPU recomendada** (ex: RTX 4090)
- **VRAM necessaria** (ex: 24GB)
- **Tempo estimado** (ex: 4 horas)
- **Custo estimado** (ex: $1.60)

### Passo 3: Aceite ou Ajuste
- Clique em **"Lancar"** para aceitar
- Ou ajuste manualmente se preferir

---

## Tipos de Analise

### Treinamento de Modelos
```
Input: "Treinar ResNet-50 com ImageNet"

Output:
- GPU: RTX 3090 (24GB VRAM)
- Batch Size Recomendado: 128
- Tempo Estimado: 12 horas
- Custo: $3.60
- Dica: Use mixed precision (FP16) para 2x mais velocidade
```

### Inferencia
```
Input: "Inferencia LLaMA 70B para chatbot"

Output:
- GPU: 2x A100 80GB (precisa de 140GB VRAM)
- Tokens/segundo: ~50
- Custo: $4.80/hora
- Alternativa: LLaMA 13B em 1x RTX 4090 por $0.40/h
```

### Fine-tuning
```
Input: "Fine-tune GPT-2 com meu dataset de 1GB"

Output:
- GPU: RTX 4090 (24GB VRAM)
- Metodo: LoRA (economia de VRAM)
- Tempo: 2 horas
- Custo: $0.80
```

---

## Perguntas de Follow-up

O wizard pode fazer perguntas para refinar a recomendacao:

### Exemplo de Dialogo
```
Voce: "Quero treinar um modelo de linguagem"

Wizard: "Qual o tamanho do modelo?"
- [ ] Pequeno (<1B parametros)
- [ ] Medio (1-10B parametros)
- [ ] Grande (10-70B parametros)
- [ ] Muito grande (>70B parametros)

Voce: "Medio"

Wizard: "Qual seu orcamento?"
- [ ] Menor custo possivel
- [ ] Balanceado
- [ ] Maxima performance

Voce: "Balanceado"

Wizard: "Recomendo RTX 4090 por $0.40/h..."
```

---

## Otimizacoes Sugeridas

O wizard tambem sugere otimizacoes:

### Para Treinamento
- **Mixed Precision (FP16)**: 2x mais rapido
- **Gradient Checkpointing**: Menos VRAM
- **Data Loading**: Num workers ideal

### Para Inferencia
- **Quantizacao (INT8/INT4)**: 4x menos VRAM
- **Batching**: Maior throughput
- **KV Cache**: Menos recomputacao

### Para Fine-tuning
- **LoRA/QLoRA**: 90% menos VRAM
- **PEFT**: Fine-tune apenas algumas camadas
- **Gradient Accumulation**: Simula batch maior

---

## Historico de Recomendacoes

Veja suas recomendacoes anteriores:

1. Va em **AI Wizard** > **Historico**
2. Clique em qualquer recomendacao anterior
3. Opcoes:
   - **Repetir**: Lancar mesma config
   - **Editar**: Ajustar e relancar
   - **Deletar**: Remover do historico

---

## Limitacoes

O AI Wizard e uma ferramenta de auxilio, nao substituindo:
- Benchmarks reais do seu workload
- Otimizacoes especificas do seu codigo
- Conhecimento de domain experts

**Dica**: Use a recomendacao como ponto de partida e ajuste conforme necessario.
