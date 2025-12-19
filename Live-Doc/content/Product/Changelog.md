# 📝 Changelog - Dumont Cloud

## v3.1 (2025-12-19) - "Artesão de Nuvens"

### ✨ New Features
- **Live Documentation CMS**: Sistema dinâmico baseado em arquivos Markdown
- **Mapeamento de Regiões v2**: IP Geolocation para latência <5ms
- **Telemetria Prometheus**: 15+ métricas exportadas
- **Dashboard API**: Endpoints dedicados para economia

### 🚀 Improvements
- Auto-hibernação agora detecta ócio em 3min (antes: 10min)
- Snapshot speed aumentou 31x (s5cmd vs s3cmd)
- Failover reduzido para <5s (antes: 15s)

### 🐛 Bug Fixes
- Corrigido crash ao criar snapshot >500GB
- Resolvido race condition no failover múltiplo
- Corrigido vazamento de memória no sync engine

---

## v3.0 (2025-11-15) - "Zero Data Loss"

### ✨ New Features
- **Failover Automático**: GPU Spot → CPU Standby em caso de interrupção
- **Snapshots LZ4**: Compressão 4x mais rápida que gzip
- **Auto-Hibernação**: Detecta GPU ociosa e hiberna automaticamente

### 📊 Metrics
- ROI: 1,650%
- Economia anual: $30,246
- Payback: <3 dias

---

## v2.5 (2025-10-01) - "Hybrid Cloud"

### ✨ New Features
- Integração GCP para backup
- Engine de sincronização em tempo real (lsyncd)
- Restic para deduplicação de snapshots

### 🚀 Improvements
- Suporte a 50+ tipos de GPU
- API RESTful completa (Swagger docs)

---

## v2.0 (2025-08-20) - "Vast Integration"

### ✨ New Features
- Integração com Vast.ai Spot Market
- Dashboard React com Vite
- PostgreSQL como database principal

---

## v1.0 (2025-06-10) - "MVP"

### ✨ Initial Release
- Criação básica de instâncias GPU
- Terminal SSH integrado
- Faturamento por hora

---

**Releases Completos**: https://github.com/dumont-cloud/releases  
**Notas de Migração**: https://docs.dumontcloud.com/migrations
