# 🔄 Component Migration Plan - Dumont UI

> **Data**: 2025-12-19
> **Objetivo**: Padronizar frontend usando Design System Dumont UI
> **Status**: ✅ COMPLETO - Todas as fases implementadas

---

## 📊 Estado Atual do Frontend

### Páginas Analisadas (8 principais)

| Página | Tipo | Componentes Não Padronizados | Prioridade |
|--------|------|------------------------------|-----------|
| **Dashboard.jsx** | Principal | StatCard (local), TierCard, OfferCard | 🔴 ALTA |
| **Machines.jsx** | Principal | MachineCard (local), status-badge CSS | 🔴 ALTA |
| **GPUMetrics.jsx** | Secundária | Badges inline, Cards customizados | 🟡 MÉDIA |
| **Settings.jsx** | Config | ValidationIndicator (local) | 🟡 MÉDIA |
| **LandingPage.jsx** | Pública | FeatureCard, PricingCard (design custom) | 🟢 BAIXA |
| **MetricsHub.jsx** | Wrapper | Sem mudanças necessárias | 🟢 BAIXA |
| **Savings.jsx** | Wrapper | Sem mudanças necessárias | 🟢 BAIXA |
| **AdvisorPage.jsx** | Wrapper | Sem mudanças necessárias | 🟢 BAIXA |

---

## 🎯 Problemas Identificados

### 1. **Duplicação de Componentes**

```javascript
// Problema 1: StatCard duplicado em Dashboard
const StatCard = ({ icon, title, value, subtext, color, trend }) => (
  <div className="p-4 rounded-xl border...">...</div>
)
// Solução: Use MetricCard do Dumont UI
```

### 2. **Inconsistência em Status Badges**

```javascript
// Problema 2: Diferentes formas de mostrar status
// Machines.jsx (CSS classes)
<span className={`status-badge ${isRunning ? 'status-badge-online' : 'status-badge-offline'}`}

// GPUMetrics.jsx (inline span)
<span className="text-xs text-green-400">Online</span>

// Solução: Use StatusBadge padronizado
<StatusBadge status="running" />
```

### 3. **Validação Sem Padrão**

```javascript
// Problema 3: ValidationIndicator customizado
function ValidationIndicator({ validation }) {
  return <div className="flex items-center gap-2">
    {validation.valid ? <Check /> : <AlertCircle />}
    <span>{validation.message}</span>
  </div>
}

// Solução: Use AlertInline
<AlertInline variant={validation.valid ? 'success' : 'error'}>
  {validation.message}
</AlertInline>
```

### 4. **Ausência de Tables Padronizadas**

- GPUMetrics não usa Table Dumont para market data
- Machines não tem alternativa de visualização em lista
- Oferta de máquinas mostra cards ao invés de tabela

---

## 📋 Plano de Migração

### **Fase 1: High Priority (Dashboard + Machines)**

#### 1.1 Dashboard.jsx - Substituir StatCard

**Arquivo**: `web/src/pages/Dashboard.jsx`

**Antes**:
```javascript
const StatCard = ({ icon: Icon, title, value, subtext, color, trend }) => (
  <div className={`p-4 rounded-xl border bg-gradient-to-br ${colorClasses[color]}`}>
    <div className="flex items-center justify-between mb-2">
      <Icon className="w-5 h-5 opacity-80" />
      {trend && <span className={`text-xs ${trend > 0 ? 'text-green-400' : 'text-red-400'}`}>
        {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
      </span>}
    </div>
    <div className="text-2xl font-bold text-white mb-1">{value}</div>
    <div className="text-xs text-gray-400">{title}</div>
    {subtext && <div className="text-[10px] text-gray-500 mt-1">{subtext}</div>}
  </div>
)

// Uso (4 instâncias):
<StatCard icon={Server} title="Máquinas Ativas" value={`${activeMachines}/${totalMachines}`} ... />
```

**Depois**:
```javascript
import { MetricCard, MetricsGrid } from '../components/ui/dumont-ui'

// Uso:
<MetricsGrid columns={4}>
  <MetricCard
    icon={Server}
    title="Máquinas Ativas"
    value={`${activeMachines}/${totalMachines}`}
    color="green"
    tooltip="Total de GPUs rodando vs contratadas"
  />
  <MetricCard
    icon={DollarSign}
    title="Custo Diário"
    value={`$${dailyCost}`}
    color="yellow"
  />
  <MetricCard
    icon={Shield}
    title="Economia Mensal"
    value={`$${savings}`}
    color="purple"
    trend={89}
    animate={true}
    comparison="vs AWS: $6,547"
  />
  <MetricCard
    icon={Activity}
    title="Uptime"
    value={`${uptime}%`}
    color="blue"
  />
</MetricsGrid>
```

**Ganho**: -50 linhas de código, melhor manutenibilidade

---

#### 1.2 Machines.jsx - Substituir status badges CSS

**Arquivo**: `web/src/pages/Machines.jsx`

**Antes**:
```javascript
// CSS em index.css
.status-badge { ... }
.status-badge-online { color: #4ade80; ... }
.status-badge-offline { color: #6b7280; ... }

// Uso em MachineCard
<span className={`status-badge ${isRunning ? 'status-badge-online' : 'status-badge-offline'}`}>
  <span className="status-indicator" />
  {isRunning ? 'Online' : 'Offline'}
</span>
```

**Depois**:
```javascript
import { StatusBadge } from '../components/ui/dumont-ui'

// Uso
<StatusBadge status={isRunning ? 'running' : 'stopped'} />
```

**Ganho**: -30 linhas CSS, uso em +5 localidades

---

#### 1.3 Machines.jsx - Substituir modais por ConfirmModal

**Antes**:
```javascript
import { AlertDialog, AlertDialogAction, ... } from '../components/ui/alert-dialog'

<AlertDialog open={deleteOpen}>
  <AlertDialogContent>
    <AlertDialogTitle>Tem certeza?</AlertDialogTitle>
    <AlertDialogDescription>Esta ação não pode ser desfeita.</AlertDialogDescription>
    <AlertDialogCancel>Cancelar</AlertDialogCancel>
    <AlertDialogAction>Deletar</AlertDialogAction>
  </AlertDialogContent>
</AlertDialog>
```

**Depois**:
```javascript
import { ConfirmModal } from '../components/ui/dumont-ui'

<ConfirmModal
  isOpen={deleteOpen}
  onClose={() => setDeleteOpen(false)}
  onConfirm={handleDelete}
  title="Excluir máquina?"
  message="Esta ação não pode ser desfeita."
  variant="danger"
/>
```

**Ganho**: -20 linhas, melhor UX com animação

---

### **Fase 2: Medium Priority (Settings + GPUMetrics)**

#### 2.1 Settings.jsx - Substituir ValidationIndicator

**Arquivo**: `web/src/pages/Settings.jsx`

**Antes**:
```javascript
function ValidationIndicator({ validation }) {
  return (
    <div className={`validation-indicator flex items-center gap-2 text-sm mt-1 ${
      validation.valid ? 'text-green-400' : 'text-red-400'
    }`}>
      {validation.valid ? <Check size={16} /> : <AlertCircle size={16} />}
      <span>{validation.message}</span>
    </div>
  )
}

// Uso (3+ instâncias)
{validation && <ValidationIndicator validation={validation} />}
```

**Depois**:
```javascript
import { AlertInline } from '../components/ui/dumont-ui'

// Uso
{validation && (
  <AlertInline variant={validation.valid ? 'success' : 'error'}>
    {validation.message}
  </AlertInline>
)}
```

**Ganho**: -25 linhas, melhor integração visual

---

#### 2.2 GPUMetrics.jsx - Adicionar Table para Market Data

**Novo**: Adicionar seção com tabela de GPUs disponíveis

```javascript
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge } from '../components/ui/dumont-ui'

<Table>
  <TableHeader>
    <TableRow hoverable={false}>
      <TableHead>#</TableHead>
      <TableHead>GPU</TableHead>
      <TableHead>Provider</TableHead>
      <TableHead align="right">Preço</TableHead>
      <TableHead align="right">Disponíveis</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {marketData.map((item, idx) => (
      <TableRow key={idx} onClick={() => selectGPU(item)}>
        <TableCell>{idx + 1}</TableCell>
        <TableCell><Badge color="success">{item.gpu_name}</Badge></TableCell>
        <TableCell>{item.provider}</TableCell>
        <TableCell align="right">${item.dph_total}</TableCell>
        <TableCell align="right">{item.available_count}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

**Ganho**: Melhor visualização de dados, interatividade

---

### **Fase 3: Consolidação**

#### 3.1 Criar StatusIndicator Wrapper

**Novo arquivo**: `web/src/components/common/StatusIndicator.jsx`

```javascript
import { StatusBadge } from '../ui/dumont-ui'

/**
 * Consolidado status indicator com múltiplas variantes
 * Garante consistência em todo o app
 */
export const StatusIndicator = ({ status, variant = 'badge' }) => {
  const variants = {
    badge: <StatusBadge status={status} />,
    dot: <div className={`w-2 h-2 rounded-full ${statusDotColors[status]}`} />,
    label: <span className={`text-sm ${statusLabelColors[status]}`}>{statusLabels[status]}</span>,
  }

  return variants[variant]
}

// Cores consolidadas
const statusDotColors = {
  running: 'bg-green-400',
  stopped: 'bg-gray-400',
  hibernating: 'bg-yellow-400',
  error: 'bg-red-400',
}

const statusLabelColors = {
  running: 'text-green-400',
  stopped: 'text-gray-400',
  hibernating: 'text-yellow-400',
  error: 'text-red-400',
}

const statusLabels = {
  running: 'Rodando',
  stopped: 'Parado',
  hibernating: 'Hibernando',
  error: 'Erro',
}
```

**Uso**:
```javascript
// Antes (3 formas diferentes)
<StatusBadge status={status} />
<span className={`text-sm ${statusColor[status]}`}>{label}</span>
<div className={`dot ${dotColor[status]}`} />

// Depois (1 forma)
<StatusIndicator status={status} variant="badge" />
<StatusIndicator status={status} variant="label" />
<StatusIndicator status={status} variant="dot" />
```

---

#### 3.2 Criar ValidationMessage Wrapper

**Novo arquivo**: `web/src/components/common/ValidationMessage.jsx`

```javascript
import { AlertInline } from '../ui/dumont-ui'

export const ValidationMessage = ({ validation, field }) => {
  if (!validation) return null

  return (
    <AlertInline variant={validation.valid ? 'success' : 'error'}>
      {validation.message || `${field} formato inválido`}
    </AlertInline>
  )
}
```

**Uso**:
```javascript
<ValidationMessage validation={validation.vastApiKey} field="Vast.ai API Key" />
```

---

## 📈 Métricas de Sucesso

| Métrica | Atual | Meta | Status |
|---------|-------|------|--------|
| Componentes locais duplicados | 8+ | 0-1 | ⏳ |
| Badges padronizados | 30% | 100% | ⏳ |
| Código CSS duplicado | 50+ classes | 5 classes | ⏳ |
| Reutilização de componentes | 40% | 80% | ⏳ |
| Tempo de dev para novo feature | 4h | 2h | ⏳ |

---

## 🗂️ Arquivos a Modificar

### **Fase 1 (High Priority)**
- [ ] `web/src/pages/Dashboard.jsx` - Remove StatCard, usa MetricCard
- [ ] `web/src/pages/Machines.jsx` - Remove status CSS, usa StatusBadge
- [ ] `web/src/styles/index.css` - Remove .status-badge* classes

### **Fase 2 (Medium Priority)**
- [ ] `web/src/pages/Settings.jsx` - Remove ValidationIndicator
- [ ] `web/src/pages/GPUMetrics.jsx` - Adiciona Table Dumont
- [ ] `web/src/components/common/StatusIndicator.jsx` (novo)
- [ ] `web/src/components/common/ValidationMessage.jsx` (novo)

### **Fase 3 (Consolidação)**
- [ ] `Live-Doc/content/Product/Component_Guidelines.md` (novo)
- [ ] Documentar padrões de uso

---

## 📅 Estimativa de Esforço

| Fase | Tarefa | Tempo | Bloqueador |
|------|--------|-------|-----------|
| 1 | Dashboard StatCard | 30min | Não |
| 1 | Machines StatusBadge | 30min | Não |
| 1 | Machines ConfirmModal | 20min | Não |
| 2 | Settings ValidationIndicator | 20min | Não |
| 2 | GPUMetrics Table | 30min | Não |
| 3 | StatusIndicator wrapper | 20min | Não |
| 3 | ValidationMessage wrapper | 15min | Não |
| 3 | Documentação | 30min | Não |
| 🎯 | **TOTAL** | **~3h** | - |

---

## ✅ Checklist de Implementação

### Fase 1 - COMPLETO ✅
- [x] Dashboard: Remover StatCard, adicionar MetricCard + MetricsGrid
- [x] Dashboard: Testar animações de economia
- [x] Dashboard: Testar tooltips
- [x] Machines: Remover CSS status-badge classes
- [x] Machines: Substituir por StatusBadge
- [x] Machines: Substituir AlertDialog por ConfirmModal
- [x] Machines: Testar em mobile
- [x] Build e verificar tamanho ✅ 189.02 KB CSS | 1,080.03 KB JS

### Fase 2 - COMPLETO ✅
- [x] Settings: Remover ValidationIndicator
- [x] Settings: Adicionar AlertInline
- [x] Settings: Testar validações
- [x] GPUMetrics: Adicionar Table com market data
- [x] GPUMetrics: Adicionar clique em linha para selecionar
- [x] GPUMetrics: Tabelas providers também convertidas

### Fase 3 - COMPLETO ✅
- [x] Criar StatusIndicator.jsx
- [x] Criar ValidationMessage.jsx
- [x] Documentar em Component_Guidelines.md
- [x] Code review (internamente validado)
- [x] Pronto para merge e deploy

---

## 🚀 Próximos Passos

1. **Começar com Fase 1** (Dashboard + Machines)
2. **Executar testes E2E** após cada mudança
3. **Coletar feedback** de UX/Design
4. **Iterar se necessário** antes da Fase 2
5. **Consolidar** ao final com wrappers e documentação

---

**Criado**: 2025-12-19
**Responsável**: Frontend Team
**Status**: ✅ IMPLEMENTADO - 19/12/2025
